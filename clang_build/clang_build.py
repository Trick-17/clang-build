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

# Global variables containing working directory etc.
environment = None



class TargetType(Enum):
    Sharedlibrary     = 0
    Staticlibrary     = 1
    HeaderOnlyLibrary = 2
    Executable        = 3
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



class Target(object):
    DEFAULT_COMPILE_FLAGS          = ["-std=c++"+supported_dialect_newest, "-Wall", "-Werror"]
    DEFAULT_RELEASE_COMPILE_FLAGS  = ['-O3', '-DNDEBUG']
    DEFAULT_DEBUG_COMPILE_FLAGS    = ['-O0', '-g3', '-DDEBUG']
    DEFAULT_COVERAGE_COMPILE_FLAGS = (
        DEFAULT_DEBUG_COMPILE_FLAGS +
        ['--coverage',
            '-fno-inline',
            '-fno-inline-small-functions',
            '-fno-default-inline'])
    defaultIncludeDirectories = ['.', 'include']

    def __init__(self, name, external, rootDirectory, includeDirectories, headerFiles, config, dependencyNames, parentNames):
        # Identifier name
        self.name          = name
        # If this target is not directly contained in the project
        self.external      = external
        # Root source directory
        self.rootDirectory = rootDirectory

        # User-defined include directories and contained headers
        self.includeDirectories = includeDirectories
        self.headerFiles        = headerFiles

        # Dependencies
        self.dependencyNames = dependencyNames
        # Dependency parents
        self.parentNames = parentNames

        # Flags
        self.compileFlags = []
        self.compileFlagsRelease = []
        self.compileFlagsDebug = []
        self.linkFlags = []

        # Parse the config
        # Version
        self.version = "0.0.0"
        if "version" in config:
            self.version = config["version"]
        # Flags
        if "flags" in config:
            flagsnode = config["flags"]
            if "compile" in flagsnode:
                for flag in flagsnode["compile"]:
                    self.compileFlags.append(flag)
            if "compileRelease" in flagsnode:
                for flag in flagsnode["compileRelease"]:
                    self.compileFlagsRelease.append(flag)
            if "compileDebug" in flagsnode:
                for flag in flagsnode["compileDebug"]:
                    self.compileFlagsDebug.append(flag)
            if "link" in flagsnode:
                for flag in flagsnode["link"]:
                    self.linkFlags.append(flag)
        # Additional scripts
        if "scripts" in config: ### TODO: maybe the scripts should be named differently
            if "before_compile" in config["scripts"]:
                self.beforeCompileScript = self.rootDirectory + "/" + config["scripts"]["before_compile"]
                self.beforeLinkScript    = self.rootDirectory + "/" + config["scripts"]["before_link"]
                self.afterBuildScript    = self.rootDirectory + "/" + config["scripts"]["after_build"]

        self.compileFlags        = self.DEFAULT_COMPILE_FLAGS
        self.compileFlagsRelease = self.DEFAULT_RELEASE_COMPILE_FLAGS
        self.compileFlagsDebug   = self.DEFAULT_DEBUG_COMPILE_FLAGS
        # TODO: where should defaultIncludeDirectories be specified?
        # if not self.external:
        self.includeDirectories = [os.path.abspath(os.path.join(self.rootDirectory, dir)) for dir in self.defaultIncludeDirectories]
        # else:
        #     self.includeDirectories = [os.path.abspath(os.path.join(self.rootDirectory, 'external_sources', dir)) for dir in self.defaultIncludeDirectories]

        # User-specified flags #TODO
        # if 'flags' in config:
        #     self.compileFlags        += config['flags'].get(['compile'],         [])
        #     self.compileFlagsRelease += config['flags'].get(['compile_release'], [])
        #     self.compileFlagsDebug   += config['flags'].get(['compile_debug'],   [])
        #     self.linkFlags           += config['flags'].get(['link'],            [])

        # User-specified include directories
        if 'sources' in config:
            if 'include_directories' in config['sources']:
                self.includeDirectories += [os.path.abspath(os.path.join(self.rootDirectory, dir)) for dir in config['sources']['include_directories']]


        # Only unique flags
        for targetName in self.dependencyNames:
            self.compileFlags       += environment.targets[targetName].compileFlags
            self.linkFlags          += environment.targets[targetName].linkFlags
            self.includeDirectories += environment.targets[targetName].includeDirectories

        # Remove redundant flags
        self.compileFlags        = list(set(self.compileFlags))
        self.compileFlagsRelease = list(set(self.compileFlagsRelease))
        self.compileFlagsDebug   = list(set(self.compileFlagsDebug))
        self.linkFlags           = list(set(self.linkFlags))


    def compile(self):
        # Needs to be implemented by subclass
        raise NotImplementedError()

    def link(self):
        # Needs to be implemented by subclass
        raise NotImplementedError()



