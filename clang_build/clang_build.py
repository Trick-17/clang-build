"""
clang-build:
  TODO: module docstring...
"""



import os
import sys
from sys import platform as _platform
import subprocess
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
    platform_extra_flags_executable = ['']
    platform_extra_flags_shared     = ['-fpic']
    platform_extra_flags_static     = ['']
elif _platform == "darwin":
    # OS X
    shared_library_prefix = 'lib'
    shared_library_suffix = '.dylib'
    static_library_prefix = 'lib'
    static_library_suffix = '.a'
    platform_extra_flags_executable = ['']
    platform_extra_flags_shared     = ['']
    platform_extra_flags_static     = ['']
elif _platform == "win32":
    # Windows
    executable_suffix     = '.exe'
    shared_library_prefix = ''
    shared_library_suffix = '.dll'
    static_library_prefix = ''
    static_library_suffix = '.lib'
    platform_extra_flags_executable = ['-Xclang', '-flto-visibility-public-std']
    platform_extra_flags_shared     = ['-Xclang', '-flto-visibility-public-std']
    platform_extra_flags_static     = ['-Xclang', '-flto-visibility-public-std']



# Get the dialects of C++ available in clang
supported_dialects = ['98']
# Create a temporary file with a main function
with tempfile.NamedTemporaryFile() as fp:
    fp.write(b"int main(int argc, char ** argv){return 0;}")
    fp.seek(0)
    # Try to compile the file using `-std=c++XX` flag
    for dialect in range(30):
        str_dialect = str(dialect).zfill(2)
        command = ["clang", "-xc++", "-std=c++"+str_dialect, fp.name, "-o"+tempfile.gettempdir()+"/test"]
        try:
            subprocess.check_output(command, stderr=subprocess.STDOUT)
            # If it compiled, the dialect is supported
            if str_dialect not in supported_dialects: supported_dialects.append(str_dialect)
        except:
            pass # We expect this to usually fail

# The most recent C++ version available
supported_dialect_newest = supported_dialects[-1]



def listToString(theList, separator=" "):
    theString = theList[0]
    for string in theList[1:]:
        theString += separator + string
    return theString



"""
Buildable describes a source file and all information needed to build it.
"""
class Buildable:
    def __init__(self, sourceFile, targetType, buildType=BuildType.Default, verbose=False, targetDirectory="", depfileDirectory="", objectDirectory="", buildDirectory="", root="", includeDirectories=[], compileFlags=[], linkFlags=[]):
        self.sourceFile         = sourceFile
        self.targetType         = targetType
        self.buildType          = buildType
        self.verbose            = verbose
        self.targetDirectory    = targetDirectory
        self.buildDirectory     = buildDirectory
        self.objectDirectory    = objectDirectory
        self.depfileDirectory   = depfileDirectory
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
        self.objectFile    = self.objectDirectory + "/" + relpath + "/" + self.name + ".o"
        self.depfile       = self.depfileDirectory + "/" + relpath + "/" + self.name + ".d"

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

    flags = []

    for flag in buildable.compileFlags:
        flags.append(flag)

    for dir in buildable.includeDirectories:
        flags.append("-I" + dir)

    command = ["clang++", "-E", "-MMD", sourceFile, "-MF", buildable.depfile]
    command += flags

    if buildable.verbose:
        print("--   " + listToString(command))
    devnull = open(os.devnull, 'w')
    subprocess.call(command, stdout=devnull, stderr=devnull)



"""
Compile a Buildable...
"""
def compile(buildable):

    path, _ = os.path.split(buildable.objectFile)
    mkpath(path)

    flags = []

    for flag in buildable.compileFlags:
        flags.append(flag)

    for dir in buildable.includeDirectories:
        flags.append("-I" + dir)

    if buildable.targetType == TargetType.Executable:
        flags += platform_extra_flags_executable
    elif buildable.targetType == TargetType.Sharedlibrary:
        flags += platform_extra_flags_shared
    elif buildable.targetType == TargetType.Staticlibrary:
        flags += platform_extra_flags_static

    command = ["clang++", "-c", buildable.sourceFile, "-o", buildable.objectFile]
    command += flags

    if buildable.verbose:
        print("--   " + listToString(command))
    subprocess.call(command)



