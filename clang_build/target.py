'''
Target describes a single build or dependency target with all needed paths and
a list of buildables that comprise it's compile and link steps.
'''

import os as _os
from pathlib import Path as _Path
import subprocess as _subprocess
from multiprocessing import freeze_support as _freeze_support
import logging as _logging

from . import platform as _platform
from .dialect_check import get_dialect_string as _get_dialect_string
from .dialect_check import get_max_supported_compiler_dialect as _get_max_supported_compiler_dialect
from .build_type import BuildType as _BuildType
from .single_source import SingleSource as _SingleSource
from .progress_bar import get_build_progress_bar as _get_build_progress_bar

_LOGGER = _logging.getLogger('clang_build.clang_build')

class Target:
    DEFAULT_COMPILE_FLAGS          = ['-Wall', '-Werror']
    DEFAULT_RELEASE_COMPILE_FLAGS  = ['-O3', '-DNDEBUG']
    DEFAULT_DEBUG_COMPILE_FLAGS    = ['-O0', '-g3', '-DDEBUG']
    DEFAULT_COVERAGE_COMPILE_FLAGS = (
        DEFAULT_DEBUG_COMPILE_FLAGS +
        ['--coverage',
         '-fno-inline',
         '-fno-inline-small-functions',
         '-fno-default-inline'])


    def __init__(self,
            name,
            root_directory,
            build_directory,
            headers,
            include_directories,
            build_type,
            clangpp,
            options=None,
            dependencies=None):

        if options is None:
            options = {}
        if dependencies is None:
            dependencies = []

        self.dependency_targets = dependencies

        # Basics
        self.name           = name
        self.root_directory = _Path(root_directory)
        self.build_type      = build_type

        self.build_directory = build_directory

        self.headers = headers

        self.include_directories = []

        # Include directories
        if self.root_directory.joinpath('include').exists():
            self.include_directories.append(self.root_directory.joinpath('include'))
        self.include_directories += include_directories

        if 'properties' in options and 'cpp_version' in options['properties']:
            self.dialect = _get_dialect_string(options['properties']['cpp_version'])
        else:
            self.dialect = _get_max_supported_compiler_dialect(clangpp)

        # TODO: parse user-specified target version

        compile_flags        = []
        compile_flags_debug   = Target.DEFAULT_DEBUG_COMPILE_FLAGS
        compile_flags_release = Target.DEFAULT_RELEASE_COMPILE_FLAGS
        self.linkFlags = []

        if 'flags' in options:
            compile_flags += options['flags'].get('compile', [])
            compile_flags_release += options['flags'].get('compileRelease', [])
            compile_flags_debug += options['flags'].get('compileDebug', [])
            self.linkFlags += options['flags'].get('link', [])

        self.compile_flags = compile_flags
        if self.build_type == _BuildType.Release:
            self.compile_flags += compile_flags_release
        if self.build_type == _BuildType.Debug:
            self.compile_flags += compile_flags_debug

        for target in self.dependency_targets:
            self.compile_flags += target.compile_flags
            self.include_directories += target.include_directories
            self.headers += target.headers

        self.compile_flags = list(set(self.compile_flags))
        self.include_directories = list(set([dir.resolve() for dir in self.include_directories]))
        self.headers = list(set(self.headers))

        self.unsuccessful_builds = []

    def get_include_directory_command(self):
        ret = []
        for dir in self.include_directories:
            ret += ['-I',  str(dir.resolve())]
        return ret

    def link(self):
        # Subclasses must implement
        raise NotImplementedError()

    def compile(self, process_pool, progress_disabled):
        # Subclasses must implement
        raise NotImplementedError()

class HeaderOnly(Target):
    def link(self):
        _LOGGER.info(f'Header-only target [{self.name}] does not require linking.')

    def compile(self, process_pool, progress_disabled):
        _LOGGER.info(f'Header-only target [{self.name}] does not require compiling.')

def generate_depfile_single_source(buildable):
    buildable.generate_depfile()
    return buildable

def compile_single_source(buildable):
    buildable.compile()
    return buildable

