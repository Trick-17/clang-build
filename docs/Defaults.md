Defaults
==============================================


General
----------------------------------------------

By default:
- all relative paths in a toml are interpreted as relative to that toml file
- if only one target is built from source, it is built into `build/<build_type>`
- if more than one target is built from source, they are built into `build/<target_name>/<build_type>`
- an external target's sources will be copied/downloaded into `build/<target_name>/external_sources`
- targets for which sources are found will be built as `executable`
- targets for which no sources are found will be `header-only`


Search Paths
----------------------------------------------

### Include directories
Default system directories for `#include`-searches are given by Clang.

`clang-build`'s include directories will be added to the search paths and will be searched
for header files for a target.
In your project file, you can add an `include_directories` array to specify a target's header directories,
where by default `clang-build` will try the target's root directory and an "include" subdirectory.

### Source directories
`clang-build`'s source directories will be searched for source files for a target.
In your project file, you can add a `source_directories` array to specify a target's source directories,
where by default `clang-build` will try the target's root directory and a "src" subdirectory.


Build Type and Flags
----------------------------------------------

The most recent C++ standard will be used by adding e.g. `-std=c++17`.
By default, the two flags `-Wall -Werror` will be added everywhere, meaning that all warnings are
activated and all warnings are errors, so that unwanted warnings need to be explicitly disabled.

The `default` build type does not add any flags, however
- `release`:  adds `-O3 -DNDEBUG`
- `debug`:    adds `-O0 -g3 -DDEBUG`
- `coverage`: adds debug flags and `--coverage -fno-inline -fno-inline-small-functions -fno-default-inline`


Build Directories
----------------------------------------------

- build
  - targetname
    - external_sources
    - release
      - obj
      - dep
      - bin
      - lib
      - include
    - debug
      - ...
    - default
      - ...
    - ...
  - othertargetname
    - ...

*Note: "release", "debug", etc. directories will be placed directly into "build", if only one target is in the build configuration.*