"""
Target describes a single build or dependency target with all needed paths and
a list of buildables that comprise it's compile and link steps.
"""
class Target:
    def __init__(self, environment, name=""):
        # Clang
        self.clangpp   = environment.clangpp
        self.clang_ar  = environment.clang_ar
        self.llvm_root = environment.llvm_root

        # Basics
        self.targetDirectory = environment.workingDirectory
        self.buildType       = environment.buildType
        self.verbose         = environment.verbose
        self.root            = ""
        self.dialect         = supported_dialect_newest

        # Properties
        self.buildDirectory  = "build"
        self.name            = name
        self.outname         = "main"
        self.targetType      = TargetType.Executable
        self.external        = False
        self.header_only     = False

        # Custom flags (set from project file)
        self.includeDirectories  = []
        self.compileFlags        = []
        self.compileFlagsDebug   = []
        self.compileFlagsRelease = []
        self.linkFlags           = []

        # Include flags
        self.defaultIncludeDirectories = ["include", "thirdparty"]

        # Default flags
        self.defaultCompileFlags       = ["-std=c++"+supported_dialect_newest, "-Wall", "-Werror"]

        # Default release flags
        self.defaultReleaseCompileFlags  = ["-O3", "-DNDEBUG"]
        # Default debug flags
        self.defaultDebugCompileFlags    = ["-O0", "-g3", "-DDEBUG"]
        # Default coverage flags
        self.defaultCoverageCompileFlags = self.defaultDebugCompileFlags + ["--coverage", "-fno-inline", "-fno-inline-small-functions", "-fno-default-inline"]

        # Output directories
        if environment.config:
            targetBuildDir = self.buildDirectory + "/" + self.name + "/" + self.buildType.name.lower()
        else:
            targetBuildDir = self.buildDirectory + "/" + self.buildType.name.lower()
        self.binaryDirectory     = targetBuildDir + "/bin"
        self.libraryDirectory    = targetBuildDir + "/lib"
        self.objectDirectory     = targetBuildDir + "/obj"
        self.depfileDirectory    = targetBuildDir + "/deps"
        self.testBinaryDirectory = targetBuildDir + "/test"

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

        # Flag whether generation of all flags has been completed
        self.flagsGenerated = False
        # Flags whether compilation/linkage has been completed
        self.compiled = False
        self.linked   = False

        # Extra scripts
        self.beforeCompileScript = ""
        self.beforeLinkScript    = ""
        self.afterBuildScript    = ""

    def generateBuildables(self):
        for sourceFile in self.sourceFiles:
            buildable = Buildable(sourceFile, self.targetType, buildType=self.buildType, verbose=self.verbose, depfileDirectory=self.depfileDirectory, objectDirectory=self.objectDirectory, targetDirectory=self.targetDirectory, buildDirectory=self.buildDirectory, root=self.root, includeDirectories=self.includeDirectories, compileFlags=self.compileFlags, linkFlags=self.linkFlags)
            self.buildables.append(buildable)

    def generateFlags(self):
        # All dependencies need to have generated their flags before this target can proceed
        for target in self.dependencyTargets:
            if not target.flagsGenerated:
                return

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
            for flag in self.compileFlagsRelease:
                flags.append(flag)
        if self.buildType == BuildType.Debug:
            for flag in self.defaultDebugCompileFlags:
                flags.append(flag)
            for flag in self.compileFlagsDebug:
                flags.append(flag)

        # Dependency flags
        for target in self.dependencyTargets:
            flags += target.compileFlags

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

        # Done
        self.flagsGenerated = True

        # Spawn compilation of dependency parents
        for parent in self.dependencyParents:
            parent.generateFlags()

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

        # Before-compile step
        if self.beforeCompileScript and not self.compiled:
            if self.verbose:
                print("-- Pre-compile step of target " + self.outname)
            originalDir = os.getcwd()
            newDir, _ = os.path.split(self.beforeCompileScript)
            os.chdir(newDir)
            execfile(self.beforeCompileScript)
            os.chdir(originalDir)
            if self.verbose:
                print("-- Finished pre-compile step of target " + self.outname)

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

        # Before-link step
        if self.beforeLinkScript:
            if self.verbose:
                print("-- Pre-link step of target " + self.outname)
            originalDir = os.getcwd()
            newDir, _ = os.path.split(self.beforeCompileScript)
            os.chdir(newDir)
            execfile(self.beforeLinkScript)
            os.chdir(originalDir)
            if self.verbose:
                print("-- Finished pre-link step of target " + self.outname)

        # Link
        if not self.header_only:
            self.outfile = self.prefix + self.outname + self.suffix

            if self.targetType == TargetType.Executable:
                linkCommand = [self.clangpp, "-o", self.binaryDirectory+"/"+self.outfile]
                mkpath(self.binaryDirectory)

            elif self.targetType == TargetType.Sharedlibrary:
                linkCommand = [self.clangpp, "-shared", "-o", self.libraryDirectory+"/"+self.outfile]
                mkpath(self.libraryDirectory)

            elif self.targetType == TargetType.Staticlibrary:
                linkCommand = [self.clang_ar, "rc", self.libraryDirectory+"/"+self.outfile]
                mkpath(self.libraryDirectory)

            ### Library dependency search paths
            for target in self.dependencyTargets:
                if not target.header_only:
                    linkCommand += ["-L"+os.path.abspath(target.libraryDirectory)]

            ### Include directories
            if self.targetType == TargetType.Executable or self.targetType == TargetType.Sharedlibrary:
                for dir in self.includeDirectories:
                    linkCommand.append("-I"+dir)

            ### Link self
            for buildable in self.buildables:
                objectFile = buildable.objectFile
                linkCommand.append(objectFile)

            ### Link dependencies
            for target in self.dependencyTargets:
                if not target.header_only:
                    linkCommand += ["-l"+target.outname]

            # Execute link command
            print("-- Link target " + self.outname)
            if self.verbose:
                print("--   " + listToString(linkCommand))
            subprocess.call(linkCommand)

        # Done
        self.linked = True

        # After-build step
        if self.afterBuildScript:
            if self.verbose:
                print("-- After-build step of target " + self.outname)
            originalDir = os.getcwd()
            newDir, _ = os.path.split(self.beforeCompileScript)
            os.chdir(newDir)
            execfile(self.afterBuildScript)
            os.chdir(originalDir)
            if self.verbose:
                print("-- Finished after-build step of target " + self.outname)

        # Spawn compilation of dependency parents
        for parent in self.dependencyParents:
            parent.link()



