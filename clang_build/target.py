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
from .io_tools import get_sources_and_headers as _get_sources_and_headers
from .build_type import BuildType as _BuildType
from .single_source import SingleSource as _SingleSource
from .progress_bar import get_build_progress_bar as _get_build_progress_bar

_LOGGER = _logging.getLogger('clang_build.clang_build')

class Target:
    DEFAULT_COMPILE_FLAGS                = ['-Wall', '-Wextra', '-Wpedantic', '-Werror']
    DEFAULT_COMPILE_FLAGS_RELEASE        = ['-O3', '-DNDEBUG']
    DEFAULT_COMPILE_FLAGS_RELWITHDEBINFO = ['-O3', '-g3', '-DNDEBUG']
    DEFAULT_COMPILE_FLAGS_DEBUG          = ['-O0', '-g3', '-DDEBUG']
    DEFAULT_COMPILE_FLAGS_COVERAGE       = DEFAULT_COMPILE_FLAGS_DEBUG + [
                                            '--coverage',
                                            '-fno-inline']

    def __init__(self,
            project_identifier,
            name,
            root_directory,
            build_directory,
            headers,
            include_directories,
            include_directories_public,
            build_type,
            clang,
            clangpp,
            options=None,
            dependencies=None):

        self.options = options if options is not None else {}

        if dependencies is None:
            dependencies = []

        self.dependency_targets = dependencies
        self.unsuccessful_builds = []

        # Basics
        self.name           = name
        self.identifier      = f'{project_identifier}.{name}' if project_identifier else name
        self.root_directory = _Path(root_directory)
        self.build_type     = build_type

        self.build_directory = build_directory

        # Clang
        self.clang     = clang
        self.clangpp   = clangpp

        # Include directories and headers
        self.include_directories        = []
        self.include_directories_public = []
        self.headers = headers

        self.test_target = None

        # Default include path
        if self.root_directory.joinpath('include').exists():
            self.include_directories_public.append(self.root_directory.joinpath('include'))

        # Discover tests
        self.tests_folder = ""
        if self.root_directory.joinpath('test').exists():
            self.tests_folder = self.root_directory.joinpath('test')
        elif self.root_directory.joinpath('tests').exists():
            self.tests_folder = self.root_directory.joinpath('tests')
        if self.tests_folder:
            _LOGGER.info(f'[{self.identifier}]: found tests folder {str(self.tests_folder)}')
            
        # Discover examples
        self.examples_folder = ""
        if self.root_directory.joinpath('example').exists():
            self.examples_folder = self.root_directory.joinpath('example')
        elif self.root_directory.joinpath('examples').exists():
            self.examples_folder = self.root_directory.joinpath('examples')
        if self.examples_folder:
            _LOGGER.info(f'[{self.identifier}]: found examples folder {str(self.examples_folder)}')

        # Parsed directories
        self.include_directories        += include_directories
        self.include_directories        += include_directories_public
        self.include_directories_public += include_directories_public

        # Include directories of dependencies
        for target in self.dependency_targets:
            # Header only include directories are always public
            if target.__class__ is HeaderOnly:
                self.include_directories += target.include_directories

            self.include_directories += target.include_directories_public
            # Public include directories are forwarded
            self.include_directories_public += target.include_directories_public

        self.include_directories = list(set([dir.resolve() for dir in self.include_directories]))
        self.headers = list(set(self.headers))

        # C language family dialect
        if 'properties' in self.options and 'cpp_version' in self.options['properties']:
            self.dialect = _get_dialect_string(self.options['properties']['cpp_version'])
        else:
            self.dialect = _get_max_supported_compiler_dialect(clangpp)

        # TODO: parse user-specified target version

        # Compile and link flags
        self.compile_flags = []
        self.link_flags = []

        self.compile_flags_interface = []
        self.link_flags_interface = []

        self.compile_flags_public = []
        self.link_flags_public = []

        # Regular (private) flags
        if self.build_type == _BuildType.Release:
            self.compile_flags += Target.DEFAULT_COMPILE_FLAGS_RELEASE

        elif self.build_type == _BuildType.Debug:
            self.compile_flags += Target.DEFAULT_COMPILE_FLAGS_DEBUG

        elif self.build_type == _BuildType.RelWithDebInfo:
            self.compile_flags += Target.DEFAULT_COMPILE_FLAGS_RELWITHDEBINFO

        elif self.build_type == _BuildType.Coverage:
            self.compile_flags += Target.DEFAULT_COMPILE_FLAGS_COVERAGE

        cf, lf = self.parse_flags_options(self.options, 'flags')
        self.compile_flags += cf
        self.link_flags += lf

        for target in self.dependency_targets:
            # Header only libraries will forward all non-private flags
            if self.__class__ is HeaderOnly:
                # Interface
                self.compile_flags_interface += target.compile_flags_interface
                self.link_flags_interface    += target.link_flags_interface
                # Public
                self.compile_flags_public += target.compile_flags_public
                self.link_flags_public    += target.link_flags_public
            # Static libraries will forward interface flags and apply public flags
            elif self.__class__ is StaticLibrary:
                # Interface
                self.compile_flags_interface += target.compile_flags_interface
                self.link_flags_interface    += target.link_flags_interface
                # Public
                self.compile_flags += target.compile_flags_public
                self.link_flags    += target.link_flags_public
            # Shared libraries and executables will not forward flags
            else:
                # Interface
                self.compile_flags += target.compile_flags_interface
                self.link_flags    += target.link_flags_interface
                # Public
                self.compile_flags += target.compile_flags_public
                self.link_flags    += target.link_flags_public

        self.compile_flags = list(set(self.compile_flags))

        # Interface flags
        cf, lf = self.parse_flags_options(self.options, 'interface-flags')
        self.compile_flags_interface += cf
        self.link_flags_interface += lf

        # Public flags
        cf, lf = self.parse_flags_options(self.options, 'public-flags')
        self.compile_flags += cf
        self.link_flags += lf
        self.compile_flags_public += cf
        self.link_flags_public += lf

    # Parse compile and link flags of any kind ('flags', 'interface-flags', ...)
    def parse_flags_options(self, options, flags_kind='flags'):
        flags_dicts   = []
        compile_flags = []
        link_flags    = []

        if flags_kind in options:
            flags_dicts.append(options.get(flags_kind, {}))

        if 'osx' in options and _platform.PLATFORM == 'osx':
            flags_dicts.append(options['osx'].get(flags_kind, {}))
        if 'windows' in options and _platform.PLATFORM == 'windows':
            flags_dicts.append(options['windows'].get(flags_kind, {}))
        if 'linux' in options and _platform.PLATFORM == 'linux':
            flags_dicts.append(options['linux'].get(flags_kind, {}))

        for fdict in flags_dicts:
            compile_flags     += fdict.get('compile', [])
            link_flags        += fdict.get('link', [])

            if self.build_type == _BuildType.Release:
                compile_flags += fdict.get('compile_release', [])

            elif self.build_type == _BuildType.Debug:
                compile_flags += fdict.get('compile_debug', [])

            elif self.build_type == _BuildType.RelWithDebInfo:
                compile_flags += fdict.get('compile_relwithdebinfo', [])

            elif self.build_type == _BuildType.Coverage:
                compile_flags += fdict.get('compile_coverage', [])

        return compile_flags, link_flags

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
        
    def create_test_target(self):
        self.test_target = None
        if self.tests_folder: # TODO: if self.test
            # test_identifier = f"{self.identifier}.test" if self.identifier else "test"
            options = self.options.get("tests", {})
            files = _get_sources_and_headers(options, self.tests_folder, self.build_directory.joinpath("tests"))
            dependencies = [self] if self.__class__ is not Executable else []
            if files['sourcefiles']:
                self.test_target = Executable(
                    self.identifier,
                    "test",
                    self.tests_folder,
                    self.build_directory.joinpath("tests"),
                    files['headers'],
                    files['include_directories'],
                    files['include_directories_public'],
                    files['sourcefiles'],
                    self.build_type,
                    self.clang,
                    self.clangpp,
                    dependencies=dependencies,
                    options=options)

    def create_example_targets(self):
        self.example_targets = []
        # TODO


