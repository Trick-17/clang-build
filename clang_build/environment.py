"""
This module contains the `Environment` class.
"""

import logging as _logging
import shutil as _shutil
from multiprocessing import Pool as _Pool
from pathlib import Path as _Path

from .build_type import BuildType as _BuildType
from .clang_build import __version__
from .toolchain import LLVM as _Clang

_LOGGER = _logging.getLogger(__name__)


class Environment:
    """
    """

    def __init__(self, args):

        # TODO: Move this out
        _LOGGER.info(f"clang-build {__version__}")

        self.toolchain = _Clang()

        # Build type (Default, Release, Debug)
        self.build_type = args.get("build_type", _BuildType.Default)
        _LOGGER.info(f"Build type: {self.build_type.name}")

        # Whether to force a rebuild
        self.force_build = args.get("force_build", False)
        if self.force_build:
            _LOGGER.info("Forcing rebuild...")

        # Build directory
        self.build_directory = _Path("build")

        # Whether to create a dotfile for graphing dependencies
        self.create_dependency_dotfile = not args.get("no_graph", False)

        # Whether to recursively clone submodules when cloning with git
        self.clone_recursive = not args.get("no_recursive_clone", False)

        # Whether to bundle binaries
        self.bundle = args.get("bundle", False)
        if self.bundle:
            _LOGGER.info("Bundling of binary dependencies is activated")

        # Whether to create redistributable bundles
        self.redistributable = args.get("redistributable", False)
        if self.redistributable:
            self.bundle = True
            _LOGGER.info("Redistributable bundling of binary dependencies is activated")
