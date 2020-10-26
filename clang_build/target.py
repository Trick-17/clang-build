"""
Target describes a single build or dependency target with all needed paths and
a list of buildables that comprise it's compile and link steps.
"""

import logging as _logging
import shutil as _shutil
import subprocess as _subprocess
from abc import abstractmethod
from multiprocessing import freeze_support as _freeze_support
from pathlib import Path as _Path

from .directories import Directories
from .errors import BundleError as _BundleError
from .errors import CompileError as _CompileError
from .errors import LinkError as _LinkError
from .errors import RedistributableError as _RedistributableError
from .flags import BuildFlags
from .git_tools import download_sources as _git_download_sources
from .logging_tools import NamedLogger as _NamedLogger
from .progress_bar import get_build_progress_bar as _get_build_progress_bar
from .single_source import SingleSource as _SingleSource
from .tree_entry import TreeEntry as _TreeEntry

_LOGGER = _logging.getLogger(__name__)

class Target(_TreeEntry, _NamedLogger):
    """Base class for all kinds of target, whose sources have been gathered.

    Target instances are used in the `build` method of a project.
    """

    @property
    def name(self):
        """Return the name of this target.
        """
        return self._name

    @property
    def identifier(self):
        """Return the unique identifier of this target.

        Targets are identified by their parent projects and their name as
        "[project.subproject.target]".
        """
        return self._identifier

    @property
    def dependencies(self):
        """Return a list of any:`clang_build.target.Target`, which this
        target depends on.
        """
        return self._dependencies

    @property
    def root_directory(self):
        """Folders "include", "src", etc. are searched
        relative to this folder.
        """

        return self._root_directory

    @property
    def build_directory(self):
        """Return the directory which serves as the root build folder
        for this target.
        """
        return self._build_directory

    @property
    def headers(self):
        """Headers found for this project.
        """
        return self._headers

    @property
    def directories(self):
        """Return the any:`clang_build.directories.Directories` in use
        by this target.
        """
        return self._directories

    def __init__(self, target_description, files, dependencies=None):
        """Initialise a target.

        The procedure for initialisation is:

        #. Setting some instance attributes
        #. Initialising sub-projects and filling the dependency tree recursively
        #. Determining the targets to configure
        #. Configuring the targets

        Parameters
        ----------
        target_description : :any:`clang_build.target.TargetDescription`
            All the information on how to gather sources and build the target.
        environment : any:`clang_build.clang_build.Environment`
            An any:`clang_build.clang_build.Environment` instance defining some global
            settings for this run of clang-build.
        dependencies
            Optional. A list of any:`clang_build.target.Target` which this target
            depends on.
        """
        _NamedLogger.__init__(self, _LOGGER)
        self._name = target_description.name
        self._identifier = target_description.identifier
        self._environment = target_description.environment

        if dependencies is None:
            dependencies = []

        self._dependencies = dependencies

        # TODO: parse user-specified target version

        self._root_directory = _Path(target_description.root_directory)
        self._build_directory = target_description.build_directory

        self._headers = list(dict.fromkeys(files["headers"]))

        self._directories = Directories(files, self._dependencies)

        # Compile and link flags
        self._build_flags = self._get_default_flags()

        # Dependencies' flags
        for target in self.dependencies:
            # Header only libraries will forward all non-private flags
            self._add_dependency_flags(target)

        self._build_flags.add_target_flags(self._environment.toolchain.platform, target_description.config)

    def __repr__(self) -> str:
        return f"clang_build.target.Target('{self.identifier}')"

    def __str__(self) -> str:
        return f"[{self.identifier}]"

    @abstractmethod
    def _get_default_flags(self):
        """Overload to return any:`clang_build.flags.BuildFlags`, which the target should use.
        """

    @abstractmethod
    def _add_dependency_flags(self, target):
        """Overload to add flags from dependencies of this target to its own.
        """

    @abstractmethod
    def compile(self, process_pool, progress_disabled):
        """Compile the target, if applicable.

        This produces an OS-dependent output in the build/bin folder.
        """

    @abstractmethod
    def link(self):
        """Link the target, if applicable.

        This produces an OS-dependent output in the corresponding build folder:
        - "bin" for executables and shared objects
        - "lib" for static libraries
        """
        pass

    def bundle(self):
        """For executable and shared library targets, bundle shared library
        dependencies into the binary output folder and amend the rpath if
        necessary.

        They can therefore be used without amending the system PATH or similar.
        """
        self.unsuccessful_bundle = False
        bundle_files = []
        for dependency in self.dependencies:
            bundle_files += dependency.bundle()
        return bundle_files

    def redistributable(self):
        """Create a redistributable bundle, suitable for installation.

        The redistributable bundle contains
        - an "include" folder with the public headers (preserving folder structure).
          Note that this includes the headers of public dependencies.
        - "bin" and "lib" folders containing compiled output of the target
          and its dependencies.
        """
        self.unsuccessful_redistributable = False

    @property
    def build_flags(self):
        """Return the any:`clang_build.flags.BuildFlags` of this target.
        """
        return self._build_flags


