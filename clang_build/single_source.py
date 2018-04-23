import os as _os
import re as _re
from pathlib import Path as _Path
import subprocess as _subprocess
from multiprocessing import freeze_support as _freeze_support
import logging as _logging

_LOGGER = _logging.getLogger('clang_build.clang_build')

# Find and parse the dependency file, return list of headers this file depends on
# TODO: Can this be simplified?
def _get_depfile_headers(depfile):
    depfileHeaders = []
    with open(depfile, 'r') as the_file:
        depStr = the_file.read()
        colonPos = depStr.find(':')
        for line in depStr[colonPos + 1:].splitlines():
            if line.endswith('\\'):
                line = line[:-1]
            depline = line.strip().split()
            for header in depline:
                depfileHeaders.append(_Path(header))
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
            sourceFile,
            platformFlags,
            current_target_root_path,
            depfileDirectory,
            objectDirectory,
            include_strings,
            compileFlags,
            clangpp):

        # Get the relative file path
        self.name          = sourceFile.name
        self.sourceFile    = sourceFile

        relpath = _os.path.relpath(sourceFile.parents[0], current_target_root_path)

        # TODO: I'm not sure I understand the necessity/function of this part
        if  current_target_root_path.joinpath('src').exists():
            relpath = _os.path.relpath(relpath, 'src')

        # Set name, extension and potentially produced output files

        self.objectFile = _Path(objectDirectory,  relpath, self.sourceFile.stem + '.o')
        self.depfile    = _Path(depfileDirectory, relpath, self.sourceFile.stem + '.d')

        self.needs_rebuild = _needs_rebuild(self.objectFile, self.sourceFile, self.depfile)

        flags = compileFlags + include_strings

        self.compilation_failed = False
        self.output_messages = []

        # prepare everything for dependency file generation
        self.depfile.parents[0].mkdir(parents=True, exist_ok=True)
        self.dependency_command = [clangpp, '-E', '-MMD', str(self.sourceFile), '-MF', str(self.depfile)] + flags

        # prepare everything for compilation
        self.objectFile.parents[0].mkdir(parents=True, exist_ok=True)
        self.compile_command = [clangpp, '-c', str(self.sourceFile), '-o', str(self.objectFile)] + flags + platformFlags


    def generate_depfile(self):
        # TODO: logging in multiprocess
        # _LOGGER.debug('    ' + ' '.join(dependency_command))
        try:
            self.depfile_report = _subprocess.check_output(self.dependency_command, stderr=_subprocess.STDOUT).decode('utf-8').strip()
        except _subprocess.CalledProcessError as error:
            self.depfile_failed = True
            self.depfile_report = error.output.decode('utf-8').strip()

        # self.parse_depfile_output()

    def compile(self):
        # TODO: logging in multiprocess
        # _LOGGER.debug('    ' + ' '.join(self.compile_command))
        try:
            self.compile_report = _subprocess.check_output(self.compile_command, stderr=_subprocess.STDOUT).decode('utf-8').strip()
        except _subprocess.CalledProcessError as error:
            self.compilation_failed = True
            self.compile_report = error.output.decode('utf-8').strip()

        self.parse_compile_output()

    def parse_compile_output(self):
        # Remove last line
        output_text = _re.split(r'(.*)\n.*generated\.$', self.compile_report)[0]

        # Find all the indivdual messages
        message_list = _re.split(_re.escape(str(self.sourceFile)), output_text)[1:]

        # Get type, row, column and content of each message
        message_parser = _re.compile(r':(?P<row>\d+):(?P<column>\d+):\s*(?P<type>error|warning):\s*(?P<message>[\s\S.]*)')
        self.output_messages = [message_parser.search(message).groupdict() for message in message_list]

    def parse_depfile_output(self):
        # Remove last line
        output_text = _re.split(r'(.*)\n.*generated\.$', self.depfile_report)[0]

        # Find all the indivdual messages
        message_list = _re.split(_re.escape(str(self.sourceFile)), output_text)[1:]

        # Get type, row, column and content of each message
        message_parser = _re.compile(r':(?P<row>\d+):(?P<column>\d+):\s*(?P<type>error|warning):\s*(?P<message>[\s\S.]*)')
        self.output_messages = [message_parser.search(message).groupdict() for message in message_list]

if __name__ == '__name__':
    _freeze_support()