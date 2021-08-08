Target settings
==============================================


Declaration
----------------------------------------------

A target can be declared with a name square brackets.
If none are specified, the default name is "main".


General parameters
----------------------------------------------


**url** (optional)

:`type`:        string
:`default`:     ""


**version** (optional)

This only has an effect if a url was specified.

:`type`:        string
:`default`:     ""


**directory** (optional)

Note, if a url is specified, this is relative to the source root.

:`type`:        string
:`default`:     ""


**target_type** (optional)

:`type`:        string
:`default`:     if sources are found "executable", else "header only"
:`options`:     "executable", "shared library", "static library", "header only"


**dependencies** (optional)

:`type`:        list of strings
:`default`:     []


**public_dependencies** (optional)

:`type`:        list of strings
:`default`:     []


Source parameters
----------------------------------------------


**include_directories** (optional)

:`type`:        list of strings
:`default`:     []


**public_include_directories** (optional)

:`type`:        list of strings
:`default`:     []


**sources** (optional)

You can list files and/or glob patterns.

:`type`:        list of strings
:`default`:     if a "src" folder is present, any sources that are found inside, else any sources found in the target directory


**sources_exclude** (optional)

You can list files and/or glob patterns.

:`type`:        list of strings
:`default`:     []


Flag parameters
----------------------------------------------


Flags can be specified inside one of the following secions

- flags
- public_flags
- interface_flags

or nested into a platform-spcific section

- linux
- osx
- windows


**compile** (optional)

:`type`:        list of strings
:`default`:     []


**link** (optional)

:`type`:        list of strings
:`default`:     []


Output parameters
----------------------------------------------


**output_name** (optional)

:`type`:        string
:`default`:     ""


**output_prefix** (optional)

:`type`:        string
:`default`:     ""


**output_suffix** (optional)

:`type`:        string
:`default`:     ""