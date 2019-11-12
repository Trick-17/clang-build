'''
Target describes a single build or dependency target with all needed paths and
a list of buildables that comprise it's compile and link steps.
'''

import os as _os
from abc import abstractmethod
from pathlib import Path as _Path
import subprocess as _subprocess
from multiprocessing import freeze_support as _freeze_support
import logging as _logging

from . import platform as _platform
from .build_type import BuildType as _BuildType
from .single_source import SingleSource as _SingleSource
from .io_tools import parse_flags_options as _parse_flags_options
from .progress_bar import get_build_progress_bar as _get_build_progress_bar

_LOGGER = _logging.getLogger('clang_build.clang_build')

class Target:
    COMPILE_FLAGS = {
        _BuildType.Default          : ['-Wall', '-Wextra', '-Wpedantic', '-Wshadow', '-Werror'],
        _BuildType.Release          : ['-O3', '-DNDEBUG'],
        _BuildType.RelWithDebInfo   : ['-O3', '-g3', '-DNDEBUG'],
        _BuildType.Debug            : ['-Og', '-g3', '-DDEBUG',
                                        '-fno-optimize-sibling-calls', '-fno-omit-frame-pointer',
                                        '-fsanitize=address', '-fsanitize=undefined'],
        _BuildType.Coverage         : ['-Og', '-g3', '-DDEBUG',
                                        '-fno-optimize-sibling-calls', '-fno-omit-frame-pointer',
                                        '-fsanitize=address', '-fsanitize=undefined',
                                        '--coverage', '-fno-inline'],
    }
    LINK_FLAGS_EXE_SHARED = {
        _BuildType.Debug            : ['-fsanitize=address', '-fsanitize=undefined'],
        _BuildType.Coverage         : ['-fsanitize=address', '-fsanitize=undefined',
                                        '--coverage', '-fno-inline'],
    }

    def __init__(self,
            environment,
            project_identifier,
            name,
            root_directory,
            build_directory,
            headers,
            include_directories_private,
            include_directories_public,
            options=None,
            dependencies=None):

        self.environment = environment

        if options is None:
            options = {}
        if dependencies is None:
            dependencies = []

        self.dependency_targets = dependencies
        self.unsuccessful_builds = []

        # TODO: parse user-specified target version

        # Basics
        self.name           = name
        self.identifier      = f'{project_identifier}.{name}' if project_identifier else name
        self.root_directory = _Path(root_directory)

        self.build_directory = build_directory

        self.headers = list(dict.fromkeys(headers))

        # Include directories
        self.include_directories_private = include_directories_private
        self.include_directories_public  = include_directories_public

        # Default include path
        if self.root_directory.joinpath('include').exists():
            self.include_directories_public = [self.root_directory.joinpath('include')] + self.include_directories_public

        # Public include directories of dependencies are forwarded
        for target in self.dependency_targets:
            self.include_directories_public += target.include_directories_public

        # Make unique and resolve
        self.include_directories_private = list(dict.fromkeys(dir.resolve() for dir in self.include_directories_private))
        self.include_directories_public  = list(dict.fromkeys(dir.resolve() for dir in self.include_directories_public))

        # Compile and link flags
        self.compile_flags_private = []
        self.link_flags_private    = []

        self.compile_flags_interface = []
        self.link_flags_interface    = []

        self.compile_flags_public = []
        self.link_flags_public    = []

        # Default flags come first
        self.add_default_flags()

        # Dependencies' flags
        for target in self.dependency_targets:
            # Header only libraries will forward all non-private flags
            self.add_target_flags(target)

        # Own private flags
        cf, lf = _parse_flags_options(options, 'flags')
        self.compile_flags_private += cf
        self.link_flags_private    += lf

        # Own interface flags
        cf, lf = _parse_flags_options(options, 'interface-flags')
        self.compile_flags_interface += cf
        self.link_flags_interface    += lf

        # Own public flags
        cf, lf = _parse_flags_options(options, 'public-flags')
        self.compile_flags_public += cf
        self.link_flags_public    += lf

    @abstractmethod
    def add_default_flags(self):
        pass

    @abstractmethod
    def add_target_flags(self, target):
        pass

    def apply_public_flags(self, target):
        self.compile_flags_private += target.compile_flags_public
        self.link_flags_private    += target.link_flags_public

    def forward_public_flags(self, target):
        self.compile_flags_public += target.compile_flags_public
        self.link_flags_public    += target.link_flags_public

    def apply_interface_flags(self, target):
        self.compile_flags_private += target.compile_flags_interface
        self.link_flags_private    += target.link_flags_interface

    def forward_interface_flags(self, target):
        self.compile_flags_interface += target.compile_flags_interface
        self.link_flags_interface    += target.link_flags_interface

    @abstractmethod
    def compile(self, process_pool, progress_disabled):
        pass

    @abstractmethod
    def link(self):
        pass


