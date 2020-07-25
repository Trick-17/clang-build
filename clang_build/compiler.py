"""Module containing compiler specifics."""

import logging as _logging
import shutil as _shutil
import subprocess as _subprocess
from functools import lru_cache as _lru_cache
from pathlib import Path as _Path
from re import search as _search

_LOGGER = _logging.getLogger(__name__)


class Clang:
    """Class of the clang compiler and related tools.

    This class bundles various paths and attributes of
    the installed clang compiler. The clang version used
    is the one that would be used if `clang` or `clang++`
    were called in the terminal directly.

    Attributes
    ----------
    clang : :any:`pathlib.Path`
        Path to the `clang` executable
    clangpp : :any:`pathlib.Path`
        Path to the `clang++` executable
    clang_ar : :any:`pathlib.Path`
        Path to the `llvm-ar` executable
    max_cpp_dialect : str
        Compile flag for the latest supported
        dialect of the found compiler

    """

    _UNSUPPORTED_DIALECT_MESSAGE = "error: invalid value 'c++{0:02d}'"

    def __init__(self):
        """Search for clang and detect compiler features.

        Raises
        ------
        RuntimeError
            If a compiler or linker tool wasn't found on the system.

        """
        self.clang = self._find("clang")
        self.clangpp = self._find("clang++")
        self.clang_ar = self._find("llvm-ar")

        self.max_cpp_dialect = self._get_max_supported_compiler_dialect(self.clangpp)

        _LOGGER.info("llvm root directory: %s", self.clangpp.parents[0])
        _LOGGER.info("clang executable:    %s", self.clang)
        _LOGGER.info("clang++ executable:  %s", self.clangpp)
        _LOGGER.info("llvm-ar executable:  %s", self.clang_ar)
        _LOGGER.info("Newest supported C++ dialect: %s", self.max_cpp_dialect)

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
            return _Path(_shutil.which(executable))
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

    @_lru_cache(maxsize=1)
    def dialect_exists(self, year):
        """Check if a given dialect flag is valid.

        Parameters
        ----------
        year : int
            The last two digits of the dialect.
            For example 11 for `C++11`.

        Returns
        -------
        bool
            True if the dialect for the given year is supported
            by clang.

        """
        std_opt = self._get_dialect_flag(year)
        try:
            _subprocess.run(
                [str(self.clangpp), std_opt, "-x", "c++", "-E", "-"],
                check=True,
                input=b"",
                stdout=_subprocess.PIPE,
                stderr=_subprocess.PIPE,
            )
        except _subprocess.CalledProcessError as subprocess_error:
            error_message = self._UNSUPPORTED_DIALECT_MESSAGE.format(year)
            strerr = subprocess_error.stderr.decode("utf8", "strict")
            if error_message in strerr:
                return False
            raise
        return True

    @_lru_cache(maxsize=1)
    def _get_max_supported_compiler_dialect(self, clangpp):
        """Check the maximally supported C++ dialect.

        Parameters
        ----------
        clangpp : :any:`pathlib.Path`
            Path to the clang++ executable

        Returns
        -------
        str
            Flag string of the latest supported dialect

        """
        _, report = self._run_clang_command(
            [str(clangpp), "-std=dummpy", "-x", "c++", "-E", "-"]
        )

        for line in reversed(report.splitlines()):
            if "draft" in line or "gnu" in line:
                continue

            return "-std=" + _search(r"'(c\+\+..)'", line).group(1)

    def _get_driver(self, source_file):
        if source_file.suffix in [".c", ".cc", ".m"]:
            return [str(self.clang)]
        else:
            return [str(self.clangpp), self.max_cpp_dialect]

    def compile(self, source_file, object_file, flags):
        """Compile a given source file into an object file.

        If the object file is placed into a non-existing folder, this
        folder is generated before compilation.

        Parameters
        ----------
        source_file : pathlib.Path
            The source file to compile

        object_file : pathlib.Path
            The object file to generate during compilation

        flags : list of str
            List of flags to pass to the compiler

        Returns
        -------
        bool
            True if the compilation was successful, else False
        str
            Output of the compiler

        """
        object_file.parents[0].mkdir(parents=True, exist_ok=True)

        return self._run_clang_command(
            self._get_driver(source_file)
            + ["-c", str(source_file), "-o", str(object_file)]
            + flags
        )

    def generate_dependency_file(self, source_file, dependency_file, flags):
        """Generate a dependency file for a given source file.

        If the dependency file is placed into a non-existing folder, this
        folder is generated before compilation.

        Parameters
        ----------
        source_file : pathlib.Path
            The source file to compile

        dependency_file : pathlib.Path
            The dependency file to generate

        flags : list of str
            List of flags to pass to the compiler

        Returns
        -------
        bool
            True if the dependency file generation was successful, else False
        str
            Output of the compiler

        """
        dependency_file.parents[0].mkdir(parents=True, exist_ok=True)

        return self._run_clang_command(
            self._get_driver(source_file)
            + ["-E", "-MMD", str(source_file), "-MF", str(dependency_file)]
            + flags
        )

    _LINKER_OPTIONS = {
        "executable": ["-o"],
        "shared": ["-shared", "-o"],
        "static": ["rc"],
    }

    def link(self, output_file, command, output_type):
        """Link into the given output_file.

        The command should contain all object files, library search paths
        and libraries against which to link. If the output_file is placed
        in a non-existing folder, the folder and all required parents
        are generated.

        Parameters
        ----------
        output_file : pathlib.Path
            The output file to generate
        command : list of str
            All objects files and search paths etc should be in here
        output_type : str
            One of the following three: "executable", "shared", "static"

        Returns
        -------
        bool
            True if linking was successful, False otherwise
        str
            The output of the linker

        Raises
        ------
        ValueError
            If an output_type other than the allowed ones is passed

        """
        output_file.parents[0].mkdir(parents=True, exist_ok=True)

        try:
            type_flags = self._LINKER_OPTIONS[output_type]
        except KeyError:
            raise ValueError(
                f"Invalid output type: {output_type}. Valid options are: "
                + f"{list(self._LINKER_OPTIONS.keys())}"
            )

        return self._run_clang_command(
            [str(self.clang_ar)] + type_flags + str(output_file) + command
        )

    def _run_clang_command(self, command):
        success = True
        _LOGGER.debug(f"Running: {' '.join(command)}")
        try:
            report = _subprocess.check_output(command, encoding="utf8").strip()
        except _subprocess.CalledProcessError as error:
            success = False
            report = error.output.strip()

        return success, report