class Environment:
    def __init__(self):
        global processpool
        self.nJobs = 1
        processpool = Pool(processes=self.nJobs)

        # Check for clang++ executable
        from distutils.spawn import find_executable
        self.clangpp  = find_executable("clang++")
        self.clang_ar = find_executable("llvm-ar")
        self.llvm_root = os.path.dirname(os.path.abspath(os.path.join(self.clangpp, "..")))

        if not self.clangpp:
            print("---- WARNING: could not find clang++! Please check your installation...")
        if not self.clang_ar:
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
        self.verbose = args.verbose
        if self.verbose:
            print("-- Verbosity turned on")
            if self.clangpp:  print("-- llvm root directory: " + self.llvm_root)
            if self.clangpp:  print("-- clang++ executable:  " + self.clangpp)
            if self.clang_ar: print("-- llvm-ar executable:  " + self.clang_ar)
            if self.clangpp:  print("-- Found supported C++ dialects: " + ', '.join(supported_dialects))

        # Directory this was called from
        self.callingdir = os.getcwd()

        # Working directory is where the project root should be - this is searched for "clang-build.toml"
        if args.directory:
            self.workingDirectory = os.path.abspath(args.directory)
        else:
            self.workingDirectory = self.callingdir

        if not os.path.exists(self.workingDirectory):
            print("-- ERROR: specified non-existent directory \'" + self.workingDirectory + "\'")
            print("---- clang-build finished")
            sys.exit(1)

        print("-- Working directory: " + self.workingDirectory)

        # Check for presence of build config file
        self.config = ""
        if os.path.isfile(self.workingDirectory + "/clang-build.toml"):
            self.config = self.workingDirectory + "/clang-build.toml"
            if self.verbose:
                print("-- Found config file!")
        elif self.verbose:
            print("-- Did not find config file!")

        # Build type (Default, Release, Debug)
        self.buildType = BuildType.Default
        if args.build_type:
            self.buildType = BuildType[args.build_type.lower().title()]
        print("-- Build type: " + self.buildType.name)


        # Multiprocessing pool
        if args.jobs:
            self.nJobs = args.jobs
            processpool = Pool(processes = self.nJobs)
            if self.verbose:
                print("-- Running " + str(self.nJobs) + " concurrent build jobs" )


