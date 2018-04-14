'''
Target describes a single build or dependency target with all needed paths and
a list of buildables that comprise it's compile and link steps.
'''

from pathlib2 import Path as _Path
import subprocess as _subprocess
from multiprocessing import freeze_support as _freeze_support
import logging as _logging

from . import platform as _platform
from .dialect_check import get_dialect_string as _get_dialect_string
from .dialect_check import get_max_supported_compiler_dialect as _get_max_supported_compiler_dialect
from .build_type import BuildType as _BuildType
from .single_source import SingleSource as _SingleSource

_LOGGER = _logging.getLogger('clang_build')


class Target:
    DEFAULT_COMPILE_FLAGS = ['-Wall', '-Werror']
    DEFAULT_RELEASE_COMPILE_FLAGS = ['-O3', '-DNDEBUG']
    DEFAULT_DEBUG_COMPILE_FLAGS = ['-O0', '-g3', '-DDEBUG']
    DEFAULT_COVERAGE_COMPILE_FLAGS = (
        DEFAULT_DEBUG_COMPILE_FLAGS +
        ['--coverage',
         '-fno-inline',
         '-fno-inline-small-functions',
         '-fno-default-inline'])


    def __init__(self,
            name,
            targetDirectory,
            headers,
            include_directories,
            clangpp,
            buildType,
            options=None,
            dependencies=None):

        if options is None:
            options = {}
        if dependencies is None:
            dependencies = []

        self.dependencyTargets = dependencies

        # Basics
        self.name            = name
        self.targetDirectory = targetDirectory
        self.root            = _Path('')
        self.buildType = buildType

        self.headers = headers
        self.includeDirectories = include_directories

        if 'properties' in options and 'cpp_version' in options['properties']:
            self.dialect = _get_dialect_string(options['properties']['cpp_version'])
        else:
            self.dialect = _get_max_supported_compiler_dialect(clangpp)

        self.external = options.get('extern', False)

        compileFlags        = Target.DEFAULT_COMPILE_FLAGS
        compileFlagsDebug   = Target.DEFAULT_DEBUG_COMPILE_FLAGS
        compileFlagsRelease = Target.DEFAULT_RELEASE_COMPILE_FLAGS
        self.linkFlags = []

        if 'flags' in options:
            compileFlags += options['flags'].get('compile', [])
            compileFlagsRelease += options['flags'].get('compileRelease', [])
            compileFlagsDebug += options['flags'].get('compileDebug', [])
            self.linkFlags += options['flags'].get('link', [])

        self.compileFlags = compileFlags
        if self.buildType == _BuildType.Release:
            self.compileFlags += compileFlagsRelease
        if self.buildType == _BuildType.Debug:
            self.compileFlags += compileFlagsDebug

        for target in self.dependencyTargets:
            self.compileFlags += target.compileFlags
            self.includeDirectories += target.includeDirectories
            self.headers += target.headers

        self.compileFlags = list(set(self.compileFlags))
        self.includeDirectories = list(set(self.includeDirectories))
        self.headers = list(set(self.headers))

    def get_include_directory_command(self):
        return [f'-I{dir}' for dir in self.includeDirectories]

    def link(self):
        # Subclasses must implement
        raise NotImplementedError()

    def compile(self, process_pool):
        # Subclasses must implement
        raise NotImplementedError()


class HeaderOnly(Target):
    pass

def generateDepfile(buildable):
    buildable.generate_dependency_file()

def compile_single_source(buildable):
    buildable.compile()

