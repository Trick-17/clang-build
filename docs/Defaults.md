
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