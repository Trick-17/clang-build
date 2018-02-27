"""
clang-build:
  TODO: module docstring...
"""



import os
import subprocess
from subprocess import call, check_output
import sys
import getopt
from distutils.dir_util import mkpath



from enum import Enum
class TargetType(Enum):
    SharedLibrary = 0
    StaticLibrary = 1
    Executable    = 2
class BuildType(Enum):
    Default        = 0
    Release        = 1
    MinSizeRel     = 2
    RelWithDebInfo = 3
    Debug          = 4



from sys import platform as _platform
executable_suffix     = ''
shared_library_prefix = ''
shared_library_suffix = ''
static_library_prefix = ''
static_library_suffix = ''
if _platform == "linux" or _platform == "linux2":
    # Linux
    shared_library_prefix = 'lib'
    shared_library_suffix = '.so'
    static_library_prefix = 'lib'
    static_library_suffix = '.a'
elif _platform == "darwin":
    # OS X
    shared_library_prefix = 'lib'
    shared_library_suffix = '.dylib'
    static_library_prefix = 'lib'
    static_library_suffix = '.a'
elif _platform == "win32":
    # Windows
    executable_suffix     = '.exe'
    shared_library_prefix = ''
    shared_library_suffix = '.dll'
    static_library_prefix = ''
    static_library_suffix = '.dll'



# Get the dialects of C++ available in clang
supported_dialects = [98]
# Create a temporary file with a main function
import tempfile
with tempfile.NamedTemporaryFile() as fp:
    fp.write(b"int main(int argc, char ** argv){return 0;}")
    fp.seek(0)
    # Try to compile the file using `-std=c++XX` flag
    for dialect in range(30):
        command = "clang -xc++ -std=c++"+str(dialect)+" "+fp.name+" -o"+tempfile.gettempdir()+"/test"
        try:
            subprocess.check_output(command, stderr=subprocess.STDOUT, shell=True)
            # If it compiled, the dialect is supported
            if dialect not in supported_dialects: supported_dialects.append(dialect)
        except:
            pass # We expect this to usually fail



# The most recent C++ version available
supported_dialect_newest = supported_dialects[-1]



class Target:
    targetDirectory    = ""
    name               = "main"
    targetType         = TargetType.Executable
    dialect            = supported_dialect_newest

    verbose = False

    includeDirectories = ["include", "thirdparty"]
    compileFlags       = ["-std=c++"+str(supported_dialect_newest)]
    linkFlags          = []

    buildType          = BuildType.Default
    buildDirectory     = "build"

    headerFiles        = []
    sourceFiles        = []


    def __init__(self):
        if self.targetType == TargetType.Executable:
            self.prefix = ""
            self.suffix = executable_suffix
        elif self.targetType == TargetType.SharedLibrary:
            self.prefix = shared_library_prefix
            self.suffix = shared_library_suffix
        elif self.targetType == TargetType.StaticLibrary:
            self.prefix = static_library_prefix
            self.suffix = static_library_suffix
        
        self.outname = self.prefix + self.name + self.suffix


    def compile(self):
        compileCommand = "clang++"

        for flag in self.compileFlags:
            compileCommand += " " + flag

        for dir in self.includeDirectories:
            compileCommand += " -I" + self.targetDirectory + "/" + dir

        if self.targetType == TargetType.Executable:
            compileCommand += " -c"
        
        elif self.targetType == TargetType.SharedLibrary:
            compileCommand += " -fPIC -c"
        
        elif self.targetType == TargetType.StaticLibrary:
            compileCommand += " -fPIC -c"

        # Execute compile command
        print("-- Compile target " + self.name)
        mkpath(self.buildDirectory)
        for sourceFile in self.sourceFiles:
            path, file = os.path.split(sourceFile)
            fname, extension = os.path.splitext(file)
            objectCommand = " " + sourceFile + " -o " + self.buildDirectory + "/" + fname + ".o"

            if self.verbose:
                print("--   " + compileCommand + objectCommand)
            call(compileCommand + objectCommand, shell=True)


    def link(self):
        ### Link self
        if self.targetType == TargetType.Executable:
            linkCommand = "clang++ -o " + self.buildDirectory + "/" + self.outname

        elif self.targetType == TargetType.SharedLibrary:
            linkCommand = "clang++ -shared -Wl,-soname," + self.buildDirectory + "/" + self.outname

        elif self.targetType == TargetType.StaticLibrary:
            linkCommand = "llvm-ar rc " + self.buildDirectory + "/" + self.outname

        for dir in self.includeDirectories:
            linkCommand += " -I" + self.targetDirectory + "/" + dir

        ### Link Dependencies

        # Execute link command
        for sourceFile in self.sourceFiles:
            path, file = os.path.split(sourceFile)
            fname, extension = os.path.splitext(file)
            linkCommand += " " + self.buildDirectory + "/" + fname + ".o"
        print("-- Link target " + self.name)
        if self.verbose:
            print("--   " + linkCommand)
        mkpath(self.buildDirectory)
        call(linkCommand, shell=True)



def main(argv=None):
    print("---- clang-build v0.0.0")

    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("-V", "--verbose",
                        help="activate verbose build",
                        action="store_true")
    parser.add_argument("-d", "--directory",
                        help="set the root source directory")
    parser.add_argument("-b", "--build-type",
                        help="set the build type (default, release, debug, ...)")
    args = parser.parse_args()

    if args.verbose:
        print("-- Verbosity turned on")

    callingdir = os.getcwd()
    workingdir = os.getcwd()
    if args.directory:
        workingdir = args.directory
        print("-- Working directory: " + workingdir)

    buildType = BuildType.Default
    if args.build_type:
        buildType = BuildType[args.build_type.lower().title()]
        print("-- Build type: " + buildType.name )

    # Check for build configuration toml file
    if os.path.isfile("clang-build.toml"):
        pass
    # Otherwise we try to build it as a simple hello world or mwe project
    else:
        # Create target
        target = Target()
        target.targetDirectory = workingdir
        target.buildType = buildType
        target.verbose = args.verbose

        from glob import glob

        # Search for header files
        headers = []
        for ext in ('*.hpp', '*.hxx'):
            headers += glob(os.path.join(workingdir, ext))

        # Search for source files
        sources = []
        for ext in ('*.cpp', '*.cxx'):
            sources += glob(os.path.join(workingdir, ext))

        # Set target
        target.headerFiles = headers
        target.sourceFiles = sources

        # List of targets
        targets = [target]

    # Build the targets
    print("---- Compile step")
    for target in targets:
        target.compile()

    print("---- Link step")
    for target in targets:
        target.link()

    print("---- clang-build finished")


if __name__ == "__main__":
    sys.exit(main())
