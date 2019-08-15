'''
Target describes a single build or dependency target with all needed paths and
a list of buildables that comprise it's compile and link steps.
'''

import os as _os
import textwrap as _textwrap
from pathlib import Path as _Path
import subprocess as _subprocess
import logging as _logging

import toml
import networkx as _nx
from .target import Executable as _Executable,\
                    SharedLibrary as _SharedLibrary,\
                    StaticLibrary as _StaticLibrary,\
                    HeaderOnly as _HeaderOnly
from .dependency_tools import find_circular_dependencies as _find_circular_dependencies,\
                              get_dependency_graph as _get_dependency_graph
from .io_tools import get_sources_and_headers as _get_sources_and_headers
from .progress_bar import IteratorProgress as _IteratorProgress

_LOGGER = _logging.getLogger('clang_build.clang_build')


class Project:
    def __init__(self, config, environment, multiple_projects, is_root_project, parent_working_dir="", parent_identifier=""):

        self.working_directory = environment.working_directory
        if parent_working_dir:
            self.working_directory = parent_working_dir

        self.is_root_project = is_root_project

        self.name = config.get("name", "")

        if "directory" in config:
            self.working_directory = self.working_directory.joinpath(config["directory"])
            toml_file = _Path(self.working_directory, 'clang-build.toml')

            if toml_file.exists():
                if self.name:
                    environment.logger.info(f'[[{self.name}]]: found config file \'{toml_file}\'')
                else:
                    environment.logger.info(f'Found config file \'{toml_file}\'')
                config = toml.load(str(toml_file))
            else:
                if self.name:
                    error_message = f"[[{self.name}]]: could not find project file in directory \'{self.working_directory}\'"
                else:
                    error_message = f"Could not find project file in directory \'{self.working_directory}\'"
                error_message += f"\n                         Checked for file \'{toml_file}\'"
                _LOGGER.exception(error_message)
                raise RuntimeError(error_message)

        # Re-fetch name if name not specified previously and config was changed
        if not self.name:
            self.name = config.get("name", "")

        # If this is not the root project, it needs to have a name
        if not is_root_project and not self.name:
            error_message = f"Subproject name was not specified in the parent project [[{parent_identifier}]], nor it's config file."
            _LOGGER.exception(error_message)
            raise RuntimeError(error_message)

        # Unique identifier
        self.identifier = f"{parent_identifier}.{self.name}" if parent_identifier else self.name

        # Project build directory
        self.build_directory = environment.build_directory
        if multiple_projects:
            self.build_directory = self.build_directory.joinpath(self.name)

        url = config.get("url", "")
        if url:
            download_directory = self.build_directory.joinpath('external_sources')
            # Check if directory is already present and non-empty
            if download_directory.exists() and _os.listdir(str(download_directory)):
                _LOGGER.info(f'[[{self.identifier}]]: external project sources found in \'{str(download_directory)}\'')
            # Otherwise we download the sources
            else:
                _LOGGER.info(f'[[{self.identifier}]]: downloading external project to \'{str(download_directory)}\'')
                download_directory.mkdir(parents=True, exist_ok=True)
                try:
                    _subprocess.run(["git", "clone", url, str(download_directory)], stdout=_subprocess.PIPE, stderr=_subprocess.PIPE, encoding='utf-8')
                except _subprocess.CalledProcessError as e:
                    error_message = f"[[{self.identifier}]]: error trying to download external project. Message " + e.output
                    _LOGGER.exception(error_message)
                    raise RuntimeError(error_message)
                _LOGGER.info(f'[[{self.identifier}]]: external project downloaded')
            self.working_directory = download_directory

            if "version" in config:
                version = config["version"]
                try:
                    _subprocess.run(["git", "checkout", version], cwd=download_directory, stdout=_subprocess.PIPE, stderr=_subprocess.PIPE, encoding='utf-8')
                except _subprocess.CalledProcessError as e:
                    error_message = f"[[{self.identifier}]]: error trying to checkout version \'{version}\' from url \'{url}\'. Message " + e.output
                    _LOGGER.exception(error_message)
                    raise RuntimeError(error_message)

        # Get subset of config which contains targets not associated to any project name
        self.targets_config = {key: val for key, val in config.items() if not key in ["subproject", "name", "url", "version"]}

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

            error_message = f"[[{self.identifier}]]:\n" + _textwrap.indent('\n'.join(error_messages), prefix=' '*3)
            _LOGGER.exception(error_message)
            raise RuntimeError(error_message)

        # Get subsets of config which define projects
        self.subprojects_config = {key: val for key, val in config.items() if key == "subproject"}

        # An "anonymous" project, i.e. project-less targets, is not allowed together with subprojects
        if self.targets_config and self.subprojects_config:
            if not self.name:
                error_message = f"[[{parent_identifier}]]: the config file specifies one or more projects. In this case it is not allowed to specify targets which do not belong to a project."
                _LOGGER.exception(error_message)
                raise RuntimeError(error_message)

        # Generate subprojects of this project
        self.subprojects = []
        if self.subprojects_config:
            self.subprojects += [Project(config, environment, multiple_projects, is_root_project=False, parent_working_dir=self.working_directory, parent_identifier=self.identifier) for config in self.subprojects_config["subproject"]]
        self.subproject_names = [project.name if project.name else "anonymous" for project in self.subprojects]

        # Create a structured dict of target and subproject configs for this project to resolve all dependencies
        dependency_graph = _get_dependency_graph(self.identifier, self.targets_config, self.subprojects)

        # Check for dependencies pointing nowhere
        non_existent_dependencies = []
        for target_identifier, dependency_indentifier in dependency_graph.edges():
            if not self.contains_target(dependency_indentifier):
                non_existent_dependencies.append((target_identifier, dependency_indentifier))
        if non_existent_dependencies:
            error_messages = [f'[{target_identifier}]: the dependency [{dependency_indentifier}] does not point to a valid target of this project or it\'s subprojects' for\
                            target_identifier, dependency_indentifier in non_existent_dependencies]

            error_message = f"[[{self.identifier}]]:\n" + _textwrap.indent('\n'.join(error_messages), prefix=' '*3)
            _LOGGER.exception(error_message)
            raise RuntimeError(error_message)

        # Unless all should be built, don't build targets which are not in the root project
        # or a dependency of a target of the root project
        self.target_dont_build_list = []
        if is_root_project and not environment.build_all:
            # Root targets (i.e. targets of the root project),
            # or the specified projects will be retained
            base_set = set(self.targets_config)
            if environment.target_list:
                _LOGGER.info(f'Only building targets [{"], [".join(environment.target_list)}] out of base set of targets [{"], [".join(base_set)}].')
                for target in self.targets_config:
                    if target not in environment.target_list:
                        base_set -= {target}

            # Descendants will be retained, too
            self.target_dont_build_list = set(dependency_graph.nodes())
            for root_name in base_set:
                root_identifier = f'{self.identifier}.{root_name}' if self.identifier else root_name
                self.target_dont_build_list -= {root_identifier}
                self.target_dont_build_list -= _nx.algorithms.dag.descendants(dependency_graph, root_identifier)
            self.target_dont_build_list = list(self.target_dont_build_list)

            if self.target_dont_build_list:
                _LOGGER.info(f'Not building target(s) [{"], [".join(self.target_dont_build_list)}].')

        elif is_root_project:
            _LOGGER.info(f'Building all targets!')
            base_set = set({})

        # Create a dotfile of the dependency graph
        if is_root_project and environment.create_dependency_dotfile:
            create_dotfile = False
            try:
                import pydot
                create_dotfile = True
            except:
                _LOGGER.error(f'Could not create dependency dotfile, as pydot is not installed')

            if create_dotfile:
                # Color the targets which should be built in red
                for root_name in base_set:
                    root_identifier = f'{self.identifier}.{root_name}' if self.identifier else root_name
                    dependency_graph.node[root_identifier]['color'] = 'red'
                    for node in _nx.algorithms.dag.descendants(dependency_graph, root_identifier):
                        dependency_graph.node[node]['color'] = 'red'

                _Path(environment.build_directory).mkdir(parents=True, exist_ok=True)
                _nx.drawing.nx_pydot.write_dot(dependency_graph, str(_Path(environment.build_directory, 'dependencies.dot')))

        # Generate a list of target identifiers of this project
        target_identifiers = [f'{self.identifier}.{target_name}' if self.identifier else target_name for target_name in self.targets_config]
        # Generate a correctly ordered list of target identifiers of this project
        target_identifiers_ordered = [identifier for identifier in list(reversed(list(_nx.topological_sort(dependency_graph)))) if identifier in target_identifiers]

        # Generate the list of target instances
        self.target_list = []
        for target_identifier in _IteratorProgress(target_identifiers_ordered, environment.progress_disabled, len(target_identifiers_ordered)):
            target_name = target_identifier.split(".")[-1]
            target_node = self.targets_config[target_name]
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
                    _LOGGER.info(f'[{target_identifier}]: external target sources found in {str(download_directory)}')
                # Otherwise we download the sources
                else:
                    _LOGGER.info(f'[{target_identifier}]: downloading external target to {str(download_directory)}')
                    download_directory.mkdir(parents=True, exist_ok=True)
                    try:
                        _subprocess.run(["git", "clone", url, str(download_directory)], stdout=_subprocess.PIPE, stderr=_subprocess.PIPE, encoding='utf-8')
                    except _subprocess.CalledProcessError as e:
                        error_message = f"[{target_identifier}]: error trying to download external target. " + e.output
                        _LOGGER.exception(error_message)
                        raise RuntimeError(error_message)
                    _LOGGER.info(f'[{target_identifier}]: external target downloaded')
                # self.includeDirectories.append(download_directory)
                target_root_directory = download_directory

                if "version" in target_node:
                    version = target_node["version"]
                    try:
                        _subprocess.run(["git", "checkout", version], cwd=target_root_directory, stdout=_subprocess.PIPE, stderr=_subprocess.PIPE, encoding='utf-8')
                    except _subprocess.CalledProcessError as e:
                        error_message = f"[{target_identifier}]: error trying to checkout version \'{version}\' from url \'{url}\'. Message " + e.output
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
            dependencies = [self.fetch_from_target_list(dependency_identifier) for dependency_identifier in dependency_graph.successors(target_identifier)]

            # Make sure all dependencies are actually libraries
            executable_dependencies = [target for target in dependencies if target.__class__ is _Executable]
            if executable_dependencies:
                exelist = ', '.join([f'[{dep.name}]' for dep in executable_dependencies])
                error_message = f'[[{self.identifier}]]: ERROR: The following targets are linking dependencies but were identified as executables:\n    {exelist}'
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
                            self.identifier,
                            target_name,
                            target_root_directory,
                            target_build_directory,
                            files['headers'],
                            files['include_directories'],
                            files['include_directories_public'],
                            files['sourcefiles'],
                            environment.buildType,
                            environment.clang,
                            environment.clangpp,
                            target_node,
                            dependencies,
                            environment.force_build))

                #
                # Add a shared library
                #
                elif target_node['target_type'].lower() == 'shared library':
                    self.target_list.append(
                        _SharedLibrary(
                            self.identifier,
                            target_name,
                            target_root_directory,
                            target_build_directory,
                            files['headers'],
                            files['include_directories'],
                            files['include_directories_public'],
                            files['sourcefiles'],
                            environment.buildType,
                            environment.clang,
                            environment.clangpp,
                            target_node,
                            dependencies,
                            environment.force_build))

                #
                # Add a static library
                #
                elif target_node['target_type'].lower() == 'static library':
                    self.target_list.append(
                        _StaticLibrary(
                            self.identifier,
                            target_name,
                            target_root_directory,
                            target_build_directory,
                            files['headers'],
                            files['include_directories'],
                            files['include_directories_public'],
                            files['sourcefiles'],
                            environment.buildType,
                            environment.clang,
                            environment.clangpp,
                            environment.clang_ar,
                            target_node,
                            dependencies,
                            environment.force_build))

                #
                # Add a header-only
                #
                elif target_node['target_type'].lower() == 'header only':
                    if files['sourcefiles']:
                        environment.logger.info(f'[{target_identifier}]: {len(files["sourcefiles"])} source file(s) found for header-only target. You may want to check your build configuration.')
                    self.target_list.append(
                        _HeaderOnly(
                            self.identifier,
                            target_name,
                            target_root_directory,
                            target_build_directory,
                            files['headers'],
                            files['include_directories'],
                            files['include_directories_public'],
                            environment.buildType,
                            environment.clang,
                            environment.clangpp,
                            target_node,
                            dependencies))

                else:
                    error_message = f'[[{self.identifier}]]: ERROR: Unsupported target type: "{target_node["target_type"].lower()}"'
                    _LOGGER.exception(error_message)
                    raise RuntimeError(error_message)

            # No target specified so must be executable or header only
            else:
                if not files['sourcefiles']:
                    environment.logger.info(f'[{target_identifier}]: no source files found. Creating header-only target.')
                    self.target_list.append(
                        _HeaderOnly(
                            self.identifier,
                            target_name,
                            target_root_directory,
                            target_build_directory,
                            files['headers'],
                            files['include_directories'],
                            files['include_directories_public'],
                            environment.buildType,
                            environment.clang,
                            environment.clangpp,
                            target_node,
                            dependencies))
                else:
                    environment.logger.info(f'[{target_identifier}]: {len(files["sourcefiles"])} source file(s) found. Creating executable target.')
                    self.target_list.append(
                        _Executable(
                            self.identifier,
                            target_name,
                            target_root_directory,
                            target_build_directory,
                            files['headers'],
                            files['include_directories'],
                            files['include_directories_public'],
                            files['sourcefiles'],
                            environment.buildType,
                            environment.clang,
                            environment.clangpp,
                            target_node,
                            dependencies,
                            environment.force_build))

    def get_targets(self, exclude=[]):
        targetlist = []
        for subproject in self.subprojects:
            targetlist += subproject.get_targets(exclude)
        targetlist += [target for target in self.target_list if target.identifier not in exclude]
        return targetlist

    def contains_target(self, identifier):
        for target_name in self.targets_config:
            target_identifier = f'{self.identifier}.{target_name}' if self.identifier else target_name
            if target_identifier == identifier:
                return True
        for subproject in self.subprojects:
            return subproject.contains_target(identifier)

    def fetch_from_target_list(self, identifier):
        for target in self.target_list:
            if target.identifier == identifier:
                return target
        for subproject in self.subprojects:
            return subproject.fetch_from_target_list(identifier)