class HeaderOnly(Target):
    def __init__(self,
            project_identifier,
            name,
            root_directory,
            build_directory,
            headers,
            include_directories,
            include_directories_public,
            build_type,
            clang,
            clangpp,
            options=None,
            dependencies=None):
        super().__init__(
            project_identifier=project_identifier,
            name=name,
            root_directory=root_directory,
            build_directory=build_directory,
            headers=headers,
            include_directories=include_directories,
            include_directories_public=include_directories_public,
            build_type=build_type,
            clang=clang,
            clangpp=clangpp,
            options=options,
            dependencies=dependencies)

        ### Create testing target
        self.create_test_target()

        ### Create example targets
        self.create_example_targets()

    def link(self):
        _LOGGER.info(f'[{self.identifier}]: Header-only target does not require linking.')

    def compile(self, process_pool, progress_disabled):
        _LOGGER.info(f'[{self.identifier}]: Header-only target does not require compiling.')

def generate_depfile_single_source(buildable):
    buildable.generate_depfile()
    return buildable

def compile_single_source(buildable):
    buildable.compile()
    return buildable


class Compilable(Target):

    def __init__(self,
            project_identifier,
            name,
            root_directory,
            build_directory,
            headers,
            include_directories,
            include_directories_public,
            source_files,
            build_type,
            clang,
            clangpp,
            link_command,
            output_folder,
            platform_flags,
            prefix,
            suffix,
            options=None,
            dependencies=None,
            force_build=False):

        super().__init__(
            project_identifier=project_identifier,
            name=name,
            root_directory=root_directory,
            build_directory=build_directory,
            headers=headers,
            include_directories=include_directories,
            include_directories_public=include_directories_public,
            build_type=build_type,
            clang=clang,
            clangpp=clangpp,
            options=options,
            dependencies=dependencies)

        if not source_files:
            error_message = f'[{self.identifier}]: ERROR: Target was defined as a {self.__class__} but no source files were found'
            _LOGGER.error(error_message)
            raise RuntimeError(error_message)

        self.force_build = force_build

        self.object_directory  = self.build_directory.joinpath('obj').resolve()
        self.depfile_directory = self.build_directory.joinpath('dep').resolve()
        self.output_folder     = self.build_directory.joinpath(output_folder).resolve()

        if 'output_name' in self.options:
            self.outname = self.options['output_name']
        else:
            self.outname = self.name

        self.outfile = _Path(self.output_folder, prefix + self.outname + suffix).resolve()

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
            compile_flags=Target.DEFAULT_COMPILE_FLAGS+self.compile_flags,
            clang  =self.clang,
            clangpp=self.clangpp,
            max_cpp_dialect=self.dialect) for source_file in self.source_files]

        # If compilation of buildables fail, they will be stored here later
        self.unsuccessful_builds = []

        # Linking setup
        self.link_command = link_command + [str(self.outfile)]

        ## Additional scripts
        self.before_compile_script = ""
        self.before_link_script    = ""
        self.after_build_script    = ""
        if 'scripts' in self.options: ### TODO: maybe the scripts should be named differently
            self.before_compile_script = self.options['scripts'].get('before_compile', "")
            self.before_link_script    = self.options['scripts'].get('before_link',    "")
            self.after_build_script    = self.options['scripts'].get('after_build',    "")


    # From the list of source files, compile those which changed or whose dependencies (included headers, ...) changed
    def compile(self, process_pool, progress_disabled):

        # Object file only needs to be (re-)compiled if the source file or headers it depends on changed
        if not self.force_build:
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
            project_identifier,
            name,
            root_directory,
            build_directory,
            headers,
            include_directories,
            include_directories_public,
            source_files,
            build_type,
            clang,
            clangpp,
            options=None,
            dependencies=None,
            force_build=False):

        super().__init__(
            project_identifier=project_identifier,
            name=name,
            root_directory=root_directory,
            build_directory=build_directory,
            headers=headers,
            include_directories=include_directories,
            include_directories_public=include_directories_public,
            source_files=source_files,
            build_type=build_type,
            clang=clang,
            clangpp=clangpp,
            link_command=[clangpp, '-o'],
            output_folder=_platform.EXECUTABLE_OUTPUT,
            platform_flags=_platform.PLATFORM_EXTRA_FLAGS_EXECUTABLE,
            prefix=_platform.EXECUTABLE_PREFIX,
            suffix=_platform.EXECUTABLE_SUFFIX,
            options=options,
            dependencies=dependencies,
            force_build=force_build)

        ### Link self
        self.link_command += [str(buildable.object_file) for buildable in self.buildables]

        ### Library dependency search paths
        for target in self.dependency_targets:
            if not target.__class__ is HeaderOnly:
                self.link_command += ['-L', str(target.output_folder.resolve())]

        self.link_command += self.link_flags

        ### Link dependencies
        for target in self.dependency_targets:
            if not target.__class__ is HeaderOnly:
                self.link_command += ['-l'+target.outname]

        ### Create testing target
        self.create_test_target()

        ### Create example targets
        self.create_example_targets()


