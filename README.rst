Clang-build
===========

Linux and OSX test: |Test status Travis| Windows test: |Test status AppVeyor| Code quality: |codacy| Coverage: |coverage|


**Motivation:**

-  Meta build systems are inherently the wrong way to go, either the build system or the compiler should be platform-agnostic (ideally both).
-  Trying to cover all use-cases is the wrong way to go - there is no need to let people do it the wrong way
-  CMake is cumbersome, unnecessarily generic and verbose and people should not need a programming/scripting language whose only purpose is to build C++
-  With Clang, finally a properly cross-platform compiler exists

**Goals:**

-  One compiler (Clang), one build system (written in Python)
-  Simple projects should be simple to build
-  Build process for reasonable project structures should still be easy
-  Adding third-party dependencies should be manageable

**Related resources:**

-  `CppCon 2017: Isabella Muerte "There Will Be Build Systems: I
   Configure Your
   Milkshake" <https://www.youtube.com/watch?v=7THzO-D0ta4>`__
-  https://medium.com/@corentin.jabot/accio-dependency-manager-b1846e1caf76


Usage
=====

In order to run ``clang-build``, you only need Clang and Python3.
Install via ``pip install clang-build`` (add the ``--user`` flag if you don't have admin rights).

Running ``clang-build`` will try to build the current directory.
The command-line options include

-  ``-d path/to/dir`` to build a different directory
-  ``-p`` to show a progress bar
-  ``-V`` to print some additional info
-  ``--debug`` to print the called clang commands

The given directory will be searched for a ``clang-build.toml`` file, which you can use to configure
your build targets, if necessary. However, if you only want to build an executable, you will
likely not even need a build file.

clang-build tries to use sane defaults, designed to make most projects very easy to configure
and even complex projects far easier than with common build or meta-build systems.


General Ideas
=============
*Note: not all of these are implemented, yet.*

What should be trivial
----------------------

This would be things that require only the invocation of ``clang-build``
and no build file.

-  build a hello world program (i.e anything with single main and
   without non-std dependencies)
-  build a reasonable MWE with local dependencies (potentially folder
   structure with e.g. ``src``, ``include/MWE`` and
   ``include/thirdparty``)
-  include stdlib
-  include anything that can be found by sane default search
-  using command line arguments:
-  specify root/source folder
-  set build type from (last used should be cached/remembered)
-  set build verbosity

Sane defaults and default behaviour:

-  platform-independence
-  build into a "build/" directory, not into toplevel
-  for multiple targets build into "build/target"
-  default search paths for different platforms, including also e.g.
   "./include", "./lib", "./build/lib", "/usr/local/...", ...

What should be easy
-------------------

This would be things that only require a minimal TOML project file

-  add dependency / external project from source folder or remote (e.g.
   github)
-  header-only should be trivial
-  for a regular (not too complicated) library it should be easy to
   write a build config
-  create a library from one subfolder, an executable from another and
   link them
-  setting target-specific (note: defaults should be sane!)
-  source file extensions
-  source directories
-  compile and link flags
-  optional version
-  dependencies (which may include non-targets, e.g. configuration
   steps)
-  properties (required c++ version, definitions/\ ``#define``\ s, ...)
-  access to flag "lists" such as flags for
-  coverage
-  cuda
-  openmp
-  set target-specific flags, include folders, etc. which should not be
   propagated to dependency parents as "private"

What should be possible
-----------------------

Steps that would involve more effort from the user, including possibly
some python code

-  a Target configuration step before building (e.g. for more involved
   version numbering)
-  through the configuration step, inclusion of e.g. CMake-project
   should be possible
-  packaging: any target may be packaged, meaning it's dependencies are
   handled and if built, binaries may be bundled
-  external package dependencies
-  binaries on a server
-  source on a server (fallback from binaries)
-  binaries on disk, try to determine version from path and file names
-  source on disk, try to determine version from path and file names


Project File By Example
=======================

A single target
---------------

Note:

-  by default, the root and <targetname> folders, as well as "include" and "src" subdirectories will be searched for ".hpp", ".hxx", ".h" and ".cpp", ".cxx" and ".c" files
-  a target without ``target_type``, but with source files will be an executable
-  ``output_name`` should not contain pre- or suffixes such as lib, .exe, .so, as they are added automatically
-  if we don't care about the output name, in this case we could skip the project file entirely

.. code:: toml

    # Top-level brackets indicate a target
    [hello]
    output_name = "runHello"

Two targets with linking
------------------------

.. code:: toml

    # Build a library
    [mylib]
    target_type = "shared library"

    # Build an executable and link the library
    [myexe]
    output_name = "runExe"
    target_type = "executable"
    dependencies = ["mylib"]
    [myexe.flags]
    link = ["-DMYEXE_SOME_DEFINE"]

Adding external dependencies
----------------------------

Note:

-  external projects will be copied/downloaded into "build/targetname/external_sources"
-  you can specify a subdirectory, if the thirdparty code has an unusual structure
-  further granularity is given by ``include_directories`` and ``source_directories``

.. code:: toml

    [mylib]
    url = "https://github.com/trick-17/mylib"
    version = 1.1 # will try to `git checkout 1.1`
    directory = "sources"           # will point to "build/mylib/external_sources/sources"
    [mylib.sources]
    include_directories = ["mylib/include"] # will point to "build/mylib/external_sources/sources/mylib/include"
    source_directories  = ["mylib/src"]     # will point to "build/mylib/external_sources/sources/mylib/src"
    # Maybe we need to deactivate annoying warnings coming from the library
    [mylib.flags]
    compile = ["-Wno-deprecated-declarations", "-Wno-self-assign"]

    # Build an executable and link the library
    [myexe]
    dependencies = ["mylib"]


.. |Test status Travis| image:: https://travis-ci.org/Trick-17/clang-build.svg?branch=master
   :target: https://travis-ci.org/Trick-17/clang-build
.. |Test status AppVeyor| image:: https://ci.appveyor.com/api/projects/status/57qv53r4totihxrj/branch/master?svg=true
   :target: https://ci.appveyor.com/project/GPMueller/clang-build
.. |codacy| image:: https://api.codacy.com/project/badge/Grade/2bcc761ed19844c48f92f7779e2cf67f
   :target: https://www.codacy.com/app/Trick-17/clang-build?utm_source=github.com&amp;utm_medium=referral&amp;utm_content=Trick-17/clang-build&amp;utm_campaign=Badge_Grade
.. |coverage| image:: https://codecov.io/gh/Trick-17/clang-build/branch/master/graph/badge.svg
  :target: https://codecov.io/gh/Trick-17/clang-build