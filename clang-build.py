"""
clang-build:
  TODO: module docstring...
"""



import os
import sys
from sys import platform as _platform
import subprocess
from subprocess import call, check_output
import getopt
import argparse
from distutils.dir_util import mkpath
from enum import Enum
from glob import glob
import tempfile
import toml



class TargetType(Enum):
    Sharedlibrary = 0
    Staticlibrary = 1
    Executable    = 2
class BuildType(Enum):
    Default        = 0
    Release        = 1
    MinSizeRel     = 2
    RelWithDebInfo = 3
    Debug          = 4



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
    def __init__(self):
        self.targetDirectory    = ""
        self.name               = "main"
        self.outname            = "main"
        self.targetType         = TargetType.Executable
        self.dialect            = supported_dialect_newest

        self.verbose            = False

        self.external           = False
        self.includeDirectories = ["include", "thirdparty"]
        self.compileFlags       = ["-std=c++"+str(supported_dialect_newest)]
        self.linkFlags          = []

        self.buildType          = BuildType.Default
        self.buildDirectory     = "build"

        self.headerFiles        = []
        self.sourceFiles        = []

        self.dependencies       = []
        self.dependencyTargets  = []



    def compile(self):
        if len(self.sourceFiles) < 1:
            print("-- Target " + self.outname + " seems to be header-only")
            return
        
        compileCommand = "clang++"

        for flag in self.compileFlags:
            compileCommand += " " + flag

        for dir in self.includeDirectories:
            compileCommand += " -I" + self.targetDirectory + "/" + dir
        for target in self.dependencyTargets:
            if target.external:
                for dir in target.includeDirectories:
                    compileCommand += " -I" + dir
            else:
                for dir in target.includeDirectories:
                    compileCommand += " -I" + target.targetDirectory + "/" + dir

        if self.targetType == TargetType.Executable:
            compileCommand += " -c"
        
        elif self.targetType == TargetType.Sharedlibrary:
            compileCommand += " -c"
        
        elif self.targetType == TargetType.Staticlibrary:
            compileCommand += " -c"

        # Execute compile command
        print("-- Compile target " + self.outname)
        mkpath(self.buildDirectory)
        for sourceFile in self.sourceFiles:
            path, file = os.path.split(sourceFile)
            fname, extension = os.path.splitext(file)
            objectCommand = " " + sourceFile + " -o " + self.buildDirectory + "/" + fname + ".o"

            if self.verbose:
                print("--   " + compileCommand + objectCommand)
            call(compileCommand + objectCommand, shell=True)


    def link(self):
        if self.targetType == TargetType.Executable:
            self.prefix = ""
            self.suffix = executable_suffix
        elif self.targetType == TargetType.Sharedlibrary:
            self.prefix = shared_library_prefix
            self.suffix = shared_library_suffix
        elif self.targetType == TargetType.Staticlibrary:
            self.prefix = static_library_prefix
            self.suffix = static_library_suffix

        if len(self.sourceFiles) < 1: return

        self.outfile = self.prefix + self.outname + self.suffix

        if self.targetType == TargetType.Executable:
            linkCommand = "clang++ -o " + self.buildDirectory + "/" + self.outfile

        elif self.targetType == TargetType.Sharedlibrary:
            linkCommand = "clang++ -shared -o " + self.buildDirectory + "/" + self.outfile

        elif self.targetType == TargetType.Staticlibrary:
            linkCommand = "llvm-ar rc " + self.buildDirectory + "/" + self.outfile

        ### Link Dependencies
        for target in self.dependencyTargets:
            for sourceFile in target.sourceFiles:
                # path, file = os.path.split(sourceFile)
                # fname, extension = os.path.splitext(file)
                # linkCommand += " " + dependency.buildDirectory + "/" + fname + ".o"
                linkCommand += " -L\""+os.path.abspath("build/mylib\"")+" build/mylib/mylib.dll"# + target.outname

        ### Link self
        for dir in self.includeDirectories:
            linkCommand += " -I" + self.targetDirectory + "/" + dir
        for target in self.dependencyTargets:
            for dir in target.includeDirectories:
                linkCommand += " -I" + dir

        for sourceFile in self.sourceFiles:
            path, file = os.path.split(sourceFile)
            fname, extension = os.path.splitext(file)
            linkCommand += " " + self.buildDirectory + "/" + fname + ".o"

        # TODO: dependencies need to be linked before they can be linked into the target
        # Execute link command
        print("-- Link target " + self.outname)
        if self.verbose:
            print("--   " + linkCommand)
        mkpath(self.buildDirectory)
        call(linkCommand, shell=True)



