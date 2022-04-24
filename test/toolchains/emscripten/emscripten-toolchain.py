import shutil as _shutil
from pathlib import Path as _Path
import logging as _logging

from sys import version_info as _version_info
from sys import platform as _platform
from sysconfig import get_paths as _get_paths
from sysconfig import get_config_var as _get_config_var
import subprocess as _subprocess

import clang_build


_LOGGER = _logging.getLogger("clang-build")


class Emscripten(clang_build.toolchain.Toolchain):

    DEFAULT_COMPILE_FLAGS = clang_build.toolchain.LLVM.DEFAULT_COMPILE_FLAGS
    DEFAULT_LINK_FLAGS = clang_build.toolchain.LLVM.DEFAULT_LINK_FLAGS

    PLATFORM_DEFAULTS = {
        "linux": {
            "PLATFORM": "linux",
            "EXECUTABLE_PREFIX": "",
            "EXECUTABLE_SUFFIX": ".js",
            "SHARED_LIBRARY_PREFIX": "lib",
            "SHARED_LIBRARY_SUFFIX": ".js",
            "STATIC_LIBRARY_PREFIX": "lib",
            "STATIC_LIBRARY_SUFFIX": ".js",
            "PLATFORM_EXTRA_FLAGS_EXECUTABLE": [],
            "PLATFORM_EXTRA_FLAGS_SHARED": [],
            "PLATFORM_EXTRA_FLAGS_STATIC": [],
            "PLATFORM_BUNDLING_LINKER_FLAGS": [],
            "EXECUTABLE_OUTPUT_DIR": "bin",
            "SHARED_LIBRARY_OUTPUT_DIR": "lib",
            "STATIC_LIBRARY_OUTPUT_DIR": "lib",
            "PLATFORM_PYTHON_INCLUDE_PATH": _Path(_get_paths()["include"]),
            "PLATFORM_PYTHON_LIBRARY_PATH": _Path(_get_paths()["data"]) / "lib",
            "PLATFORM_PYTHON_LIBRARY_NAME": f"python{_version_info.major}.{_version_info.minor}",
            "PLATFORM_PYTHON_EXTENSION_SUFFIX": _get_config_var("EXT_SUFFIX"),
        },
        "darwin": {
            "PLATFORM": "osx",
            "EXECUTABLE_PREFIX": "",
            "EXECUTABLE_SUFFIX": ".js",
            "SHARED_LIBRARY_PREFIX": "lib",
            "SHARED_LIBRARY_SUFFIX": ".js",
            "STATIC_LIBRARY_PREFIX": "lib",
            "STATIC_LIBRARY_SUFFIX": ".js",
            "PLATFORM_EXTRA_FLAGS_EXECUTABLE": [],
            "PLATFORM_EXTRA_FLAGS_SHARED": [],
            "PLATFORM_EXTRA_FLAGS_STATIC": [],
            "PLATFORM_BUNDLING_LINKER_FLAGS": [],
            "EXECUTABLE_OUTPUT_DIR": "bin",
            "SHARED_LIBRARY_OUTPUT_DIR": "lib",
            "STATIC_LIBRARY_OUTPUT_DIR": "lib",
            "PLATFORM_PYTHON_INCLUDE_PATH": _Path(_get_paths()["include"]),
            "PLATFORM_PYTHON_LIBRARY_PATH": _Path(_get_paths()["data"]) / "lib",
            "PLATFORM_PYTHON_LIBRARY_NAME": f"python{_version_info.major}.{_version_info.minor}",
            "PLATFORM_PYTHON_EXTENSION_SUFFIX": _get_config_var("EXT_SUFFIX"),
        },
        "win32": {
            "PLATFORM": "windows",
            "EXECUTABLE_PREFIX": "",
            "EXECUTABLE_SUFFIX": ".js",
            "SHARED_LIBRARY_PREFIX": "lib",
            "SHARED_LIBRARY_SUFFIX": ".js",
            "STATIC_LIBRARY_PREFIX": "lib",
            "STATIC_LIBRARY_SUFFIX": ".js",
            "PLATFORM_EXTRA_FLAGS_EXECUTABLE": [],
            "PLATFORM_EXTRA_FLAGS_SHARED": [],
            "PLATFORM_EXTRA_FLAGS_STATIC": [],
            "PLATFORM_BUNDLING_LINKER_FLAGS": [],
            "EXECUTABLE_OUTPUT_DIR": "bin",
            "SHARED_LIBRARY_OUTPUT_DIR": "lib",
            "STATIC_LIBRARY_OUTPUT_DIR": "lib",
            "PLATFORM_PYTHON_INCLUDE_PATH": _Path(_get_paths()["include"]),
            "PLATFORM_PYTHON_LIBRARY_PATH": _Path(_get_paths()["data"]) / "libs",
            "PLATFORM_PYTHON_LIBRARY_NAME": f"python{_version_info.major}{_version_info.minor}",
            "PLATFORM_PYTHON_EXTENSION_SUFFIX": _get_config_var("EXT_SUFFIX"),
        },
    }

    _UNSUPPORTED_DIALECT_MESSAGE = "error: invalid value 'c++{0:02d}'"

    def __init__(self):
        """Search for clang and detect compiler features.

        Raises
        ------
        RuntimeError
            If a compiler or linker tool wasn't found on the system.

        """
        super().__init__()

        self.c_compiler = self._find("emcc")
        self.cpp_compiler = self._find("em++")
        self.archiver = self._find("emar")

        self.max_cpp_standard = (
            "-std=c++17"  # self._get_max_supported_compiler_dialect()
        )

        if _platform == "linux":
            self.platform = "linux"
        elif _platform == "darwin":
            self.platform = "osx"
        elif _platform == "win32":
            self.platform = "windows"
        else:
            raise RuntimeError("Platform " + _platform + "is currently not supported.")

        self.platform_defaults = self.PLATFORM_DEFAULTS[_platform]

        _LOGGER.info("toolchain root directory: %s", self.cpp_compiler.parents[0])
        _LOGGER.info("emcc executable:     %s", self.c_compiler)
        _LOGGER.info("em++ executable:     %s", self.cpp_compiler)
        _LOGGER.info("llvm-ar executable:  %s", self.archiver)
        _LOGGER.info("Newest supported C++ dialect: %s", self.max_cpp_standard)
        _LOGGER.info(
            "Python headers in:   %s",
            self.platform_defaults["PLATFORM_PYTHON_INCLUDE_PATH"],
        )
        _LOGGER.info(
            "Python library in:   %s",
            self.platform_defaults["PLATFORM_PYTHON_LIBRARY_PATH"],
        )

    def _find(self, executable):
        """Find path of executable.

        Parameters
        ----------
        executable : str
            The executable for which to search the location.

        Returns
        -------
        pathlib.Path
            Path where the executable was found.

        Raises
        ------
        RuntimeError
            If the executable was not found in the systems default
            look-up places.

        """
        try:
            return _Path(
                _shutil.which(executable), path="/usr/local/emsdk/emscripten/1.38.29/"
            )
        except TypeError:
            error_message = f"Couldn't find {executable} executable"
            _LOGGER.error(error_message)
            raise RuntimeError(error_message)

    def _get_dialect_flag(self, year):
        """Return a dialect flag for a given year.

        Parameters
        ----------
        year : int
            The last two digits of the year to convert.
            For example 11 will yield `-std=c++11`.

        Returns
        -------
        str
            A dialect flag from a given year.

        """
        return "-std=c++{:02d}".format(year)

    def _get_compiler(self, is_c_target):
        return [str(self.c_compiler)] if is_c_target else [str(self.cpp_compiler)]

    def _get_compiler_command(
        self, source_file, object_file, include_directories, flags, is_c_target
    ):
        return (
            self._get_compiler(is_c_target)
            + (["-o", str(object_file)] if object_file else [])
            + ["-c", str(source_file)]
            # + flags
            + [part for flag in flags for part in flag.split()]
            + [
                item
                for include_directory in include_directories
                for item in ["-I", str(include_directory)]
            ]
        )

    def _run_clang_command(self, command):
        _LOGGER.debug(f"Running: {' '.join(command)}")
        try:
            return (
                True,
                _subprocess.check_output(
                    command, encoding="utf8", stderr=_subprocess.STDOUT
                ),
            )
        except _subprocess.CalledProcessError as error:
            return False, error.output.strip()

    def generate_dependency_file(
        self, source_file, dependency_file, flags, include_directories, is_c_target
    ):
        dependency_file.parents[0].mkdir(parents=True, exist_ok=True)

        command = self._get_compiler_command(
            source_file, None, include_directories, flags, is_c_target
        ) + ["-E", "-MMD", str(source_file), "-MF", str(dependency_file)]
        return command, *self._run_clang_command(command)

    def compile(
        self, source_file, object_file, include_directories, flags, is_c_target
    ):
        object_file.parents[0].mkdir(parents=True, exist_ok=True)

        command = self._get_compiler_command(
            source_file, object_file, include_directories, flags, is_c_target
        )
        return command, *self._run_clang_command(command)

    def link(
        self,
        object_files,
        output_file,
        flags,
        library_directories,
        libraries,
        is_library,
        is_c_target,
    ):
        _LOGGER.info(f'link -> "{output_file}"')
        output_file.parents[0].mkdir(parents=True, exist_ok=True)

        command = (
            self._get_compiler(is_c_target)
            + (["-shared"] if is_library else [])
            + ["-o", str(output_file)]
        )
        command += [str(o) for o in object_files]
        command += [part for flag in flags for part in flag.split()]
        command += ["-L" + str(directory) for directory in library_directories]
        command += ["-l" + str(library) for library in libraries]

        return self._run_clang_command(command)

    def archive(self, object_files, output_file, flags):
        output_file.parents[0].mkdir(parents=True, exist_ok=True)

        command = [str(self.archiver), "rc", str(output_file)] + [
            str(o) for o in object_files
        ]

        return self._run_clang_command(command)


def get_toolchain() -> clang_build.toolchain.Toolchain:
    return Emscripten()
