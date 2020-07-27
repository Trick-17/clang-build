'''
clang-build:
  TODO: module docstring...
'''

import sys as _sys
import argparse as _argparse
import logging as _logging
from pathlib import Path as _Path
from multiprocessing import freeze_support as _freeze_support

from pbr.version import VersionInfo as _VersionInfo
_v = _VersionInfo('clang-build').semantic_version()
__version__ = _v.release_string()
version_info = _v.version_tuple

from .build_type import BuildType as _BuildType
from .project import Project as _Project
from .progress_bar import CategoryProgress as _CategoryProgress
from .logging_tools import TqdmHandler as _TqdmHandler
from .environment import Environment as _Environment
from .errors import CompileError as _CompileError
from .errors import LinkError as _LinkError
from .errors import BundleError as _BundleError
from .errors import RedistributableError as _RedistributableError

_LOGGER = _logging.getLogger(__name__)

def _setup_logger(log_level=None):
    _LOGGER.setLevel(_logging.DEBUG)

    # create formatter _and add it to the handlers
    formatter = _logging.Formatter('%(message)s')

    # add log file handler
    fh = _logging.FileHandler('clang-build.log', mode='w')
    fh.setLevel(_logging.DEBUG)
    fh.setFormatter(formatter)
    _LOGGER.addHandler(fh)

    if log_level is not None:
        ch = _TqdmHandler()
        ch.setLevel(log_level)
        ch.setFormatter(formatter)
        _LOGGER.addHandler(ch)


def parse_args(args):
    _command_line_description = (
    '`clang-build` is a build system to build your C++ projects. It uses the clang '
    'compiler/toolchain in the background and python as the build-system\'s scripting '
    'language.\n'
    'For more information please visit: https://github.com/trick-17/clang-build')
    parser = _argparse.ArgumentParser(description=_command_line_description, formatter_class=_argparse.ArgumentDefaultsHelpFormatter)
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
                        nargs="+",
                        help='only these targets and their dependencies should be built')
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


def build(args):
    # Create container of environment variables
    environment = _Environment(vars(args))

    categories = ['Configure', 'Compile', 'Link']
    if environment.bundle:
        categories.append('Generate bundle')
    if environment.redistributable:
        categories.append('Generate redistributable')

    with _CategoryProgress(categories, not args.progress) as progress_bar:
        project = _Project.from_directory(args.directory, environment)
        project.build(args.all, args.targets, args.jobs)
        progress_bar.update()

    _LOGGER.info('clang-build finished.')


def _main():
    # Build
    try:
        args = parse_args(_sys.argv[1:])

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
        _LOGGER.error('Compilation was unsuccessful:')
        for target, errors in compile_error.error_dict.items():
            printout = f'[{target}]: target did not compile. Errors:\n'
            printout += ' '.join(errors)
            _LOGGER.error(printout)
    except _LinkError as link_error:
        _LOGGER.error('Linking was unsuccessful:')
        for target, errors in link_error.error_dict.items():
            printout = f'[{target}]: target did not link. Errors:\n{errors}'
            _LOGGER.error(printout)
    except _BundleError as bundle_error:
        _LOGGER.error('Bundling was unsuccessful:')
        for target, errors in bundle_error.error_dict.items():
            printout = f'[{target}]: target could not be bundled. Errors:\n{errors}'
            _LOGGER.error(printout)
    except _RedistributableError as redistributable_error:
        _LOGGER.error('Redistibutable bundling was unsuccessful:')
        for target, errors in redistributable_error.error_dict.items():
            printout = f'[{target}]: target could not be bundled into a redistributable. Errors:\n{errors}'
            _LOGGER.error(printout)


if __name__ == '__main__':
    _freeze_support()
    _main()
