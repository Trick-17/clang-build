"""
clang-build:
  TODO: module docstring...
"""



import os
import sys
from sys import platform as _platform
import subprocess
from subprocess import call, check_output
from multiprocessing import Pool
import getopt
import argparse
from distutils.dir_util import mkpath
from enum import Enum
from glob import glob
import tempfile
import toml



# Global pool for multiprocess build
processpool = None



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
    Coverage       = 5



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
    platform_extra_flags_executable = ''
    platform_extra_flags_shared     = ' -fpic'
    platform_extra_flags_static     = ''
elif _platform == "darwin":
    # OS X
    shared_library_prefix = 'lib'
    shared_library_suffix = '.dylib'
    static_library_prefix = 'lib'
    static_library_suffix = '.a'
    platform_extra_flags_executable = ''
    platform_extra_flags_shared     = ''
    platform_extra_flags_static     = ''
elif _platform == "win32":
    # Windows
    executable_suffix     = '.exe'
    shared_library_prefix = ''
    shared_library_suffix = '.dll'
    static_library_prefix = ''
    static_library_suffix = '.lib'
    platform_extra_flags_executable = ' -Xclang -flto-visibility-public-std'
    platform_extra_flags_shared     = ' -Xclang -flto-visibility-public-std'
    platform_extra_flags_static     = ' -Xclang -flto-visibility-public-std'



# Get the dialects of C++ available in clang
supported_dialects = ['98']
# Create a temporary file with a main function
with tempfile.NamedTemporaryFile() as fp:
    fp.write(b"int main(int argc, char ** argv){return 0;}")
    fp.seek(0)
    # Try to compile the file using `-std=c++XX` flag
    for dialect in range(30):
        str_dialect = str(dialect).zfill(2)
        command = "clang -xc++ -std=c++"+str_dialect+" "+fp.name+" -o"+tempfile.gettempdir()+"/test"
        try:
            subprocess.check_output(command, stderr=subprocess.STDOUT, shell=True)
            # If it compiled, the dialect is supported
            if str_dialect not in supported_dialects: supported_dialects.append(str_dialect)
        except:
            pass # We expect this to usually fail

# The most recent C++ version available
supported_dialect_newest = supported_dialects[-1]



"""
Buildable describes a source file and all information needed to build it.
"""
class Buildable:
    def __init__(self, sourceFile, targetType, verbose=False, targetDirectory="", buildDirectory="", root="", includeDirectories=[], compileFlags=[], linkFlags=[]):
        self.sourceFile         = sourceFile
        self.targetType         = targetType
        self.verbose            = verbose
        self.targetDirectory    = targetDirectory
        self.buildDirectory     = buildDirectory
        self.root               = root
        self.includeDirectories = includeDirectories
        self.compileFlags       = compileFlags
        self.linkFlags          = linkFlags

        # Get the relative file path
        path, file = os.path.split(sourceFile)
        relpath = os.path.relpath(path, self.targetDirectory+"/"+self.root)
        if  os.path.exists(self.targetDirectory+"/"+self.root+'/src'):
            relpath = os.path.relpath(relpath, 'src')
        # Get file name and extension
        name, extension = os.path.splitext(file)

        # Set name, extension and potentially produced output files
        self.name          = name
        self.fileExtension = extension
        self.objectFile    = self.buildDirectory + "/" + relpath + "/" + self.name + ".o"
        self.depfile       = self.buildDirectory + "/" + relpath + "/" + self.name + ".d"

    # Find and parse the dependency file, return list of headers this file depends on
    def getDepfileHeaders(self):
        depfileHeaders = []
        with open(self.depfile, "r") as the_file:
            depStr = the_file.read()
            colonPos = depStr.find(":")
            for line in depStr[colonPos + 1:].splitlines():
                depline = line.replace(' \\', '').strip().split()
                for header in depline:
                    depfileHeaders.append(header)
        return depfileHeaders



