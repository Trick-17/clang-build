import clang_build

"""
Sources can be generated and subsequentially a project created
"""

def get_project(directory, environment, parent=None) -> clang_build.project.Project:
    print("------------------ mylib subproject start")

    project_name = "mysubproject"
    target_name = "mylib"
    target_identifier = f"{project_name}.{target_name}"
    if parent:
        target_identifier = f"{parent.identifier}.{project_name}.{target_name}"

    print("parent: ", parent)
    print("target_identifier: ", target_identifier)

    target = clang_build.target.TargetDescription(target_name, {"target_type": "static library"}, target_identifier, parent.directory, parent.build_directory, environment)

    # project = clang_build.project.Project(directory, environment, parent=parent)
    project = clang_build.project.Project.from_targets(project_name, [], directory, environment, parent=parent)
    project.add_targets([target])

    print("------------------ mylib subproject end")
    return project