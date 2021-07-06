Inheritance
==============================================


General
----------------------------------------------

In the following, "private" generally means that a target only needs the corresponding
flags, include-directories or dependencies internally, i.e. they are not needed in
consumers' code and should therefore not be applied to dependent targets.

As one should carefully choose which of these to expose to ones users, "private" is the
default and "public" or "interface" need to be explicitly stated where needed.

The distinction from "public" becomes important when your dependency-graph grows to more
than two layers, as you want to be able to tell what your top-level targets can include
and what gets linked.
Additionally, if everything was public, no two targets in the entire dependency-graph
would be allowed to depend on different versions of the same library.


Include directories
----------------------------------------------

**`include_directories`**

    A list of private include directories, i.e. accessible only to the target itself.

    Exceptions: for header-only libraries, they are treated as public.

    Default, if none are specified: the target directory and "include", if they exist.

**`public_include_directories`**

    A list of public include directories, which are accessible to any dependent target.

    Note that these can be forwarded up the dependency graph, as a target adds all of its
    public dependencies' public include directories to its own `public_include_directories`.
    The public include directories of a targets private dependencies are added to its
    `include_directories`

    Default, if none are specified: "include", if it exists.

**Example:**

.. code-block:: TOML

    [mylib]
        include_directories        = ["src/mylib/include", "src/mylib/detail/include"]
        public_include_directories = ["src/mylib/include"]


Flags
----------------------------------------------

The following sections of a target configuration can each contain `compile` and
`link` lists of flags.

**`flags`**

    Private flags which are only applied to the target itself.

    Exceptions: for header-only libraries, they are treated as public.

**`public_flags`**

    Public flags are applied to the target itself, as well as any dependent targets.

    Note that these can be forwarded up the dependency graph, as a target adds all of its
    public dependencies' public flags to its own `public_flags`.
    The public flags of a targets private dependencies are added to its `flags`.

**`interface_flags`**

    Interface flags are not applied to the target itself, but instead to the next
    transitively dependent shared library or executable.

    Executables and shared libraries will apply the interface flags of their private and
    public dependencies to themselves (i.e. add them to their own `flags`) and will not
    forward them.

    Header-only and static libraries will not apply their private or public dependencies'
    interface flags to themselves, but will forward them (i.e. add them to their own
    `interface_flags`).

An example use-case is a static library A, which depends on a dynamic library B. As B
cannot be linked into A, it needs to be linked to the next shared library or executable
which depends directly or transitively on A.

**Example:**

.. code-block:: TOML

    [mylib]
        target_type     = "static library"
        flags           = ["-Wno-unused-parameter"]
        public_flags    = ["-DMYLIB_NO_EXCEPTIONS"]
        interface_flags = ["-lpthread"]


Dependencies
----------------------------------------------

**Example:**

In the following example, "src/C/include" will be available to app as it is
forwarded by A, while "src/B/include" will not be available because B is a
private dependency of A.

.. code-block:: TOML

    [app]
        dependencies = ["A"]

    [A]
        target_type         = "static library"
        dependencies        = ["B"]
        public_dependencies = ["C"]

    [B]
        target_type                = "shared library"
        public_include_directories = ["src/B/include"]

    [C]
        target_type                = "shared library"
        public_include_directories = ["src/C/include"]