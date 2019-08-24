GLFW
==============================================

This is a configuration to build GLFW with the OpenGL backend.
It has not yet been tested on Linux and building the Vulkan
backend has not yet been attempted.

.. code-block:: TOML
    name = "glfw"
    url = "https://github.com/glfw/glfw"

    [glfw]
        target_type = "static library"
        include_directories = ["include", "src", "deps"]
        sources = ["src/context.c", "src/init.c", "src/input.c", "src/monitor.c", "src/vulkan.c", "src/window.c",
                    "deps/glad.c", "deps/getopt.c", "deps/tinycthread.c"]

        [glfw.osx]
            sources = ["src/cocoa_init.m", "src/cocoa_joystick.m", "src/cocoa_monitor.m", "src/cocoa_window.m",
                        "src/cocoa_time.c", "src/posix_thread.c", "src/nsgl_context.m", "src/egl_context.c",
                        "src/osmesa_context.c"]
            [glfw.osx.flags]
                compile = ["-D_GLFW_COCOA",
                            "-Wdeclaration-after-statement", "-Wno-extra-semi",
                            "-Wno-sign-compare", "-Wno-unused-parameter", "-Wno-missing-field-initializers",
                            "-Wno-pedantic"]
            [glfw.osx.interface-flags]
                link = ["-framework", "Cocoa",
                        "-framework", "IOKit",
                        "-framework", "CoreFoundation",
                        "-framework", "CoreVideo"]

        [glfw.windows]
            sources = ["src/win32_init.c", "src/win32_joystick.c", "src/win32_monitor.c", "src/win32_time.c", "src/win32_thread.c",
                        "src/win32_window.c", "src/wgl_context.c", "src/egl_context.c", "src/osmesa_context.c"]
            [glfw.windows.flags]
                compile = ["-D_GLFW_WIN32", "-D_CRT_SECURE_NO_WARNINGS",
                        "-Wno-unused-parameter", "-Wno-missing-field-initializers", "-Wno-pedantic"]
            [glfw.windows.interface-flags]
                link = ["-luser32.lib", "-lshell32.lib", "-lgdi32.lib"]

        [glfw.tests]
            single_executable = false
            sources_exclude = ["vulkan.c", "windows.c", "glfwinfo.c", "triangle-vulkan.c"]
            dependencies = ["glad", "tinycthread"]
            [glfw.tests.flags]
                compile = ["-Wno-unused-parameter", "-Wno-sign-compare", "-Wno-missing-field-initializers"]

        [glfw.examples]
            dependencies = ["glad"]
            [glfw.examples.flags]
                compile = ["-Wno-unused-parameter"]
            [glfw.examples.windows.flags]
                compile = ["-Wno-deprecated-declarations"]

    [glad]
        target_type = "static library"
        include_directories_public = ["deps"]
        sources = ["deps/glad_gl.c"]
        [glad.tests]
            sources_exclude = ["*"]
        [glad.examples]
            sources_exclude = ["*"]

    [getopt]
        target_type = "static library"
        include_directories_public = ["deps"]
        sources = ["deps/getopt.c"]
        [getopt.tests]
            sources_exclude = ["*"]
        [getopt.examples]
            sources_exclude = ["*"]

    [tinycthread]
        target_type = "static library"
        include_directories_public = ["deps"]
        sources = ["deps/tinycthread.c"]
        [tinycthread.flags]
            compile = ["-Wno-unused-parameter"]
        [tinycthread.windows.flags]
            compile = ["-Wno-deprecated-declarations"]
        [tinycthread.tests]
            sources_exclude = ["*"]
        [tinycthread.examples]
            sources_exclude = ["*"]