class SharedLibrary(Compilable):
    def __init__(self,
            project_identifier,
            name,
            root_directory,
            build_directory,
            headers,
            include_directories,
            include_directories_public,
            source_files,
            build_type,
            clang,
            clangpp,
            options=None,
            dependencies=None,
            force_build=False):

        super().__init__(
            project_identifier=project_identifier,
            name=name,
            root_directory=root_directory,
            build_directory=build_directory,
            headers=headers,
            include_directories=include_directories,
            include_directories_public=include_directories_public,
            source_files=source_files,
            build_type=build_type,
            clang=clang,
            clangpp=clangpp,
            link_command=[clangpp, '-shared', '-o'],
            output_folder=_platform.SHARED_LIBRARY_OUTPUT,
            platform_flags=_platform.PLATFORM_EXTRA_FLAGS_SHARED,
            prefix=_platform.SHARED_LIBRARY_PREFIX,
            suffix=_platform.SHARED_LIBRARY_SUFFIX,
            options=options,
            dependencies=dependencies,
            force_build=force_build)

        ### Link self
        self.link_command += [str(buildable.object_file) for buildable in self.buildables]

        ### Library dependency search paths
        for target in self.dependency_targets:
            if not target.__class__ is HeaderOnly:
                self.link_command += ['-L', str(target.output_folder.resolve())]

        self.link_command += self.link_flags

        ### Link dependencies
        for target in self.dependency_targets:
            if not target.__class__ is HeaderOnly:
                self.link_command += ['-l'+target.outname]

        ### Create testing target
        self.create_test_target()

        ### Create example targets
        self.create_example_targets()


