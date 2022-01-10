Project settings
==============================================


Examples of the project config parameters in use can be found in test/public_dependency.


**name** (optional)

A name is required if a project has subprojects.

:`type`:        string
:`default`:     "project"


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


**subprojects** (optional)

:`type`:        list of strings
:`default`:     []