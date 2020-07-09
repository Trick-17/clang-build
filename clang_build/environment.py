'''
This module contains the `Environment` class.
'''

import logging as _logging
import shutil as _shutil
from pathlib import Path as _Path
from multiprocessing import Pool as _Pool

from .clang_build import __version__
from .dialect_check import get_max_supported_compiler_dialect as _get_max_supported_compiler_dialect
from .platform import PLATFORM_PYTHON_INCLUDE_PATH, PLATFORM_PYTHON_LIBRARY_PATH


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
    logger.info(f'Python headers in:   {PLATFORM_PYTHON_INCLUDE_PATH}')
    logger.info(f'Python library in:   {PLATFORM_PYTHON_LIBRARY_PATH}')

    return clang, clangpp, clang_ar


class Environment:
    """
    """
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

        self.logger = _logging.getLogger("clang_build.clang_build")
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