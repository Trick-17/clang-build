Bundling
=================================

A common task for software developers is to make their projects
more accessible to non-developers, for example by creating binary
releases.

`clang-build` carries the following opinion:
non-system packages should work on their own, i.e. they should
bring their own dependencies with them. This means that a
redistributable bundle can simply be a zip archive.


Build-folder binary bundle
---------------------------------

You can use the `--bundle` flag to tell `clang-build` to gather all
dependencies of executable and shared library targets next to them
into their respective build folders. They should then be usable on
their own, i.e. without manually gathering additional binaries.

For example, the binary build folders on Linux may then look as follows:

.. code-block:: text

    build
    ├── myexe/default/bin
    |   ├── myexe
    |   ├── libA.so
    |   └── libB.so
    ├── libA/default/bin
    |   ├── libA.so
    |   └── libB.so
    └── libB/default/bin
        └── libB.so


On Linux and OSX, the `-rpath` flag is automatically used to cause
those targets to search for dependencies in their own directory.

Regardless of whether you use Linux, OSX or Windows, you can then
run your executables without having to make sure that the right
dependencies are found.


Redistributable bundle
---------------------------------

**This feature is still experimental and not fully implemented**

A redistributable bundle is what someone would need to run an
executable or use a library. A main purpose is to create a bundle
which will make it easy for someone to create e.g. a system package
or an installer out of it.

Each target gathers from itself and its dependencies, depending
on its type:

- For an executable
    - the executable
    - shared library dependencies
    - runtime files (config, resource, shaders, ...)
- For a shared library
    - the shared library
    - shared library dependencies
    - own header files and those of dependencies
    - usage instructions (compiler/linker flags)
- For a static library
    - the static library
    - shared library dependencies
    - own header files and those of dependencies
    - usage instructions (compiler/linker flags)
- For a header only library
    - own header files and those of dependencies
    - usage instructions (compiler/linker flags)

On OSX, this will be a `.app` folder.
On Linux and Windows, this will be a regular folder with a structure

.. code-block:: text

    build/myexe/default/redistributable
    ├── README.md
    ├── bin
    |   ├── myexe
    |   ├── libA.so
    |   └── libB.so
    └── res
        ├── config.toml
        └── img
            ├── logo.icns
            └── background.png

    build/libA/default/redistributable
    ├── instructions.toml
    ├── README.md
    ├── bin
    |   ├── libA.so
    |   └── libB.so
    └── include
        ├── libA
        |   └── libA.hpp
        └── libB
            └── libB.hpp