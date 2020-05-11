import clang_build

"""
Sources can be generated and subsequentially a project created
"""

def get_project(directory, environment, parent=None) -> clang_build.project.Project:
    print("------------------ mylib subproject start")
    print("parent:", parent)

    project_name = "mysubproject"
    project = clang_build.project.Project(project_name, {}, directory, environment, parent=parent)

    print("project identifier: ", project.identifier)

    target_name = "mylib"
    target = clang_build.target.TargetDescription(
        target_name,
        {
            "name": target_name,
            "target_type": "static library"
        },
        project
    )

    print("target identifier: ", target.identifier)

    project.add_targets([target])

    print("------------------ mylib subproject end")
    return project