class HeaderOnly(Target):
    """HeaderOnly targets are the default target type when no source files are found.

    Header-only targets cannot have private compile flags, link flags or dependencies.
    They are automatically promoted to public instead.

    TODO: need to check whether "public" makes sense for header-only, when we have implemented "private" dependencies
    """

    def __init__(self, target_description, files, dependencies=None):
        """Initialise a header-only target.

        Header-only targets' private flags and include-directories are public.
        """
        super().__init__(
            target_description=target_description,
            files=files,
            dependencies=dependencies,
        )

        if files["sourcefiles"]:
            self._logger.info(
                f'{len(files["sourcefiles"])} source file(s) found for header-only target. '
                + "You may want to check your build configuration."
            )

        self._build_flags.make_private_flags_public()
        self._directories.make_private_directories_public()

    def link(self):
        self._logger.info("header-only target does not require linking.")

    def compile(self, process_pool, progress_disabled):
        self._logger.info("header-only target does not require compiling.")

    def _get_default_flags(self):
        """Return the default any:`clang_build.flags.BuildFlags` without compile or link flags.
        """
        return BuildFlags(self._environment.build_type, self._environment.toolchain, True)

    def _add_dependency_flags(self, target):
        """Forward dependencies' public and interface flags.
        """
        self._build_flags.forward_public_flags(target)
        self._build_flags.forward_interface_flags(target)


def generate_depfile_single_source(buildable):
    buildable.generate_depfile()
    return buildable


def compile_single_source(buildable):
    buildable.compile()
    return buildable


