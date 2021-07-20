Toolchains
==============================================


clang-build also allows you to use a different toolchain than llvm-clang. For
this, you need to create a Python-file which you pass to clang-build as
`clang-build ... --toolchain=/path/to/your_toolchain.py` and which defines the
following function

.. code-block:: Python

    import clang_build

    def get_toolchain(environment) -> clang_build.toolchain.Toolchain:
        toolchain = clang_build.toolchain.Toolchain()
        #...
        return toolchain

The important part is the signature. Instead of using the default toolchain
provided by clang-build, you should derive from it or define a new one from
scratch.

The toolchain needs to provide
 - the build platform (on which clang-build is being run), e.g.
    - windows
    - osx
    - linux
 - the host platform (on which the build results may be run), e.g.
    - windows
    - osx
    - linux
    - web / browser
 - the host architecture (on which to run the built binaries), e.g.
    - x86
    - GPU
    - web / wasm
 - a list of supported C-dialect languages, e.g.
    - C
    - C++
    - CUDA-C
    - CUDA-C++
    - OpenCL
    - Objective-C
    - Objective-C++
 - default compile and link flags for all target types (executable, ...) for all build types (debug, ...) for the available languages for the given combination of build and host platform