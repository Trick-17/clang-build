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
    DEFAULT_COMPILE_FLAGS          = ['-Wall', '-Werror']
    DEFAULT_RELEASE_COMPILE_FLAGS  = ['-O3', '-DNDEBUG']
    DEFAULT_DEBUG_COMPILE_FLAGS    = ['-O0', '-g3', '-DDEBUG']
    DEFAULT_COVERAGE_COMPILE_FLAGS = (
        DEFAULT_DEBUG_COMPILE_FLAGS +
        ['--coverage',
            '-fno-inline',
            '-fno-inline-small-functions',
            '-fno-default-inline'])
    defaultIncludeDirectories = ['include']

    def __init__(self, name, rootDirectory, includeDirectories, headerFiles, config, dependencyNames, parentNames):
        # Identifier name
        self.name          = name
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
        # User-specified flags #TODO
        # if 'flags' in config:
        #     self.compileFlags        += config['flags'].get(['compile'],         [])
        #     self.compileFlagsRelease += config['flags'].get(['compile_release'], [])
        #     self.compileFlagsDebug   += config['flags'].get(['compile_debug'],   [])
        #     self.linkFlags           += config['flags'].get(['link'],            [])
        # Only unique flags
        self.compileFlags = list(set(self.compileFlags))
        self.compileFlagsRelease = list(set(self.compileFlagsRelease))
        self.compileFlagsDebug = list(set(self.compileFlagsDebug))
        self.linkFlags = list(set(self.linkFlags))

        # TODO: where should defaultIncludeDirectories be specified?
        self.includeDirectories = [os.path.abspath(os.path.join(self.rootDirectory, dir)) for dir in self.defaultIncludeDirectories]

    def compile(self):
        # Needs to be implemented by subclass
        raise NotImplementedError()

    def link(self):
        # Needs to be implemented by subclass
        raise NotImplementedError()




class HeaderOnly(Target):
    def __init__(self, name, rootDirectory, includeDirectories, headerFiles, config, dependencyNames, parentNames):
        super(HeaderOnly, self).__init__(name, rootDirectory, includeDirectories, headerFiles, config, dependencyNames, parentNames)

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
        # All dependencies need to be linked before the target can be linked
        for targetName in self.dependencyNames:
            if not environment.targets[targetName].__class__ is HeaderOnly:
                if not environment.targets[targetName].compiled:
                    return

        print("-- Target "+self.name+" is header-only")
        # Trigger linking of parents in the dependency graph
        for name in self.parentNames:
            environment.targets[name].link()


class BuildableFile():
    def __init__(self):
        #TODO
        # self.sourceFile         = sourceFile
        # self.targetType         = targetType
        # self.buildType          = buildType
        # environment.verbose            = verbose
        # self.targetDirectory    = targetDirectory
        # self.buildDirectory     = buildDirectory
        # self.directory          = directory
        # self.depfileDirectory   = depfileDirectory
        # # self.root               = root
        # self.includeDirectories = includeDirectories
        # self.compileFlags       = compileFlags
        # self.linkFlags          = linkFlags

        # # Get the relative file path
        # path, file = os.path.split(sourceFile)
        # relpath = os.path.relpath(path, self.targetDirectory+"/"+self.root)
        # if  os.path.exists(self.targetDirectory+"/"+self.root+'/src'):
        #     relpath = os.path.relpath(relpath, 'src')
        # # Get file name and extension
        # name, extension = os.path.splitext(file)

        # # Set name, extension and potentially produced output files
        # self.name          = name
        # self.fileExtension = extension
        # self.objectFile    = self.objectDirectory + "/" + relpath + "/" + self.name + ".o"
        # self.depfile       = self.depfileDirectory + "/" + relpath + "/" + self.name + ".d"
        pass

    def generateDepFile(self):
        raise NotImplementedError()

    def compile(self):
        raise NotImplementedError()

    def link(self):
        raise NotImplementedError()


