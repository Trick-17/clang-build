Clang-build
==============================================

This project exists in order to work towards the following goals:
- one compiler, one build system, one dependency
- simplification of build process for reasonable project structures
- make trivial projects trivial to build (hello world, MWEs, ...)
- drop-in replacement 

In order to run `clang-build` one should only need to have Python and Clang.
`pip install` it or, if e.g. you don't have admin rights, drop-in a single python script.



Usage
----------------------------------------------

- `clang-build` to build the current directory
- `clang-build -d"path/to/dir"` to build a different directory (alternatively `--directory`)



General Ideas
==============================================



What should be trivial
----------------------------------------------

This would be things that require only the invocation of `clang-build`

- build a hello world program (i.e anything with single main and without non-std dependencies)
- build a reasonable MWE with local dependencies (potentially folder structure with e.g. `src`, `include/MWE` and `include/thirdparty`)
- include stdlib
- include anything that can be found by sane default search
- set build type (last used should be remembered)
- set build verbosity

The sane defaults and default behaviour should include:

- platform-independence
- build into a "build/" directory, not into toplevel. For multiple targets into "build/target"
- default search paths for different platforms, including also e.g. "./include", "./lib", "./build/lib", "/usr/local/...", ...



What should be easy
----------------------------------------------

This would be things that only require a minimal TOML project file

- add a header-only dependency, via source folder or external (github, ...)
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
- possibly explicit exporting of variables, targets, include paths; maybe default is that namespace contents are public;
  (note: it's probably sane to require a "namespace" if anything is to be exported. A target cannot just be exported,
  should require names to be inside a namespace in order to e.g. avoid collisions of common target names, such as "test".)
  This may be related directly to packaging - maybe only a package can export anything?



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
[mylib.sources]
include_directories = ["mylib/include"]
source_directories = ["mylib/src"]

# Build an executable and link the library
[myexe]
[myexe.sources]
include_directories = ["myexe/include"]
source_directories = ["myexe/src"]

[myexe.link]
dependencies = ["mylib"]
flags = ["-DMYLIB_SOME_DEFINE"]
```



A package used by a target
----------------------------------------------

`mypackage/clang-build.toml`
```TOML
# Build a library
[mylib]
[mylib.sources]
include_directories = ["mylib/include"]
source_directories = ["mylib/src"]
```

`myexe/clang-build.toml`
```TOML
# Include an external package/target (i.e. not from this toml file)
[external] # should this be a reserved name??
[external.mylib]
add_search_directories = [".."] # all paths by default relative to the toml file

# Build an executable and link the library
[myexe]
[myexe.sources]
include_directories = ["include", "mylib.sources.include_directories"]
source_directories = ["src"]

[myexe.link]
dependencies = ["mylib"]
flags = ["-DMYLIB_SOME_DEFINE"]
```



Nested target in package
----------------------------------------------

`mypackage/clang-build.toml`
```TOML
# Include an external package/target (i.e. not from this toml file)
[external] # should this be a reserved name??
[external.mycorelib]
version = 2.4.5 # if available
version_required = 2.4 # failure if not satisfied

### Maybe instead:
[mycorelib]
external = true
version = 2.4.5 # if available
version_required = 2.4 # failure if not satisfied
# optionally specify additional search paths, ".", "/usr/local" etc are in default
###

# Build a library
[mylib]
[mylib.sources]
include_directories = ["mylib/include"]
source_directories = ["mylib/src"]
[mylib.link]
dependencies = ["mycorelib"]
```

`mypackage/mycorelib/clang-build.toml`
```TOML
# Build a library
[mycorelib]
version = 2.4.6 # this automatically defines mylib.version.major etc.
[mycorelib.sources]
include_directories = ["mycorelib/include"]
source_directories = ["mycorelib/src"]
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
flags = ["-DMYLIB_SOME_DEFINE"]
```