class Compilable(Target):

    def __init__(self,
            name,
            root_directory,
            build_directory,
            headers,
            include_directories,
            source_files,
            build_type,
            clangpp,
            link_command,
            output_folder,
            platform_flags,
            prefix,
            suffix,
            options=None,
            dependencies=None):

        super().__init__(
            name=name,
            root_directory=root_directory,
            build_directory=build_directory,
            headers=headers,
            include_directories=include_directories,
            build_type=build_type,
            clangpp=clangpp,
            options=options,
            dependencies=dependencies)

        if not source_files:
            error_message = f'ERROR: Targt [{name}] was defined as a {self.__class__} but no source files were found'
            _LOGGER.error(error_message)
            raise RuntimeError(error_message)

        if options is None:
            options = {}
        if dependencies is None:
            dependencies = []

        self.object_directory  = self.build_directory.joinpath('obj').resolve()
        self.depfile_directory = self.build_directory.joinpath('dep').resolve()
        self.output_folder     = self.build_directory.joinpath(output_folder).resolve()

        self.object_directory.mkdir(parents=True, exist_ok=True)
        self.depfile_directory.mkdir(parents=True, exist_ok=True)
        self.output_folder.mkdir(parents=True, exist_ok=True)

        if 'output_name' in options:
            self.outname = options['output_name']
        else:
            self.outname = self.name

        self.outfile = _Path(self.output_folder, prefix + self.outname + suffix).resolve()


        # Clang
        self.clangpp   = clangpp

        # Sources
        self.source_files        = source_files

        # Buildables which this Target contains
        self.buildables = [_SingleSource(
            source_file=source_file,
            platform_flags=platform_flags,
            current_target_root_path=self.root_directory,
            depfile_directory=self.depfile_directory,
            object_directory=self.object_directory,
            include_strings=self.get_include_directory_command(),
            compile_flags=[self.dialect] + Target.DEFAULT_COMPILE_FLAGS + self.compile_flags,
            clangpp=self.clangpp) for source_file in self.source_files]

        # If compilation of buildables fail, they will be stored here later
        self.unsuccessful_builds = []

        # Linking setup
        self.link_command = link_command + [str(self.outfile)]

        self.link_command += self.linkFlags


        ## Additional scripts
        self.before_compile_script = ""
        self.before_link_script    = ""
        self.after_build_script    = ""
        if 'scripts' in options: ### TODO: maybe the scripts should be named differently
            self.before_compile_script = options['scripts'].get('before_compile', "")
            self.before_link_script    = options['scripts'].get('before_link',    "")
            self.after_build_script    = options['scripts'].get('after_build',    "")


    # From the list of source files, compile those which changed or whose dependencies (included headers, ...) changed
    def compile(self, process_pool, progress_disabled):

        # Object file only needs to be (re-)compiled if the source file or headers it depends on changed
        self.needed_buildables = [buildable for buildable in self.buildables if buildable.needs_rebuild]

        # If the target was not modified, it may not need to compile
        if not self.needed_buildables:
            _LOGGER.info(f'Target [{self.name}] is already compiled')
            return

        _LOGGER.info(f'Target [{self.name}] needs to build sources %s', [b.name for b in self.needed_buildables])

        # Before-compile step
        if self.before_compile_script:
            script_file = self.root_directory.joinpath(self.before_compile_script)
            _LOGGER.info(f'Pre-compile step of target [{self.name}]: {script_file}')
            original_directory = _os.getcwd()
            _os.chdir(self.root_directory)
            with open(script_file) as f:
                code = compile(f.read(), script_file, 'exec')
                exec(code, globals(), locals())
            _os.chdir(original_directory)
            _LOGGER.info(f'Finished pre-compile step of target [{self.name}]')

        # Execute depfile generation command
        _LOGGER.info(f'Scan dependencies of target [{self.outname}]')
        for b in self.needed_buildables:
            _LOGGER.debug(' '.join(b.dependency_command))
        self.needed_buildables = list(_get_build_progress_bar(
                process_pool.imap(
                    generate_depfile_single_source,
                    self.needed_buildables),
                progress_disabled,
                total=len(self.needed_buildables),
                name=self.name))

        # Execute compile command
        _LOGGER.info(f'Compile target [{self.outname}]')
        for b in self.needed_buildables:
            _LOGGER.debug(' '.join(b.compile_command))
        self.needed_buildables = list(_get_build_progress_bar(
                process_pool.imap(
                    compile_single_source,
                    self.needed_buildables),
                progress_disabled,
                total=len(self.needed_buildables),
                name=self.name))

        self.unsuccessful_builds = [buildable for buildable in self.needed_buildables if (buildable.compilation_failed or buildable.depfile_failed)]


    def link(self):
        # Before-link step
        if self.before_link_script:
            _LOGGER.info(f'Pre-link step of target [{self.name}]')
            original_directory = _os.getcwd()
            _os.chdir(self.root_directory)
            script_file = self.root_directory.joinpath(self.before_link_script)
            with open(script_file) as f:
                code = compile(f.read(), script_file, 'exec')
                exec(code, globals(), locals())
            _os.chdir(original_directory)
            _LOGGER.info(f'Finished pre-link step of target [{self.name}]')

        _LOGGER.info(f'Link target [{self.name}]')
        _LOGGER.debug('    ' + ' '.join(self.link_command))

        # Execute link command
        try:
            self.link_report = _subprocess.check_output(self.link_command, stderr=_subprocess.STDOUT).decode('utf-8').strip()
            self.unsuccessful_link = False
        except _subprocess.CalledProcessError as error:
            self.unsuccessful_link = True
            self.link_report = error.output.decode('utf-8').strip()

        ## After-build step
        if self.after_build_script:
            _LOGGER.info(f'After-build step of target [{self.name}]')
            original_directory = _os.getcwd()
            _os.chdir(self.root_directory)
            script_file = self.root_directory.joinpath(self.after_build_script)
            with open(script_file) as f:
                code = compile(f.read(), script_file, 'exec')
                exec(code, globals(), locals())
            _os.chdir(original_directory)
            _LOGGER.info(f'Finished after-build step of target [{self.name}]')


