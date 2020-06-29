Adding projects with custom behaviour
==============================================


Instead of configuring a project using a "clang-build.toml",
you can also use a "clang-build.py" script.
This allows you, for example, to generate a version-header
based on git tags or to (de-)activate features or targets
depending on environment variables.


Script requirements
----------------------------------------------

The "clang-build.py" script, is required to define
the following function:

.. code-block:: Python

    import clang_build

    def get_project(directory, environment, parent=None) -> clang_build.project.Project:
        project = clang_build.project.Project("projectname", {}, directory, environment, parent=parent)
        #...
        return project


Creating a project
----------------------------------------------

You can default-initialize a project without targets
or let clang-build create the project for you, from a
folder or from a configuration `dict`.

.. code-block:: Python

    from clang_build.project import Project

    def get_project(directory, environment, parent=None) -> Project:
        # Empty project:
        project = Project("projectname", {}, directory, environment, parent=parent)
        # Use defaults to initialize from a folder:
        project = Project.from_directory(directory, environment, parent=parent)
        # Use a dictionary:
        project = Project.from_config({}, directory, environment, parent=parent)


Creating targets
----------------------------------------------

A target always belongs to a project, meaning you
need to create a project first. Then,

.. code-block:: Python

    def get_project(directory, environment, parent=None) -> clang_build.project.Project:
        project = #...
        target = clang_build.target.TargetDescription("targetname", {}, project)
        project.add_targets([target])
        return project


Manipulating sources
----------------------------------------------

Both projects and targets may fetch external sources,
if a `url` is provided. The source fetching process can
be customised by overriding their `get_sources` functions.

.. code-block:: Python

    class CustomSources(clang_build.target.TargetDescription):
        def get_sources(self):
            # The base class `get_sources` checks if a `url` was specified in
            # the config, in which case it will download the sources
            super().get_sources()
            # Write some sources
            # ...

Note, when generating sources you should use the properties
of `TargetDescription` to place them in the right folder.