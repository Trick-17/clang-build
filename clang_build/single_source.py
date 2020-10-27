import os as _os
import re as _re
from pathlib import Path as _Path
import subprocess as _subprocess
from multiprocessing import freeze_support as _freeze_support
# import logging as _logging

# _LOGGER = _logging.getLogger('clang_build.clang_build')

# Find and parse the dependency file, return list of headers this file depends on
# See e.g. https://gcc.gnu.org/onlinedocs/gcc-8.1.0/gcc/Preprocessor-Options.html#Preprocessor-Options for documentation
# TODO: Can this be simplified?
def _get_depfile_headers(depfile):
    depfileHeaders = []
    with open(depfile, 'r') as the_file:
        depStr = the_file.read()
        # Find the first colon, which will be right after the object file name
        colonPos = depStr.find(':')
        # Separate the remainder into lines
        for line in depStr[colonPos + 1:].splitlines():
            # Remove the newline character ('\'-newline)
            if line.endswith('\\'):
                line = line[:-1].strip()
            # Add header (or source, actually)
            depfileHeaders += list([_Path(filename).resolve() for filename in _re.split(r'(?<!\\)\s+', line)])
    return depfileHeaders

def _needs_rebuild(object_file, source_file, depfile):
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
            object_directory,
            include_directories,
            compile_flags,
            is_c_target):

        # Get the relative file path
        self.name        = source_file.name
        self.source_file = source_file

        # If the source file is in a directory called 'src', we do not create a
        # subdirectory called 'src' in the build folder structure
        relpath = _os.path.relpath(source_file.parents[0], current_target_root_path)
        if current_target_root_path.joinpath('src').exists() and  "src" in self.source_file.parts:
            relpath = _os.path.relpath(relpath, 'src')

        # Set name, extension and potentially produced output files
        self.object_file = _Path(object_directory,  relpath, self.source_file.stem + '.o')
        self.depfile     = _Path(depfile_directory, relpath, self.source_file.stem + '.d')

        self.toolchain = environment.toolchain
        self.is_c_target = is_c_target

        self.needs_rebuild = _needs_rebuild(self.object_file, self.source_file, self.depfile)

        self.include_directories = include_directories
        self.flags = compile_flags

        self.compilation_failed = False


    def generate_depfile(self):
        success, self.depfile_report = self.toolchain.generate_dependency_file(
            self.source_file,
            self.depfile,
            self.flags,
            self.include_directories,
            self.is_c_target)
        self.depfile_failed = not success

    def compile(self):
        success, self.compile_report = self.toolchain.compile(
            self.source_file,
            self.object_file,
            self.include_directories,
            self.flags,
            self.is_c_target)
        self.compilation_failed = not success

if __name__ == '__name__':
    _freeze_support()