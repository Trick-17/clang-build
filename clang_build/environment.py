"""
This module contains the `Environment` class.
"""

import logging as _logging
import shutil as _shutil
from multiprocessing import Pool as _Pool
from pathlib import Path as _Path
from importlib import util as importlib_util

import json

from . import __version__
from .build_type import BuildType as _BuildType
from .toolchain import Toolchain as _Toolchain
from .toolchain import LLVM as _LLVM

_LOGGER = _logging.getLogger(__name__)


def _get_toolchain(module_file_path: _Path):
    """Returns a Toolchain created from a Python script.
    """
    module_name = module_file_path.stem

    module_spec = importlib_util.spec_from_file_location(module_name, module_file_path)
    if module_spec is None:
        raise RuntimeError(f'No "{module_name}" module could be found in "{directory.resolve()}"')

    clang_build_module = importlib_util.module_from_spec(module_spec)
    module_spec.loader.exec_module(clang_build_module)

    if clang_build_module.get_toolchain is None:
        raise RuntimeError(f'Module "{module_name}" in "{directory.resolve()}" does not contain a `get_toolchain` method')

    return clang_build_module.get_toolchain()

class Environment:
    """
    """

    def __init__(self, args):

        # TODO: Move this out
        _LOGGER.info(f"clang-build {__version__}")

        # Toolchain
        self.toolchain = None
        toolchain_file_str = args.get("toolchain", None)
        _LOGGER.info(f"toolchain_file_str \"{toolchain_file_str}\"")
        if toolchain_file_str:
            toolchain_file = _Path(toolchain_file_str)
            if toolchain_file.is_file():
                _LOGGER.info(f"Using toolchain file \"{toolchain_file.resolve()}\"")
                self.toolchain = _get_toolchain(toolchain_file)
                if not isinstance(self.toolchain, _Toolchain):
                    raise RuntimeError(f'Unable to initialize toolchain:\nThe `get_toolchain` method in "{py_file}" did not return a valid `clang_build.toolchain.Toolchain`, its type is "{type(toolchain)}"')
            else:
                _LOGGER.error("Could not find toolchain file \"{toolchain_file_str}\"")

        if not self.toolchain:
            _LOGGER.info("Using default LLVM toolchain")
            self.toolchain = _LLVM()

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

        self.compilation_database_file = (self.build_directory / 'compile_commands.json')
        self.compilation_database = []
        if self.compilation_database_file.exists():
            self.compilation_database = json.loads(self.compilation_database_file.read_text())
