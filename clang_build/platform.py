"""Module containing platform specific definitions.

.. data:: PLATFORM

    The platform name as it can appear in clang-build
    TOML files.

.. data:: EXECUTABLE_PREFIX

    Prefix added to executable file names.

.. data:: EXECUTABLE_SUFFIX

    Suffix added to executable name, including extension.

.. data:: EXECUTABLE_OUTPUT

    Folder to place compiled executable in.

.. data:: SHARED_LIBRARY_PREFIX

    Prefix added to shared library file names.

.. data:: SHARED_LIBRARY_SUFFIX

    Suffix added to shared library name, including extension.

.. data:: SHARED_LIBRARY_OUTPUT

    Folder to place compiled shared library in.

.. data:: STATIC_LIBRARY_PREFIX

    Prefix added to static library file names.

.. data:: STATIC_LIBRARY_SUFFIX

    Suffix added to static library name, including extension.

.. data:: STATIC_LIBRARY_OUTPUT

    Folder to place compiled static library in.

.. data:: PLATFORM_EXTRA_FLAGS_EXECUTABLE

    Platform specific flags that are added to the compilation of
    executables.

.. data:: PLATFORM_EXTRA_FLAGS_SHARED

    Platform specific flags that are added to the compilation of
    shared libraries.

.. data:: PLATFORM_EXTRA_FLAGS_STATIC

    Platform specific flags that are added to the compilation of
    static libraries.

"""

from sys import platform as _platform

if _platform == 'linux' or _platform == 'linux2':
    # Linux
    PLATFORM = 'linux'
    EXECUTABLE_PREFIX = ''
    EXECUTABLE_SUFFIX = ''
    EXECUTABLE_OUTPUT = 'bin'
    SHARED_LIBRARY_PREFIX = 'lib'
    SHARED_LIBRARY_SUFFIX = '.so'
    SHARED_LIBRARY_OUTPUT = 'lib'
    STATIC_LIBRARY_PREFIX = 'lib'
    STATIC_LIBRARY_SUFFIX = '.a'
    STATIC_LIBRARY_OUTPUT = 'lib'
    PLATFORM_EXTRA_FLAGS_EXECUTABLE = []
    PLATFORM_EXTRA_FLAGS_SHARED     = ['-fpic']
    PLATFORM_EXTRA_FLAGS_STATIC     = []
    PLATFORM_BUNDLING_LINKER_FLAGS = ["-Wl,-rpath,$ORIGIN"]
elif _platform == 'darwin':
    # OS X
    PLATFORM = 'osx'
    EXECUTABLE_PREFIX = ''
    EXECUTABLE_SUFFIX = ''
    EXECUTABLE_OUTPUT = 'bin'
    SHARED_LIBRARY_PREFIX = 'lib'
    SHARED_LIBRARY_SUFFIX = '.dylib'
    SHARED_LIBRARY_OUTPUT = 'lib'
    STATIC_LIBRARY_PREFIX = 'lib'
    STATIC_LIBRARY_SUFFIX = '.a'
    STATIC_LIBRARY_OUTPUT = 'lib'
    PLATFORM_EXTRA_FLAGS_EXECUTABLE = []
    PLATFORM_EXTRA_FLAGS_SHARED     = []
    PLATFORM_EXTRA_FLAGS_STATIC     = []
    PLATFORM_BUNDLING_LINKER_FLAGS = ["-Wl,-rpath,@executable_path"]
elif _platform == 'win32':
    # Windows
    PLATFORM = 'windows'
    EXECUTABLE_PREFIX = ''
    EXECUTABLE_SUFFIX = '.exe'
    EXECUTABLE_OUTPUT = 'bin'
    SHARED_LIBRARY_PREFIX = ''
    SHARED_LIBRARY_SUFFIX = '.dll'
    SHARED_LIBRARY_OUTPUT = 'bin'
    STATIC_LIBRARY_PREFIX = ''
    STATIC_LIBRARY_SUFFIX = '.lib'
    STATIC_LIBRARY_OUTPUT = 'lib'
    PLATFORM_EXTRA_FLAGS_EXECUTABLE = ['-Xclang', '-flto-visibility-public-std']
    PLATFORM_EXTRA_FLAGS_SHARED     = ['-Xclang', '-flto-visibility-public-std']
    PLATFORM_EXTRA_FLAGS_STATIC     = ['-Xclang', '-flto-visibility-public-std']
    PLATFORM_BUNDLING_LINKER_FLAGS = []
else:
    raise RuntimeError('Platform ' + _platform + 'is currently not supported.')
