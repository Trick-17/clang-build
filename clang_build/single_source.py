import os as _os
import re as _re
from pathlib import Path as _Path
import subprocess as _subprocess
from multiprocessing import freeze_support as _freeze_support
import logging as _logging

_LOGGER = _logging.getLogger('clang_build.clang_build')

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
                line = line[:-1]
            # Add header (or source, actually)
            depfileHeaders.append(_Path(line.strip().replace('\\ ', ' ')).resolve())
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
            source_file,
            platform_flags,
            current_target_root_path,
            depfile_directory,
            object_directory,
            include_strings,
            compile_flags,
            clang,
            clangpp,
            max_cpp_dialect):

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

        compiler = clangpp
        if source_file.suffix in [".c", ".cc", ".m"]:
            compiler = clang
            max_cpp_dialect = ''

        self.needs_rebuild = _needs_rebuild(self.object_file, self.source_file, self.depfile)

        flags = compile_flags + include_strings

        self.compilation_failed = False

        # prepare everything for dependency file generation
        self.dependency_command = [compiler, max_cpp_dialect, '-E', '-MMD', str(self.source_file), '-MF', str(self.depfile)] + flags

        # prepare everything for compilation
        self.compile_command = [compiler, max_cpp_dialect, '-c', str(self.source_file), '-o', str(self.object_file)] + flags + platform_flags


    def generate_depfile(self):
        # TODO: logging in multiprocess
        # _LOGGER.debug('    ' + ' '.join(dependency_command))
        try:
            self.depfile.parents[0].mkdir(parents=True, exist_ok=True)
            self.depfile_report = _subprocess.check_output(self.dependency_command, stderr=_subprocess.STDOUT).decode('utf-8').strip()
            self.depfile_failed = False
        except _subprocess.CalledProcessError as error:
            self.depfile_failed = True
            self.depfile_report = error.output.decode('utf-8').strip()


    def compile(self):
        # TODO: logging in multiprocess
        # _LOGGER.debug('    ' + ' '.join(self.compile_command))
        try:
            self.object_file.parents[0].mkdir(parents=True, exist_ok=True)
            self.compile_report = _subprocess.check_output(self.compile_command, stderr=_subprocess.STDOUT).decode('utf-8').strip()
            self.compilation_failed = False
        except _subprocess.CalledProcessError as error:
            self.compilation_failed = True
            self.compile_report = error.output.decode('utf-8').strip()


if __name__ == '__name__':
    _freeze_support()