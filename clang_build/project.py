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
                              get_dependency_graph as _get_dependency_graph,\
                              get_dependency_graph_from_stubs as _get_dependency_graph_from_stubs
from .io_tools import get_sources_and_headers as _get_sources_and_headers
from .progress_bar import IteratorProgress as _IteratorProgress

_LOGGER = _logging.getLogger('clang_build.clang_build')


class Target_Stub:
    def __init__(self,
            environment,
            project_identifier,
            name,
            options,
            is_root_project,
            root_directory,
            build_directory):

        self.environment        = environment
        self.project_identifier = project_identifier
        self.name               = name
        self.options            = options
        self.is_root_project    = is_root_project
        self.root_directory     = root_directory
        self.build_directory    = build_directory

        self.identifier = f"{project_identifier}.{name}" if project_identifier else name
        self.files      = {}
        self.build      = False

        # If target is marked as external, try to fetch the sources
        ### TODO: external sources should be fetched before any sources are read in, i.e. even before the first target is created
        external_sources = "url" in self.options
        if external_sources:
            url = self.options["url"]
            download_directory = self.build_directory.joinpath('external_sources')
            # Check if directory is already present and non-empty
            if download_directory.exists() and _os.listdir(str(download_directory)):
                _LOGGER.info(f'[{self.identifier}]: external target sources found in {str(download_directory)}')
            # Otherwise we download the sources
            else:
                _LOGGER.info(f'[{self.identifier}]: downloading external target to {str(download_directory)}')
                download_directory.mkdir(parents=True, exist_ok=True)
                try:
                    if environment.clone_recursive:
                        _subprocess.run(["git", "clone", "--recurse-submodules", url, str(download_directory)], stdout=_subprocess.PIPE, stderr=_subprocess.PIPE, encoding='utf-8')
                    else:
                        _subprocess.run(["git", "clone", url, str(download_directory)], stdout=_subprocess.PIPE, stderr=_subprocess.PIPE, encoding='utf-8')
                except _subprocess.CalledProcessError as e:
                    error_message = f"[{self.identifier}]: error trying to download external target. " + e.output
                    _LOGGER.exception(error_message)
                    raise RuntimeError(error_message)
                _LOGGER.info(f'[{self.identifier}]: external target downloaded')
            self.root_directory = download_directory

            if "version" in self.options:
                version = self.options["version"]
                try:
                    _subprocess.run(["git", "checkout", version], cwd=root_directory, stdout=_subprocess.PIPE, stderr=_subprocess.PIPE, encoding='utf-8')
                except _subprocess.CalledProcessError as e:
                    error_message = f"[{self.identifier}]: error trying to checkout version \'{version}\' from url \'{url}\'. Message " + e.output
                    _LOGGER.exception(error_message)
                    raise RuntimeError(error_message)

        # Build directory for obj, bin etc. should be under build type folder, e.g. default
        self.build_directory = self.build_directory.joinpath(environment.build_type.name.lower())

        # Sub-directory, if specified
        if 'directory' in self.options:
            self.root_directory = self.root_directory.joinpath(self.options['directory'])

        # Sources
        self.files = _get_sources_and_headers(self.name, self.options, self.root_directory, self.build_directory)

        # Whether this target should be built
        if is_root_project or environment.build_all:
            if self.files["sourcefiles"]:
                self.build = True

        # Determine target type
        self.target_type = ''
        if 'target_type' in options:
            self.target_type = options['target_type'].lower()
        else:
            if not self.files['sourcefiles']:
                environment.logger.info(f'[{self.identifier}]: no source files found. Creating header-only target.')
                self.target_type = 'header only'
            else:
                environment.logger.info(f'[{self.identifier}]: {len(self.files["sourcefiles"])} source file(s) found. Creating executable target.')
                self.target_type = 'executable'

        if self.target_type == 'header only':
            self.build = False

        ### TODO: determine from CLI target lists etc., if this target should be built

        # Discover tests
        self.build_tests = False
        self.tests_options = {}
        self.tests_folder = self.root_directory
        self.tests_files = {}
        if environment.tests:
            if self.root_directory.joinpath('test').exists():
                self.tests_folder = self.root_directory.joinpath('test')
            elif self.root_directory.joinpath('tests').exists():
                self.tests_folder = self.root_directory.joinpath('tests')

            self.tests_options = self.options.get("tests", {})

            if self.tests_folder:
                _LOGGER.info(f'[{self.identifier}]: found tests folder {str(self.tests_folder)}')
            # If there is no tests folder, but sources were specified, the root directory is used
            elif "sources" in self.tests_options:
                self.tests_folder = self.root_directory

            # TODO: tests_folder should potentially be parsed from the tests_options
            self.tests_files = _get_sources_and_headers("tests", self.tests_options, self.tests_folder, self.build_directory.joinpath("tests"))

            if self.tests_files['sourcefiles']:
                self.build_tests = True

        # Discover examples
        self.build_examples = False
        self.examples_options = {}
        self.examples_folder = self.root_directory
        self.examples_files = {}
        if environment.examples:
            if self.root_directory.joinpath('example').exists():
                self.examples_folder = self.root_directory.joinpath('example')
            elif self.root_directory.joinpath('examples').exists():
                self.examples_folder = self.root_directory.joinpath('examples')

            self.examples_options = self.options.get("examples", {})

            if self.examples_folder:
                _LOGGER.info(f'[{self.identifier}]: found examples folder {str(self.examples_folder)}')
            # If there is no examples folder, but sources were specified, the root directory is used
            elif "sources" in self.examples_options:
                self.examples_folder = self.root_directory

            # TODO: examples_folder should potentially be parsed from the examples_options
            self.examples_files = _get_sources_and_headers("examples", self.examples_options, self.examples_folder, self.build_directory.joinpath("examples"))

            if self.examples_files['sourcefiles']:
                self.build_examples = True


