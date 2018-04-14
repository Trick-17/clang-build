from sys import platform as _platform

if _platform == 'linux' or _platform == 'linux2':
    # Linux
    EXECUTABLE_PREFIX = ''
    EXECUTABLE_SUFFIX = ''
    EXECUTABLE_OUTPUT = 'bin'
    SHARED_LIBRARY_PREFIX = 'lib'
    SHARED_LIBRARY_SUFFIX = '.so'
    SHARED_LIBRARY_OUTPUT = 'lib'
    STATIC_LIBRARY_PREFIX = 'lib'
    STATIC_LIBRARY_SUFFIX = '.a'
    STATIC_LIBRARY_OUTPUT = 'lib'
    PLATFORM_EXTRA_FLAGS_EXECUTABLE = ['']
    PLATFORM_EXTRA_FLAGS_SHARED     = ['-fpic']
    PLATFORM_EXTRA_FLAGS_STATIC     = ['']
elif _platform == 'darwin':
    # OS X
    EXECUTABLE_PREFIX = ''
    EXECUTABLE_SUFFIX = ''
    EXECUTABLE_OUTPUT = 'bin'
    SHARED_LIBRARY_PREFIX = 'lib'
    SHARED_LIBRARY_SUFFIX = '.dylib'
    SHARED_LIBRARY_OUTPUT = 'lib'
    STATIC_LIBRARY_PREFIX = 'lib'
    STATIC_LIBRARY_SUFFIX = '.a'
    STATIC_LIBRARY_OUTPUT = 'lib'
    PLATFORM_EXTRA_FLAGS_EXECUTABLE = ['']
    PLATFORM_EXTRA_FLAGS_SHARED     = ['']
    PLATFORM_EXTRA_FLAGS_STATIC     = ['']
elif _platform == 'win32':
    # Windows
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
else:
    raise RuntimeError('Platform ' + _platform + 'is currently not supported.')