class HeaderOnly(Target):
    def __init__(self,
            environment,
            project_identifier,
            name,
            root_directory,
            build_directory,
            headers,
            include_directories_private,
            include_directories_public,
            options=None,
            dependencies=None):
        super().__init__(
            environment                 = environment,
            project_identifier          = project_identifier,
            name                        = name,
            root_directory              = root_directory,
            build_directory             = build_directory,
            headers                     = headers,
            include_directories_private = [],
            include_directories_public  = include_directories_private+include_directories_public,
            options                     = options,
            dependencies                = dependencies)

        self.compile_flags_public       += self.compile_flags_private
        self.link_flags_public          += self.link_flags_private

    def link(self):
        _LOGGER.info(f'[{self.identifier}]: Header-only target does not require linking.')

    def compile(self, process_pool, progress_disabled):
        _LOGGER.info(f'[{self.identifier}]: Header-only target does not require compiling.')

    def add_target_flags(self, target):
        self.forward_public_flags(target)
        self.forward_interface_flags(target)

def generate_depfile_single_source(buildable):
    buildable.generate_depfile()
    return buildable

def compile_single_source(buildable):
    buildable.compile()
    return buildable


class Compilable(Target):

    def __init__(self,
            environment,
            project_identifier,
            name,
            root_directory,
            build_directory,
            headers,
            include_directories_private,
            include_directories_public,
            source_files,
            link_command,
            output_folder,
            platform_flags,
            prefix,
            suffix,
            options=None,
            dependencies=None):

        super().__init__(
            environment                 = environment,
            project_identifier          = project_identifier,
            name                        = name,
            root_directory              = root_directory,
            build_directory             = build_directory,
            headers                     = headers,
            include_directories_private = include_directories_private,
            include_directories_public  = include_directories_public,
            options                     = options,
            dependencies                = dependencies)

        if not source_files:
            error_message = f'[{self.identifier}]: ERROR: Target was defined as a {self.__class__.__name__} but no source files were found'
            _LOGGER.error(error_message)
            raise RuntimeError(error_message)

        if options is None:
            options = {}
        if dependencies is None:
            dependencies = []

        self.object_directory  = self.build_directory.joinpath('obj').resolve()
        self.depfile_directory = self.build_directory.joinpath('dep').resolve()
        self.output_folder     = self.build_directory.joinpath(output_folder).resolve()

        if 'output_name' in options:
            self.outname = options['output_name']
        else:
            self.outname = self.name

        self.outfile = _Path(self.output_folder, prefix + self.outname + suffix).resolve()

        # Sources
        self.source_files = source_files

        # Full list of flags
        compile_flags = self.compile_flags_private+self.compile_flags_public
        link_flags    = self.link_flags_private+self.link_flags_public
        # Make flags unique
        compile_flags = list(dict.fromkeys(compile_flags))
        link_flags    = list(dict.fromkeys(link_flags))
        # Split strings containing spaces
        compile_flags = list(str(' '.join(compile_flags)).split())
        link_flags    = list(str(' '.join(link_flags)).split())

        # List of unique include directories
        include_directories = self.include_directories_private + self.include_directories_public
        include_directories = list(dict.fromkeys(include_directories))

        # Buildables which this Target contains
        self.include_directories_command = []
        for directory in include_directories:
            self.include_directories_command += ['-I', str(directory.resolve())]

        self.buildables = [
            _SingleSource(
                environment              = self.environment,
                source_file              = source_file,
                platform_flags           = platform_flags,
                current_target_root_path = self.root_directory,
                depfile_directory        = self.depfile_directory,
                object_directory         = self.object_directory,
                include_strings          = self.include_directories_command,
                compile_flags            = compile_flags)
            for source_file in self.source_files]

        # If compilation of buildables fail, they will be stored here later
        self.unsuccessful_builds = []

        # Linking setup
        self.link_command = link_command + [str(self.outfile)]

        ## Additional scripts
        self.before_compile_script = ""
        self.before_link_script    = ""
        self.after_build_script    = ""
        if 'scripts' in options: ### TODO: maybe the scripts should be named differently
            self.before_compile_script = options['scripts'].get('before_compile', "")
            self.before_link_script    = options['scripts'].get('before_link',    "")
            self.after_build_script    = options['scripts'].get('after_build',    "")

    def add_default_flags(self):
        self.compile_flags_private += Target.COMPILE_FLAGS.get(_BuildType.Default)
        if self.environment.build_type != _BuildType.Default:
            self.compile_flags_private += Target.COMPILE_FLAGS.get(self.environment.build_type)

    # From the list of source files, compile those which changed or whose dependencies (included headers, ...) changed
    def compile(self, process_pool, progress_disabled):

        # Object file only needs to be (re-)compiled if the source file or headers it depends on changed
        if not self.environment.force_build:
            self.needed_buildables = [buildable for buildable in self.buildables if buildable.needs_rebuild]
        else:
            self.needed_buildables = self.buildables

        # If the target was not modified, it may not need to compile
        if not self.needed_buildables:
            _LOGGER.info(f'[{self.identifier}]: target is already compiled')
            return

        _LOGGER.info(f'[{self.identifier}]: target needs to build sources %s', [b.name for b in self.needed_buildables])

        # Before-compile step
        if self.before_compile_script:
            script_file = self.root_directory.joinpath(self.before_compile_script).resolve()
            _LOGGER.info(f'[{self.identifier}]: pre-compile step: \'{script_file}\'')
            original_directory = _os.getcwd()
            _os.chdir(self.root_directory)
            with open(script_file) as f:
                code = compile(f.read(), script_file, 'exec')
                exec(code, globals(), locals())
            _os.chdir(original_directory)
            _LOGGER.info(f'[{self.identifier}]: finished pre-compile step')

        # Execute depfile generation command
        _LOGGER.info(f'[{self.identifier}]: scan dependencies')
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
        _LOGGER.info(f'[{self.identifier}]: compile')
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
            script_file = self.root_directory.joinpath(self.before_link_script)
            _LOGGER.info(f'[{self.identifier}]: pre-link step: \'{script_file}\'')
            original_directory = _os.getcwd()
            _os.chdir(self.root_directory)
            with open(script_file) as f:
                code = compile(f.read(), script_file, 'exec')
                exec(code, globals(), locals())
            _os.chdir(original_directory)
            _LOGGER.info(f'[{self.identifier}]: finished pre-link step')

        _LOGGER.info(f'[{self.identifier}]: link -> "{self.outfile}"')
        _LOGGER.debug('    ' + ' '.join(self.link_command))

        # Execute link command
        try:
            self.output_folder.mkdir(parents=True, exist_ok=True)
            self.link_report = _subprocess.check_output(self.link_command, stderr=_subprocess.STDOUT).decode('utf-8').strip()
            self.unsuccessful_link = False
        except _subprocess.CalledProcessError as error:
            self.unsuccessful_link = True
            self.link_report = error.output.decode('utf-8').strip()

        ## After-build step
        if self.after_build_script:
            script_file = self.root_directory.joinpath(self.after_build_script)
            _LOGGER.info(f'[{self.identifier}]: after-build step: \'{script_file}\'')
            original_directory = _os.getcwd()
            _os.chdir(self.root_directory)
            with open(script_file) as f:
                code = compile(f.read(), script_file, 'exec')
                exec(code, globals(), locals())
            _os.chdir(original_directory)
            _LOGGER.info(f'[{self.identifier}]: finished after-build step')


