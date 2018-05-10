Subprojects
==============================================

In order to manage larger project structures and nested dependencies,
subprojects can be used.

Requirements
----------------------------------------------

### Project Naming

- When one or more subprojects are specified, the root project has to be named,
as targets are then identified by project.
- If a subproject is not given a name, it is required that the corresponding config file specifies a name

### Build Paths

If there is only a single project, the build paths will be the same as if only targets had been specified.
Otherwise, every project will get its own folder `build/projectname` and targets will get their own folders under this folder.

Example configuration file
----------------------------------------------

A simple example of a main project consuming a second one, which is located in a subdirectory:

```toml
name = "mainproject"

[myexe]
output_name  = "runLib"
dependencies = ["mysubproject.mylib"]
directory    = "myexe"


[[subproject]]
name = "mysubproject"
directory = "mylib"
```