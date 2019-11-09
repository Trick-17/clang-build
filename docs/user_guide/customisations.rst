Customisations
==============

Let's have a look at some of the ways you can configure your project, if it does not have
a default setup such as in the example above.

Custom target name
------------------

First you might want to customize the name of the executable of your project. To do this you can
add a `clang-build.toml` file to your project.

.. code-block:: text

    my_project
    ├── include
    |   ├── cool_features.hpp
    |   └── math_lib.hpp
    ├── src
    |   ├── cool_features.cpp
    |   └── my_app.cpp
    └── clang-build.toml

The `toml` file looks as follows:

.. code-block:: TOML

    [myexe]
        output_name = "MyNextApp-v1.0"

Here the square brackets define a target. Since only the `output_name` is given, Clang Build continues
to assume that a default project is inside this folder, with the default folder names. This is of course
the case in the example above sou you can simply call:

.. code-block:: console

    clang-build

and your project get's compiled.

Custom folder names
-------------------

While it is common to have a folder structure like the one above, maybe for some reason
the folders are called differently in your project. While automatic detection now does not
work, you can just specify the folder names in your `toml`-file.

.. code-block:: text

    my_project
    ├── header_files
    |   ├── cool_features.hpp
    |   └── math_lib.hpp
    ├── external_header_files
    |   ├── collaborator1_interface.hpp
    |   └── collaborator2_interface.hpp
    ├── sauce
    |   ├── cool_features.cpp
    |   └── my_app.cpp
    └── clang-build.toml

The `toml` file now looks as follows:

.. code-block:: TOML

    [myexe]
        output_name = "MyNextApp-v1.0"
        include_directories = ["header_files", "external_header_files"]
        sources = ["sauce/*.cpp"]

Compiling a library
-------------------

If you want to compile a library instead of an executable, you can simply change
the target type in the toml file:

.. code-block:: TOML

    [mylib]
        output_name = "MyNextLibrary-v1.0"
        target_type = "shared library"

    [mylib-static]
        output_name = "MyNextLibrary-static-v1.0"
        target_type = "static library"