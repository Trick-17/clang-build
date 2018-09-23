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
from .dependency_tools import find_non_existent_dependencies as _find_non_existent_dependencies,\
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
    parser.add_argument('-p', '--progress',
                        help='activates a progress bar output',
                        action='store_true')
    parser.add_argument('-d', '--directory',
                        type=_Path,
                        help='set the root source directory')
    parser.add_argument('-b', '--build-type',
                        choices=list(_BuildType),
                        type=_BuildType,
                        default=_BuildType.Default,
                        help='set the build type for this project')
    parser.add_argument('-a', '--all',
                        help='build every target, irrespective of whether any root target depends on it',
                        action='store_true')
    parser.add_argument('-t', '--targets',
                        type=str,
                        default="",
                        help='only these targets and their dependencies should be built (comma-separated list)')
    parser.add_argument('-f', '--force-rebuild',
                        help='whether the targets should be rebuilt',
                        action='store_true')
    parser.add_argument('-j', '--jobs',
                        type=int,
                        default=1,
                        help='set the number of concurrent build jobs')
    parser.add_argument('--debug',
                        help='activates additional debug output, overrides verbosity option.',
                        action='store_true')
    parser.add_argument('--no-graph',
                        help='deactivates output of a dependency graph dotfile',
                        action='store_true')
    return parser.parse_args(args=args)


def _find_clang(logger):
    clang = _which('clang')
    clangpp = _which('clang++')
    clang_ar = _which('llvm-ar')
    if clangpp:
        llvm_root = _Path(clangpp).parents[0]
    else:
        error_message = 'Couldn\'t find clang++ executable'
        logger.error(error_message)
        raise RuntimeError(error_message)
    if not clang_ar:
        error_message = 'Couldn\'t find llvm-ar executable'
        logger.error(error_message)
        raise RuntimeError(error_message)
    if not clang:
        error_message = 'Couldn\'t find clang executable'
        logger.error(error_message)
        raise RuntimeError(error_message)

    logger.info(f'llvm root directory: {llvm_root}')
    logger.info(f'clang executable:    {clang}')
    logger.info(f'clang++ executable:  {clangpp}')
    logger.info(f'llvm-ar executable:  {clang_ar}')
    logger.info(f'Newest supported C++ dialect: {_get_max_supported_compiler_dialect(clangpp)}')

    return clang, clangpp, clang_ar



class _Environment:
    def __init__(self, args):
        # Some defaults
        self.logger    = None
        self.buildType = None
        self.clang     = "clang"
        self.clangpp   = "clang++"
        self.clang_ar  = "llvm-ar"
        # Directory this was called from
        self.calling_directory = _Path().resolve()
        # Working directory is where the project root should be - this is searched for 'clang-build.toml'
        self.working_directory = self.calling_directory

        self.logger = _logging.getLogger(__name__)
        self.logger.info(f'clang-build {__version__}')

        # Check for clang++ executable
        self.clang, self.clangpp, self.clang_ar = _find_clang(self.logger)

        # Working directory
        if args.directory:
            self.working_directory = args.directory.resolve()

        if not self.working_directory.exists():
            error_message = f'ERROR: specified non-existent directory \'{self.working_directory}\''
            self.logger.error(error_message)
            raise RuntimeError(error_message)

        self.logger.info(f'Working directory: \'{self.working_directory}\'')

        # Build type (Default, Release, Debug)
        self.buildType = args.build_type
        self.logger.info(f'Build type: {self.buildType.name}')

        # Whether to build all targets
        self.build_all = True if args.all else False

        # List of targets which should be built
        self.target_list = []
        if args.targets:
            if args.all:
                error_message = f'ERROR: specified target list \'{args.targets}\', but also flag \'--all\''
                self.logger.error(error_message)
                raise RuntimeError(error_message)
            self.target_list = [str(target) for target in args.targets.split(',')]

        # Whether to force a rebuild
        self.force_rebuild = True if args.force_rebuild else False

        # Multiprocessing pool
        self.processpool = _Pool(processes = args.jobs)
        self.logger.info(f'Running up to {args.jobs} concurrent build jobs')

        # Build directory
        self.build_directory = _Path('build')

        # Progress bar
        self.progress_disabled = False if args.progress else True

        # Whether to create a dotfile for graphing dependencies
        self.create_dependency_dotfile = False if args.no_graph else True


def build(args):
    # Create container of environment variables
    environment = _Environment(args)

    with _CategoryProgress(['Configure', 'Compile', 'Link'], environment.progress_disabled) as progress_bar:
        target_list = []
        logger = environment.logger
        processpool = environment.processpool

        # Check for build configuration toml file
        toml_file = _Path(environment.working_directory, 'clang-build.toml')
        if toml_file.exists():
            logger.info(f'Found config file: \'{toml_file}\'')

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
            root_project = _Project(config, environment, multiple_projects, True)

            # Get list of all targets
            target_list += root_project.get_targets(root_project.target_dont_build_list)

            # # Generate list of all targets
            # for project in working_projects:
            #     target_list.append(project.get_targets())

        # Otherwise we try to build it as a simple hello world or mwe project
        else:
            files = _get_sources_and_headers({}, environment.working_directory, environment.build_directory)

            if not files['sourcefiles']:
                error_message = f'Error, no sources and no \'clang-build.toml\' found in folder \'{environment.working_directory}\''
                logger.error(error_message)
                raise RuntimeError(error_message)
            # Create target
            target_list.append(
                _Executable(
                    '',
                    'main',
                    environment.working_directory,
                    environment.build_directory.joinpath(environment.buildType.name.lower()),
                    files['headers'],
                    files['include_directories'],
                    files['sourcefiles'],
                    environment.buildType,
                    environment.clang,
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
            if target.__class__ is not _HeaderOnly:
                if target.unsuccessful_builds:
                    errors[target.full_name] = [source.compile_report for source in target.unsuccessful_builds]
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
            if target.__class__ is not _HeaderOnly:
                if target.unsuccessful_link:
                    errors[target.full_name] = target.link_report
        if errors:
            raise _LinkError('Linking was unsuccessful', errors)

        progress_bar.update()
        logger.info('clang-build finished.')



def _main():
    # Build
    try:
        args = parse_args(sys.argv[1:])

        # Logger verbosity
        if not args.debug:
            if args.verbose:
                _setup_logger(_logging.INFO)
            else:
                # Only file log
                _setup_logger(None)
        else:
            _setup_logger(_logging.DEBUG)

        build(args)

    except _CompileError as compile_error:
        logger = _logging.getLogger(__name__)
        logger.error('Compilation was unsuccessful:')
        for target, errors in compile_error.error_dict.items():
            printout = f'[{target}]: target did not compile. Errors:\n'
            printout += ' '.join(errors)
            logger.error(printout)
    except _LinkError as link_error:
        logger = _logging.getLogger(__name__)
        logger.error('Linking was unsuccessful:')
        for target, errors in link_error.error_dict.items():
            printout = f'[{target}]: target did not link. Errors:\n{errors}'
            logger.error(printout)



if __name__ == '__main__':
    _freeze_support()
    _main()
