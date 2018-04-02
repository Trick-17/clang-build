import os as _os
from pathlib2 import Path as _Path
import subprocess as _subprocess

class SingleSource:
    def __init__(
            self,
            sourceFile,
            platformFlags,
            buildType,
            targetDirectory,
            depfileDirectory,
            objectDirectory,
            buildDirectory,
            root,
            includeDirectories,
            compileFlags,
            linkFlags,
            clangpp):
        self.sourceFile         = sourceFile
        self.buildType          = buildType
        self.targetDirectory    = targetDirectory
        self.buildDirectory     = buildDirectory
        self.objectDirectory    = objectDirectory
        self.depfileDirectory   = depfileDirectory
        self.root               = root
        self.includeDirectories = includeDirectories
        self.compileFlags       = compileFlags
        self.linkFlags          = linkFlags
        self.clangpp            = clangpp

        self.platformFlags = platformFlags

        # Get the relative file path
        current_root = self.targetDirectory.joinpath(self.root)
        relpath = _os.path.relpath(sourceFile.parents[0], current_root)
        if  current_root.joinpath('src').exists():
            relpath = _os.path.relpath(relpath, 'src')

        # Set name, extension and potentially produced output files
        self.name          = sourceFile.name
        self.fileExtension = sourceFile.suffix
        self.objectFile    = _Path(self.objectDirectory, relpath, self.name + '.o')
        self.depfile       = _Path(self.depfileDirectory, relpath, self.name + '.d')

    # Find and parse the dependency file, return list of headers this file depends on
    # Replace as soon as we know how the dependency file looks like
    def getDepfileHeaders(self):
        depfileHeaders = []
        with open(self.depfile, 'r') as the_file:
            depStr = the_file.read()
            colonPos = depStr.find(':')
            for line in depStr[colonPos + 1:].splitlines():
                depline = line.replace(' \\', '').strip().split()
                for header in depline:
                    depfileHeaders.append(header)
        return depfileHeaders

    def needs_rebuild(self):
        if self.objectFile.exists():
            # If object file is found, check if it is up to date
            if self.sourceFile.stat().st_mtime > self.objectFile.stat().st_mtime:
                return True
            # If object file is up to date, we check the headers it depends on
            else:
                for depHeaderFile in self.getDepfileHeaders():
                    if depHeaderFile.stat().st_mtime > self.objectFile.stat().st_mtime:
                        return True

                return False
        else:
            return True

    def generate_dependency_file(self):
        self.depfile.parents[0].mkdir(parents=True, exist_ok=True)
        flags = self.compileFlags + ['-I' + dir for dir in self.includeDirectories]
        command = [self.clangpp, '-E', '-MMD', self.sourceFile, '-MF', self.depfile]
        command += flags

        # TODO: should be logged to debug instead of just outputting nothing!
        # TODO: also check_call should be used!
        devnull = open(_os.devnull, 'w')
        _subprocess.call(command, stdout=devnull, stderr=devnull)

    def compile(self):
        self.objectFile.parents[0].mkdir(parents=True, exist_ok=True)
        flags = self.compileFlags + ['-I' + dir for dir in self.includeDirectories]
        flags += self.platformFlags
        command = ['clang++', '-c', self.sourceFile, '-o', self.objectFile]
        command += flags

        # TODO: check_call shoud be used!
        self.compile_command = command
        _subprocess.call(command)