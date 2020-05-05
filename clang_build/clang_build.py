'''
clang-build:
  TODO: module docstring...
'''

import logging as _logging
from pathlib import Path as _Path
import sys
from multiprocessing import Pool as _Pool
from multiprocessing import freeze_support as _freeze_support
import argparse
import shutil as _shutil
from pbr.version import VersionInfo as _VersionInfo

from .dialect_check import get_max_supported_compiler_dialect as _get_max_supported_compiler_dialect
from .build_type import BuildType as _BuildType
from .project import Project as _Project
from .progress_bar import CategoryProgress as _CategoryProgress
from .logging_tools import TqdmHandler as _TqdmHandler
from .errors import CompileError as _CompileError
from .errors import LinkError as _LinkError
from .errors import BundleError as _BundleError
from .errors import RedistributableError as _RedistributableError

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
    target_group = parser.add_mutually_exclusive_group()
    target_group.add_argument('-a', '--all',
                        help='build every target, irrespective of whether any root target depends on it',
                        action='store_true')
    target_group.add_argument('-t', '--targets',
                        type=str,
                        default="",
                        help='only these targets and their dependencies should be built (comma-separated list)')
    parser.add_argument('-f', '--force-build',
                        help='also build sources which have already been built',
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
    parser.add_argument('--no-recursive-clone',
                        help='deactivates recursive cloning of git submodules',
                        action='store_true')
    parser.add_argument('--bundle',
                        help='automatically gather dependencies into the binary directories of targets',
                        action='store_true')
    parser.add_argument('--redistributable',
                        help='Automatically create redistributable bundles from binary bundles. Implies `--bundle`',
                        action='store_true')
    return parser.parse_args(args=args)


def _find_clang(logger):
    clang    = _shutil.which('clang')
    clangpp  = _shutil.which('clang++')
    clang_ar = _shutil.which('llvm-ar')
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

    return clang, clangpp, clang_ar


class _Environment:
    def __init__(self, args):
        # Some defaults
        self.logger     = None
        self.build_type = None
        self.clang      = "clang"
        self.clangpp    = "clang++"
        self.clang_ar   = "llvm-ar"
        # Directory this was called from
        self.calling_directory = _Path().resolve()
        # Working directory is where the project root should be - this is searched for 'clang-build.toml'
        self.working_directory = self.calling_directory

        self.logger = _logging.getLogger(__name__)
        self.logger.info(f'clang-build {__version__}')

        # Check for clang++ executable
        self.clang, self.clangpp, self.clang_ar = _find_clang(self.logger)

        # Maximum available C++ dialect
        self.max_cpp_dialect = _get_max_supported_compiler_dialect(self.clangpp)
        self.logger.info(f'Newest supported C++ dialect: {self.max_cpp_dialect}')

        # Working directory
        if args.directory:
            self.working_directory = args.directory.resolve()

        if not self.working_directory.exists():
            error_message = f'ERROR: specified non-existent directory \'{self.working_directory}\''
            self.logger.error(error_message)
            raise RuntimeError(error_message)

        self.logger.info(f'Working directory: \'{self.working_directory}\'')

        # Build type (Default, Release, Debug)
        self.build_type = args.build_type
        self.logger.info(f'Build type: {self.build_type.name}')

        # Whether to build all targets
        self.build_all = True if args.all else False
        if self.build_all:
            self.logger.info('Building all targets...')

        # List of targets which should be built
        self.target_list = []
        if args.targets:
            if args.all:
                error_message = f'ERROR: specified target list \'{args.targets}\', but also flag \'--all\''
                self.logger.error(error_message)
                raise RuntimeError(error_message)
            self.target_list = [str(target) for target in args.targets.split(',')]

        # Whether to force a rebuild
        self.force_build = True if args.force_build else False
        if self.force_build:
            self.logger.info('Forcing build...')

        # Multiprocessing pool
        self.processpool = _Pool(processes = args.jobs)
        if args.jobs > 1:
            self.logger.info(f'Running up to {args.jobs} concurrent build jobs')
        else:
            self.logger.info(f'Running 1 build job')

        # Build directory
        self.build_directory = _Path('build')

        # Progress bar
        self.progress_disabled = False if args.progress else True

        # Whether to create a dotfile for graphing dependencies
        self.create_dependency_dotfile = False if args.no_graph else True

        # Whether to recursively clone submodules when cloning with git
        self.clone_recursive = False if args.no_recursive_clone else True

        # Whether to bundle binaries
        self.bundle = True if args.bundle else False
        if self.bundle:
            self.logger.info('Bundling of binary dependencies is activated')

        # Whether to create redistributable bundles
        self.redistributable = True if args.redistributable else False
        if self.redistributable:
            self.bundle = True
            self.logger.info('Redistributable bundling of binary dependencies is activated')


def build(args):
    # Create container of environment variables
    environment = _Environment(args)

    categories = ['Configure', 'Compile', 'Link']
    if environment.bundle:
        categories.append('Generate bundle')
    if environment.redistributable:
        categories.append('Generate redistributable')

    with _CategoryProgress(categories, environment.progress_disabled) as progress_bar:
        logger = environment.logger

        project = _Project(environment.working_directory, environment)

        #TODO: Dot file if requested

        project.build(environment.build_all, environment.target_list)

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
    except _BundleError as bundle_error:
        logger = _logging.getLogger(__name__)
        logger.error('Bundling was unsuccessful:')
        for target, errors in bundle_error.error_dict.items():
            printout = f'[{target}]: target could not be bundled. Errors:\n{errors}'
            logger.error(printout)
    except _RedistributableError as redistributable_error:
        logger = _logging.getLogger(__name__)
        logger.error('Redistibutable bundling was unsuccessful:')
        for target, errors in redistributable_error.error_dict.items():
            printout = f'[{target}]: target could not be bundled into a redistributable. Errors:\n{errors}'
            logger.error(printout)


if __name__ == '__main__':
    _freeze_support()
    _main()
