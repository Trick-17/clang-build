from importlib import util as importlib_util

from .errors import ApiError as _ApiError

def get_project(path, working_directory, environment, parent=None):

    module_file_path = path.resolve() / "clang-build.py"
    module_name = "clang-build"

    module_spec = importlib_util.spec_from_file_location(module_name, module_file_path)
    if module_spec is None:
        raise _ApiError(f'No "{module_name}" module could be found in "{path.resolve()}"')

    clang_build_module = importlib_util.module_from_spec(module_spec)
    module_spec.loader.exec_module(clang_build_module)

    if clang_build_module.get_project is None:
        raise _ApiError(f'Module "{module_name}" in "{path.resolve()}" does not contain a `get_project` method')

    return clang_build_module.get_project(working_directory, environment, parent=parent)