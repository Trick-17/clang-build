import clang_build

"""
Sources can be generated and subsequentially a project created
"""

def get_project(directory, environment, parent=None) -> clang_build.project.Project:
    with open(directory / "main.cpp", "w") as fh:
        fh.write(
            "#include <iostream>\n"
            "\n"
            "int main()\n"
            "{\n"
            "    std::cerr << \"............\\n\";\n"
            "    return 1;\n"
            "}")
    return clang_build.project.Project.from_directory(directory, environment, parent=parent)