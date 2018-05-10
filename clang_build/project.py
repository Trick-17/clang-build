'''
Target describes a single build or dependency target with all needed paths and
a list of buildables that comprise it's compile and link steps.
'''

import os as _os
import textwrap as _textwrap
import sys
from pathlib import Path as _Path
import subprocess as _subprocess
from multiprocessing import freeze_support as _freeze_support
import logging as _logging

import toml
from .dialect_check import get_max_supported_compiler_dialect as _get_max_supported_compiler_dialect
from .build_type import BuildType as _BuildType
from .target import Executable as _Executable,\
                    SharedLibrary as _SharedLibrary,\
                    StaticLibrary as _StaticLibrary,\
                    HeaderOnly as _HeaderOnly
from .dependency_tools import find_circular_dependencies as _find_circular_dependencies,\
                              find_non_existent_dependencies as _find_non_existent_dependencies,\
                              get_dependency_walk as _get_dependency_walk
from .io_tools import get_sources_and_headers as _get_sources_and_headers
from .progress_bar import CategoryProgress as _CategoryProgress,\
                          IteratorProgress as _IteratorProgress
from .logging_stream_handler import TqdmHandler as _TqdmHandler

_LOGGER = _logging.getLogger('clang_build.clang_build')



class Project:
    def __init__(self, config, environment, multiple_projects):

        self.name = config.get("name", "")

        # print(f"Project {self.name}")

        if "url" in config:
            # TODO: implement "external" projects
            print("external project...")
        if "directory" in config:
            toml_dir  = environment.workingdir.joinpath(config["directory"])
            toml_file = _Path(toml_dir, 'clang-build.toml')
            if toml_file.exists():
                environment.logger.info(f'Found config file {toml_file}')
                config = toml.load(str(toml_file))
            else:
                print(f"Project {self.name}: could not find project file in directory {toml_dir}")

        # Get subset of config which contains targets not associated to any project name
        self.targets_config = {key: val for key, val in config.items() if not key == "subproject" and not key == "name"}

        # Get subsets of config which define projects
        self.subprojects_config = {key: val for key, val in config.items() if key == "subproject"}

        # print("targets:     ", self.targets_config)
        # print("subprojects: ", self.subprojects_config)
        # print("full config: ", config)

        # An "anonymous" project, i.e. project-less targets, is not allowed together with subprojects
        if self.targets_config and self.subprojects_config:
            if not self.name:
                print(f"Project {self.name}: Your config file specified one or more projects. In this case you are not allowed to specify targets which do not belong to a project.")
                environment.logger.error(f"Project {self.name}: Your config file specified one or more projects. In this case you are not allowed to specify targets which do not belong to a project.")
                sys.exit(1)



        # Generate Projects
        subprojects = []
        # if targets_config:
        #     subprojects += [Project(targets_config, environment, multiple_projects)]

        if self.subprojects_config:
            subprojects += [Project(config, environment, multiple_projects) for config in self.subprojects_config["subproject"]]

        self.subprojects = subprojects
        self.subproject_names = [project.name if project.name else "anonymous" for project in subprojects]

        # print(f"subprojects of {self.name}: ", [project.name if project.name else "anonymous" for project in subprojects])


        # Use sub-build directories if the project contains multiple targets
        multiple_targets = False
        if len(self.targets_config.items()) > 1:
            multiple_targets = True

        if not self.targets_config:
            return
        # print("targets config: ", self.targets_config)

        targets_and_subprojects = self.targets_config.copy()
        for project in subprojects:
            targets_and_subprojects[project.name] = project.targets_config

        targets_and_subproject_targets = self.targets_config.copy()
        for project in subprojects:
            targets_and_subproject_targets.update(project.targets_config)

        # Parse targets from toml file
        # print(targets_and_subprojects)
        non_existent_dependencies = _find_non_existent_dependencies(targets_and_subprojects)
        if non_existent_dependencies:
            error_messages = [f'In {target}: the dependency {dependency} does not point to a valid target' for\
                            target, dependency in non_existent_dependencies]

            error_message = _textwrap.indent('\n'.join(error_messages), prefix=' '*3)
            environment.logger.error(error_message)
            # print(f"Project {self.name}: non_existent_dependencies.")
            # print(f"                     ", error_messages)
            sys.exit(1)

        circular_dependencies = _find_circular_dependencies(self.targets_config)
        if circular_dependencies:
            error_messages = [f'In {target}: circular dependency -> {dependency}' for\
                            target, dependency in non_existent_dependencies]

            error_message = _textwrap.indent('\n'.join(error_messages), prefix=' '*3)
            environment.logger.error(error_message)
            print(f"Project {self.name}: circular_dependencies.")
            sys.exit(1)


        target_names_total = _get_dependency_walk(targets_and_subproject_targets)
        target_names_project = []
        for name in target_names_total:
            if name in self.targets_config:
                target_names_project.append(name)
        # print(f"-- Project {self.name}: target names of project and subprojects: ", target_names_total)
        # print(f"-- Project {self.name}: target names of project: ", target_names_project)
        # print(f"-- Project {self.name}: target config: ", targets_and_subproject_targets)

        self.target_list = []

        # Project build directory
        self.build_directory = environment.build_directory
        if multiple_projects:
            self.build_directory = self.build_directory.joinpath(self.name)

        for target_name in _IteratorProgress(target_names_project, environment.progress_disabled, len(target_names_project)):
            # print(f"-- Project {self.name}: target {name}:................")
            target_node = targets_and_subproject_targets[target_name]
            # Directories
            target_build_dir = self.build_directory if not multiple_targets else self.build_directory.joinpath(target_name)
            # Sources
            files = _get_sources_and_headers(target_node, environment.workingdir, target_build_dir)
            # Dependencies
            dependencies = []
            for name in target_node.get('dependencies', []):
                subnames = name.split(".")
                if subnames[0] in self.subproject_names:
                    idx = self.subproject_names.index(subnames[0])
                    # TODO: so far, we are only going one layer deep... this is not enough
                    subproject = self.subprojects[idx]
                    for i in range(1, len(subnames)):
                        subproject = self.subprojects[i-1]
                        for target in subproject.target_list:
                            if subnames[-1] == target.name:
                                dependencies.append(target)
                                i = len(subnames)
                if name in target_names_project:
                    dependencies.append(self.target_list[target_names_project.index(name)])

            executable_dependencies = [target for target in dependencies if target.__class__ is _Executable]

            # print(f"-- Project {self.name}: target {target_name}: dependencies: ", dependencies)

            if executable_dependencies:
                environment.logger.error(f'Error: The following targets are linking dependencies but were identified as executables: {executable_dependencies}')


            if 'target_type' in target_node:
                #
                # Add an executable
                #
                if target_node['target_type'].lower() == 'executable':
                    self.target_list.append(
                        _Executable(
                            target_name,
                            environment.workingdir,
                            target_build_dir,
                            files['headers'],
                            files['include_directories'],
                            files['sourcefiles'],
                            environment.buildType,
                            environment.clangpp,
                            target_node,
                            dependencies))

                #
                # Add a shared library
                #
                if target_node['target_type'].lower() == 'shared library':
                    self.target_list.append(
                        _SharedLibrary(
                            target_name,
                            environment.workingdir,
                            target_build_dir,
                            files['headers'],
                            files['include_directories'],
                            files['sourcefiles'],
                            environment.buildType,
                            environment.clangpp,
                            target_node,
                            dependencies))

                #
                # Add a static library
                #
                elif target_node['target_type'].lower() == 'static library':
                    self.target_list.append(
                        _StaticLibrary(
                            target_name,
                            environment.workingdir,
                            target_build_dir,
                            files['headers'],
                            files['include_directories'],
                            files['sourcefiles'],
                            environment.buildType,
                            environment.clangpp,
                            environment.clang_ar,
                            target_node,
                            dependencies))

                #
                # Add a header-only
                #
                elif target_node['target_type'].lower() == 'header only':
                    if files['sourcefiles']:
                        environment.logger.info(f'Source files found for header-only target {target_name}. You may want to check your build configuration.')
                    self.target_list.append(
                        _HeaderOnly(
                            target_name,
                            environment.workingdir,
                            target_build_dir,
                            files['headers'],
                            files['include_directories'],
                            environment.buildType,
                            environment.clangpp,
                            target_node,
                            dependencies))

                else:
                    environment.logger.error(f'ERROR: Unsupported target type: {target_node["target_type"]}')

            # No target specified so must be executable or header only
            else:
                if not files['sourcefiles']:
                    environment.logger.info(f'No source files found for target {target_name}. Creating header-only target.')
                    self.target_list.append(
                        _HeaderOnly(
                            target_name,
                            environment.workingdir,
                            target_build_dir,
                            files['headers'],
                            files['include_directories'],
                            environment.buildType,
                            environment.clangpp,
                            target_node,
                            dependencies))
                else:
                    environment.logger.info(f'{len(files["sourcefiles"])} source files found for target {target_name}. Creating executable target.')
                    self.target_list.append(
                        _Executable(
                            target_name,
                            environment.workingdir,
                            target_build_dir,
                            files['headers'],
                            files['include_directories'],
                            files['sourcefiles'],
                            environment.buildType,
                            environment.clangpp,
                            target_node,
                            dependencies))

    def get_targets(self):
        targetlist = []
        for subproject in self.subprojects:
            targetlist += subproject.get_targets()
        targetlist += self.target_list
        return targetlist