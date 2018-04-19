'''
clang-build:
  TODO: module docstring...
'''

import logging as _logging
from pathlib import Path as _Path
import textwrap as _textwrap
import sys
from multiprocessing import Pool as _Pool
from multiprocessing import freeze_support as _freeze_support
import argparse
from shutil import which as _which
import toml
from pbr.version import VersionInfo as _VersionInfo

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

_v = _VersionInfo('clang-build').semantic_version()
__version__ = _v.release_string()
version_info = _v.version_tuple



def _setup_logger(log_level=None):
    logger = _logging.getLogger(__name__)
    logger.setLevel(_logging.DEBUG)

    # create formatter _and add it to the handlers
    formatter = _logging.Formatter('%(message)s')

    # add log file handler
    fh = _logging.FileHandler('clang-build.log', mode='w')
    fh.setLevel(_logging.DEBUG)
    fh.setFormatter(formatter)
    logger.addHandler(fh)

    if log_level is not None:
        ch = _TqdmHandler()
        ch.setLevel(log_level)
        ch.setFormatter(formatter)
        logger.addHandler(ch)




_command_line_description = (
'`clang-build` is a build system to build your C++ projects. It uses the clang '
'compiler/toolchain in the background and python as the build-system\'s scripting '
'language.\n'
'For more information please visit: https://github.com/trick-17/clang-build')

