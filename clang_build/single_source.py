import os as _os
import re as _re
from pathlib import Path as _Path
import subprocess as _subprocess
from multiprocessing import freeze_support as _freeze_support

# import logging as _logging


# Find and parse the dependency file, return list of headers this file depends on
# See e.g. https://gcc.gnu.org/onlinedocs/gcc-8.1.0/gcc/Preprocessor-Options.html#Preprocessor-Options for documentation
# TODO: Can this be simplified?
def _get_depfile_headers(depfile):
    depfileHeaders = []
    with open(depfile, "r") as the_file:
        depStr = the_file.read()
        # Find the first colon with a space behind it, which will be right after the dependent file name
        colonPos = depStr.find(": ")
        # Separate the remainder into lines
        for line in depStr[colonPos + 1 :].splitlines():
            # Remove the newline character ('\'-newline)
            if line.endswith("\\"):
                line = line[:-1].strip()
            # Add header (or source, actually)
            depfileHeaders += list(
                [
                    _Path(filename).resolve()
                    for filename in _re.split(r"(?<!\\)\s+", line)
                ]
            )
    return depfileHeaders


def _needs_rebuild(object_file, source_file, depfile, prebuilt_module):
    if depfile.exists():
        if object_file.exists():
            # If object file is found, check if it is up to date
            if source_file.stat().st_mtime > object_file.stat().st_mtime:
                return True
            # If object file is up to date, we check the headers it depends on
            else:
                for depHeaderFile in _get_depfile_headers(depfile):
                    if depHeaderFile.stat().st_mtime > object_file.stat().st_mtime:
                        return True

                return False
        else:
            return True
    else:
        return True


class SingleSource:
    def __init__(
        self,
        environment,
        source_file,
        current_target_root_path,
        depfile_directory,
        precompiled_module_directory,
        object_directory,
        include_directories,
        module_directories,
        compile_flags,
        is_c_target,
        is_module,
    ):
        self._environment = environment

        # Get the relative file path
        self.name = source_file.name
        self.source_file = source_file

        self.toolchain = environment.toolchain
        self.is_c_target = is_c_target
        self.is_module = is_module

        # If the source file is in a directory called 'src', we do not create a
        # subdirectory called 'src' in the build folder structure
        relpath = _os.path.relpath(source_file.parents[0], current_target_root_path)
        if (
            current_target_root_path.joinpath("src").exists()
            and "src" in self.source_file.parts
        ):
            relpath = _os.path.relpath(relpath, "src")

        # Set name, extension and potentially produced output files
        self.object_file = _Path(
            object_directory, relpath, self.source_file.stem + ".o"
        )
        self.precompiled_module_file = _Path(
            precompiled_module_directory, relpath, self.source_file.stem + ".pcm"
        )
        self.depfile = _Path(depfile_directory, relpath, self.source_file.stem + ".d")
        if self.is_module:
            self.prebuilt_module = _Path(
                precompiled_module_directory, relpath, self.source_file.stem + ".pcm"
            )
        else:
            self.prebuilt_module = None

        self.needs_rebuild = _needs_rebuild(
            self.object_file, self.source_file, self.depfile, self.prebuilt_module
        )

        self.include_directories = include_directories
        self.module_directories = [precompiled_module_directory] + module_directories
        self.flags = compile_flags

        self.compilation_failed = False

    def precompile_and_generate_dependency_file(self):
        (
            command,
            success,
            self.depfile_and_pcm_report,
        ) = self.toolchain.precompile_and_generate_dependency_file(
            self.source_file,
            self.depfile,
            self.prebuilt_module,
            self.include_directories,
            self.module_directories,
            self.flags,
            self.is_c_target,
        )
        self.depfile_and_pcm_failed = not success

        command_missing = True
        for idx, db_command in enumerate(self._environment.compilation_database):
            if (
                str(self.source_file) == db_command["file"]
                and str(self.depfile) == db_command["output"]
            ):
                self._environment.compilation_database[idx] = {
                    "directory": str(self._environment.build_directory),
                    "command": " ".join(command),
                    "file": str(self.source_file),
                    "output": str(self.depfile),
                }
                command_missing = False
                break
        if command_missing:
            self._environment.compilation_database.append(
                {
                    "directory": str(self._environment.build_directory),
                    "command": " ".join(command),
                    "file": str(self.source_file),
                    "output": str(self.depfile),
                }
            )

    def compile(self):
        command, success, self.compile_report = self.toolchain.compile(
            self.source_file,
            self.prebuilt_module,
            self.object_file,
            self.include_directories,
            self.module_directories,
            self.flags,
            self.is_c_target,
            self.is_module,
        )
        self.compilation_failed = not success

        command_missing = True
        for idx, db_command in enumerate(self._environment.compilation_database):
            if (
                str(self.source_file) == db_command["file"]
                and str(self.object_file) == db_command["output"]
            ):
                self._environment.compilation_database[idx] = {
                    "directory": str(self._environment.build_directory),
                    "command": " ".join(command),
                    "file": str(self.source_file),
                    "output": str(self.object_file),
                }
                command_missing = False
                break
        if command_missing:
            self._environment.compilation_database.append(
                {
                    "directory": str(self._environment.build_directory),
                    "command": " ".join(command),
                    "file": str(self.source_file),
                    "output": str(self.object_file),
                }
            )


if __name__ == "__name__":
    _freeze_support()