class Compilable(Target):
    """A compilable target will generate object files.
    """

    def __init__(
        self,
        target_description,
        files,
        output_folder,
        platform_flags,
        prefix,
        suffix,
        dependencies=None,
    ):
        self.source_files = files["sourcefiles"]
        self.is_c_target = not any(
            not (f.suffix.lower() in ['.c', '.cc']) for f in self.source_files
        )

        super().__init__(
            target_description=target_description,
            files=files,
            dependencies=dependencies,
        )

        if not self.source_files:
            error_message = f"[{self.identifier}]: ERROR: Target was defined as a {self.__class__.__name__} but no source files were found"
            self._logger.error(error_message)
            raise RuntimeError(error_message)

        self.object_directory = (self.build_directory / "obj").resolve()
        self.depfile_directory = (self.build_directory / "dep").resolve()
        self.output_folder = (self.build_directory / output_folder).resolve()
        self.redistributable_folder = (self.build_directory / "redistributable").resolve()
        self.link_command = []
        self.unsuccessful_link = None
        self.link_report = None

        prefix = target_description.config.get("output_prefix", prefix)
        suffix = target_description.config.get("output_suffix", suffix)

        self.outname = target_description.config.get("output_name", self.name)
        self.outfilename = prefix + self.outname + suffix
        self.outfile = (self.output_folder / self.outfilename).resolve()

        compile_flags = self._build_flags.final_compile_flags_list() + platform_flags

        # Buildables which this Target contains
        include_directories = self._directories.final_directories_list()

        self.buildables = [
            _SingleSource(
                environment=self._environment,
                source_file=source_file,
                current_target_root_path=self.root_directory,
                depfile_directory=self.depfile_directory,
                object_directory=self.object_directory,
                include_directories=include_directories,
                compile_flags=compile_flags,
                is_c_target=self.is_c_target
            )
            for source_file in self.source_files
        ]

        # If compilation of buildables fail, they will be stored here later
        self._unsuccessful_compilations = []


    def _get_default_flags(self):
        """Return the default any:`clang_build.flags.BuildFlags` with compile flags but without link flags.
        """
        return BuildFlags(self._environment.build_type, self._environment.toolchain, self.is_c_target, default_compile_flags=True)

    def compile(self, process_pool, progress_disabled):
        """From the list of source files, compile those which changed or whose dependencies (included headers, ...) changed.
        """

        # Object file only needs to be (re-)compiled if the source file or headers it depends on changed
        if not self._environment.force_build:
            self.needed_buildables = [
                buildable for buildable in self.buildables if buildable.needs_rebuild
            ]
        else:
            self.needed_buildables = self.buildables

        # If the target was not modified, it may not need to compile
        if not self.needed_buildables:
            self._logger.info("target is already compiled")
            return

        self._logger.info(
            "target needs to build sources %s", [b.name for b in self.needed_buildables]
        )

        # Execute depfile generation command
        #
        #
        #    TODO: Remove hardcoded progress bar and use callback function instead
        #
        #
        self._logger.info(f"generate dependency files")
        self.needed_buildables = list(
            _get_build_progress_bar(
                process_pool.imap(
                    generate_depfile_single_source, self.needed_buildables
                ),
                progress_disabled,
                total=len(self.needed_buildables),
                name=self.name,
            )
        )

        # Execute compile command
        self._logger.info("compile object files")
        self.needed_buildables = list(
            _get_build_progress_bar(
                process_pool.imap(compile_single_source, self.needed_buildables),
                progress_disabled,
                total=len(self.needed_buildables),
                name=self.name,
            )
        )

        # Catch compilation errors
        self._unsuccessful_compilations = [
            buildable
            for buildable in self.needed_buildables
            if (buildable.compilation_failed or buildable.depfile_failed)
        ]
        if self._unsuccessful_compilations:
            raise _CompileError('Compilation was unsuccessful',
                {self.identifier: [source.compile_report for source in self._unsuccessful_compilations]})

    def link(self):
        pass


