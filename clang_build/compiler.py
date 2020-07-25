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

        self.max_cpp_dialect = self._get_max_supported_compiler_dialect()

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
    def _get_max_supported_compiler_dialect(self):
        """Check the maximally supported C++ dialect.

        Returns
        -------
        str
            Flag string of the latest supported dialect

        """
        try:
            _subprocess.run(
                [str(self.clangpp), "-std=dummpy", "-x", "c++", "-E", "-"],
                check=True,
                stdout=_subprocess.PIPE,
                stderr=_subprocess.PIPE,
                encoding="utf8",
            )
        except _subprocess.CalledProcessError as subprocess_error:
            for line in reversed(subprocess_error.stderr.splitlines()):
                if "draft" in line or "gnu" in line:
                    continue

                return "-std=" + _search(r"'(c\+\+..)'", line).group(1)

            raise RuntimeError("Could not find a supported C++ standard.")
