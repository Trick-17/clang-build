from pathlib import Path as _Path
from shutil import which as _which
import subprocess as _subprocess
from logging import getLogger as _getLogger
from functools import lru_cache as _lru_cache

_UNSUPPORTED_DIALECT_MESSAGE = "error: invalid value 'c++{0:02d}'"
"""Error message clangpp returns if dialect not supported."""


def _get_dialect_string(year):
    """Convert a year to a CLI dialect option for clangpp.

    Parameters
    ----------
    year : int
        The last two digits of a year (e.g. 17 for 2017)

    Returns
    -------
    dialect_CLI_flag : str
        The corresponding CLI flag of the given year.

    """
    return "-std=c++{:02d}".format(year)


@_lru_cache()
def _check_dialect(year, clangpp):
    """Check a given dialect to see if the given compiler supports it.

    Parameters
    ----------
    year : int
        The last two digits of a year (e.g. 17 to check for C++17)
    clangpp : pathlib.Path
        The path to an existing C++ clang compiler executable

    Returns
    -------
    bool
        True if the dialect exists, false otherwise.

    """
    std_opt = _get_dialect_string(year)
    try:
        _subprocess.run(
            [str(clangpp), std_opt, "-x", "c++", "-E", "-"],
            check=True,
            input=b"",
            stdout=_subprocess.PIPE,
            stderr=_subprocess.PIPE,
        )
    except _subprocess.CalledProcessError as e:
        error_message = _UNSUPPORTED_DIALECT_MESSAGE.format(year)
        strerr = e.stderr.decode("utf8", "strict")
        if error_message in strerr:
            return False
        raise
    return True


@_lru_cache(maxsize=1)
def _get_max_supported_compiler_dialect(clangpp):
    """Check for the newest supported C++ dialect.

    Given a clang C++ compiler executable, check to see
    which dialect is the newest one it supports.

    Parameters
    ----------
    clangpp : str
        The path to an existing C++ clang compiler executable

    Returns
    -------
    dialect_CLI_flag : str
        Returns the latest dialect the given compiler
        supports. The fallback mode is ``C++98``.

    """
    supported_dialects = []
    for dialect in range(30):
        if _check_dialect(dialect, clangpp):
            supported_dialects.append(dialect)

    if supported_dialects:
        return _get_dialect_string(max(supported_dialects))

    return _get_dialect_string(98)


_logger = _getLogger(__name__)


class Clang:
    """Compiler representation bundling all important paths.

    Attributes
    ----------
    clang : pathlib.Path
        The path to the C compiler executable
    clangpp : pathlib.Path
        The path to the C++ compiler executable
    clang_ar : pathlib.Path
        The path to the llvm archiver tool executable
    link_command_executable : list
        The command to use to link executables
    link_command_shared_library : list
        The command to use to link a shared library
    link_command_static_library : list
        The command to use to link a static library
    max_supported_cpp_dialect : str
        The highest C++ dialect supported by the found
        C++ compiler, given as a CLI argument.

    """

    def __init__(self):
        """Set all compiler paths."""
        self.clang = _Path(_which("clang"))
        self.clangpp = _Path(_which("clang++"))
        self.clang_ar = _Path(_which("llvm-ar"))

        if self.clangpp:
            llvm_root = _Path(self.clangpp).parents[0]
        else:
            error_message = "Couldn't find clang++ executable"
            _logger.error(error_message)
            raise RuntimeError(error_message)

        if not self.clang_ar:
            error_message = "Couldn't find llvm-ar executable"
            _logger.error(error_message)
            raise RuntimeError(error_message)

        if not self.clang:
            error_message = "Couldn't find clang executable"
            _logger.error(error_message)
            raise RuntimeError(error_message)

        self.link_command_executable = [str(self.clangpp), "-o"]
        self.link_command_shared_library = [str(self.clangpp), "-shared", "-o"]
        self.link_command_static_library = [str(self.clang_ar), 'rc']
        self.max_cpp_dialect = _get_max_supported_compiler_dialect(self.clangpp)

        _logger.info(f"llvm root directory: {llvm_root}")
        _logger.info(f"clang executable:    {self.clang}")
        _logger.info(f"clang++ executable:  {self.clangpp}")
        _logger.info(f"llvm-ar executable:  {self.clang_ar}")
        _logger.info(f"Newest supported C++ dialect: {self.max_cpp_dialect}")
