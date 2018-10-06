Platform dependence
==============================================


Per-Platform Target Configuration
----------------------------------------------

The following lists and sections of the target configuration can be specified individually per platform:

- `include_directories` and `public_include_directories`
- `sources`
- `flags`

Available platforms are `osx`, `linux` and `windows`.
The corresponding platform-specific lists are merged with the general lists,
meaning that they are not overridden.


Example
----------------------------------------------

.. code-block:: TOML

    [mylib]
        target_type = "static library"
        include_directories_public = ["include"]
        sources = ["src/common.c"]

        [mylib.public-flags]
            compile = ["-DMYLIB_VERSION_MAJOR=2", "-DMYLIB_VERSION_MINOR=1", "-DMYLIB_VERSION_PATCH=2"]

        [mylib.osx]
            include_directories = ["include/osx"]
            sources = ["src/osx/cocoa.m", "src/osx/handle.cpp"]

            [mylib.osx.flags]
                compile = ["-DMYLIB_OSX"]
            [mylib.osx.interface-flags]
                link = ["-framework", "Cocoa"]

        [mylib.windows]
            include_directories = ["include/win"]
            sources = ["src/win/win32.cpp", "src/win/handle.cpp"]

            [mylib.windows.flags]
                compile = ["-DMYLIB_WINDOWS", "-D_CRT_SECURE_NO_WARNINGS"]
                link = ["-luser32.lib"]