class StaticLibrary(Compilable):
    def __init__(self,
            project_identifier,
            name,
            root_directory,
            build_directory,
            headers,
            include_directories,
            include_directories_public,
            source_files,
            build_type,
            clang,
            clangpp,
            clang_ar,
            options=None,
            dependencies=None,
            force_build=False):

        super().__init__(
            project_identifier=project_identifier,
            name=name,
            root_directory=root_directory,
            build_directory=build_directory,
            headers=headers,
            include_directories=include_directories,
            include_directories_public=include_directories_public,
            source_files=source_files,
            build_type=build_type,
            clang=clang,
            clangpp=clangpp,
            link_command=[clang_ar, 'rc'],
            output_folder=_platform.STATIC_LIBRARY_OUTPUT,
            platform_flags=_platform.PLATFORM_EXTRA_FLAGS_STATIC,
            prefix=_platform.STATIC_LIBRARY_PREFIX,
            suffix=_platform.STATIC_LIBRARY_SUFFIX,
            options=options,
            dependencies=dependencies,
            force_build=force_build)

        # ### Include directories
        # self.link_command += self.get_include_directory_command()

        ### Link self
        self.link_command += [str(buildable.object_file) for buildable in self.buildables]
        self.link_command += self.link_flags

        ### Link dependencies
        for target in self.dependency_targets:
            if not target.__class__ is HeaderOnly:
                self.link_command += [str(buildable.object_file) for buildable in target.buildables]

        ### Create testing target
        self.create_test_target()

        ### Create example targets
        self.create_example_targets()


if __name__ == '__main__':
    _freeze_support()