class BuildableTarget(Target):

    COMPILE_COMMAND = ""
    LINK_COMMAND    = ""
    PREFIX          = ""
    SUFFIX          = ""
    OUT_DIR         = ""

    def __init__(self, name, rootDirectory, includeDirectories, headerFiles, sourceFiles, config, dependencyNames, parentNames):
        super(BuildableTarget, self).__init__(name, rootDirectory, includeDirectories, headerFiles, config, dependencyNames, parentNames)

        # User-defined compile flags
        self.compileFlags = {
            BuildType.Default        : [],
            BuildType.Release        : [],
            BuildType.MinSizeRel     : [],
            BuildType.RelWithDebInfo : [],
            BuildType.Debug          : [],
            BuildType.Coverage       : []
        }

        # User-defined link flags
        self.linkFlags = {
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
        self.buildDirectory = "" #TODO

        # Parse the config
        # Output name
        if "output_name" in config:
            self.outname     = config["output_name"]
        else:
            self.outname     = self.name

        self.outfile = self.PREFIX + self.outname + self.SUFFIX
        self.outdir  = self.buildDirectory + "/" + self.OUT_DIR
        # self.compilecommand = [self.COMPILE_COMMAND, self.outdir+"/"+self.outfile]
        self.linkCommand    = [self.LINK_COMMAND,    self.outdir+"/"+self.outfile]

        self.beforeCompileScript = ""
        self.beforeLinkScript    = ""
        self.afterBuildScript    = ""

    def generateBuildableFiles(self):
        #TODO
        # for sourceFile in self.sourceFiles:
        #     buildableFile = ObjectFile(sourceFile, self.targetType, buildType=self.buildType, verbose=environment.verbose, depfileDirectory=self.depfileDirectory, objectDirectory=self.objectDirectory, targetDirectory=self.targetDirectory, buildDirectory=self.buildDirectory, root=self.root, includeDirectories=self.includeDirectories, compileFlags=self.compileFlags, linkFlags=self.linkFlags)
        #     self.buildableFiles.append(buildableFile)
        pass

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
                print("-- Target " + self.outname + " is already compiled")
            self.compiled = True

        if environment.verbose and buildList:
            print("-- Target " + self.outname + ": need to rebuild sources ", [b.name for b in buildList])

        # Before-compile step
        if self.beforeCompileScript and not self.compiled:
            if environment.verbose:
                print("-- Pre-compile step of target " + self.outname)
            originalDir = os.getcwd()
            newDir, _ = os.path.split(self.beforeCompileScript)
            os.chdir(newDir)
            execfile(self.beforeCompileScript)
            os.chdir(originalDir)
            if environment.verbose:
                print("-- Finished pre-compile step of target " + self.outname)

        # Compile
        if not self.compiled:
            # Create base directory for build
            mkpath(self.buildDirectory)

            # Create header dependency graph
            print("-- Scanning dependencies of target " + self.outname)
            # processpool.map(generateDepfile, buildList) #TODO

            # Execute compile command
            print("-- Compile target " + self.outname)
            processpool.map(compile, buildList)

        # Done
        self.compiled = True

        # Spawn compilation of dependency parents
        for parentName in self.parentNames:
            environment.targets[parentName].compile()

    # Link the compiled object files
    def link(self):
        # All dependencies need to be finished before the target can be linked
        for targetName in self.parentNames:
            if not environment.targets[targetName].__class__ is HeaderOnly:
                if not environment.targets[targetName].linked:
                    return

        # Before-link step
        if self.beforeLinkScript:
            if environment.verbose:
                print("-- Pre-link step of target " + self.outname)
            originalDir = os.getcwd()
            newDir, _ = os.path.split(self.beforeCompileScript)
            os.chdir(newDir)
            execfile(self.beforeLinkScript)
            os.chdir(originalDir)
            if environment.verbose:
                print("-- Finished pre-link step of target " + self.outname)

        # Link
        mkpath(self.outdir)
        linkCommand = self.linkCommand

        ### Library dependency search paths
        for targetName in self.dependencyNames:
            if not environment.targets[targetName].header_only:
                linkCommand += ["-L"+os.path.abspath(environment.targets[targetName].libraryDirectory)]

        ### Include directories
        for dir in self.includeDirectories:
            linkCommand.append("-I"+dir)

        ### Link self #TODO
        # for buildable in self.buildables:
        #     objectFile = buildable.objectFile
        #     linkCommand.append(objectFile)

        ### Link dependencies
        for targetName in self.dependencyNames:
            if not environment.targets[targetName].header_only:
                linkCommand += ["-l"+environment.targets[targetName].outname]

        # Execute link command
        print("-- Link target " + self.outname)
        if environment.verbose:
            print("--   " + ' '.join(linkCommand))
        subprocess.call(linkCommand)

        # Done
        self.linked = True

        # After-build step
        if self.afterBuildScript:
            if environment.verbose:
                print("-- After-build step of target " + self.outname)
            originalDir = os.getcwd()
            newDir, _ = os.path.split(self.beforeCompileScript)
            os.chdir(newDir)
            execfile(self.afterBuildScript)
            os.chdir(originalDir)
            if environment.verbose:
                print("-- Finished after-build step of target " + self.outname)

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

    def __init__(self, name, rootDirectory, includeDirectories, headerFiles, sourceFiles, config, dependencyNames, parentNames):
        super(Executable, self).__init__(name, rootDirectory, includeDirectories, headerFiles, sourceFiles, config, dependencyNames, parentNames)
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

    def __init__(self, name, rootDirectory, includeDirectories, headerFiles, sourceFiles, config, dependencyNames, parentNames):
        super(SharedLibrary, self).__init__(name, rootDirectory, includeDirectories, headerFiles, sourceFiles, config, dependencyNames, parentNames)
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
        
    def __init__(self, name, rootDirectory, includeDirectories, headerFiles, sourceFiles, config, dependencyNames, parentNames):
        super(StaticLibrary, self).__init__(name, rootDirectory, includeDirectories, headerFiles, sourceFiles, config, dependencyNames, parentNames)
        pass







class Environment():
    def __init__(self):
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



def parseDependencyGraph():
    class DummyTarget():
        def __init__(self, name, config):
            self.name         = name
            self.dependencies = []
            self.parents      = []
            self.visited      = False
            self.config       = config
        def visit(self):
            # All dependencies need to have been visited
            for target in self.dependencies:
                if not target.visited:
                    return
            self.visited = True
            # Move visitation up the dependency graph
            for parent in self.parents:
                parent.visit()

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

    # # Done
    # print("DONE")
    # return dummyTargets

    # Generate targets from dummies
    targets = {}
    for name, dummyTarget in dummyTargets.items():
        # Dependencies
        dependencyNames = [dependency.name for dependency in dummyTarget.dependencies]
        # Parents
        parentNames = [parent.name for parent in dummyTarget.parents]
        # Target root directory
        targetDirectory = environment.workingDirectory
        relativeTargetDirectory = name
        if 'directory' in dummyTarget.config:
            relativeTargetDirectory = dummyTarget.config['directory']
        targetDirectory = os.path.abspath(os.path.join(targetDirectory, relativeTargetDirectory))
        # Sources
        headerOnly = True
        includeDirectories = []
        headerFiles = []
        sourceFiles = []
        if 'sources' in dummyTarget.config:
            sources            = parseSources(relativeTargetDirectory, dummyTarget.config['sources'])
            sourceFiles        = sources['sourceFiles']
            headerFiles        = sources['headerFiles']
            includeDirectories = sources['includeDirectories']
            if sourceFiles:
                headerOnly = False
        # Create target corresponding to specified type
        if "target_type" in dummyTarget.config:
            targetType = dummyTarget.config["target_type"].lower()
            if not headerOnly:
                # Executable
                if   targetType == "executable":
                    targets[name] = Executable(name, targetDirectory, includeDirectories, headerFiles, sourceFiles, dummyTarget.config, dependencyNames, parentNames)
                # Shared library
                elif targetType == "shared_library":
                    targets[name] = SharedLibrary(name, targetDirectory, includeDirectories, headerFiles, sourceFiles, dummyTarget.config, dependencyNames, parentNames)
                # Static library
                elif targetType == "static_library":
                    targets[name] = StaticLibrary(name, targetDirectory, includeDirectories, headerFiles, sourceFiles, dummyTarget.config, dependencyNames, parentNames)
                # Header only
                elif targetType == "header_only":
                    print("-- Error: target type \"header_only\" was specified, but sources were specified, too!")
                # Unknown
                else:
                    print("-- Error: target type \"" + targetType + "\" unknown!")
            else:
                # Header only
                if targetType == "header_only":
                    targets[name] = HeaderOnly(name, targetDirectory, includeDirectories, headerFiles, dummyTarget.config, dependencyNames, parentNames)
                # Other
                else:
                    print("-- Error: target type \"" + targetType + "\" was specified, but no sources were found! Maybe you wanted to use \"header_only\"?")
        # If the type was not specified, we assume it's an executable unless it's header-only
        else:
            if headerOnly:
                targets[name] = HeaderOnly(name, targetDirectory, includeDirectories, headerFiles, dummyTarget.config, dependencyNames, parentNames)
            else:
                targets[name] = Executable(name, targetDirectory, includeDirectories, headerFiles, sourceFiles, dummyTarget.config, dependencyNames, parentNames)


        # # Create target corresponding to specified type
        # if "build" in dummyTarget.config:
        #     build_types = [x.lower() for x in dummyTarget.config["build"]]
        #     # Executable
        #     if   dummyTarget.config["build"].lower() == "executable":
        #         targets[name] = Executable(name, includeDirectories, headerFiles, sourceFiles, dummyTarget.config, dependencyNames, parentNames)
        #     elif dummyTarget.config["target_type"].lower() == "library":
        #         targets[name] = Library(name, includeDirectories, headerFiles, sourceFiles, dummyTarget.config, dependencyNames, parentNames)
        #     else:
        #         targets[name] = HeaderOnly(name, includeDirectories, headerFiles, dummyTarget.config, dependencyNames, parentNames)
        # # If the type was not specified, we assume it's an executable unless it's header-only
        # else:
        #     if headerOnly:
        #         targets[name] = HeaderOnly(name, includeDirectories, headerFiles, dummyTarget.config, dependencyNames, parentNames)
        #     else:
        #         targets[name] = Executable(name, includeDirectories, headerFiles, sourceFiles, dummyTarget.config, dependencyNames, parentNames)


    return targets, leafs
















def main():
    print("---- clang-build v0.0.0")

    # Parse command line arguments, check for presence of build config file, etc.
    global environment
    environment = Environment()

    # Check dependencies
    if environment.configFile:
        print("---- Parsing dependencies")
        targets, leafs = parseDependencyGraph()

    # If build configuration toml file exists, parse lists of targets and leaf nodes of the dependency graph
    # if environment.configFile:
    #     targets, leafs = parseBuildConfig(environment)
    # Otherwise we try to build it as a simple hello world or mwe project
    else:
        defaultTarget = getDefaultTarget()
        targets = { 'main': defaultTarget }
        leafs   = [ 'main' ]

    environment.targets = targets
    environment.leafs   = leafs

    # # Generate flags of all targets, propagating up the dependency graph
    # print(targets)
    # for targetName in leafs:
    #     targets[targetName].generateFlags()

    # # Generate the buildables of all targets
    # for targetName in targets:
    #     targets[targetName].generateBuildables()

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