class Executable(Compilable):
    """Executable targets are the default target type when source files are found.

    An executable cannot be the dependency of another target.
    """

    def __init__(self, target_description, files, dependencies=None):
        """Initialise an executable target.
        """

        super().__init__(
            target_description=target_description,
            files=files,
            output_folder=target_description.environment.toolchain.platform_defaults['EXECUTABLE_OUTPUT_DIR'],
            platform_flags=target_description.environment.toolchain.platform_defaults['PLATFORM_EXTRA_FLAGS_EXECUTABLE'],
            prefix=target_description.environment.toolchain.platform_defaults['EXECUTABLE_PREFIX'],
            suffix=target_description.environment.toolchain.platform_defaults['EXECUTABLE_SUFFIX'],
            dependencies=dependencies,
        )

        ### Bundling requires extra flags
        if self._environment.bundle:
            self._build_flags.add_bundling_flags()

    def bundle(self):
        self.unsuccessful_bundle = False

        ### Gather
        bundle_files = []
        for dependency in self.dependencies:
            bundle_files += dependency.bundle()

        ### Copy
        for bundle_file in bundle_files:
            try:
                _shutil.copy(bundle_file, self.output_folder)
            except _subprocess.CalledProcessError as error:
                self.unsuccessful_bundle = True
                self.bundle_report = error.output.decode("utf-8").strip()

        # Catch bundling errors
        if self.unsuccessful_bundle:
            raise _BundleError('Bundling was unsuccessful',
                {self.identifier: self.bundle_report})

        return [self.outfile] + bundle_files

    def redistributable(self):
        self.unsuccessful_redistributable = False
        if self._environment.toolchain.platform == "osx":
            appfolder = self.redistributable_folder / f"{self.outname}.app"
            binfolder = appfolder / "Contents"/ "MacOS"
            try:
                binfolder.mkdir(parents=True, exist_ok=True)
                with (appfolder / "Contents"/ "Info.plist").open(
                    mode="w"
                ) as plist:
                    plist.write(
                        f"""<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple Computer//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>CFBundleGetInfoString</key>
  <string>{self.outname}</string>
  <key>CFBundleExecutable</key>
  <string>{self.outname}</string>
  <key>CFBundleIdentifier</key>
  <string>com.your-company-name.www</string>
  <key>CFBundleName</key>
  <string>{self.outname}</string>
  <key>CFBundleShortVersionString</key>
  <string>0.0</string>
  <key>CFBundleInfoDictionaryVersion</key>
  <string>6.0</string>
  <key>CFBundlePackageType</key>
  <string>APPL</string>
  <key>IFMajorVersion</key>
  <integer>0</integer>
  <key>IFMinorVersion</key>
  <integer>0</integer>
</dict>
</plist>"""
                    )
                _shutil.copy(self.outfile, binfolder)
                bundle_files = self.bundle()
                for bundle_file in bundle_files:
                    _shutil.copy(bundle_file, binfolder)
            except _subprocess.CalledProcessError as error:
                self.unsuccessful_redistributable = True
                self.redistributable_report = error.output.decode("utf-8").strip()
        elif self._environment.toolchain.platform == "linux":
            try:
                self.redistributable_folder.mkdir(parents=True, exist_ok=True)
                # TODO: gather includes and shared libraries
            except _subprocess.CalledProcessError as error:
                self.unsuccessful_redistributable = True
                self.redistributable_report = error.output.decode("utf-8").strip()
        elif self._environment.toolchain.platform == "windows":
            try:
                self.redistributable_folder.mkdir(parents=True, exist_ok=True)
                # TODO: gather includes and shared libraries
            except _subprocess.CalledProcessError as error:
                self.unsuccessful_redistributable = True
                self.redistributable_report = error.output.decode("utf-8").strip()

        # Check for redistibutable bundling errors
        if self.unsuccessful_redistributable:
            raise _RedistributableError('Creating redistributables was unsuccessful',
                {self.identifier: self.redistributable_report})

    def _get_default_flags(self):
        """Return the default any:`clang_build.flags.BuildFlags` with compile flags and link flags.
        """
        return BuildFlags(self._environment.build_type, self._environment.toolchain, self.is_c_target, default_compile_flags=True, default_link_flags=True)

    def _add_dependency_flags(self, target):
        """Add dependencies' public and interface flags to the own and forward their public flags.
        """
        self._build_flags.apply_public_flags(target)
        self._build_flags.forward_public_flags(target)
        self._build_flags.apply_interface_flags(target)

    def link(self):
        success, self.link_report = self._environment.toolchain.link(
            [buildable.object_file for buildable in self.buildables],
            self.outfile,
            self._build_flags._language_flags() + self._build_flags.final_link_flags_list(),
            [target.output_folder.resolve() for target in self.dependencies if target.__class__ is not HeaderOnly],
            [target.outname for target in self.dependencies if target.__class__ is not HeaderOnly],
            False,
            self.is_c_target)

        self.unsuccessful_link = not success

        # Catch link errors
        if self.unsuccessful_link:
            raise _LinkError('Linking was unsuccessful',
                {self.identifier: self.link_report})

