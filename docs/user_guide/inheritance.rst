Inheritance
==============================================


Include directories
----------------------------------------------

**`include-directories`**

    A list of private include directories, i.e. accessible only to the target itself.

    Defaults are the target directory and "include".

**`public-include-directories`**

    A list of public include directories, which are accessible to any dependent target.
    Note that these are forwarded up the dependency graph, i.e. a target adds all of
    its dependencies' public include directories to its own public include directories.

    "include" is the default public include directory if none are specified

**Example:**

.. code-block:: TOML

    [mylib]
        include_directories = ["src/mylib/include", "src/mylib/detail/include"]
        public_include_directories = ["src/mylib/include"]


Flags
----------------------------------------------

The following sections of a target configuration can each contain `compile` and
`link` lists of flags.

**`flags`**

    Private flags which are only applied to the target itself, with the exception
    of header-only libraries, for which they are added to the public flags.

**`interface-flags`**

    Interface flags are potentially applied to dependent targets, but not the target itself.
    An example use-case is a static library, which depends on a dynamic library, which can
    therefore not be linked into the target itself.

    Executables and shared libraries will apply the interface flags of their dependencies
    to themselves (i.e. add them to their own `flags`) and will not forward them.

    Header only and static libraries will not apply their dependencies' interface flags to
    themselves, but will forward them (i.e. add them to their own `interface-flags`).

**`public-flags`**

    Public flags are applied to the target and any dependent target.

    Public flags are always forwarded (i.e. added to a target's own `public-flags`).


Note a slightly subtle difference between interface and public flags:
interface flags are not forwarded beyond a shared library, while public flags are
forwarded up until an executable.