def main(argv=None):
    print("---- clang-build v0.0.0")

    parser = argparse.ArgumentParser()
    parser.add_argument("-V", "--verbose",
                        help="activate verbose build",
                        action="store_true")
    parser.add_argument("-d", "--directory",
                        help="set the root source directory")
    parser.add_argument("-b", "--build-type",
                        help="set the build type (default, release, debug, ...)")
    args = parser.parse_args()

    if args.verbose: print("-- Verbosity turned on")

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
    if os.path.isfile(workingdir + "/clang-build.toml"):
        config = toml.load(workingdir + "/clang-build.toml")
        # print(toml.dumps(config))

        # Use sub-build directories if multiple targets
        subbuilddirs = False
        if len(config.items()) > 1:
            subbuilddirs = True

        targets = []
        for nodename, node in config.items():
            # Create target
            target = Target()
            target.targetDirectory = workingdir
            target.buildType       = buildType
            target.verbose         = args.verbose
            target.name            = nodename

            target.targetType      = TargetType.Executable
            if "target_type" in node:
                target.targetType  = TargetType[node["target_type"].lower().title()]

            if "output_name" in node:
                target.outname     = node["output_name"]
            else:
                target.outname     = target.name

            if subbuilddirs:
                target.buildDirectory += "/"+target.name
            
            if "external" in node:
                target.external        = node["external"]
                if target.external:
                    downloaddir = target.buildDirectory + "/external_sources"
                    # Check if directory is already present and non-empty
                    if os.path.exists(downloaddir) and os.listdir(downloaddir):
                        print("-- External target " + target.name + ": sources found in "+downloaddir)
                    else:
                        print("-- External target " + target.name + ": downloading to "+downloaddir)
                        mkpath(downloaddir)
                        call("git clone "+node["url"]+" "+downloaddir, shell=True)
                        print("-- External target " + target.name + ": downloaded")
                    target.includeDirectories.append(downloaddir)

            if "sources" in node:
                sourcenode = node["sources"]
                sources = []
                headers = []
                # Add include directories
                if "include_directories" in sourcenode:
                    for dir in sourcenode["include_directories"]:
                        if dir not in target.includeDirectories:
                            target.includeDirectories.append(dir)

                    # Search for header files
                    for ext in ('*.hpp', '*.hxx'):
                        for dir in sourcenode["include_directories"]:
                            headers += glob(os.path.join(workingdir+"/"+dir, ext))

                # Search for source files
                if "source_directories" in sourcenode:
                    for ext in ('*.cpp', '*.cxx'):
                        for dir in sourcenode["source_directories"]:
                            sources += glob(os.path.join(workingdir+"/"+dir, ext))

                # Set target sources
                target.headerFiles = headers
                target.sourceFiles = sources

            # Dependencies
            if "link" in node:
                if "dependencies" in node["link"]:
                    deps = node["link"]["dependencies"]
                    for dep in deps:
                        if dep not in target.dependencies:
                            target.dependencies.append(str(dep))
                            if args.verbose: print("-- Dependency added: "+target.name+" depends on "+dep)

            # List of targets
            targets.append(target)

        # Check if all dependencies are resolved in terms of defined targets, check for circular dependencies...
        # Add all valid dependencies to the targets as Target instead of just string
        for target in targets:
            for dep in target.dependencies:
                valid = False
                for depTarget in targets:
                    if dep == depTarget.name:
                        valid = True
                        if depTarget not in target.dependencyTargets:
                            target.dependencyTargets.append(depTarget)
                            print("-- Dependency: "+target.name+" depends on "+dep)
                        else:
                            print("-- WARNING: you may have a double dependency of "+target.name+" on "+dep)
                if not valid:
                    print("-- WARNING: could not resolve dependency of "+target.name+" on "+dep)

    # Otherwise we try to build it as a simple hello world or mwe project
    else:
        # Create target
        target = Target()
        target.targetDirectory = workingdir
        target.buildType = buildType
        target.verbose = args.verbose

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