Tests and Examples
==============================================

It is common for projects to provide tests and often also examples.
`clang-build` can automatically generate the binaries and link them.
The following descriptions are made on the basis of tests, but the
equivalent rules apply to examples.

See also `test/tests_examples <https://github.com/Trick-17/clang-build/tree/master/test/tests_examples>`_

Folder structure
----------------------------------------------

It is commonplace for tests to be written per target and positioned
in a "test" or "tests" folder inside the target folder.
`clang-build` expects this project structure for automatic detection.

The following structure will automatically build the two examples and
three test executables.

.. code-block:: text

    mylib
    ├── examples
    |   ├── basics.cpp
    |   └── advanced.cpp
    ├── include
    |   └── mylib.hpp
    └── tests
        ├── interface.cpp
        ├── inner_functions.cpp
        └── combinations.cpp

Additional Configuration
----------------------------------------------

To add manual configuration to your tests, you can add a section to
the configuration of your target:

.. code-block:: TOML

    [mylib]
        [mylib.tests]
            single_executable = true
            dependencies = ["catch"]

    [catch]
        url = "https://github.com/catchorg/Catch2"
        include_directories_public = ["single_include"]
        [catch.tests]
            sources_exclude = ["*"]
        [catch.examples]
            sources = ["010-TestCase.cpp", "231-Cfg-OutputStreams.cpp"]

Note the new keyword `single_executable`, which is available for tests
but not for examples. This allows the distinctions between tests which
should be compiled into one big executable and a single file per test
structure.

As with regular targets, test sources can be selected with the `sources`
and `sources_exclude` keywords.

The corresponding command line arguments (see also the output of
`clang-build -h`) give a user the ability to either compile the tests
of the root targets or of all targets.