"""
Scan the dependencies of a Buildable and write them into a depfile
This is not a class method, so that it can be called from multiprocessing
"""
def generateDepfile(buildable):
    sourceFile = buildable.sourceFile
    objectFile = buildable.objectFile

    path, _ = os.path.split(buildable.depfile)
    mkpath(path)

    flags = ""

    for flag in buildable.compileFlags:
        flags += " " + flag

    for dir in buildable.includeDirectories:
        flags += " -I" + dir

    command = "clang++ -E -MMD "+ sourceFile + " -MF " + buildable.depfile + flags

    if buildable.verbose:
        print("--   " + command )
    devnull = open(os.devnull, 'w')
    call(command, shell=True, stdout=devnull, stderr=devnull)

"""
Compile a Buildable...
"""
def compile(buildable):

    path, _ = os.path.split(buildable.objectFile)
    mkpath(path)

    flags = ""

    for flag in buildable.compileFlags:
        flags += " " + flag

    for dir in buildable.includeDirectories:
        flags += " -I" + dir

    if buildable.targetType == TargetType.Executable:
        flags += platform_extra_flags_executable
    elif buildable.targetType == TargetType.Sharedlibrary:
        flags += platform_extra_flags_shared
    elif buildable.targetType == TargetType.Staticlibrary:
        flags += platform_extra_flags_static

    command = "clang++ -c " + buildable.sourceFile + " -o " + buildable.objectFile + flags

    if buildable.verbose:
        print("--   " + command)
    call(command, shell=True)