class Project:
    def __init__(self,
            environment,
            config,
            multiple_projects,
            is_root_project,
            parent_working_dir="",
            parent_identifier=""):

        self.environment = environment
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

        self.subprojects = []
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
                    if environment.clone_recursive:
                        _subprocess.run(["git", "clone", "--recurse-submodules", url, str(download_directory)], stdout=_subprocess.PIPE, stderr=_subprocess.PIPE, encoding='utf-8')
                    else:
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
        self.targets_config = {key: val for key, val in config.items() if key not in ["subproject", "name", "url", "version"]}

        # Use sub-build directories if the project contains multiple targets
        multiple_targets = False
        if len(self.targets_config.items()) > 1:
            multiple_targets = True

        # TODO: document why this is here
        if not self.targets_config:
            return

        # Check this project's targets for circular dependencies
        circular_dependencies = _find_circular_dependencies(self.targets_config)
        error_messages = []
        if circular_dependencies:
            for circle in circular_dependencies:
                message = f'Circular dependency: ... -> [{circle[0]}]'
                for target in circle[1:]:
                    message += f' -> [{target}]'
                message += f' -> ...'
                error_messages.append(message)

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
        if self.subprojects_config:
            self.subprojects += [Project(environment, config, multiple_projects, is_root_project=False, parent_working_dir=self.working_directory, parent_identifier=self.identifier) for config in self.subprojects_config["subproject"]]
        self.subproject_names = [project.name if project.name else "anonymous" for project in self.subprojects]

        # Create target stubs for infos about
        # - target types
        # - dependency lists
        # - tests and examples
        self.target_stubs = []
        for target_name, target_config in self.targets_config.items():
            self.target_stubs.append(
                Target_Stub(
                    environment         = environment,
                    project_identifier  = self.identifier,
                    name                = target_name,
                    options             = target_config,
                    is_root_project     = is_root_project,
                    root_directory      = self.working_directory,
                    build_directory     = self.build_directory if not multiple_targets else self.build_directory.joinpath(target_name)))

        # Create a structured dict of target and subproject configs for this project to resolve all dependencies
        dependency_graph = _get_dependency_graph_from_stubs(self.environment, self.identifier, self.target_stubs, self.subprojects)

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
                for stub in self.target_stubs:
                    if stub.build:
                        dependency_graph.node[stub.identifier]['color'] = 'red'
                        if stub.build_tests:
                            dependency_graph.node[f"{stub.identifier}.tests"]['color'] = 'red'
                        if stub.build_examples:
                            dependency_graph.node[f"{stub.identifier}.examples"]['color'] = 'red'

                        for node in _nx.algorithms.dag.descendants(dependency_graph, stub.identifier):
                            dependency_graph.node[node]['color'] = 'red'

                # Write the file
                _Path(environment.build_directory).mkdir(parents=True, exist_ok=True)
                _nx.drawing.nx_pydot.write_dot(dependency_graph, str(_Path(environment.build_directory, 'dependencies.dot')))

                ### TODO: per-project subgraphs?

        # Check for dependencies pointing nowhere
        non_existent_dependencies = []
        for target_identifier, dependency_indentifier in dependency_graph.edges():
            if not self.contains_target(dependency_indentifier):
                non_existent_dependencies.append((target_identifier, dependency_indentifier))
        if non_existent_dependencies:
            error_messages = [f'[{target_identifier}]: the dependency [{dependency_indentifier}] does not point to a valid target of this project or its subprojects' for\
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
                        base_set.discard(target)

            # Descendants will be retained, too
            self.target_dont_build_list = set(dependency_graph.nodes())
            for root_name in base_set:
                root_identifier = f'{self.identifier}.{root_name}' if self.identifier else root_name
                self.target_dont_build_list.discard(root_identifier)
                self.target_dont_build_list -= _nx.algorithms.dag.descendants(dependency_graph, root_identifier)
            self.target_dont_build_list = list(self.target_dont_build_list)

            if self.target_dont_build_list:
                _LOGGER.info(f'Not building target(s) [{"], [".join(self.target_dont_build_list)}].')

        elif is_root_project:
            _LOGGER.info(f'Building all targets!')

        # Generate a list of target identifiers of this project
        target_identifiers = [stub.identifier for stub in self.target_stubs]

        # Generate a correctly ordered list of target identifiers of this project
        target_identifiers_ordered = [identifier for identifier in list(reversed(list(_nx.topological_sort(dependency_graph)))) if identifier in target_identifiers]

        # Generate the list of target instances
        self.target_list = []
        for target_identifier in _IteratorProgress(target_identifiers_ordered, environment.progress_disabled, len(target_identifiers_ordered)):
            # Dependencies
            target_dependencies = [self.fetch_from_target_list(dependency_identifier) for dependency_identifier in dependency_graph.successors(target_identifier)]

            # Make sure all dependencies are actually libraries
            executable_dependencies = [target for target in target_dependencies if target.__class__ is _Executable]
            if executable_dependencies:
                exelist = ', '.join([f'[{dep.name}]' for dep in executable_dependencies])
                error_message = f'[[{self.identifier}]]: ERROR: The following targets are linking dependencies but were identified as executables:\n    {exelist}'
                _LOGGER.exception(error_message)
                raise RuntimeError(error_message)

            target_stub = None
            for stub in self.target_stubs:
                if stub.identifier == target_identifier: target_stub = stub

            #
            # Add an executable
            #
            if target_stub.target_type == 'executable':
                self.target_list.append(
                    _Executable(
                        environment                 = environment,
                        project_identifier          = self.identifier,
                        name                        = target_stub.name,
                        root_directory              = target_stub.root_directory,
                        build_directory             = target_stub.build_directory,
                        headers                     = target_stub.files['headers'],
                        include_directories_private = target_stub.files['include_directories'],
                        include_directories_public  = target_stub.files['include_directories_public'],
                        source_files                = target_stub.files['sourcefiles'],
                        options                     = target_stub.options,
                        dependencies                = target_dependencies))

            #
            # Add a shared library
            #
            elif target_stub.target_type == 'shared library':
                self.target_list.append(
                    _SharedLibrary(
                        environment                 = environment,
                        project_identifier          = self.identifier,
                        name                        = target_stub.name,
                        root_directory              = target_stub.root_directory,
                        build_directory             = target_stub.build_directory,
                        headers                     = target_stub.files['headers'],
                        include_directories_private = target_stub.files['include_directories'],
                        include_directories_public  = target_stub.files['include_directories_public'],
                        source_files                = target_stub.files['sourcefiles'],
                        options                     = target_stub.options,
                        dependencies                = target_dependencies))

            #
            # Add a static library
            #
            elif target_stub.target_type == 'static library':
                self.target_list.append(
                    _StaticLibrary(
                        environment                 = environment,
                        project_identifier          = self.identifier,
                        name                        = target_stub.name,
                        root_directory              = target_stub.root_directory,
                        build_directory             = target_stub.build_directory,
                        headers                     = target_stub.files['headers'],
                        include_directories_private = target_stub.files['include_directories'],
                        include_directories_public  = target_stub.files['include_directories_public'],
                        source_files                = target_stub.files['sourcefiles'],
                        options                     = target_stub.options,
                        dependencies                = target_dependencies))

            #
            # Add a header-only
            #
            elif target_stub.target_type == 'header only':
                if target_stub.files['sourcefiles']:
                    environment.logger.info(
                        f'[{target_stub.identifier}]: {len(target_stub.files["sourcefiles"])} source file(s) found for header-only target. You may want to check your build configuration.')
                self.target_list.append(
                    _HeaderOnly(
                        environment                 = environment,
                        project_identifier          = self.identifier,
                        name                        = target_stub.name,
                        root_directory              = target_stub.root_directory,
                        build_directory             = target_stub.build_directory,
                        headers                     = target_stub.files['headers'],
                        include_directories_private = target_stub.files['include_directories'],
                        include_directories_public  = target_stub.files['include_directories_public'],
                        options                     = target_stub.options,
                        dependencies                = target_dependencies))

            else:
                error_message = f'[[{self.identifier}]]: ERROR: Unsupported target type: "{target_stub.target_type}"'
                _LOGGER.exception(error_message)
                raise RuntimeError(error_message)

        #
        # Add tests and examples for libraries
        #
        for target_identifier in _IteratorProgress(target_identifiers_ordered, environment.progress_disabled, len(target_identifiers_ordered)):

            target_stub = None
            for stub in self.target_stubs:
                if stub.identifier == target_identifier: target_stub = stub

            if target_stub.target_type == 'shared library' or target_stub.target_type == 'static library' or target_stub.target_type == 'header only':
                if target_stub.build_tests:
                    target_tests_identifier = f'{target_identifier}.tests'

                    target_tests_dependencies = [self.fetch_from_target_list(dependency_identifier)
                        for dependency_identifier in dependency_graph.successors(target_tests_identifier)]

                    single_executable = True
                    if target_stub.tests_options:
                        single_executable = target_stub.tests_options.get("single_executable", True)

                    # Add the tests themselves
                    if single_executable:
                        self.target_list.append(_Executable(
                            environment                 = self.environment,
                            project_identifier          = self.identifier,
                            name                        = f"{target_stub.name}_test",
                            root_directory              = target_stub.tests_folder,
                            build_directory             = target_stub.build_directory.joinpath("tests"),
                            headers                     = target_stub.tests_files['headers'],
                            include_directories_private = target_stub.tests_files['include_directories'],
                            include_directories_public  = target_stub.tests_files['include_directories_public'],
                            source_files                = target_stub.tests_files['sourcefiles'],
                            dependencies                = target_tests_dependencies,
                            options                     = target_stub.tests_options))
                    else:
                        for sourcefile in target_stub.tests_files['sourcefiles']:
                            self.target_list.append(_Executable(
                                environment                 = self.environment,
                                project_identifier          = self.identifier,
                                name                        = f"{target_stub.name}_test_{sourcefile.stem}",
                                root_directory              = target_stub.tests_folder,
                                build_directory             = target_stub.build_directory.joinpath("tests"),
                                headers                     = target_stub.tests_files['headers'],
                                include_directories_private = target_stub.tests_files['include_directories'],
                                include_directories_public  = target_stub.tests_files['include_directories_public'],
                                source_files                = [sourcefile],
                                dependencies                = target_tests_dependencies,
                                options                     = target_stub.tests_options))

                if target_stub.build_examples:
                    target_examples_identifier = f'{target_identifier}.examples'

                    target_examples_dependencies = [self.fetch_from_target_list(dependency_identifier)
                        for dependency_identifier in dependency_graph.successors(target_examples_identifier)]

                    for sourcefile in target_stub.examples_files['sourcefiles']:
                        self.target_list.append(_Executable(
                            environment                 = self.environment,
                            project_identifier          = self.identifier,
                            name                        = f"{target_stub.name}_example_{sourcefile.stem}",
                            root_directory              = target_stub.examples_folder,
                            build_directory             = target_stub.build_directory.joinpath("examples"),
                            headers                     = target_stub.examples_files['headers'],
                            include_directories_private = target_stub.examples_files['include_directories'],
                            include_directories_public  = target_stub.examples_files['include_directories_public'],
                            source_files                = [sourcefile],
                            dependencies                = target_examples_dependencies,
                            options                     = target_stub.examples_options))

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