class Executable(Compilable):
    def __init__(self,
            environment,
            project_identifier,
            name,
            root_directory,
            build_directory,
            headers,
            include_directories_private,
            include_directories_public,
            source_files,
            options=None,
            dependencies=None):

        super().__init__(
            environment                 = environment,
            project_identifier          = project_identifier,
            name                        = name,
            root_directory              = root_directory,
            build_directory             = build_directory,
            headers                     = headers,
            include_directories_private = include_directories_private,
            include_directories_public  = include_directories_public,
            source_files                = source_files,
            link_command                = [environment.clangpp, '-o'],
            output_folder               = _platform.EXECUTABLE_OUTPUT,
            platform_flags              = _platform.PLATFORM_EXTRA_FLAGS_EXECUTABLE,
            prefix                      = _platform.EXECUTABLE_PREFIX,
            suffix                      = _platform.EXECUTABLE_SUFFIX,
            options                     = options,
            dependencies                = dependencies)

        ### Link self
        self.link_command += [str(buildable.object_file) for buildable in self.buildables]

        ### Library dependency search paths
        for target in self.dependency_targets:
            if not target.__class__ is HeaderOnly:
                self.link_command += ['-L', str(target.output_folder.resolve())]

        self.link_command += self.link_flags_private + self.link_flags_public

        ### Link dependencies
        for target in self.dependency_targets:
            if not target.__class__ is HeaderOnly:
                self.link_command += ['-l'+target.outname]

    def add_default_flags(self):
        super().add_default_flags()
        if self.environment.build_type == _BuildType.Debug:
            self.link_flags_private += Target.LINK_FLAGS_EXE_SHARED[_BuildType.Debug]
        elif self.environment.build_type == _BuildType.Coverage:
            self.link_flags_private += Target.LINK_FLAGS_EXE_SHARED[_BuildType.Coverage]

    def add_target_flags(self, target):
        self.apply_public_flags(target)
        self.forward_public_flags(target)
        self.apply_interface_flags(target)

