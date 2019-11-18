Automatic Target Creation
=================================

Tests
---------------------------------

Assuming a standard structure, such as the following, where
tests are located within a folder called `test` or `tests`,
`clang-build` will automatically detect sources and construct
corresponding tests.

.. code-block:: text

    my_project
    ├── build
    |   └── default
    |       └── tests
    |           └── bin
    |               └── test
    ├── mylib
    |   └── include
    |       └── mylib.hpp
    ├── tests
    |   ├── feature_a.cpp
    |   └── feature_b.cpp
    └── clang-build.toml

By default, this will produce a single executable, called `test`.

A `tests` block can be added to a target's configuration to
specify additional variables for the tests, analogous to a regular
target.

.. code-block:: TOML

    [mylib]
        [mylib.tests]
            single_executable = false
            dependencies = ["catch"]
            [mylib.tests.flags]
                compile = ["-Wno-unused-parameter"]

    [catch]
        url = "..."

If the sources should be compiled into one binary each, the flag
`single_executable = false` can be used. The build folder would
then look as

.. code-block:: text

    my_project
    └── build
        └── default
            └── tests
                ├── test_feature_a
                └── test_feature_a

Examples
---------------------------------

Examples work analogous to tests. The folder can be named `example`
or `examples`.

.. code-block:: text

    my_project
    ├── build
    |   └── default
    |       └── examples
    |           └── bin
    |               ├── example_feature_a
    |               └── example_feature_a
    ├── mylib
    |   └── include
    |       └── mylib.hpp
    ├── examples
    |   ├── feature_a.cpp
    |   └── feature_b.cpp
    └── clang-build.toml

This will produce two example binaries, named after their respective
sources. There is no option to produce a single example from multiple
source files.

An `examples` block can be added to a target's configuration to
specify additional variables for the examples, analogous to a regular
target.

.. code-block:: TOML

    [mylib]
        [mylib.examples.flags]
            compile = ["-Wno-unused-parameter"]