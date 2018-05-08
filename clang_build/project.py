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
    def __init__(self, config, envirionment):
        
        # Use sub-build directories if multiple targets
        subbuilddirs = False
        if len(config.items()) > 1:
            subbuilddirs = True

        # Parse targets from toml file
        non_existent_dependencies = _find_non_existent_dependencies(config)
        if non_existent_dependencies:
            error_messages = [f'In {target}: the dependency {dependency} does not point to a valid target' for\
                            target, dependency in non_existent_dependencies]

            error_message = _textwrap.indent('\n'.join(error_messages), prefix=' '*3)
            envirionment.logger.error(error_message)
            sys.exit(1)

        circular_dependencies = _find_circular_dependencies(config)
        if circular_dependencies:
            error_messages = [f'In {target}: circular dependency -> {dependency}' for\
                            target, dependency in non_existent_dependencies]

            error_message = _textwrap.indent('\n'.join(error_messages), prefix=' '*3)
            envirionment.logger.error(error_message)
            sys.exit(1)


        target_names = _get_dependency_walk(config)

        self.target_list = []

        for target_name in _IteratorProgress(target_names, envirionment.progress_disabled, len(target_names)):
            project_node = config[target_name]
            # Directories
            target_build_dir = envirionment.build_directory if not subbuilddirs else envirionment.build_directory.joinpath(target_name)
            # Sources
            files = _get_sources_and_headers(project_node, envirionment.workingdir, target_build_dir)
            # Dependencies
            dependencies = [self.target_list[target_names.index(name)] for name in project_node.get('dependencies', [])]
            executable_dependencies = [target for target in dependencies if target.__class__ is _Executable]

            if executable_dependencies:
                envirionment.logger.error(f'Error: The following targets are linking dependencies but were identified as executables: {executable_dependencies}')


            if 'target_type' in project_node:
                #
                # Add an executable
                #
                if project_node['target_type'].lower() == 'executable':
                    self.target_list.append(
                        _Executable(
                            target_name,
                            envirionment.workingdir,
                            target_build_dir,
                            files['headers'],
                            files['include_directories'],
                            files['sourcefiles'],
                            envirionment.buildType,
                            envirionment.clangpp,
                            project_node,
                            dependencies))

                #
                # Add a shared library
                #
                if project_node['target_type'].lower() == 'shared library':
                    self.target_list.append(
                        _SharedLibrary(
                            target_name,
                            envirionment.workingdir,
                            target_build_dir,
                            files['headers'],
                            files['include_directories'],
                            files['sourcefiles'],
                            envirionment.buildType,
                            envirionment.clangpp,
                            project_node,
                            dependencies))

                #
                # Add a static library
                #
                elif project_node['target_type'].lower() == 'static library':
                    self.target_list.append(
                        _StaticLibrary(
                            target_name,
                            envirionment.workingdir,
                            target_build_dir,
                            files['headers'],
                            files['include_directories'],
                            files['sourcefiles'],
                            envirionment.buildType,
                            envirionment.clangpp,
                            envirionment.clang_ar,
                            project_node,
                            dependencies))

                #
                # Add a header-only
                #
                elif project_node['target_type'].lower() == 'header only':
                    if files['sourcefiles']:
                        envirionment.logger.info(f'Source files found for header-only target {target_name}. You may want to check your build configuration.')
                    self.target_list.append(
                        _HeaderOnly(
                            target_name,
                            envirionment.workingdir,
                            target_build_dir,
                            files['headers'],
                            files['include_directories'],
                            envirionment.buildType,
                            envirionment.clangpp,
                            project_node,
                            dependencies))

                else:
                    envirionment.logger.error(f'ERROR: Unsupported target type: {project_node["target_type"]}')

            # No target specified so must be executable or header only
            else:
                if not files['sourcefiles']:
                    envirionment.logger.info(f'No source files found for target {target_name}. Creating header-only target.')
                    self.target_list.append(
                        _HeaderOnly(
                            target_name,
                            envirionment.workingdir,
                            target_build_dir,
                            files['headers'],
                            files['include_directories'],
                            envirionment.buildType,
                            envirionment.clangpp,
                            project_node,
                            dependencies))
                else:
                    envirionment.logger.info(f'{len(files["sourcefiles"])} source files found for target {target_name}. Creating executable target.')
                    self.target_list.append(
                        _Executable(
                            target_name,
                            envirionment.workingdir,
                            target_build_dir,
                            files['headers'],
                            files['include_directories'],
                            files['sourcefiles'],
                            envirionment.buildType,
                            envirionment.clangpp,
                            project_node,
                            dependencies))

    def get_targets(self):
        return self.target_list