def parseBuildConfig(environment):
    config = toml.load(environment.config)

    # Use sub-build directories if multiple targets
    subbuilddirs = False
    if len(config.items()) > 1:
        subbuilddirs = True

    # Parse targets from toml file
    targets = []
    for nodename, node in config.items():
        # Create target
        target = Target(environment, nodename)

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
                    subprocess.call(["git", "clone", node["url"], downloaddir])
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
                        if environment.verbose: print("-- Dependency added: "+target.name+" -> "+dep)

        if "scripts" in node:
            if "before_compile" in node["scripts"]:
                target.beforeCompileScript = target.targetDirectory + "/" + node["scripts"]["before_compile"]

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

    # Determine leafs on dependency graph
    leafs = []
    for target in targets:
        if not target.dependencyTargets:
            leafs.append(target)
    if not leafs:
        print("-- WARNING: did not find any leafs in dependency graph!")

    # Done
    return targets, leafs



def getDefaultTarget(environment):
    # Create target
    target = Target(environment)

    # Search for header files
    headers = []
    for ext in ('*.hpp', '*.hxx', '*.h'):
        headers += glob(os.path.join(environment.workingDirectory, ext))

    # Search for source files
    sources = []
    for ext in ('*.cpp', '*.cxx', '*.c'):
        sources += glob(os.path.join(environment.workingDirectory, ext))

    # Set target
    target.headerFiles = headers
    target.sourceFiles = sources

    # Done
    return target



def main():
    print("---- clang-build v0.0.0")

    # Parse command line arguments, check for presence of build config file, etc.
    environment = Environment()

    # If build configuration toml file exists, parse lists of targets and leaf nodes of the dependency graph
    if environment.config:
        targets, leafs = parseBuildConfig(environment)
    # Otherwise we try to build it as a simple hello world or mwe project
    else:
        defaultTarget = getDefaultTarget(environment)
        targets = [defaultTarget]
        leafs   = [defaultTarget]

    # Generate flags of all targets, propagating up the dependency graph
    for target in leafs:
        target.generateFlags()

    # Generate the buildables of all targets
    for target in targets:
        target.generateBuildables()

    # Build the targets, moving successively up the dependency graph
    print("---- Compile step")
    for target in leafs:
        target.compile()

    print("---- Link step")
    for target in leafs:
        target.link()

    print("---- clang-build finished")


if __name__ == "__main__":
    sys.exit(main())