import clang_build

def get_project(directory, environment, parent=None) -> clang_build.project.Project:

    py_include_dir = environment.toolchain.platform_defaults['PLATFORM_PYTHON_INCLUDE_PATH']
    py_library_dir = environment.toolchain.platform_defaults['PLATFORM_PYTHON_LIBRARY_PATH']
    py_library_name = environment.toolchain.platform_defaults['PLATFORM_PYTHON_LIBRARY_NAME']
    py_library_extension = environment.toolchain.platform_defaults['PLATFORM_PYTHON_EXTENSION_SUFFIX']

    project = clang_build.project.Project("", {}, directory, environment, parent=parent)

    pylib = clang_build.target.TargetDescription(
        "pylib",
        {
            "target_type": "shared library",
            "output_name": "pylib",
            "output_prefix": "",
            "output_suffix": py_library_extension,
            "dependencies": ["pybind", "mylib"],
            "sources": ["python/bindings.cpp"],
            "include_directories": [py_include_dir],
            "flags": {
                "compile": ['-Wno-deprecated-declarations'],
                "link": ['-Wno-deprecated-declarations', f'-L{py_library_dir}', f'-l{py_library_name}']
            },
            "windows": {
                "flags": {
                    "compile": ['-Dstrdup=_strdup']
                }
            },
        },
        project
    )

    mylib = clang_build.target.TargetDescription(
        "mylib",
        {
            "target_type": "static library",
            "output_name": "mylib",
            "sources": ["src/mylib.cpp"]
        },
        project
    )

    pybind = clang_build.target.TargetDescription(
        "pybind",
        {
            "target_type": "header only",
            "url": "https://github.com/pybind/pybind11"
        },
        project
    )

    project.add_targets([mylib, pylib, pybind])

    return project