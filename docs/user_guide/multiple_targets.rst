Multiple targets
================

For a lot of projects you will have more than one target. Maybe a main application, some libraries and
some test executables. Let's have a look at different scenarios of multiple targets in a single project.

Multiple self-developed targets
-------------------------------

In this first example we have a library and an executable both in the same project. We want to link the
library and the exectuable. This is our folder structure.

.. code-block:: text

    my_project
    ├── shared_headers
    |   └── header1.hpp
    ├── my_executable
    |   ├── include
    |   |   ├── header1.hpp
    |   |   └── header2.hpp
    |   └── src
    |       ├── src1.cpp
    |       └── src2.hpp
    ├── my_lib
    |   ├── include
    |   |   └── header3.hpp
    |   └── src
    |       └── src3.hpp
    └── clang-build.toml

The following `toml` file will create and link the targets:

.. code-block:: TOML

    [additional_includes]
        directory = "shared_headers"
        target_type = "header only"

    [my_library]
        directory = "my_lib"
        target_type = "shared library"
        dependencies = ["shared_headers"]

    [app]
        directory    = "my_executable"
        dependencies = ["my_lib", "shared_headers"]

As you can see we defined the shared headers as another target. Because there is no "additional_includes"
in Clang Build currently, this has the advantage, that we do not have to list the default folders as include
folders, too.

.. note:: Header files of dependencies are automatically also available for include, no extra configuration required!

External GitHub target
----------------------

Maybe you have a dependency on an external library on GitHub like Eigen. In this case we can use Clang Build's
feature to automatically download the library for you. If this is your folder structure:

.. code-block:: text

    my_project
    ├── include
    |   ├── cool_features.hpp
    |   └── math_lib.hpp
    ├── src
    |   ├── cool_features.cpp
    |   └── my_app.cpp
    └── clang-build.toml

and this is your toml file:

.. code-block:: TOML

    [myexe]
        dependencies = ["Eigen"]

    [Eigen]
        target_type = "header only"
        url         = "https://github.com/eigenteam/eigen-git-mirror"
    [Eigen.flags]
        compile  = ["-Wno-deprecated-declarations"]
        compileRelease = ["-DEIGEN_NO_DEBUG"]

Then you already have your project support Eigen. As soon as you run `clang-build`, it will download (or
use the cached version if you rebuild) Eigen and make it available for including its headers.