"""
Target describes a single build or dependency target with all needed paths and
a list of buildables that comprise it's compile and link steps.
"""
class Target:
    def __init__(self):
        # Clang
        self.clangpp   = "clang++"
        self.clang_ar  = "llvm-ar"
        self.llvm_root = ""
        # Basics
        self.targetDirectory = ""
        self.root            = ""
        self.name            = "main"
        self.outname         = "main"
        self.targetType      = TargetType.Executable
        self.dialect         = supported_dialect_newest
        self.external        = False
        self.header_only     = False

        self.verbose         = False

        # Custom flags (set from project file)
        self.includeDirectories  = []
        self.compileFlags        = []
        self.compileFlagsDebug   = []
        self.compileFlagsRelease = []
        self.linkFlags           = []

        # Include flags
        self.defaultIncludeDirectories = ["include", "thirdparty"]

        # Default flags
        self.defaultCompileFlags       = ["-std=c++" + str(supported_dialect_newest) + " -Wall -Werror"]

        # Default release flags
        self.defaultReleaseCompileFlags  = ["-O3 -DNDEBUG"]
        # Default debug flags
        self.defaultDebugCompileFlags    = ["-O0 -g3 -DDEBUG"]
        # Default coverage flags
        self.defaultCoverageCompileFlags = self.defaultDebugCompileFlags + ["--coverage -fno-inline -fno-inline-small-functions -fno-default-inline"]

        # Build options
        self.buildType          = BuildType.Default
        self.buildDirectory     = "build"

        # Sources
        self.headerFiles        = []
        self.sourceFiles        = []

        # Buildables which this Target contains
        self.buildables         = []

        # Dependencies
        self.dependencies       = [] # string
        self.dependencyTargets  = [] # Target
        # Parents in the dependency graph
        self.dependencyParents  = []

        # Flags whether compilation/linkage has been completed
        self.compiled = False
        self.linked   = False

    def generateBuildables(self):
        for sourceFile in self.sourceFiles:
            buildable = Buildable(sourceFile, self.targetType, verbose=self.verbose, targetDirectory=self.targetDirectory, buildDirectory=self.buildDirectory, root=self.root, includeDirectories=self.includeDirectories, compileFlags=self.compileFlags, linkFlags=self.linkFlags)
            self.buildables.append(buildable)

    def generateFlags(self):
        flags = []
        # Default flags
        for flag in self.defaultCompileFlags:
            flags.append(flag)
        # Own flags
        for flag in self.compileFlags:
            flags.append(flag)
        if self.buildType == BuildType.Release:
            for flag in self.defaultReleaseCompileFlags:
                flags.append(flag)
        if self.buildType == BuildType.Debug:
            for flag in self.defaultDebugCompileFlags:
                flags.append(flag)
        # Dependency flags
        for target in self.dependencyTargets:
            for flag in target.defaultCompileFlags:
                flags.append(flag)
            for flag in target.compileFlags:
                flags.append(flag)
            if target.buildType == BuildType.Release:
                for flag in target.defaultReleaseCompileFlags:
                    flags.append(flag)
                for flag in target.compileFlagsRelease:
                    flags.append(flag)
            if target.buildType == BuildType.Debug:
                for flag in target.defaultDebugCompileFlags:
                    flags.append(flag)
                for flag in target.compileFlagsDebug:
                    flags.append(flag)
        # Append
        self.compileFlags = []
        for flag in flags:
            if flag not in self.compileFlags:
                self.compileFlags.append(flag)

        includeDirs = []
        # Own include directories
        for dir in self.defaultIncludeDirectories:
            includeDirs.append(self.targetDirectory + "/" +dir)
        # Dependency include directories
        for target in self.dependencyTargets:
            for dir in target.includeDirectories:
                includeDirs.append(dir)

        # Append
        for dir in includeDirs:
            if not dir in self.includeDirectories:
                self.includeDirectories.append(dir)

    # From the list of source files, compile those which changed or whose dependencies (included headers, ...) changed
    def compile(self):
        # All dependencies need to be compiled before the target can be compiled
        for target in self.dependencyTargets:
            if not target.compiled:
                return

        # If the target is header-only it does not need to be compiled
        if len(self.sourceFiles) < 1:
            if self.verbose:
                print("-- Target " + self.outname + " seems to be header-only")
            self.header_only = True

        # Object file only needs to be (re-)compiled if the source file or headers it depends on changed
        neededBuildables = []
        for buildable in self.buildables:
            sourceFile = buildable.sourceFile
            objectFile = buildable.objectFile
            # Check if object file has been compiled
            if os.path.isfile(objectFile):
                # If object file is found, check if it is up to date
                if os.path.getmtime(sourceFile) > os.path.getmtime(objectFile):
                    neededBuildables.append(buildable)
                # If object file is up to date, we check the headers it depends on
                else:
                    depHeaderFiles = buildable.getDepfileHeaders()
                    for depHeaderFile in depHeaderFiles:
                        if os.path.getmtime(depHeaderFile) > os.path.getmtime(objectFile):
                            neededBuildables.append(buildable)
            else:
                neededBuildables.append(buildable)

        # If the target was not modified, it may not need to compile
        if not neededBuildables and not self.header_only:
            if self.verbose:
                print("-- Target " + self.outname + " is already compiled")
            self.compiled = True

        if self.verbose and neededBuildables:
            print("-- Target " + self.outname + ": need to rebuild sources ", [b.name for b in neededBuildables])

        # Compile
        if not (self.compiled or self.header_only):
            # Create base directory for build
            mkpath(self.buildDirectory)

            # Create header dependency graph
            print("-- Scanning dependencies of target " + self.outname)
            processpool.map(generateDepfile, neededBuildables)

            # Execute compile command
            print("-- Compile target " + self.outname)
            processpool.map(compile, neededBuildables)

        # Done
        self.compiled = True

        # Spawn compilation of dependency parents
        for parent in self.dependencyParents:
            parent.compile()

    # Link the compiled object files
    def link(self):
        # All dependencies need to be finished before the target can be linked
        for target in self.dependencyTargets:
            if not target.linked:
                return

        if self.targetType == TargetType.Executable:
            self.prefix = ""
            self.suffix = executable_suffix
        elif self.targetType == TargetType.Sharedlibrary:
            self.prefix = shared_library_prefix
            self.suffix = shared_library_suffix
        elif self.targetType == TargetType.Staticlibrary:
            self.prefix = static_library_prefix
            self.suffix = static_library_suffix

        if len(self.sourceFiles) < 1:
            self.header_only = True
        else:
            self.outfile = self.prefix + self.outname + self.suffix

            if self.targetType == TargetType.Executable:
                linkCommand = self.clangpp + " -o " + self.buildDirectory + "/" + self.outfile

            elif self.targetType == TargetType.Sharedlibrary:
                linkCommand = self.clangpp + " -shared -o " + self.buildDirectory + "/" + self.outfile

            elif self.targetType == TargetType.Staticlibrary:
                linkCommand = self.clang_ar + " rc " + self.buildDirectory + "/" + self.outfile

            ### Link dependencies
            for target in self.dependencyTargets:
                if not target.header_only:
                    linkCommand += " -L\""+ target.buildDirectory +"\" -l" + target.outname

            ### Include directories
            if self.targetType == TargetType.Executable or self.targetType == TargetType.Sharedlibrary:
                for dir in self.includeDirectories:
                    linkCommand += " -I" + dir

            ### Link self
            for buildable in self.buildables:
                objectFile = buildable.objectFile
                linkCommand += " " + objectFile

            # Execute link command
            print("-- Link target " + self.outname)
            if self.verbose:
                print("--   " + linkCommand)
            mkpath(self.buildDirectory)
            call(linkCommand, shell=True)

        # Done
        self.linked = True

        # Spawn compilation of dependency parents
        for parent in self.dependencyParents:
            parent.link()



