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
from .project import Project as _Project
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
from .errors import CompileError as _CompileError
from .errors import LinkError as _LinkError

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



class _Environment:
    def __init__(self, args):
        # Some defaults
        self.logger = None
        self.progress_disabled = True
        self.buildType  = None
        self.clangpp  = "clang++"
        self.clang_ar = "llvm-ar"
        # Directory this was called from
        self.callingdir = _Path().resolve()
        # Working directory is where the project root should be - this is searched for 'clang-build.toml'
        self.workingdir = self.callingdir

        # Verbosity
        if not args.debug:
            if args.verbose:
                _setup_logger(_logging.INFO)
            else:
                # Only file log
                _setup_logger(None)
        else:
            _setup_logger(_logging.DEBUG)

        # Progress bar
        if args.progress:
            self.progress_disabled = False

        self.logger = _logging.getLogger(__name__)
        self.logger.info(f'clang-build {__version__}')

        # Check for clang++ executable
        self.clangpp, self.clang_ar = _find_clang(self.logger)

        # Working directory
        if args.directory:
            self.workingdir = args.directory.resolve()

        if not self.workingdir.exists():
            error_message = f'ERROR: specified non-existent directory [{self.workingdir}]'
            self.logger.error(error_message)
            raise RuntimeError(error_message)

        self.logger.info(f'Working directory: {self.workingdir}')

        # Build type (Default, Release, Debug)
        self.buildType = args.build_type
        self.logger.info(f'Build type: {self.buildType.name}')

        # Multiprocessing pool
        self.processpool = _Pool(processes = args.jobs)
        self.logger.info(f'Running up to {args.jobs} concurrent build jobs')

        # Build directory
        self.build_directory = _Path('build')



def main():
    # Build
    try:
        build(parse_args(sys.argv[1:]))
    except _CompileError as compile_error:
        logger = _logging.getLogger(__name__)
        logger.error('Compilation was unsuccessful:')
        for target, errors in compile_error.error_dict.items():
            printout = f'Target {target} did not compile. Errors:'
            for file, output in errors:
                for out in output:
                    row = out['row']
                    column = out['column']
                    messagetype = out['type']
                    message = out['message']
                    printout += f'\n{file}:{row}:{column}: {messagetype}: {message}'
            logger.error(printout)
    except _LinkError as link_error:
        logger = _logging.getLogger(__name__)
        logger.error('Linking was unsuccessful:')
        for target, errors in link_error.error_dict.items():
            printout = f'Target {target} did not link. Errors:\n{errors}'
            logger.error(printout)



def build(args):
    # Create container of environment variables
    environment = _Environment(args)

    with _CategoryProgress(['Configure', 'Compile', 'Link'], environment.progress_disabled) as progress_bar:
        target_list = []
        logger = environment.logger
        processpool = environment.processpool

        # Check for build configuration toml file
        toml_file = _Path(environment.workingdir, 'clang-build.toml')
        if toml_file.exists():
            logger.info('Found config file')

            # Parse config file
            config = toml.load(str(toml_file))

            # Determine if there are multiple projects
            targets_config = {key: val for key, val in config.items() if not key == "subproject" and not key == "name"}
            subprojects_config = {key: val for key, val in config.items() if key == "subproject"}
            multiple_projects = False
            if subprojects_config:
                if targets_config or (len(subprojects_config["subproject"]) > 1):
                    multiple_projects = True

            # Create root project
            project = _Project(config, environment, multiple_projects)

            # Get list of all targets
            target_list += project.get_targets()

            # # Generate list of all targets
            # for project in working_projects:
            #     target_list.append(project.get_targets())

        # Otherwise we try to build it as a simple hello world or mwe project
        else:
            files = _get_sources_and_headers({}, environment.workingdir, environment.build_directory)

            if not files['sourcefiles']:
                error_message = f'Error, no sources and no [clang-build.toml] found in folder: {environment.workingdir}'
                logger.error(error_message)
                raise RuntimeError(error_message)
            # Create target
            target_list.append(
                _Executable(
                    'main',
                    environment.workingdir,
                    environment.build_directory,
                    files['headers'],
                    files['include_directories'],
                    files['sourcefiles'],
                    environment.buildType,
                    environment.clangpp))

        # Build the targets
        progress_bar.update()

        logger.info('Compile')

        for target in _IteratorProgress(target_list, environment.progress_disabled, len(target_list), lambda x: x.name):
            target.compile(environment.processpool, environment.progress_disabled)

        # No parallel linking atm, could be added via
        # https://stackoverflow.com/a/5288547/2305545
        #

        processpool.close()
        processpool.join()

        # Check for compile errors
        errors = {}
        for target in target_list:
            if target.unsuccessful_builds:
                outputs = [(file, output) for file, output in zip(
                        [t.sourceFile for t in target.unsuccessful_builds],
                        [t.depfile_message if t.depfile_failed else t.output_messages for t in target.unsuccessful_builds])]
                errors[target.name] = outputs
        if errors:
            raise _CompileError('Compilation was unsuccessful', errors)

        # Link
        progress_bar.update()
        logger.info('Link')
        for target in target_list:
            target.link()

        # Check for link errors
        errors = {}
        for target in target_list:
            if target.unsuccessful_link:
                errors[target.name] = target.link_report
        if errors:
            raise _LinkError('Linking was unsuccessful', errors)

        progress_bar.update()
        logger.info('clang-build finished.')



if __name__ == '__main__':
    _freeze_support()
    main()