def parse_args(args):
    parser = argparse.ArgumentParser(description=_command_line_description, formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument('-V', '--verbose',
                        help='activate more detailed output',
                        action='store_true')
    parser.add_argument('-p', '--progress', help='activates a progress bar output. is overruled by -V and --debug', action='store_true')
    parser.add_argument('-d', '--directory', type=_Path,
                        help='set the root source directory')
    parser.add_argument('-b', '--build-type', choices=list(_BuildType), type=_BuildType, default=_BuildType.Default,
                        help='set the build type for this project')
    parser.add_argument('-j', '--jobs', type=int, default=1,
                        help='set the number of concurrent build jobs')
    parser.add_argument('--debug', help='activates additional debug output, overrides verbosity option.', action='store_true')
    return parser.parse_args(args=args)


def _find_clang(logger):
    clangpp = _which('clang++')
    clang_ar = _which('llvm-ar')
    if clangpp:
        llvm_root = _Path(clangpp).parents[0]
    else:
        logger.error('Couldn\'t find clang++ executable')
        sys.exit(1)
    if not clang_ar:
        logger.error('Couldn\'t find llvm-ar executable')
        sys.exit(1)

    logger.info(f'llvm root directory: {llvm_root}')
    logger.info(f'clang++ executable: {clangpp}')
    logger.info(f'llvm-ar executable: {clang_ar}')
    logger.info(f'Newest supported C++ dialect: {_get_max_supported_compiler_dialect(clangpp)}')

    return clangpp, clang_ar


def main():
    args = parse_args(sys.argv[1:])

    progress_disabled = True
    # Verbosity
    if not args.debug:
        if args.verbose:
            _setup_logger(_logging.INFO)
        else:
            # Only file log
            _setup_logger(None)
    else:
        _setup_logger(_logging.DEBUG)

    if args.progress:
        progress_disabled = False

    #
    # TODO: create try except around build and deal with it.
    #
    build(args, progress_disabled)

def build(args, progress_disabled=True):
    logger = _logging.getLogger(__name__)
    logger.info(f'clang-build {__version__}')

    messages = ['Configure', 'Compile', 'Link']

    with _CategoryProgress(messages, progress_disabled) as progress_bar:
        # Check for clang++ executable
        clangpp, clang_ar = _find_clang(logger)

        # Directory this was called from
        callingdir = _Path().resolve()

        # Working directory is where the project root should be - this is searched for 'clang-build.toml'
        if args.directory:
            workingdir = args.directory.resolve()
        else:
            workingdir = callingdir

        if not workingdir.exists():
            error_message = f'ERROR: specified non-existent directory [{workingdir}]'
            logger.error(f'ERROR: specified non-existent directory [{workingdir}]')
            raise RuntimeError(f'ERROR: specified non-existent directory [{workingdir}]')


        logger.info(f'Working directory: {workingdir}')

        # Build type (Default, Release, Debug)
        buildType = args.build_type
        logger.info(f'Build type: {buildType.name}')

        # Multiprocessing pool
        processpool = _Pool(processes = args.jobs)
        logger.info(f'Running up to {args.jobs} concurrent build jobs')

        build_directory = _Path('build')
        target_list = []

        # Check for build configuration toml file
        toml_file = _Path(workingdir, 'clang-build.toml')
        if toml_file.exists():
            logger.info('Found config file')
            config = toml.load(str(toml_file))

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
                logger.error(error_message)
                sys.exit(1)

            circular_dependencies = _find_circular_dependencies(config)
            if circular_dependencies:
                error_messages = [f'In {target}: circular dependency -> {dependency}' for\
                                target, dependency in non_existent_dependencies]

                error_message = _textwrap.indent('\n'.join(error_messages), prefix=' '*3)
                logger.error(error_message)
                sys.exit(1)

            target_names = _get_dependency_walk(config)

            for target_name in _IteratorProgress(target_names, progress_disabled, len(target_names)):
                project_node = config[target_name]
                # Directories
                target_build_dir = build_directory if not subbuilddirs else build_directory.joinpath(target_name)
                # Sources
                files = _get_sources_and_headers(project_node, workingdir, target_build_dir)
                # Dependencies
                dependencies = [target_list[target_names.index(name)] for name in project_node.get('dependencies', [])]
                executable_dependencies = [target for target in dependencies if target.__class__ is _Executable]

                if executable_dependencies:
                    logger.error(f'Error: The following targets are linking dependencies but were identified as executables: {executable_dependencies}')


                if 'target_type' in project_node:
                    #
                    # Add an executable
                    #
                    if project_node['target_type'].lower() == 'executable':
                        target_list.append(
                            _Executable(
                                target_name,
                                workingdir,
                                target_build_dir,
                                files['headers'],
                                files['include_directories'],
                                files['sourcefiles'],
                                buildType,
                                clangpp,
                                project_node,
                                dependencies))

                    #
                    # Add a shared library
                    #
                    if project_node['target_type'].lower() == 'shared library':
                        target_list.append(
                            _SharedLibrary(
                                target_name,
                                workingdir,
                                target_build_dir,
                                files['headers'],
                                files['include_directories'],
                                files['sourcefiles'],
                                buildType,
                                clangpp,
                                project_node,
                                dependencies))

                    #
                    # Add a static library
                    #
                    elif project_node['target_type'].lower() == 'static library':
                        target_list.append(
                            _StaticLibrary(
                                target_name,
                                workingdir,
                                target_build_dir,
                                files['headers'],
                                files['include_directories'],
                                files['sourcefiles'],
                                buildType,
                                clangpp,
                                clang_ar,
                                project_node,
                                dependencies))

                    #
                    # Add a header-only
                    #
                    elif project_node['target_type'].lower() == 'header only':
                        if files['sourcefiles']:
                            logger.info(f'Source files found for header-only target {target_name}. You may want to check your build configuration.')
                        target_list.append(
                            _HeaderOnly(
                                target_name,
                                workingdir,
                                target_build_dir,
                                files['headers'],
                                files['include_directories'],
                                buildType,
                                clangpp,
                                project_node,
                                dependencies))

                    else:
                        logger.error(f'ERROR: Unsupported target type: {project_node["target_type"]}')

                # No target specified so must be executable or header only
                else:
                    if not files['sourcefiles']:
                        logger.info(f'No source files found for target {target_name}. Creating header-only target.')
                        target_list.append(
                            _HeaderOnly(
                                target_name,
                                workingdir,
                                target_build_dir,
                                files['headers'],
                                files['include_directories'],
                                buildType,
                                clangpp,
                                project_node,
                                dependencies))
                    else:
                        logger.info(f'{len(files["sourcefiles"])} source files found for target {target_name}. Creating executable target.')
                        target_list.append(
                            _Executable(
                                target_name,
                                workingdir,
                                target_build_dir,
                                files['headers'],
                                files['include_directories'],
                                files['sourcefiles'],
                                buildType,
                                clangpp,
                                project_node,
                                dependencies))


        # Otherwise we try to build it as a simple hello world or mwe project
        else:
            files = _get_sources_and_headers({}, workingdir, build_directory)

            if not files['sourcefiles']:
                error_message = f'Error, no sources and no [clang-build.toml] found in folder: {workingdir}'
                logger.error(error_message)
                raise RuntimeError(error_message)
            # Create target
            target_list.append(
                _Executable(
                    'main',
                    workingdir,
                    build_directory,
                    files['headers'],
                    files['include_directories'],
                    files['sourcefiles'],
                    buildType,
                    clangpp))

        # Build the targets
        progress_bar.update()

        logger.info('Compile')

        for target in _IteratorProgress(target_list, progress_disabled, len(target_list), lambda x: x.name):
            target.compile(processpool, progress_disabled)

        # No parallel linking atm, could be added via
        # https://stackoverflow.com/a/5288547/2305545
        #

        processpool.close()
        processpool.join()

        progress_bar.update()
        logger.info('Link')
        for target in target_list:
            if not target.unsuccesful_builds:
                target.link()
            else:
                logger.error(f'Target {target} did not compile. Errors:\n%s',
                    [f'{file}: {output}' for file, output in zip(
                        [t.name for t in target.unsuccesful_builds],
                        [t.output_messages for t in target.unsuccesful_builds])])
                break

        progress_bar.update()
        logger.info('clang-build finished.')


if __name__ == '__main__':
    _freeze_support()
    main()