class Executable(Compilable):
    def __init__(self,
            name,
            root_directory,
            build_directory,
            headers,
            include_directories,
            source_files,
            build_type,
            clangpp,
            options=None,
            dependencies=None):

        super().__init__(
            name=name,
            root_directory=root_directory,
            build_directory=build_directory,
            headers=headers,
            include_directories=include_directories,
            source_files=source_files,
            build_type=build_type,
            clangpp=clangpp,
            link_command=[clangpp, '-o'],
            output_folder = _platform.EXECUTABLE_OUTPUT,
            platform_flags=_platform.PLATFORM_EXTRA_FLAGS_EXECUTABLE,
            prefix=_platform.EXECUTABLE_PREFIX,
            suffix=_platform.EXECUTABLE_SUFFIX,
            options=options,
            dependencies=dependencies)

        ### Library dependency search paths
        for target in self.dependency_targets:
            if not target.__class__ is HeaderOnly:
                self.link_command += ['-L', str(target.output_folder.resolve())]

        ### Link self
        self.link_command += [str(buildable.object_file) for buildable in self.buildables]

        ### Link dependencies
        for target in self.dependency_targets:
            if not target.__class__ is HeaderOnly:
                self.link_command += ['-l'+target.outname]


class SharedLibrary(Compilable):
    def __init__(self,
            name,
            root_directory,
            build_directory,
            headers,
            include_directories,
            source_files,
            build_type,
            clangpp,
            options=None,
            dependencies=None):

        super().__init__(
            name=name,
            root_directory=root_directory,
            build_directory=build_directory,
            headers=headers,
            include_directories=include_directories,
            source_files=source_files,
            build_type=build_type,
            clangpp=clangpp,
            link_command=[clangpp, '-shared', '-o'],
            output_folder = _platform.SHARED_LIBRARY_OUTPUT,
            platform_flags=_platform.PLATFORM_EXTRA_FLAGS_SHARED,
            prefix=_platform.SHARED_LIBRARY_PREFIX,
            suffix=_platform.SHARED_LIBRARY_SUFFIX,
            options=options,
            dependencies=dependencies)

        ### Library dependency search paths
        for target in self.dependency_targets:
            if not target.__class__ is HeaderOnly:
                self.link_command += ['-L', str(target.output_folder.resolve())]

        ### Link self
        self.link_command += [str(buildable.object_file) for buildable in self.buildables]

        ### Link dependencies
        for target in self.dependency_targets:
            if not target.__class__ is HeaderOnly:
                self.link_command += ['-l'+target.outname]


class StaticLibrary(Compilable):
    def __init__(self,
            name,
            root_directory,
            build_directory,
            headers,
            include_directories,
            source_files,
            build_type,
            clangpp,
            clang_ar,
            options=None,
            dependencies=None):

        super().__init__(
            name=name,
            root_directory=root_directory,
            build_directory=build_directory,
            headers=headers,
            include_directories=include_directories,
            source_files=source_files,
            build_type=build_type,
            clangpp=clangpp,
            link_command=[clang_ar, 'rc'],
            output_folder = _platform.STATIC_LIBRARY_OUTPUT,
            platform_flags=_platform.PLATFORM_EXTRA_FLAGS_STATIC,
            prefix=_platform.STATIC_LIBRARY_PREFIX,
            suffix=_platform.STATIC_LIBRARY_SUFFIX,
            options=options,
            dependencies=dependencies)

        # ### Include directories
        # self.link_command += self.get_include_directory_command()

        ### Link self
        self.link_command += [str(buildable.object_file) for buildable in self.buildables]

        ### Link dependencies
        for target in self.dependency_targets:
            if not target.__class__ is HeaderOnly:
                self.link_command += [str(buildable.object_file) for buildable in target.buildables]

if __name__ == '__main__':
    _freeze_support()