class SharedLibrary(Compilable):
    def __init__(self, target_description, files, dependencies=None):

        super().__init__(
            target_description=target_description,
            files=files,
            output_folder=target_description.environment.toolchain.platform_defaults['SHARED_LIBRARY_OUTPUT_DIR'],
            platform_flags=target_description.environment.toolchain.platform_defaults['PLATFORM_EXTRA_FLAGS_SHARED'],
            prefix=target_description.environment.toolchain.platform_defaults['SHARED_LIBRARY_PREFIX'],
            suffix=target_description.environment.toolchain.platform_defaults['SHARED_LIBRARY_SUFFIX'],
            dependencies=dependencies,
        )

        # TODO: This has to go to the flags department I guess
        ### Bundling requires some link flags
        #if self._environment.bundle:
        #    if _platform.PLATFORM == "osx":
        #        ### Install name for OSX
        #        self.link_command += ["-install_name", f"@rpath/{self.outfilename}"]
        #    elif _platform.PLATFORM == "linux":
        #        pass
        #    elif _platform.PLATFORM == "windows":
        #        pass

    def bundle(self):
        self.unsuccessful_bundle = False

        ### Gather
        self_bundle_files = [self.outfile]
        if self._environment.toolchain.platform == "windows":
            self_bundle_files.append(_Path(str(self.outfile)[:-3] + "exp"))
            self_bundle_files.append(_Path(str(self.outfile)[:-3] + "lib"))

        bundle_files = []
        for dependency in self.dependencies:
            bundle_files += dependency.bundle()

        ### Copy
        for bundle_file in bundle_files:
            try:
                _shutil.copy(bundle_file, self.output_folder)
            except _subprocess.CalledProcessError as error:
                self.unsuccessful_bundle = True
                self.bundle_report = error.output.decode("utf-8").strip()

        # Catch bundling errors
        if self.unsuccessful_bundle:
            raise _BundleError('Bundling was unsuccessful',
                {self.identifier: self.bundle_report})

        return self_bundle_files + bundle_files

    def _get_default_flags(self):
        """Return the default any:`clang_build.flags.BuildFlags` with compile flags and link flags.
        """
        return BuildFlags(self._environment.build_type, self._environment.toolchain, self.is_c_target, default_compile_flags=True, default_link_flags=True)

    def _add_dependency_flags(self, target):
        """Add dependencies' public and interface flags to the own and forwards their public flags.
        """
        self._build_flags.apply_public_flags(target)
        self._build_flags.forward_public_flags(target)
        self._build_flags.apply_interface_flags(target)

    def link(self):
        success, self.link_report = self._environment.toolchain.link(
            [buildable.object_file for buildable in self.buildables],
            self.outfile,
            self._build_flags._language_flags() + self._build_flags.final_link_flags_list(),
            [target.output_folder.resolve() for target in self.dependencies if target.__class__ is not HeaderOnly],
            [target.outname for target in self.dependencies if target.__class__ is not HeaderOnly],
            True,
            self.is_c_target)

        self.unsuccessful_link = not success

        # Catch link errors
        if self.unsuccessful_link:
            raise _LinkError('Linking was unsuccessful',
                {self.identifier: self.link_report})


class StaticLibrary(Compilable):
    def __init__(self, target_description, files, dependencies=None):

        super().__init__(
            target_description=target_description,
            files=files,
            output_folder=target_description.environment.toolchain.platform_defaults['STATIC_LIBRARY_OUTPUT_DIR'],
            platform_flags=target_description.environment.toolchain.platform_defaults['PLATFORM_EXTRA_FLAGS_STATIC'],
            prefix=target_description.environment.toolchain.platform_defaults['STATIC_LIBRARY_PREFIX'],
            suffix=target_description.environment.toolchain.platform_defaults['STATIC_LIBRARY_SUFFIX'],
            dependencies=dependencies,
        )

    def _add_dependency_flags(self, target):
        """Add dependencies' public flags to the own and forwards their public and interface flags.

        This is done, because the dependency's interface flags cannot be applied to this static
        library but only to the shared library or executable that includes this static library.
        """
        self._build_flags.apply_public_flags(target)
        self._build_flags.forward_public_flags(target)
        self._build_flags.forward_interface_flags(target)

    def link(self):
        """Although not really a "link" procedure, but really only an archiving procedure
        for simplicity's sake, this is also called link
        """
        # This library's objects
        objects = [buildable.object_file for buildable in self.buildables]

        # Dependencies' objects
        for target in self.dependencies:
            if not target.__class__ is HeaderOnly:
                objects += [buildable.object_file for buildable in target.buildables]

        success, self.link_report = self._environment.toolchain.archive(
            objects,
            self.outfile,
            self._build_flags.final_link_flags_list())

        self.unsuccessful_link = not success

        # Catch link errors
        if self.unsuccessful_link:
            raise _LinkError('Linking was unsuccessful',
                {self.identifier: self.link_report})


