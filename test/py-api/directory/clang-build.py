import clang_build

"""
Sources can be generated and subsequentially a project created
"""

def get_project(directory, environment, parent=None) -> clang_build.project.Project:
    with open(directory / "version.h", 'w') as f:
        f.write(
            "#define VERSION_MAJOR 1\n"
            "#define VERSION_MINOR 2\n"
            "#define VERSION_PATCH 0")
    with open(directory / "main.cpp", "w") as fh:
        fh.write(
            "#include <iostream>\n"
            "#include \"version.h\"\n"
            "\n"
            "int main()\n"
            "{\n"
            "    std::cerr << \"the version is \" << VERSION_MAJOR << \".\" << VERSION_MINOR << \".\" << VERSION_PATCH << std::endl;\n"
            "    return 0;\n"
            "}")

    project = clang_build.project.Project("", {}, directory, environment, parent=parent)
    target = clang_build.target.TargetDescription("", {}, project)
    project.add_targets([target])

    return project