def main():
    print("---- clang-build v0.0.0")
    global processpool
    processpool = Pool(processes=1)
    # Check for clang++ executable
    from distutils.spawn import find_executable
    clangpp  = find_executable("clang++")
    clang_ar = find_executable("llvm-ar")
    llvm_root = os.path.dirname(os.path.abspath(os.path.join(clangpp, "..")))

    if not clangpp:
        print("---- WARNING: could not find clang++! Please check your installation...")
    if not clang_ar:
        print("---- WARNING: could not find llvm-ar! Please check your installation...")

    # Parse command line arguments
    parser = argparse.ArgumentParser()
    parser.add_argument("-V", "--verbose",
                        help="activate verbose build",
                        action="store_true")
    parser.add_argument("-d", "--directory",
                        help="set the root source directory")
    parser.add_argument("-b", "--build-type",
                        help="set the build type (default, release, debug, ...)")
    parser.add_argument("-j", "--jobs", type=int,
                        help="set the number of concurrent build jobs (default: 1)")
    args = parser.parse_args()

    # Verbosity
    if args.verbose: print("-- Verbosity turned on")
    if args.verbose:
        if clangpp:  print("-- llvm root directory: " + llvm_root)
        if clangpp:  print("-- clang++ executable:  " + clangpp)
        if clang_ar: print("-- llvm-ar executable:  " + clang_ar)
        if clangpp:  print("-- Found supported C++ dialects: ", supported_dialects)

    # Directory this was called from
    callingdir = os.getcwd()

    # Working directory is where the project root should be - this is searched for "clang-build.toml"
    if args.directory:
        workingdir = os.path.abspath(args.directory)
    else:
        workingdir = callingdir
    print("-- Working directory: " + workingdir)

    # Build type (Default, Release, Debug)
    buildType = BuildType.Default
    if args.build_type:
        buildType = BuildType[args.build_type.lower().title()]
        print("-- Build type: " + buildType.name )

    # Multiprocessing pool
    if args.jobs:
        processpool = Pool(processes = args.jobs)
        if args.verbose:
            print("-- Running " + str(args.jobs) + " concurrent build jobs" )

    # Check for build configuration toml file
    if os.path.isfile(workingdir + "/clang-build.toml"):
        config = toml.load(workingdir + "/clang-build.toml")

        # Use sub-build directories if multiple targets
        subbuilddirs = False
        if len(config.items()) > 1:
            subbuilddirs = True

        # Parse targets from toml file
        targets = []
        for nodename, node in config.items():
            # Create target
            target = Target()
            target.llvm_root       = llvm_root
            target.targetDirectory = workingdir
            target.buildType       = buildType
            target.verbose         = args.verbose
            target.name            = nodename
            target.includeDirectories = []

            # Parse Targets type (Executable, Library, Test)
            target.targetType      = TargetType.Executable
            if "target_type" in node:
                target.targetType  = TargetType[node["target_type"].lower().title()]

            # Parse output name for the compiled target
            if "output_name" in node:
                target.outname     = node["output_name"]
            else:
                target.outname     = target.name

            # If we have multiple targets, each gets its own sub-builddirectory
            if subbuilddirs:
                target.buildDirectory += "/"+target.name

            # Handle the case that the target is an external project
            if "external" in node:
                target.external        = node["external"]
                if target.external:
                    downloaddir = target.buildDirectory + "/external_sources"
                    # Check if directory is already present and non-empty
                    if os.path.exists(downloaddir) and os.listdir(downloaddir):
                        print("-- External target " + target.name + ": sources found in "+downloaddir)
                    # Otherwise we download the sources
                    else:
                        print("-- External target " + target.name + ": downloading to "+downloaddir)
                        mkpath(downloaddir)
                        call("git clone "+node["url"]+" "+downloaddir, shell=True)
                        print("-- External target " + target.name + ": downloaded")
                    target.includeDirectories.append(downloaddir)

            # Parse the Targets sources
            sources = []
            headers = []
            if "sources" in node:
                sourcenode = node["sources"]

                # Target root directory
                sourceroot = ""
                if "root" in sourcenode:
                    target.root = sourcenode["root"]
                    target.includeDirectories.append(target.targetDirectory+"/"+target.root)

                # Add include directories
                if "include_directories" in sourcenode:
                    for dir in sourcenode["include_directories"]:
                        if dir not in target.includeDirectories:
                            target.includeDirectories.append(target.targetDirectory+"/"+target.root+"/"+dir)

                    # Search for header files
                    for ext in ('*.hpp', '*.hxx', '*.h'):
                        for dir in sourcenode["include_directories"]:
                            headers += glob(os.path.join(target.targetDirectory+"/"+target.root+"/"+dir, ext))

                # Search for source files
                if "source_directories" in sourcenode:
                    for ext in ('*.cpp', '*.cxx', '*.c'):
                        for dir in sourcenode["source_directories"]:
                            sources += glob(os.path.join(target.targetDirectory+"/"+target.root+"/"+dir, ext))

            # If sources were not specified we try to glob them
            else:
                # Search for header files
                for ext in ('*.hpp', '*.hxx'):
                    headers += glob(os.path.join(target.targetDirectory, ext))
                # Search for source files
                for ext in ('*.cpp', '*.cxx'):
                    sources += glob(os.path.join(target.targetDirectory, ext))

            # Set target sources
            target.headerFiles = headers
            target.sourceFiles = sources

            # Flags
            if "flags" in node:
                flagsnode = node["flags"]
                if "compile" in flagsnode:
                    for flag in flagsnode["compile"]:
                        target.compileFlags.append(flag)
                if "compileRelease" in flagsnode:
                    for flag in flagsnode["compileRelease"]:
                        target.compileFlagsRelease.append(flag)
                if "compileDebug" in flagsnode:
                    for flag in flagsnode["compileDebug"]:
                        target.compileFlagsDebug.append(flag)
                if "link" in flagsnode:
                    for flag in flagsnode["link"]:
                        target.linkFlags.append(flag)

            # Dependencies
            if "link" in node:
                if "dependencies" in node["link"]:
                    deps = node["link"]["dependencies"]
                    for dep in deps:
                        if dep not in target.dependencies:
                            target.dependencies.append(str(dep))
                            if args.verbose: print("-- Dependency added: "+target.name+" -> "+dep)

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
                            depTarget.dependencyParents.append(target)
                            print("-- Dependency resolved: "+target.name+" -> "+dep)
                        else:
                            print("-- WARNING: you may have a double dependency: "+target.name+" -> "+dep)
                if not valid:
                    print("-- WARNING: could not resolve dependency "+target.name+" -> "+dep)

        # Let the targets generate flags and buildables
        for target in targets:
            target.generateFlags()
            target.generateBuildables()

        # Determine leafs on dependency graph
        leafs = []
        for target in targets:
            if not target.dependencyTargets:
                leafs.append(target)
        if not leafs:
            print("-- WARNING: did not find any leafs in dependency graph!")

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

        # Let the target generate its flags and buildables
        target.generateFlags()
        target.generateBuildables()

        # Only one target -> root and leaf of dependency graph
        leafs = [target]

    # Build the targets
    print("---- Compile step")
    for target in leafs:
        target.compile()

    print("---- Link step")
    for target in leafs:
        target.link()

    print("---- clang-build finished")


if __name__ == "__main__":
    sys.exit(main())