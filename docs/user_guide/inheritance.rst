Inheritance
==============================================


General
----------------------------------------------

Targets can inherit include directories and flags from their direct, as well as
transitive, dependencies.
The classification of dependencies as "private" or "public" determines their
visibility to transitively dependent targets. Private dependencies are intended as
internal to a target and public dependencies are part of a targets interface.

Which include directories and flags are visible to dependent targets is in turn
determined by an additional classification into "private"/"public" and "private"/
"public"/"interface", respectively.

As one should carefully choose, which of these to expose to ones users, "private"
is the default and "public" and "interface" are made explicit in the corresponding
keywords.
Note, the distinction from "public" becomes important when your dependency-graph
grows to more than two layers, as you want to be able to tell what your top-level
targets can include and what gets linked.
Additionally, if everything was public, no two targets in the entire dependency-
graph would be allowed to depend on different versions of the same library.

The specific inheritance rules are determined by the combination of the
classification of dependenies and the classification of include directories and
flags. They are described in detail below.


Include directories
----------------------------------------------

**`include_directories`**

    A list of private include directories, i.e. accessible only to the target itself.

    Exceptions: for header-only libraries, they are treated as public.

    Default, if none are specified: the target directory and "include", if they exist.

**`public_include_directories`**

    A list of public include directories, which are accessible to the target itself and
    any dependent target.

    A target forwards its public dependencies' public include directories, i.e. it adds
    them to its own `public_include_directories`. The public include directories of a
    targets private dependencies are added to its (private) `include_directories`.

    Default, if none are specified: "include", if it exists.

Note that this mechanism allows `public_include_directories` to be forwarded far up the
dependency graph. You may want to keep them minimal and follow best practices for your
folder structure, in order to avoid confusion in larger projects.

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

    A target forwards its public dependencies' public flags, i.e. it adds them to its own
    `public_flags`. The public flags of a targets private dependencies are added to its
    (private) `flags`.

Note that this mechanism allows `public_flags` to be forwarded far up the dependency graph,
so it is recommended to be mindful of the flags added here. For example, don't put force
your users to adopt your warning settings by putting flags like `-Werror` here.

**`interface_flags`**

    Interface flags are not applied to the target itself, but instead to the next
    transitively dependent shared library or executable.

    Executables and shared libraries will apply the interface flags of their private and
    public dependencies to themselves (i.e. add them to their own private `flags`).
    They will not be forwared (added to their own `interface_flags` or `public_flags`).

    Header-only and static libraries will not apply their private or public dependencies'
    interface flags to themselves, but will forward them (i.e. they will add them to their
    own `interface_flags`).

An example use-case is a static library `A`, which depends on a dynamic library `B`. As `B`
cannot be linked into `A`, it needs to be linked to the next shared library or executable
which depends directly or transitively on `A`.

**Example:**

.. code-block:: TOML

    [mylib]
        target_type     = "static library"
        [mylib.flags]
            compile = ["-Wno-unused-parameter"]
        [mylib.public_flags]
            compile = ["-DMYLIB_NO_EXCEPTIONS"]
        [mylib.interface_flags]
            link = ["-lpthread"]


Dependencies
----------------------------------------------

**Example:**

In the following example, "src/C/include" will be available to `app` as it is
forwarded by `A`, while "src/B/include" will not be available because `B` is a
private dependency of `A`.

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