TARGET_MAP = {
    "executable": Executable,
    "shared library": SharedLibrary,
    "static library": StaticLibrary,
    "header only": HeaderOnly,
}


class TargetDescription(_TreeEntry, _NamedLogger):
    """A hollow Target used for dependency checking.

    Before Projects actually configure targets, they first
    make sure that all dependencies etc are correctly defined.
    For this initial step, these TargetDescriptions are used.
    This is also necessary, because some of the target properties
    like the build folder, depend on the entire project structure
    and thus the two step procedure is necessary.

    TODO: Change Attributes to properties :)
    """

    def __init__(self, name: str, config: dict, parent_project):
        """Generate a TargetDescription.

        Parameters
        ----------
        name: str
            The name of this target as it will also later be named
        config : dict
            The config for this target (e.g. read from a toml)
        identifier : str
            Unique str representation of this target
        parent_project : clang_build.project.Project
            The project to which this target belongs
        """
        _NamedLogger.__init__(self, _LOGGER)

        # The "." character is used by clang-build to create unique
        # target identifiers and is therefore forbidden in naming
        if "." in name:
            error_message = self.log_message(
                f"Name contains illegal character '.': {name}"
            )
            self._logger.error(error_message)
            raise RuntimeError(error_message)

        # If no name is given, and no "output_name" is configured,
        # the output_name will be "main"
        if not name and not config.get("output_name", None):
            config["output_name"] = "main"

        # If no name is given it will be "target"
        if not name:
            name = "target"

        self.name = name
        self.config = config
        self.parent_project = parent_project

        self.only_target = False
        self.environment = self.parent_project.environment
        self._relative_directory = self.config.get("directory", "")
        self._download_directory = None

        if self.config.get("url"):
            self._download_directory = self.build_directory.parent / "external_sources"

    def __repr__(self) -> str:
        return f"clang_build.target.TargetDescription('{self.identifier}')"

    def __str__(self) -> str:
        return f"[{self.identifier}]"

    @property
    def identifier(self):
        """Return the unique identifier of this target.

        Targets are identified by their parent projects and their name as
        "[project_name.sub_project_name.target_name]".

        The default target name is "target".
        """
        return f"{self.parent_project.identifier}.{self.name}"

    @property
    def root_directory(self):
        """Return the root source directory.

        By default, the "include" and "src" directories are searched relative to
        this folder.

        The folder can be set by adding a "directory" in the config.
        If this target has external sources, it is relative to the "external_sources"
        directory, else it is relative to the parent project's directory.
        """
        if self._download_directory:
            return self._download_directory / self._relative_directory
        else:
            return self.parent_project.directory / self._relative_directory

    @property
    def build_directory(self):
        """Return the directory that serves as root build folder for the target.
        """
        if self.only_target:
            return (
                self.parent_project.build_directory
                / self.environment.build_type.name.lower()
            )
        else:
            return (
                self.parent_project.build_directory
                / self.name
                / self.environment.build_type.name.lower()
            )

    def get_sources(self):
        """Download external sources, if present, to "build_directory/external_sources".
        """
        if self._download_directory:
            url = self.config.get("url", None)
            version = self.config.get("version", None)
            _git_download_sources(url, self._download_directory, self._logger, version, self.environment.clone_recursive)


if __name__ == "__main__":
    _freeze_support()
