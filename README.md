Clang-build
==============================================

Linux and OSX test: [![Test status](https://travis-ci.org/Trick-17/clang-build.svg?branch=master)](https://travis-ci.org/Trick-17/clang-build)
Windows test: [![Test status](https://ci.appveyor.com/api/projects/status/57qv53r4totihxrj/branch/master?svg=true)](https://ci.appveyor.com/project/GPMueller/clang-build)



**Motivation:**

- Meta build systems are inherently the wrong way to go, either the build system or the compiler should be platform-agnostic.
- Trying to cover all use-cases is the wrong way to go - there is no need to let people do it the wrong way
- CMake is cumbersome, unnecessarily generic and verbose and people should not need a second programming language to be able to build C++
- With Clang, finally a properly cross-platform compiler exists
- With Python we have a language we can use consistently across platforms

**Goals:**

- One compiler (Clang), one build system (written in Python)
- Simple projects should be simple to build
- Build process for reasonable project structures should still be easy
- Adding third-party dependencies should be manageable

**Related resources:**

- [CppCon 2017: Isabella Muerte "There Will Be Build Systems: I Configure Your Milkshake"](https://www.youtube.com/watch?v=7THzO-D0ta4)
- https://medium.com/@corentin.jabot/accio-dependency-manager-b1846e1caf76



Usage
----------------------------------------------

In order to run `clang-build` one should only need to have Python and Clang installed.
If you have admin rights, `pip install`, otherwise just drop-in the `clang-build.py` script,
e.g. `curl -O https://raw.githubusercontent.com/GPMueller/clang-build-test/master/clang-build.py`

- `clang-build` to build the current directory
- `clang-build -d"path/to/dir"` to build a different directory (alternatively `--directory`)
- `clang-build -V` to print the called clang commands (alternatively `--verbose`)

The given directory will be searched for a `clang-build.toml` file, which you can use to configure
your build targets, if necessary. If the build file cannot be found, `clang-build` will try to
create an executable from your project, searching the root and some default folders for sources
and headers.

*Note: until this is a package on pypi, you need to call `python clang-build.py` instead of just `clang-build`...*



General Ideas
==============================================



What should be trivial
----------------------------------------------

This would be things that require only the invocation of `clang-build` and no build file.

- build a hello world program (i.e anything with single main and without non-std dependencies)
- build a reasonable MWE with local dependencies (potentially folder structure with e.g. `src`, `include/MWE` and `include/thirdparty`)
- include stdlib
- include anything that can be found by sane default search
- using command line arguments:
  - specify root/source folder
  - set build type from (last used should be cached/remembered)
  - set build verbosity

Sane defaults and default behaviour:

- platform-independence
- build into a "build/" directory, not into toplevel
- for multiple targets build into "build/target"
- default search paths for different platforms, including also e.g. "./include", "./lib", "./build/lib", "/usr/local/...", ...



What should be easy
----------------------------------------------

This would be things that only require a minimal TOML project file

- add dependency / external project from source folder or remote (e.g. github)
  - header-only should be trivial
  - for a regular (not too complicated) library it should be easy to write a build config
- create a library from one subfolder, an executable from another and link them
- setting target-specific (note: defaults should be sane!)
  - source file extensions
  - source directories
  - compile and link flags
  - optional version
  - dependencies (which may include non-targets, e.g. configuration steps)
  - properties (required c++ version, definitions/`#define`s, ...)
- access to flag "lists" such as flags for
  - coverage
  - cuda
  - openmp
- set target-specific flags, include folders, etc. which should not be propagated to dependency parents as "private"



What should be possible
----------------------------------------------

Steps that would involve more effort from the user, including possibly some python code

- a Target configuration step before building (e.g. for more involved version numbering)
- through the configuration step, inclusion of e.g. CMake-project should be possible
- packaging: any target may be packaged, meaning it's dependencies are handled and if built, binaries may be bundled
- external package dependencies
  - binaries on a server
  - source on a server (fallback from binaries)
  - binaries on disk, try to determine version from path and file names
  - source on disk, try to determine version from path and file names



Project File By Example
==============================================



A single target
----------------------------------------------

```TOML
# Top-level brackets indicate a target
[hello]
# Note: the following sources settings could be left out.
# .hpp and .cpp files will be searched for in include and src by default
[hello.sources]
file_extensions = [".hpp", ".cpp"]
include_directories = ["include"]
source_directories = ["src"]
# Some properties
[hello.properties]
cpp_version = 17
output_name = "runHello" # name should not contain pre- or suffixes such as lib, .exe, .so
```



Two targets with linking
----------------------------------------------

```TOML
# Build a library
[mylib]
target_type = "sharedlibrary"
[mylib.sources]
include_directories = ["mylib/include"]
source_directories = ["mylib/src"]

# Build an executable and link the library
[myexe]
output_name = "runExe"
target_type = "executable"
[myexe.sources]
include_directories = ["myexe/include"]
source_directories = ["myexe/src"]

[myexe.link]
dependencies = ["mylib"]

[myexe.flags]
link = ["-DMYLIB_SOME_DEFINE"]
```



A package used by a target
----------------------------------------------

`mypackage/clang-build.toml`
```TOML
# Build a library
[mylib]
target_type = "library"
[mylib.sources]
include_directories = ["mylib/include"]
source_directories = ["mylib/src"]
```

`myexe/clang-build.toml`
```TOML
# Include an external package/target (i.e. not from this toml file)
[somelib]
external = true
path = "/path/to/sources"

# Build an executable and link the library
[myexe]
[myexe.sources]
include_directories = ["include", "mylib.sources.include_directories"]
source_directories = ["src"]

[myexe.link]
dependencies = ["somelib"]
```



Packages from server
----------------------------------------------

```TOML
# Build a library
[mylib]
external = true
url = "https://github.com/trick-17/mylib"
version = 1.1 # will try to git checkout [v]1.1[.*]

# Build an executable and link the library
[myexe]
[myexe.link]
dependencies = ["mylib"]
```



Defaults
==============================================



General
----------------------------------------------

- all relative paths in a toml are interpreted as relative to that toml file
- if only one target is built from source, it is built into `build/<build_type>`
- if more than one target is built from source, they are built into `build/<target_name>/<build_type>`



Target properties
----------------------------------------------

- target and its properties are **public** by default. The property `private = true`
  can be used to set a target to be only visible in the local .toml.



Include Paths
----------------------------------------------

Note: only those paths should be added to the build flags, which the build system finds contain needed files.

### Linux
- .
- ./include
- /usr/local
- /opt
- $PATH
- /include

### OSX
- .
- ./include
- /usr/local
- /opt
- $PATH
- /include

### Windows
- .
- ./include
- %PATH%



External targets
----------------------------------------------

### Search paths

The build system should search these paths for folders with names corresponding
to the external targets.
For paths which were manually specified, the build system should search more
deeply to try and find a `clang-build.toml` and in turn search that for the
corresponding target names.

Local:

- `./`
- `./<target_name>`

git server:
- `<url>`
- `<url>/<target_name>`