class Compilable(Target):

    def __init__(self,
            name,
            targetDirectory,
            headers,
            include_directories,
            source_files,
            buildType,
            clangpp,
            link_command,
            buildDirectory,
            output_folder,
            platform_flags,
            prefix,
            suffix,
            options=None,
            dependencies=None):

        super().__init__(
            name=name,
            targetDirectory=targetDirectory,
            headers=headers,
            include_directories=include_directories,
            clangpp=clangpp,
            buildType=buildType,
            options=options,
            dependencies=dependencies)

        if options is None:
            options = {}
        if dependencies is None:
            dependencies = []

        self.buildDirectory      = buildDirectory.joinpath(self.buildType.name.lower(), self.name)

        self.objectDirectory     = self.buildDirectory.joinpath('obj')
        self.depfileDirectory    = self.buildDirectory.joinpath('dep')
        self.outputFolder        = self.buildDirectory.joinpath(output_folder)

        self.objectDirectory.mkdir(parents=True, exist_ok=True)
        self.depfileDirectory.mkdir(parents=True, exist_ok=True)
        self.outputFolder.mkdir(parents=True, exist_ok=True)

        if 'output_name' in options:
            self.outname = options['output_name']
        else:
            self.outname = self.name

        self.outfile = _Path(self.outputFolder, prefix + self.outname + suffix)


        # Clang
        self.clangpp   = clangpp

        # Sources
        self.sourceFiles        = source_files

        # Buildables which this Target contains
        self.buildables = [_SingleSource(
            sourceFile=sourceFile,
            platformFlags=platform_flags,
            current_target_root_path=self.targetDirectory.joinpath(self.root),
            depfileDirectory=self.depfileDirectory,
            objectDirectory=self.objectDirectory,
            include_strings=self.get_include_directory_command(),
            compileFlags=self.compileFlags,
            clangpp=self.clangpp) for sourceFile in self.sourceFiles]

        # If compilation of buildables fail, they will be stored here later
        self.unsuccesful_builds = []

        # Linking setup
        self.linkCommand = link_command + [str(self.outfile)]

        ### Library dependency search paths
        for target in self.dependencyTargets:
            if not target.__class__ is HeaderOnly:
                self.linkCommand += ['-L'+target.libraryDirectory.resolve()]

        ### Include directories
        #linkCommand += self.get_include_directory_command()

        ### Link self
        self.linkCommand += [str(buildable.objectFile) for buildable in self.buildables]

        ### Link dependencies
        for target in self.dependencyTargets:
            if not target.__class__ is HeaderOnly:
                self.linkCommand += ['-l'+target.outname]

    # From the list of source files, compile those which changed or whose dependencies (included headers, ...) changed
    def compile(self, process_pool):
        # Object file only needs to be (re-)compiled if the source file or headers it depends on changed
        neededBuildables = [buildable for buildable in self.buildables if buildable.needs_rebuild]

        # If the target was not modified, it may not need to compile
        if not neededBuildables:
            _LOGGER.info(f'Target [{self.outname}] is already compiled')
            return

        _LOGGER.info(f'Target [{self.outname}] needs to rebuild sources %s', [b.name for b in neededBuildables])

        # Compile

        # Execute compile command
        _LOGGER.info(f'Compile target [{self.outname}]')
        process_pool.map(compile_single_source, neededBuildables)

        self.unsuccesful_builds = [buildable for buildable in neededBuildables if buildable.compilation_failed]

    def link(self):
        # Execute link command
        _LOGGER.info(f'Link target [{self.outname}]')
        # TODO: Capture output
        _subprocess.call(self.linkCommand)


class Executable(Compilable):
    def __init__(self,
            name,
            targetDirectory,
            headers,
            include_directories,
            source_files,
            buildType,
            clangpp,
            buildDirectory,
            options=None,
            dependencies=None):

        super().__init__(
            name=name,
            targetDirectory=targetDirectory,
            headers=headers,
            include_directories=include_directories,
            source_files=source_files,
            buildType=buildType,
            clangpp=clangpp,
            link_command=[clangpp, '-o'],
            buildDirectory=buildDirectory,
            output_folder = _platform.EXECUTABLE_OUTPUT,
            platform_flags=_platform.PLATFORM_EXTRA_FLAGS_EXECUTABLE,
            prefix=_platform.EXECUTABLE_PREFIX,
            suffix=_platform.EXECUTABLE_SUFFIX,
            options=options,
            dependencies=dependencies)


class SharedLibrary(Compilable):
    def __init__(self,
            name,
            targetDirectory,
            headers,
            include_directories,
            source_files,
            buildType,
            clangpp,
            buildDirectory,
            options=None,
            dependencies=None):

        super().__init__(
            name=name,
            targetDirectory=targetDirectory,
            headers=headers,
            include_directories=include_directories,
            source_files=source_files,
            buildType=buildType,
            clangpp=clangpp,
            link_command=[clangpp, '-shared' '-o'],
            buildDirectory=buildDirectory,
            output_folder = _platform.SHARED_LIBRARY_OUTPUT,
            platform_flags=_platform.PLATFORM_EXTRA_FLAGS_SHARED,
            prefix=_platform.SHARED_LIBRARY_PREFIX,
            suffix=_platform.SHARED_LIBRARY_SUFFIX,
            options=options,
            dependencies=dependencies)


class StaticLibrary(Compilable):
    def __init__(self,
            name,
            targetDirectory,
            headers,
            include_directories,
            source_files,
            buildType,
            clangpp,
            clang_ar,
            buildDirectory,
            options=None,
            dependencies=None):

        super().__init__(
            name=name,
            targetDirectory=targetDirectory,
            headers=headers,
            include_directories=include_directories,
            source_files=source_files,
            buildType=buildType,
            clangpp=clangpp,
            link_command=[clang_ar, 'rc'],
            buildDirectory=buildDirectory,
            output_folder = _platform.STATIC_LIBRARY_OUTPUT,
            platform_flags=_platform.PLATFORM_EXTRA_FLAGS_SHARED,
            prefix=_platform.SHARED_LIBRARY_PREFIX,
            suffix=_platform.SHARED_LIBRARY_SUFFIX,
            options=options,
            dependencies=dependencies)

if __name__ == '__main__':
    _freeze_support()
