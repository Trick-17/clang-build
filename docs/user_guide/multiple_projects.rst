Multiple projects
==============================================

In order to manage larger project structures and nested dependencies,
subprojects can be used.


Requirements
----------------------------------------------

**Project Naming**

- When one or more subprojects are specified, the root project has to be named,
  as targets are then grouped and identified by project.
- If a subproject is not given a name, it is required to be external and that
  the corresponding config file specifies a name

**Build Paths**

If there is only a single project, the build paths will be the same as if only targets had been specified.
Otherwise, every project will get its own folder `build/projectname` and targets will get their own folders under this folder.


Example configuration file
----------------------------------------------

A simple example of a main project consuming a second one, which is located in a subdirectory:

.. code-block:: TOML

    name = "mainproject"

    [myexe]
    output_name  = "runLib"
    dependencies = ["mysubproject.mylib"]
    directory    = "myexe"


    [[subproject]]
    name = "mysubproject"
    directory = "mylib"

See also `test/subproject <https://github.com/Trick-17/clang-build/tree/master/test/subproject>`_

Instead of `directory`, you may also specify `url` -- analogous to external targets -- to fetch
an external repository and use it's build config as a subproject configuration file.
Note: the external repository may simply contain a single configuration file, specifying targets
to be fetched from various other repositories (e.g. boost).


Multiple subprojects in the same file
----------------------------------------------

A second simple example:

.. code-block:: TOML

    name = "mainproject"

    [myexe]
    output_name  = "runLib"
    dependencies = ["mysubproject.mylib"]
    directory    = "myexe"


    [[subproject]]
    name = "mysubproject"

    [subproject.mylib]
    target_type  = "static library"

See also `test/boost-filesystem <https://github.com/Trick-17/clang-build/tree/master/test/boost-filesystem>`_