class SharedLibrary(Compilable):
    def __init__(self,
            environment,
            project_identifier,
            name,
            root_directory,
            build_directory,
            headers,
            include_directories_private,
            include_directories_public,
            source_files,
            options=None,
            dependencies=None):

        super().__init__(
            environment                 = environment,
            project_identifier          = project_identifier,
            name                        = name,
            root_directory              = root_directory,
            build_directory             = build_directory,
            headers                     = headers,
            include_directories_private = include_directories_private,
            include_directories_public  = include_directories_public,
            source_files                = source_files,
            link_command                = [environment.clangpp, '-shared', '-o'],
            output_folder               = _platform.SHARED_LIBRARY_OUTPUT,
            platform_flags              = _platform.PLATFORM_EXTRA_FLAGS_SHARED,
            prefix                      = _platform.SHARED_LIBRARY_PREFIX,
            suffix                      = _platform.SHARED_LIBRARY_SUFFIX,
            options                     = options,
            dependencies                = dependencies)

        ### Link self
        self.link_command += [str(buildable.object_file) for buildable in self.buildables]

        ### Library dependency search paths
        for target in self.dependency_targets:
            if not target.__class__ is HeaderOnly:
                self.link_command += ['-L', str(target.output_folder.resolve())]

        self.link_command += self.link_flags_private + self.link_flags_public

        ### Link dependencies
        for target in self.dependency_targets:
            if not target.__class__ is HeaderOnly:
                self.link_command += ['-l'+target.outname]

    def add_default_flags(self):
        super().add_default_flags()
        if self.environment.build_type == _BuildType.Debug:
            self.link_flags_private += Target.LINK_FLAGS_EXE_SHARED[_BuildType.Debug]
        elif self.environment.build_type == _BuildType.Coverage:
            self.link_flags_private += Target.LINK_FLAGS_EXE_SHARED[_BuildType.Coverage]

    def add_target_flags(self, target):
        self.apply_public_flags(target)
        self.forward_public_flags(target)
        self.apply_interface_flags(target)

class StaticLibrary(Compilable):
    def __init__(self,
            environment,
            project_identifier,
            name,
            root_directory,
            build_directory,
            headers,
            include_directories_private,
            include_directories_public,
            source_files,
            options=None,
            dependencies=None):

        super().__init__(
            environment                 = environment,
            project_identifier          = project_identifier,
            name                        = name,
            root_directory              = root_directory,
            build_directory             = build_directory,
            headers                     = headers,
            include_directories_private = include_directories_private,
            include_directories_public  = include_directories_public,
            source_files                = source_files,
            link_command                = [environment.clang_ar, 'rc'],
            output_folder               = _platform.STATIC_LIBRARY_OUTPUT,
            platform_flags              = _platform.PLATFORM_EXTRA_FLAGS_STATIC,
            prefix                      = _platform.STATIC_LIBRARY_PREFIX,
            suffix                      = _platform.STATIC_LIBRARY_SUFFIX,
            options                     = options,
            dependencies                = dependencies)

        ### Link self
        self.link_command += [str(buildable.object_file) for buildable in self.buildables]
        self.link_command += self.link_flags_private + self.link_flags_public

        ### Link dependencies
        for target in self.dependency_targets:
            if not target.__class__ is HeaderOnly:
                self.link_command += [str(buildable.object_file) for buildable in target.buildables]

    def add_target_flags(self, target):
        self.apply_public_flags(target)
        self.forward_public_flags(target)
        self.forward_interface_flags(target)

if __name__ == '__main__':
    _freeze_support()