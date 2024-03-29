boost/filesystem
==============================================

This example contains what you need in order to build boost/filesystem, but
for now without examples or tests. It requires a few other boost-libraries,
most of which are header-only.

.. code-block:: TOML

    name = "boost"

    [filesystem]
        target_type = "static library"
        url = "https://github.com/boostorg/filesystem"
        version = "boost-1.65.0"
        dependencies = ["detail"]
        public_dependencies = ["assert", "config", "core", "io", "iterator", "functional", "mpl", "predef", "range", "smart_ptr", "static_assert", "system", "throw_exception", "type_traits"]
        [filesystem.flags]
            compile = ["-Wno-parentheses-equality", "-Wno-unused-parameter", "-Wno-nested-anon-types", "-Wno-vla-extension", "-Wno-pedantic"]

    [system]
        target_type = "static library"
        url = "https://github.com/boostorg/system"
        version = "boost-1.65.0"
        dependencies = ["core", "winapi", "config", "predef", "assert"]
        [system.public_flags]
            compile = ['-DBOOST_NO_CXX11_HDR_SYSTEM_ERROR', '-Wno-deprecated-declarations', '-Wno-language-extension-token']

    [winapi]
        url = "https://github.com/boostorg/winapi"
        version = "boost-1.65.0"

    [config]
        url = "https://github.com/boostorg/config"
        version = "boost-1.65.0"

    [core]
        url = "https://github.com/boostorg/core"
        version = "boost-1.65.0"

    [smart_ptr]
        url = "https://github.com/boostorg/smart_ptr"
        version = "boost-1.65.0"

    [preprocessor]
        url = "https://github.com/boostorg/preprocessor"
        version = "boost-1.65.0"

    [mpl]
        url = "https://github.com/boostorg/mpl"
        version = "boost-1.65.0"
        dependencies = ["preprocessor"]

    [io]
        url = "https://github.com/boostorg/io"
        version = "boost-1.65.0"

    [detail]
        url = "https://github.com/boostorg/detail"
        version = "boost-1.65.0"

    [functional]
        url = "https://github.com/boostorg/functional"
        version = "boost-1.65.0"

    [throw_exception]
        url = "https://github.com/boostorg/throw_exception"
        version = "boost-1.65.0"

    [iterator]
        url = "https://github.com/boostorg/iterator"
        version = "boost-1.65.0"
        dependencies = ["detail"]

    [predef]
        url = "https://github.com/boostorg/predef"
        version = "boost-1.65.0"

    [range]
        url = "https://github.com/boostorg/range"
        version = "boost-1.65.0"

    [assert]
        url = "https://github.com/boostorg/assert"
        version = "boost-1.65.0"

    [static_assert] # has sources which should not be included
        target_type = "header only"
        url = "https://github.com/boostorg/static_assert"
        version = "boost-1.65.0"

    [utility] # has sources which should not be included
        target_type = "header only"
        url = "https://github.com/boostorg/utility"
        version = "boost-1.65.0"

    [type_traits]
        url = "https://github.com/boostorg/type_traits"
        version = "boost-1.65.0"