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
                              get_dependency_walk as _get_dependency_walk,\
                              get_dependency_graph as _get_dependency_graph
from .io_tools import get_sources_and_headers as _get_sources_and_headers
from .progress_bar import CategoryProgress as _CategoryProgress,\
                          IteratorProgress as _IteratorProgress
from .logging_stream_handler import TqdmHandler as _TqdmHandler

_LOGGER = _logging.getLogger('clang_build.clang_build')



class Project:
    def __init__(self, config, environment, multiple_projects, is_root_project, parent_name=""):

        self.working_directory = environment.working_directory
        self.is_root_project = is_root_project

        self.name = config.get("name", "")

        if "directory" in config:
            self.working_directory = environment.working_directory.joinpath(config["directory"])
            toml_file = _Path(self.working_directory, 'clang-build.toml')
            if toml_file.exists():
                environment.logger.info(f'Found config file {toml_file}')
                config = toml.load(str(toml_file))
            else:
                error_message = f"Project [[{self.name}]]: could not find project file in directory {self.working_directory}"
                _LOGGER.exception(error_message)
                raise RuntimeError(error_message)

        # Re-fetch name if name not specified previously and config was changed
        if not self.name:
            self.name = config.get("name", "")

        # If this is not the root project, it needs to have a name
        if not is_root_project and not self.name:
            error_message = f"Subproject name was not specified in the parent project [[{parent_name}]], nor it's config file."
            _LOGGER.exception(error_message)
            raise RuntimeError(error_message)

        # Project build directory
        self.build_directory = environment.build_directory
        if multiple_projects:
            self.build_directory = self.build_directory.joinpath(self.name)

        self.external = "url" in config
        if self.external:
            download_directory = self.build_directory.joinpath('external_sources')
            # Check if directory is already present and non-empty
            if download_directory.exists() and _os.listdir(str(download_directory)):
                _LOGGER.info(f'[[{self.name}]]: external project sources found in \'{str(download_directory)}\'')
            # Otherwise we download the sources
            else:
                _LOGGER.info(f'[[{self.name}]]: downloading external project to \'{str(download_directory)}\'')
                download_directory.mkdir(parents=True, exist_ok=True)
                try:
                    _subprocess.run(["git", "clone", config["url"], str(download_directory)], stdout=_subprocess.PIPE, stderr=_subprocess.PIPE, encoding='utf-8')
                except _subprocess.CalledProcessError as e:
                    error_message = f"[[{self.name}]]: error trying to download external project. Message " + e.output
                    _LOGGER.exception(error_message)
                    raise RuntimeError(error_message)
                _LOGGER.info(f'[[{self.name}]]: external project downloaded')
            self.working_directory = download_directory

            if "version" in config:
                version = config["version"]
                try:
                    _subprocess.run(["git", "checkout", version], cwd=download_directory, stdout=_subprocess.PIPE, stderr=_subprocess.PIPE, encoding='utf-8')
                except _subprocess.CalledProcessError as e:
                    error_message = f"[{target_name_full}]: error trying to checkout version \'{version}\' from url \'{url}\'. Message " + e.output
                    _LOGGER.exception(error_message)
                    raise RuntimeError(error_message)

        # Get subset of config which contains targets not associated to any project name
        self.targets_config = {key: val for key, val in config.items() if not key in ["subproject", "name", "url", "version"]}

        # Get subsets of config which define projects
        self.subprojects_config = {key: val for key, val in config.items() if key == "subproject"}

        # An "anonymous" project, i.e. project-less targets, is not allowed together with subprojects
        if self.targets_config and self.subprojects_config:
            if not self.name:
                error_message = f"[[{self.name}]]: the config file specifies one or more projects. In this case it is not allowed to specify targets which do not belong to a project."
                _LOGGER.exception(error_message)
                raise RuntimeError(error_message)

        # Generate subprojects of this project
        self.subprojects = []
        if self.subprojects_config:
            self.subprojects += [Project(config, environment, multiple_projects, False, self.name) for config in self.subprojects_config["subproject"]]
        self.subproject_names = [project.name if project.name else "anonymous" for project in self.subprojects]

        # Use sub-build directories if the project contains multiple targets
        multiple_targets = False
        if len(self.targets_config.items()) > 1:
            multiple_targets = True

        # TODO: document why this is here
        if not self.targets_config:
            return

        # Check this project's targets for circular dependencies
        circular_dependencies = _find_circular_dependencies(self.targets_config)
        if circular_dependencies:
            error_messages = [f'Circular dependency [{target}] -> [{dependency}]' for\
                            target, dependency in circular_dependencies]

            error_message = f"[[{self.name}]]:\n" + _textwrap.indent('\n'.join(error_messages), prefix=' '*3)
            _LOGGER.exception(error_message)
            raise RuntimeError(error_message)

        # Create a structured dict of target and subproject configs for this project to resolve all dependencies
        targets_and_subprojects_config = self.targets_config.copy()
        for project in self.subprojects:
            targets_and_subprojects_config[project.name] = project.targets_config

        non_existent_dependencies = _find_non_existent_dependencies(targets_and_subprojects_config)
        if non_existent_dependencies:
            error_messages = [f'[[{self.name}]].[{target}]: the dependency [{dependency}] does not point to a valid target of this project or it\'s subprojects' for\
                            target, dependency in non_existent_dependencies]

            error_message = f"[[{self.name}]]:\n" + _textwrap.indent('\n'.join(error_messages), prefix=' '*3)
            _LOGGER.exception(error_message)
            raise RuntimeError(error_message)

        # Create a dict of all target configs for this project and its subprojects
        # TODO: this approach has the problem that two subprojects cannot have a target with the same name!
        targets_and_subproject_targets_config = self.targets_config.copy()
        for project in self.subprojects:
            targets_and_subproject_targets_config.update(project.targets_config)

        # Unless all should be built, don't build targets which are not in the root project
        # or a dependency of a target of the root project
        self.target_dont_build_list = []
        if is_root_project and not environment.build_all:

            import networkx as nx
            G = _get_dependency_graph(targets_and_subproject_targets_config)

            # Root targets (i.e. targets of the root project),
            # or the specified projects will be retained
            base_set = set(self.targets_config)
            if environment.target_list:
                _LOGGER.info(f'Only building targets [{"], [".join(environment.target_list)}] out of base set of targets [{"], [".join(base_set)}].')
                for target in self.targets_config:
                    if target not in environment.target_list:
                        base_set -= {target}

            # Descendants will be retained, too
            self.target_dont_build_list = set(targets_and_subproject_targets_config)
            for root_target in base_set:
                self.target_dont_build_list -= {root_target}
                self.target_dont_build_list -= nx.algorithms.dag.descendants(G, root_target)
            self.target_dont_build_list = list(self.target_dont_build_list)

            if self.target_dont_build_list:
                _LOGGER.info(f'Not building target(s) [{"], [".join(self.target_dont_build_list)}].')

        elif is_root_project:
            _LOGGER.info(f'Building all targets!')


        # Create a dotfile of the dependency graph
        if is_root_project and environment.create_dependency_dotfile:
            create_dotfile = False
            try:
                import pydot
                create_dotfile = True
            except:
                _LOGGER.error(f'Could not create dependency dotfile, as pydot is not installed')

            if create_dotfile:
                import networkx as nx
                G = _get_dependency_graph(targets_and_subproject_targets_config)

                # Color the targets which should be built in red
                for d in set(targets_and_subproject_targets_config) - set(self.target_dont_build_list):
                    G.node[d]['color'] = 'red'

                _Path(environment.build_directory).mkdir(parents=True, exist_ok=True)
                nx.drawing.nx_pydot.write_dot(G, str(_Path(environment.build_directory, 'dependencies.dot')))

        # Generate a correctly ordered list of target names
        target_names_ordered = [name for name in _get_dependency_walk(targets_and_subproject_targets_config) if name in self.targets_config]

        # Generate the list of target instances
        self.target_list = []
        for target_name in _IteratorProgress(target_names_ordered, environment.progress_disabled, len(target_names_ordered)):
            target_name_full = f'{self.name}.{target_name}' if self.name else target_name
            target_node = targets_and_subproject_targets_config[target_name]
            # Directories
            target_build_directory = self.build_directory if not multiple_targets else self.build_directory.joinpath(target_name)
            target_root_directory  = self.working_directory

            # If target is marked as external, try to fetch the sources
            ### TODO: external sources should be fetched before any sources are read in, i.e. even before the first target is created
            external = "url" in target_node
            if external:
                url = target_node["url"]
                download_directory = target_build_directory.joinpath('external_sources')
                # Check if directory is already present and non-empty
                if download_directory.exists() and _os.listdir(str(download_directory)):
                    _LOGGER.info(f'[{target_name_full}]: external target sources found in {str(download_directory)}')
                # Otherwise we download the sources
                else:
                    _LOGGER.info(f'[{target_name_full}]: downloading external target to {str(download_directory)}')
                    download_directory.mkdir(parents=True, exist_ok=True)
                    try:
                        _subprocess.run(["git", "clone", url, str(download_directory)], stdout=_subprocess.PIPE, stderr=_subprocess.PIPE, encoding='utf-8')
                    except _subprocess.CalledProcessError as e:
                        error_message = f"[{target_name_full}]: error trying to download external target. " + e.output
                        _LOGGER.exception(error_message)
                        raise RuntimeError(error_message)
                    _LOGGER.info(f'[{target_name_full}]: external target downloaded')
                # self.includeDirectories.append(download_directory)
                target_root_directory = download_directory

                if "version" in target_node:
                    version = target_node["version"]
                    try:
                        _subprocess.run(["git", "checkout", version], cwd=target_root_directory, stdout=_subprocess.PIPE, stderr=_subprocess.PIPE, encoding='utf-8')
                    except _subprocess.CalledProcessError as e:
                        error_message = f"[{target_name_full}]: error trying to checkout version \'{version}\' from url \'{url}\'. Message " + e.output
                        _LOGGER.exception(error_message)
                        raise RuntimeError(error_message)

            # Build directory for obj, bin etc. should be under build type folder, e.g. default
            target_build_directory = target_build_directory.joinpath(environment.buildType.name.lower())

            # Sub-directory, if specified
            if 'directory' in target_node:
                target_root_directory = target_root_directory.joinpath(target_node['directory'])

            # Sources
            files = _get_sources_and_headers(target_node, target_root_directory, target_build_directory)
            # Dependencies
            dependencies = []
            for name in target_node.get('dependencies', []):
                subnames = name.split(".")
                if subnames[0] in self.subproject_names:
                    idx = self.subproject_names.index(subnames[0])
                    # TODO: so far, we are only going one layer deep... this is not enough!
                    #       Also, this should probably be done differently...
                    subproject = self.subprojects[idx]
                    for target in subproject.target_list:
                        if subnames[-1] == target.name:
                            dependencies.append(target)
                            i = len(subnames)
                if name in target_names_ordered:
                    dependencies.append(self.target_list[target_names_ordered.index(name)])

            # Make sure all dependencies are actually libraries
            executable_dependencies = [target for target in dependencies if target.__class__ is _Executable]
            if executable_dependencies:
                exelist = ', '.join([f'[{dep.name}]' for dep in executable_dependencies])
                error_message = f'[[{self.name}]]: ERROR: The following targets are linking dependencies but were identified as executables:\n    {exelist}'
                _LOGGER.exception(error_message)
                raise RuntimeError(error_message)

            # Create specific target if the target type was specified
            if 'target_type' in target_node:
                #
                # Add an executable
                #
                if target_node['target_type'].lower() == 'executable':
                    self.target_list.append(
                        _Executable(
                            self.name,
                            target_name,
                            target_root_directory,
                            target_build_directory,
                            files['headers'],
                            files['include_directories'],
                            files['sourcefiles'],
                            environment.buildType,
                            environment.clang,
                            environment.clangpp,
                            target_node,
                            dependencies,
                            environment.force_rebuild))

                #
                # Add a shared library
                #
                elif target_node['target_type'].lower() == 'shared library':
                    self.target_list.append(
                        _SharedLibrary(
                            self.name,
                            target_name,
                            target_root_directory,
                            target_build_directory,
                            files['headers'],
                            files['include_directories'],
                            files['sourcefiles'],
                            environment.buildType,
                            environment.clang,
                            environment.clangpp,
                            target_node,
                            dependencies,
                            environment.force_rebuild))

                #
                # Add a static library
                #
                elif target_node['target_type'].lower() == 'static library':
                    self.target_list.append(
                        _StaticLibrary(
                            self.name,
                            target_name,
                            target_root_directory,
                            target_build_directory,
                            files['headers'],
                            files['include_directories'],
                            files['sourcefiles'],
                            environment.buildType,
                            environment.clang,
                            environment.clangpp,
                            environment.clang_ar,
                            target_node,
                            dependencies,
                            environment.force_rebuild))

                #
                # Add a header-only
                #
                elif target_node['target_type'].lower() == 'header only':
                    if files['sourcefiles']:
                        environment.logger.info(f'[{target_name_full}]: {len(files["sourcefiles"])} source file(s) found for header-only target. You may want to check your build configuration.')
                    self.target_list.append(
                        _HeaderOnly(
                            self.name,
                            target_name,
                            target_root_directory,
                            target_build_directory,
                            files['headers'],
                            files['include_directories'],
                            environment.buildType,
                            environment.clang,
                            environment.clangpp,
                            target_node,
                            dependencies))

                else:
                    error_message = f'[[{self.name}]]: ERROR: Unsupported target type: "{target_node["target_type"].lower()}"'
                    _LOGGER.exception(error_message)
                    raise RuntimeError(error_message)

            # No target specified so must be executable or header only
            else:
                if not files['sourcefiles']:
                    environment.logger.info(f'[{target_name_full}]: no source files found. Creating header-only target.')
                    self.target_list.append(
                        _HeaderOnly(
                            self.name,
                            target_name,
                            target_root_directory,
                            target_build_directory,
                            files['headers'],
                            files['include_directories'],
                            environment.buildType,
                            environment.clang,
                            environment.clangpp,
                            target_node,
                            dependencies))
                else:
                    environment.logger.info(f'[{target_name_full}]: {len(files["sourcefiles"])} source file(s) found. Creating executable target.')
                    self.target_list.append(
                        _Executable(
                            self.name,
                            target_name,
                            target_root_directory,
                            target_build_directory,
                            files['headers'],
                            files['include_directories'],
                            files['sourcefiles'],
                            environment.buildType,
                            environment.clang,
                            environment.clangpp,
                            target_node,
                            dependencies,
                            environment.force_rebuild))

    def get_targets(self, exclude=[]):
        targetlist = []
        for subproject in self.subprojects:
            targetlist += subproject.get_targets(exclude)
        targetlist += [target for target in self.target_list if target.name not in exclude]
        return targetlist