class HeaderOnly(Target):
    def __init__(self, name, external, rootDirectory, includeDirectories, headerFiles, config, dependencyNames, parentNames):
        super(HeaderOnly, self).__init__(name, external, rootDirectory, includeDirectories, headerFiles, config, dependencyNames, parentNames)

    def compile(self):
        # All dependencies need to be compiled before the target can be compiled
        for targetName in self.dependencyNames:
            if not environment.targets[targetName].__class__ is HeaderOnly:
                if not environment.targets[targetName].compiled:
                    return

        print("-- Target "+self.name+" is header-only")
        # Trigger compilation of parents in the dependency graph
        for name in self.parentNames:
            environment.targets[name].compile()

    def link(self):
        # print(" link "+self.name)
        # All dependencies need to be linked before the target can be linked
        for targetName in self.dependencyNames:
            if not environment.targets[targetName].__class__ is HeaderOnly:
                if not environment.targets[targetName].compiled:
                    # print("not yet built: ", environment.targets[targetName])
                    return

        print("-- Target "+self.name+" is header-only", self.parentNames)
        # Trigger linking of parents in the dependency graph
        for name in self.parentNames:
            environment.targets[name].link()


class BuildableFile():
    def __init__(self, sourceFile, targetDirectory, depfileDirectory, objectDirectory, includeDirectories, compileFlags):
        #TODO
        self.sourceFile         = sourceFile
        # self.targetType         = targetType
        # self.buildType          = buildType
        self.targetDirectory    = targetDirectory
        # self.buildDirectory     = buildDirectory
        # self.directory          = directory
        self.depfileDirectory   = depfileDirectory
        self.objectDirectory    = objectDirectory
        # # self.root               = root

        self.includeDirectories = includeDirectories
        self.compileFlags       = compileFlags
        # self.linkFlags          = linkFlags

        # Get the relative file path
        path, file = os.path.split(sourceFile)
        relpath = os.path.relpath(path, self.targetDirectory)
        if  os.path.exists(os.path.join(self.targetDirectory, 'src')):
            relpath = os.path.relpath(relpath, 'src')
        # Get file name and extension
        name, extension = os.path.splitext(file)

        # # Set name, extension and potentially produced output files
        self.name          = name
        # self.fileExtension = extension
        self.fileName      = name + extension
        self.objectFile    = os.path.join(self.objectDirectory,  relpath, self.name + ".o")
        self.depfile       = os.path.join(self.depfileDirectory, relpath, self.name + ".d")

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
Scan the dependencies of a BuildableFile and write them into a depfile
This is not a class method, so that it can be called from multiprocessing
"""
def generateDepfile(buildableFile):
    sourceFile = buildableFile.sourceFile
    depfile    = os.path.abspath(buildableFile.depfile)

    path, _ = os.path.split(depfile)
    mkpath(path)

    flags = []

    for flag in buildableFile.compileFlags:
        flags.append(flag)

    for dir in buildableFile.includeDirectories:
        flags.append("-I" + dir)

    command = ["clang++", "-E", "-MMD", sourceFile, "-MF", depfile]
    command += flags

    # if environment.verbose:
    #     print("--   " + ' '.join(command))
    print("--   " + ' '.join(command))

    devnull = open(os.devnull, 'w')
    subprocess.call(command, stdout=devnull, stderr=devnull)



"""
Compile a BuildableFile...
"""
def compile(buildableFile):
    objectFile = buildableFile.objectFile

    path, _ = os.path.split(objectFile)
    mkpath(path)

    flags = []

    for flag in buildableFile.compileFlags:
        flags.append(flag)

    for dir in buildableFile.includeDirectories:
        flags.append("-I" + dir)

    command = ["clang++", "-c", buildableFile.sourceFile, "-o", objectFile]
    command += flags

    # if environment.verbose:
    #     print("--   " + ' '.join(command))
    print("--   " + ' '.join(command))

    subprocess.call(command)



class BuildableTarget(Target):

    COMPILE_COMMAND = ""
    LINK_COMMAND    = ""
    PREFIX          = ""
    SUFFIX          = ""
    OUT_DIR         = ""

    def __init__(self, name, external, rootDirectory, includeDirectories, headerFiles, sourceFiles, config, dependencyNames, parentNames):
        super(BuildableTarget, self).__init__(name, external, rootDirectory, includeDirectories, headerFiles, config, dependencyNames, parentNames)

        # User-defined compile flags
        self.compileFlagsDict = {
            BuildType.Default        : [],
            BuildType.Release        : [],
            BuildType.MinSizeRel     : [],
            BuildType.RelWithDebInfo : [],
            BuildType.Debug          : [],
            BuildType.Coverage       : []
        }

        # User-defined link flags
        self.linkFlagsDict = {
            BuildType.Default        : [],
            BuildType.Release        : [],
            BuildType.MinSizeRel     : [],
            BuildType.RelWithDebInfo : [],
            BuildType.Debug          : [],
            BuildType.Coverage       : []
        }

        self.compiled = False
        self.linked   = False

        self.sourceFiles = sourceFiles
        # Generate object files which to compile and link
        self.buildableFiles = []

        # Build dirs
        self.buildDirectory   = "build" #TODO
        self.depfileDirectory = "build/deps" #TODO
        self.objectDirectory  = "build/obj" #TODO

        # Parse the config
        # Output name
        if "output_name" in config:
            self.outname     = config["output_name"]
        else:
            self.outname     = self.name
        # # Dependencies
        # if "link" in config:
        #     if "dependencies" in config["link"]:
        #         deps = config["link"]["dependencies"]
        #         for dep in deps:
        #             if dep not in target.dependencies:
        #                 target.dependencies.append(str(dep))
        #                 if environment.verbose: print("-- Dependency added: "+target.name+" -> "+dep)

        self.outfile = self.PREFIX + self.outname + self.SUFFIX
        self.outdir  = self.buildDirectory + "/" + self.OUT_DIR
        # self.compilecommand = [self.COMPILE_COMMAND, self.outdir+"/"+self.outfile]
        self.linkCommand    = [self.LINK_COMMAND,    self.outdir+"/"+self.outfile]

        self.beforeCompileScript = ""
        self.beforeLinkScript    = ""
        self.afterBuildScript    = ""

        # Create set of buildables
        for sourceFile in self.sourceFiles:
            buildableFile = BuildableFile(
                sourceFile,
                targetDirectory    = self.rootDirectory,
                depfileDirectory   = self.depfileDirectory,
                objectDirectory    = self.objectDirectory,
                includeDirectories = self.includeDirectories,
                compileFlags       = self.compileFlags)#, linkFlags=self.linkFlags)
            self.buildableFiles.append(buildableFile)

    # From the list of source files, compile those which changed or whose dependencies (included headers, ...) changed
    def compile(self):
        # All dependencies need to be compiled before the target can be compiled
        for targetName in self.dependencyNames:
            if not environment.targets[targetName].__class__ is HeaderOnly:
                if not environment.targets[targetName].compiled:
                    return

        # Object file only needs to be (re-)compiled if the source file or headers it depends on changed
        buildList = []
        for buildable in self.buildableFiles:
            sourceFile = buildable.sourceFile
            objectFile = buildable.objectFile
            # Check if object file has been compiled
            if os.path.isfile(objectFile):
                # If object file is found, check if it is up to date
                if os.path.getmtime(sourceFile) > os.path.getmtime(objectFile):
                    buildList.append(buildable)
                # If object file is up to date, we check the headers it depends on
                else:
                    depHeaderFiles = buildable.getDepfileHeaders()
                    for depHeaderFile in depHeaderFiles:
                        if os.path.getmtime(depHeaderFile) > os.path.getmtime(objectFile):
                            buildList.append(buildable)
            else:
                buildList.append(buildable)

        # If the target was not modified, it may not need to compile
        if not buildList:
            if environment.verbose:
                print("-- Target " + self.name + " is already compiled")
            self.compiled = True

        if environment.verbose and buildList:
            print("-- Target " + self.name + ": need to build sources " + ', '.join([b.fileName for b in buildList]))

        # Before-compile step
        if self.beforeCompileScript and not self.compiled:
            if environment.verbose:
                print("-- Pre-compile step of target " + self.name)
            originalDir = os.getcwd()
            newDir, _ = os.path.split(self.beforeCompileScript)
            os.chdir(newDir)
            execfile(self.beforeCompileScript)
            os.chdir(originalDir)
            if environment.verbose:
                print("-- Finished pre-compile step of target " + self.name)

        # Compile
        if not self.compiled:
            # Create base directory for build
            mkpath(self.buildDirectory)

            # Create header dependency graph
            print("-- Scanning dependencies of target " + self.name)
            processpool.map(generateDepfile, buildList)

            # Execute compile command
            print("-- Compile target " + self.name)
            processpool.map(compile, buildList)

        # Done
        self.compiled = True

        # Spawn compilation of dependency parents
        for parentName in self.parentNames:
            environment.targets[parentName].compile()

    # Link the compiled object files
    def link(self):
        # All dependencies need to be finished before the target can be linked
        for targetName in self.dependencyNames:
            if not environment.targets[targetName].__class__ is HeaderOnly:
                if not environment.targets[targetName].linked:
                    return

        # Before-link step
        if self.beforeLinkScript:
            if environment.verbose:
                print("-- Pre-link step of target " + self.name)
            originalDir = os.getcwd()
            newDir, _ = os.path.split(self.beforeCompileScript)
            os.chdir(newDir)
            execfile(self.beforeLinkScript)
            os.chdir(originalDir)
            if environment.verbose:
                print("-- Finished pre-link step of target " + self.name)

        # Link
        mkpath(self.outdir)
        linkCommand = self.linkCommand

        ### Library dependency search paths
        for targetName in self.dependencyNames:
            if not environment.targets[targetName].__class__ == HeaderOnly:
                linkCommand += ["-L"+os.path.abspath(environment.targets[targetName].libraryDirectory)]

        ### Include directories
        for dir in self.includeDirectories:
            linkCommand.append("-I"+dir)

        ### Link dependencies
        for targetName in self.dependencyNames:
            if not environment.targets[targetName].__class__ == HeaderOnly:
                linkCommand += ["-l"+environment.targets[targetName].outname]

        # Execute link command
        print("-- Link target " + self.name)
        if environment.verbose:
            print("--   " + ' '.join(linkCommand))
        subprocess.call(linkCommand)

        # Done
        self.linked = True

        # After-build step
        if self.afterBuildScript:
            if environment.verbose:
                print("-- After-build step of target " + self.name)
            originalDir = os.getcwd()
            newDir, _ = os.path.split(self.beforeCompileScript)
            os.chdir(newDir)
            execfile(self.afterBuildScript)
            os.chdir(originalDir)
            if environment.verbose:
                print("-- Finished after-build step of target " + self.name)

        # Spawn compilation of dependency parents
        for parentName in self.parentNames:
            environment.targets[parentName].link()



class Executable(BuildableTarget):

    COMPILE_COMMAND = "clang++ -o"
    LINK_COMMAND    = "clang++ -o"
    PREFIX          = ""
    SUFFIX          = ""
    OUT_DIR         = "bin"
    if _platform == "win32":
        SUFFIX     = '.exe'
        platform_extra_flags_executable = ['-Xclang', '-flto-visibility-public-std']

    def __init__(self, name, external, rootDirectory, includeDirectories, headerFiles, sourceFiles, config, dependencyNames, parentNames):
        super(Executable, self).__init__(name, external, rootDirectory, includeDirectories, headerFiles, sourceFiles, config, dependencyNames, parentNames)
        pass



class SharedLibrary(BuildableTarget):

    COMPILE_COMMAND = "clang++ -shared -o"
    LINK_COMMAND    = "clang++ -o"
    PREFIX          = "lib"
    SUFFIX          = ".so"
    OUT_DIR         = "bin"

    if _platform == "linux" or _platform == "linux2":
        # Linux
        platform_extra_flags_shared = ['-fpic']
    elif _platform == "darwin":
        # OS X
        PREFIX = 'lib'
        SUFFIX = '.dylib'
        platform_extra_flags_shared = ['']
    elif _platform == "win32":
        # Windows
        PREFIX = ''
        SUFFIX = '.dll'
        platform_extra_flags_shared = ['-Xclang', '-flto-visibility-public-std']

    def __init__(self, name, external, rootDirectory, includeDirectories, headerFiles, sourceFiles, config, dependencyNames, parentNames):
        super(SharedLibrary, self).__init__(name, external, rootDirectory, includeDirectories, headerFiles, sourceFiles, config, dependencyNames, parentNames)
        pass



class StaticLibrary(BuildableTarget):

    COMPILE_COMMAND = "clang++ -o"
    LINK_COMMAND    = "llvm-ar rc"
    PREFIX          = "lib"
    SUFFIX          = ".a"
    OUT_DIR         = "lib"

    if _platform == "win32":
        # Windows
        PREFIX = ''
        SUFFIX = '.lib'
        platform_extra_flags_static     = ['-Xclang', '-flto-visibility-public-std']
        
    def __init__(self, name, external, rootDirectory, includeDirectories, headerFiles, sourceFiles, config, dependencyNames, parentNames):
        super(StaticLibrary, self).__init__(name, external, rootDirectory, includeDirectories, headerFiles, sourceFiles, config, dependencyNames, parentNames)
        pass



class Environment():
    def __init__(self):
        # Pool for multiprocessing
        global processpool
        self.nJobs = 1
        processpool = Pool(processes=self.nJobs)

        # Default include directories
        self.defaultIncludeDirectories = ["include", "thirdparty"]

        # Default compile flags
        compileFlagsAny = ["-std=c++"+supported_dialect_newest, "-Wall", "-Werror"]
        self.defaultCompileFlags = {
            BuildType.Default        : compileFlagsAny + [],
            BuildType.Release        : compileFlagsAny + ["-O3", "-DNDEBUG"],
            BuildType.MinSizeRel     : compileFlagsAny + ["-O3", "-DNDEBUG"],
            BuildType.RelWithDebInfo : compileFlagsAny + ["-O3", "-g3", "-DDEBUG"],
            BuildType.Debug          : compileFlagsAny + ["-O0", "-g3", "-DDEBUG"],
            BuildType.Coverage       : compileFlagsAny + ["-O0", "-g3", "-DDEBUG", "--coverage", "-fno-inline", "-fno-inline-small-functions", "-fno-default-inline"]
        }

        # Default link flags
        linkFlagsAny = []
        self.defaultCompileFlags = {
            BuildType.Default        : linkFlagsAny + [],
            BuildType.Release        : linkFlagsAny + [],
            BuildType.MinSizeRel     : linkFlagsAny + [],
            BuildType.RelWithDebInfo : linkFlagsAny + [],
            BuildType.Debug          : linkFlagsAny + [],
            BuildType.Coverage       : linkFlagsAny + []
        }

        # Check for clang executables
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
        self.configFile = ""
        if os.path.isfile(self.workingDirectory + "/clang-build.toml"):
            self.configFile = self.workingDirectory + "/clang-build.toml"
            if self.verbose:
                print("-- Found config file!")
        elif self.verbose:
            print("-- Did not find config file!")

        # Build type (Default, Release, Debug)
        self.buildType = BuildType.Default
        if args.build_type:
            self.buildType = BuildType[args.build_type.lower().title()]
        print("-- Build type: " + self.buildType.name)




def parseSources(relativeDirectory, sourceConfig):
    output = {
        'includeDirectories': [],
        'sourceDirectories':  [],
        'headerFiles': [],
        'sourceFiles': []
    }
    # if 'sources' in config:
    #     sourceConfig = node["sources"]

    # sourceroot = os.path.join(environment.workingDirectory, relativeDirectory)
    sourceroot = environment.workingDirectory

    # # Target root directory
    # if "root" in sourceConfig:
    #     target.root = sourceConfig["root"]
    #     target.includeDirectories.append(target.targetDirectory+"/"+target.root)

    if "include_directories" in sourceConfig:
        # Add include directories
        for dir in sourceConfig["include_directories"]:
            if dir not in output['includeDirectories']:
                output['includeDirectories'].append(os.path.join(sourceroot, dir))

        # Search for header files
        for ext in ('*.hpp', '*.hxx', '*.h'):
            for dir in output['includeDirectories']:
                output['headerFiles'] += glob(os.path.join(sourceroot, dir, ext))

    # Search for source files
    if "source_directories" in sourceConfig:
        for ext in ('*.cpp', '*.cxx', '*.c'):
            for dir in sourceConfig["source_directories"]:
                output['sourceFiles'] += glob(os.path.join(sourceroot, dir, ext))

    return output


class DummyTarget():
    def __init__(self, name, config):
        self.name          = name
        self.dependencies  = []
        self.parents       = []
        self.visited       = False
        self.config        = config
        self.createdTarget = False

    def visit(self):
        # All dependencies need to have been visited
        for target in self.dependencies:
            if not target.visited:
                return
        self.visited = True
        # Move visitation up the dependency graph
        for parent in self.parents:
            parent.visit()

    def createTarget(self):
        # All dependencies need to have been visited
        for target in self.dependencies:
            if not target.createdTarget:
                return

        # Create Target
        headerOnly = True
        external = False
        includeDirectories = []
        headerFiles = []
        sourceFiles = []
        
        # Dependencies
        dependencyNames = [dependency.name for dependency in self.dependencies]
        # Parents
        parentNames = [parent.name for parent in self.parents]
        # Target root directory
        targetDirectory = environment.workingDirectory
        relativeTargetDirectory = self.name
        if 'directory' in self.config:
            relativeTargetDirectory = self.config['directory']
        targetDirectory = os.path.abspath(os.path.join(targetDirectory, relativeTargetDirectory))
        # Handle the case that the target is an external project
        if "external" in self.config:
            external        = self.config["external"]
            if external:
                downloaddir = os.path.join("build", relativeTargetDirectory, "external_sources")
                # Check if directory is already present and non-empty
                if os.path.exists(downloaddir) and os.listdir(downloaddir):
                    print("-- External target " + self.name + ": sources found in "+downloaddir)
                # Otherwise we download the sources
                else:
                    print("-- External target " + self.name + ": downloading to "+downloaddir)
                    mkpath(downloaddir)
                    subprocess.call(["git", "clone", self.config["url"], downloaddir])
                    print("-- External target " + self.name + ": downloaded")
                includeDirectories.append(downloaddir)
                targetDirectory = downloaddir
        # Sources
        if 'sources' in self.config:
            sources            = parseSources(relativeTargetDirectory, self.config['sources'])
            sourceFiles        = sources['sourceFiles']
            headerFiles        = sources['headerFiles']
            includeDirectories = sources['includeDirectories']
            if sourceFiles:
                headerOnly = False
        # Create target corresponding to specified type
        if "target_type" in self.config:
            targetType = self.config["target_type"].lower()
            if not headerOnly:
                # Executable
                if   targetType == "executable":
                    environment.targets[self.name] = Executable(self.name, external, targetDirectory, includeDirectories, headerFiles, sourceFiles, self.config, dependencyNames, parentNames)
                # Shared library
                elif targetType == "shared_library":
                    environment.targets[self.name] = SharedLibrary(self.name, external, targetDirectory, includeDirectories, headerFiles, sourceFiles, self.config, dependencyNames, parentNames)
                # Static library
                elif targetType == "static_library":
                    environment.targets[self.name] = StaticLibrary(self.name, external, targetDirectory, includeDirectories, headerFiles, sourceFiles, self.config, dependencyNames, parentNames)
                # Header only
                elif targetType == "header_only":
                    print("-- Error: target type \"header_only\" was specified, but sources were specified, too!")
                # Unknown
                else:
                    print("-- Error: target type \"" + targetType + "\" unknown!")
            else:
                # Header only
                if targetType == "header_only":
                    environment.targets[self.name] = HeaderOnly(self.name, external, targetDirectory, includeDirectories, headerFiles, self.config, dependencyNames, parentNames)
                # Other
                else:
                    print("-- Error: target type \"" + targetType + "\" was specified, but no sources were found! Maybe you wanted to use \"header_only\"?")
        # If the type was not specified, we assume it's an executable unless it's header-only
        else:
            if headerOnly:
                environment.targets[self.name] = HeaderOnly(self.name, external, targetDirectory, includeDirectories, headerFiles, self.config, dependencyNames, parentNames)
            else:
                environment.targets[self.name] = Executable(self.name, external, targetDirectory, includeDirectories, headerFiles, sourceFiles, self.config, dependencyNames, parentNames)

        self.createdTarget = True

        # Move creation up the dependency graph
        for parent in self.parents:
            parent.createTarget()


def parseDependencyGraph():

    # Read the project configuration file
    project = toml.load(environment.configFile)

    # Create a list of unique dummy targets
    dummyTargets = {}
    for targetname, targetconfig in project.items():
        if targetname not in dummyTargets:
            # # Dependencies
            dummyTargets[targetname] = DummyTarget(targetname, targetconfig)
        else:
            print("-- ERROR: target named twice")
            exit(1)

    # Resolve dependencies among dummy targets
    for targetname, target in dummyTargets.items():
        if "dependencies" in target.config:
            deps = target.config["dependencies"]
            for dep in deps:
                if dep not in target.dependencies:
                    valid = False
                    for depTargetName, depTarget in dummyTargets.items():
                        if dep == depTarget.name:
                            valid = True
                            if depTarget not in target.dependencies:
                                target.dependencies.append(depTarget)
                                depTarget.parents.append(target)
                                print("-- Dependency resolved: "+target.name+" -> "+dep)
                            else:
                                print("-- WARNING: you may have a double dependency: "+target.name+" -> "+dep)
                    if not valid:
                        print("-- WARNING: could not resolve dependency "+target.name+" -> "+dep)

    # Determine leafs on dependency graph
    leafs = []
    for name, dummyTarget in dummyTargets.items():
        if not dummyTarget.dependencies:
            leafs.append(name)

    # Check for circular dependencies:
    # if any target has not completed visitation after this, there is a circular dependency.
    # This will automatically also detect if there are no leaf nodes.
    for leaf in leafs:
        dummyTargets[leaf].visit()
    for name, dummyTarget in dummyTargets.items():
        if not dummyTarget.visited:
            print("-- ERROR: circular dependency!")
            exit(1)

    environment.leafs   = leafs
    environment.targets = {}

    # Generate targets from dummies
    # for name, dummyTarget in dummyTargets.items():
    for name in leafs:
        dummyTarget = dummyTargets[name]
        dummyTarget.createTarget()





def main():
    print("---- clang-build v0.0.0")

    # Parse command line arguments, check for presence of build config file, etc.
    global environment
    environment = Environment()

    # Check dependencies
    if environment.configFile:
        print("---- Parsing dependencies")
        parseDependencyGraph()
        targets = environment.targets
        leafs   = environment.leafs

    # If build configuration toml file exists, parse lists of targets and leaf nodes of the dependency graph
    # if environment.configFile:
    #     targets, leafs = parseBuildConfig(environment)
    # Otherwise we try to build it as a simple hello world or mwe project
    else:
        defaultTarget = getDefaultTarget()
        targets = { 'main': defaultTarget }
        leafs   = [ 'main' ]

    # Build the targets, moving successively up the dependency graph
    print("---- Compile step")
    for targetName in leafs:
        targets[targetName].compile()

    print("---- Link step")
    for targetName in leafs:
        targets[targetName].link()

    print("---- clang-build finished")


if __name__ == "__main__":
    sys.exit(main())