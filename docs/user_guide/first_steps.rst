First steps
===========

Let's start with a very simple project. You only have one source file in your project
folder and you want to compile it into an executable.

.. image:: https://thumbs.gfycat.com/BewitchedAshamedDeermouse-size_restricted.gif


The minimum working example
---------------------------

.. code-block:: text

    my_project
    └── my_app.cpp

All you have to do, to compile this app is go into your project folder and call

.. code-block:: console

    clang-build

Your project quickly grows and you decide to put all your headers into an `include` folder
and all your source files into a `src` folder.

.. code-block:: text

    my_project
    ├── include
    |   ├── cool_features.hpp
    |   └── math_lib.hpp
    └── src
        ├── cool_features.cpp
        └── my_app.cpp

To compile your project, you just go into your project folder and call:

.. code-block:: console

    clang-build

The `include` folder will automatically be added as an include folder to clang. So all files
in the `include` folder or subfolders of the `include` folder can be included in the source files
in the `src` folder as you would normally do:

.. code-block:: c++

    // my_app.cpp
    #include "math_lib.hpp"
    // ...

At the same time, all source files in the `src` folder and subfolders of the `src` folder are
automatically detected, compiled and linked into one executable.


Switching between debug and release
-----------------------------------
By default Clang Build compiles in `Release` mode meaning optimizations are turned on. If you want
to debug an application, you need to pass extra flags to the compiler. Clang Build does this automatically
if you pass it the debug flag:

.. code-block:: console

    clang-build --build-type debug

or

.. code-block:: console

    clang-build -b debug