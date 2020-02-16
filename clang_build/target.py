"""
Target describes a single build or dependency target with all needed paths and
a list of buildables that comprise it's compile and link steps.
"""

import logging as _logging
import os as _os
import shutil as _shutil
import subprocess as _subprocess
from abc import abstractmethod
from multiprocessing import freeze_support as _freeze_support
from pathlib import Path as _Path

from . import platform as _platform
from .build_type import BuildType
from .dialect_check import get_dialect_string as _get_dialect_string
from .dialect_check import \
    get_max_supported_compiler_dialect as _get_max_supported_compiler_dialect
from .git_tools import checkout_version as _checkout_version
from .git_tools import clone_repository as _clone_repository
from .git_tools import needs_download as _needs_download
from .io_tools import get_sources_and_headers as _get_sources_and_headers
from .io_tools import parse_flags_options as _parse_flags_options
from .logging_tools import NamedLogger as _NamedLogger
from .progress_bar import get_build_progress_bar as _get_build_progress_bar
from .single_source import SingleSource as _SingleSource
from .tree_entry import TreeEntry as _TreeEntry

_LOGGER = _logging.getLogger("clang_build.clang_build")


class Target(_TreeEntry, _NamedLogger):
    COMPILE_FLAGS = {
        BuildType.Default: ["-Wall", "-Wextra", "-Wpedantic", "-Wshadow", "-Werror"],
        BuildType.Release: ["-O3", "-DNDEBUG"],
        BuildType.RelWithDebInfo: ["-O3", "-g3", "-DNDEBUG"],
        BuildType.Debug: [
            "-Og",
            "-g3",
            "-DDEBUG",
            "-fno-optimize-sibling-calls",
            "-fno-omit-frame-pointer",
            "-fsanitize=address",
            "-fsanitize=undefined",
        ],
        BuildType.Coverage: [
            "-Og",
            "-g3",
            "-DDEBUG",
            "-fno-optimize-sibling-calls",
            "-fno-omit-frame-pointer",
            "-fsanitize=address",
            "-fsanitize=undefined",
            "--coverage",
            "-fno-inline",
        ],
    }
    LINK_FLAGS_EXE_SHARED = {
        BuildType.Debug: ["-fsanitize=address", "-fsanitize=undefined"],
        BuildType.Coverage: [
            "-fsanitize=address",
            "-fsanitize=undefined",
            "--coverage",
            "-fno-inline",
        ],
    }

    def __init__(self, target_description, files, dependencies=None):
        # Basics
        _NamedLogger.__init__(self)
        self.name = target_description.name
        self.identifier = target_description.identifier

        self.environment = target_description.environment

        if dependencies is None:
            dependencies = []

        self.dependency_targets = dependencies
        self.unsuccessful_builds = []

        # TODO: parse user-specified target version

        self.root_directory = _Path(target_description.root_directory)
        self.build_directory = target_description.build_directory

        self.headers = list(dict.fromkeys(files["headers"]))

        # Include directories
        self.include_directories_private = files["include_directories"]
        self.include_directories_public = files["include_directories_public"]

        # Default include path
        # if self.root_directory.joinpath('include').exists():
        #    self.include_directories_public = [self.root_directory.joinpath('include')] + self.include_directories_public

        # Public include directories of dependencies are forwarded
        for target in self.dependency_targets:
            self.include_directories_public += target.include_directories_public

        # Make unique and resolve
        self.include_directories_private = list(
            dict.fromkeys(dir.resolve() for dir in self.include_directories_private)
        )
        self.include_directories_public = list(
            dict.fromkeys(dir.resolve() for dir in self.include_directories_public)
        )

        # Compile and link flags
        self.compile_flags_private = []
        self.link_flags_private = []

        self.compile_flags_interface = []
        self.link_flags_interface = []

        self.compile_flags_public = []
        self.link_flags_public = []

        # Default flags come first
        self.add_default_flags()

        # Dependencies' flags
        for target in self.dependency_targets:
            # Header only libraries will forward all non-private flags
            self.add_target_flags(target)

        # Own private flags
        cf, lf = _parse_flags_options(target_description.config, "flags")
        self.compile_flags_private += cf
        self.link_flags_private += lf

        # Own interface flags
        cf, lf = _parse_flags_options(target_description.config, "interface-flags")
        self.compile_flags_interface += cf
        self.link_flags_interface += lf

        # Own public flags
        cf, lf = _parse_flags_options(target_description.config, "public-flags")
        self.compile_flags_public += cf
        self.link_flags_public += lf

    @abstractmethod
    def add_default_flags(self):
        pass

    @abstractmethod
    def add_target_flags(self, target):
        pass

    def apply_public_flags(self, target):
        self.compile_flags_private += target.compile_flags_public
        self.link_flags_private += target.link_flags_public

    def forward_public_flags(self, target):
        self.compile_flags_public += target.compile_flags_public
        self.link_flags_public += target.link_flags_public

    def apply_interface_flags(self, target):
        self.compile_flags_private += target.compile_flags_interface
        self.link_flags_private += target.link_flags_interface

    def forward_interface_flags(self, target):
        self.compile_flags_interface += target.compile_flags_interface
        self.link_flags_interface += target.link_flags_interface

    @abstractmethod
    def compile(self, process_pool, progress_disabled):
        pass

    @abstractmethod
    def link(self):
        pass

    def bundle(self):
        self.unsuccessful_bundle = False
        bundle_files = []
        for dependency in self.dependency_targets:
            bundle_files += dependency.bundle()
        return bundle_files

    def redistributable(self):
        self.unsuccessful_redistributable = False


class HeaderOnly(Target):
    def __init__(self, target_description, files, dependencies=None):
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

        self.compile_flags_public += self.compile_flags_private
        self.link_flags_public += self.link_flags_private
        self.include_directories_public = list(
            dict.fromkeys(
                self.include_directories_public + self.include_directories_private
            )
        )
        self.include_directories_private = []

    def link(self):
        self._logger.info("Header-only target does not require linking.")

    def compile(self, process_pool, progress_disabled):
        self._logger.info("Header-only target does not require compiling.")

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
    def __init__(
        self,
        target_description,
        files,
        link_command,
        output_folder,
        platform_flags,
        prefix,
        suffix,
        dependencies=None,
    ):

        super().__init__(
            target_description=target_description,
            files=files,
            dependencies=dependencies,
        )

        source_files = files["sourcefiles"]

        if not source_files:
            error_message = f"[{self.identifier}]: ERROR: Target was defined as a {self.__class__.__name__} but no source files were found"
            _LOGGER.error(error_message)
            raise RuntimeError(error_message)

        self.object_directory = self.build_directory.joinpath("obj").resolve()
        self.depfile_directory = self.build_directory.joinpath("dep").resolve()
        self.output_folder = self.build_directory.joinpath(output_folder).resolve()
        self.redistributable_folder = self.build_directory.joinpath("redistributable")

        self.outname = target_description.config.get("output_name", self.name)

        self.outfilename = prefix + self.outname + suffix
        self.outfile = _Path(self.output_folder, self.outfilename).resolve()

        # Sources
        self.source_files = source_files

        # Full list of flags
        compile_flags = self.compile_flags_private + self.compile_flags_public
        link_flags = self.link_flags_private + self.link_flags_public
        # Make flags unique
        compile_flags = list(dict.fromkeys(compile_flags))
        link_flags = list(dict.fromkeys(link_flags))
        # Split strings containing spaces
        compile_flags = list(str(" ".join(compile_flags)).split())
        link_flags = list(str(" ".join(link_flags)).split())

        # List of unique include directories
        include_directories = (
            self.include_directories_private + self.include_directories_public
        )
        include_directories = list(dict.fromkeys(include_directories))

        # Buildables which this Target contains
        self.include_directories_command = []
        for directory in include_directories:
            self.include_directories_command += ["-I", str(directory.resolve())]

        self.buildables = [
            _SingleSource(
                environment=self.environment,
                source_file=source_file,
                platform_flags=platform_flags,
                current_target_root_path=self.root_directory,
                depfile_directory=self.depfile_directory,
                object_directory=self.object_directory,
                include_strings=self.include_directories_command,
                compile_flags=compile_flags,
            )
            for source_file in self.source_files
        ]

        # If compilation of buildables fail, they will be stored here later
        self.unsuccessful_builds = []

        # Linking setup
        self.link_command = link_command + [str(self.outfile)]

        ## Additional scripts
        self.before_compile_script = ""
        self.before_link_script = ""
        self.after_build_script = ""
        if (
            "scripts" in target_description.config
        ):  ### TODO: maybe the scripts should be named differently
            self.before_compile_script = target_description.config["scripts"].get(
                "before_compile", ""
            )
            self.before_link_script = target_description.config["scripts"].get(
                "before_link", ""
            )
            self.after_build_script = target_description.config["scripts"].get(
                "after_build", ""
            )

    def add_default_flags(self):
        self.compile_flags_private += Target.COMPILE_FLAGS.get(BuildType.Default)
        if self.environment.build_type != BuildType.Default:
            self.compile_flags_private += Target.COMPILE_FLAGS.get(
                self.environment.build_type
            )

    # From the list of source files, compile those which changed or whose dependencies (included headers, ...) changed
    def compile(self, process_pool, progress_disabled):

        # Object file only needs to be (re-)compiled if the source file or headers it depends on changed
        if not self.environment.force_build:
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

        # Before-compile step
        if self.before_compile_script:
            script_file = self.root_directory.joinpath(
                self.before_compile_script
            ).resolve()
            self._logger.info(f"pre-compile step: '{script_file}'")
            original_directory = _os.getcwd()
            _os.chdir(self.root_directory)
            with open(script_file) as f:
                code = compile(f.read(), script_file, "exec")
                exec(code, globals(), locals())
            _os.chdir(original_directory)
            self._logger.info(f"finished pre-compile step")

        # Execute depfile generation command
        #
        #
        #    TODO: Remove hardcoded progress bar and use callback function instead
        #
        #
        self._logger.info(f"scan dependencies")
        for b in self.needed_buildables:
            self._logger.debug(" ".join(b.dependency_command))
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
        self._logger.info("compile")
        for b in self.needed_buildables:
            self._logger.debug(" ".join(b.compile_command))
        self.needed_buildables = list(
            _get_build_progress_bar(
                process_pool.imap(compile_single_source, self.needed_buildables),
                progress_disabled,
                total=len(self.needed_buildables),
                name=self.name,
            )
        )

        self.unsuccessful_builds = [
            buildable
            for buildable in self.needed_buildables
            if (buildable.compilation_failed or buildable.depfile_failed)
        ]

    def link(self):
        # Before-link step
        if self.before_link_script:
            script_file = self.root_directory.joinpath(self.before_link_script)
            self._logger.info(f"pre-link step: '{script_file}'")
            original_directory = _os.getcwd()
            _os.chdir(self.root_directory)
            with open(script_file) as f:
                code = compile(f.read(), script_file, "exec")
                exec(code, globals(), locals())
            _os.chdir(original_directory)
            self._logger.info("finished pre-link step")

        self._logger.info(f'link -> "{self.outfile}"')
        self._logger.debug("    " + " ".join(self.link_command))

        # Execute link command
        try:
            self.output_folder.mkdir(parents=True, exist_ok=True)
            self.link_report = (
                _subprocess.check_output(self.link_command, stderr=_subprocess.STDOUT)
                .decode("utf-8")
                .strip()
            )
            self.unsuccessful_link = False
        except _subprocess.CalledProcessError as error:
            self.unsuccessful_link = True
            self.link_report = error.output.decode("utf-8").strip()

        ## After-build step
        if self.after_build_script:
            script_file = self.root_directory.joinpath(self.after_build_script)
            self._logger.info(f"after-build step: '{script_file}'")
            original_directory = _os.getcwd()
            _os.chdir(self.root_directory)
            with open(script_file) as f:
                code = compile(f.read(), script_file, "exec")
                exec(code, globals(), locals())
            _os.chdir(original_directory)
            self._logger.info("finished after-build step")


class Executable(Compilable):
    def __init__(self, target_description, files, dependencies=None):

        super().__init__(
            target_description=target_description,
            files=files,
            link_command=[target_description.environment.clangpp, "-o"],
            output_folder=_platform.EXECUTABLE_OUTPUT,
            platform_flags=_platform.PLATFORM_EXTRA_FLAGS_EXECUTABLE,
            prefix=_platform.EXECUTABLE_PREFIX,
            suffix=_platform.EXECUTABLE_SUFFIX,
            dependencies=dependencies,
        )

        ### Link self
        self.link_command += [
            str(buildable.object_file) for buildable in self.buildables
        ]

        ### Library dependency search paths
        for target in self.dependency_targets:
            if target.__class__ is not HeaderOnly:
                self.link_command += ["-L", str(target.output_folder.resolve())]

        self.link_command += self.link_flags_private + self.link_flags_public

        ### Link dependencies
        for target in self.dependency_targets:
            if target.__class__ is not HeaderOnly:
                self.link_command += ["-l" + target.outname]

        ### Bundling requires extra flags
        if self.environment.bundle:
            ### Search for libraries relative to the executable
            if _platform.PLATFORM == "osx":
                self.link_command += ["-Wl,-rpath,@executable_path"]
            elif _platform.PLATFORM == "linux":
                self.link_command += ["-Wl,-rpath,$ORIGIN"]
            elif _platform.PLATFORM == "windows":
                pass

    def bundle(self):
        self.unsuccessful_bundle = False

        ### Gather
        bundle_files = []
        for dependency in self.dependency_targets:
            bundle_files += dependency.bundle()

        ### Copy
        for bundle_file in bundle_files:
            try:
                _shutil.copy(bundle_file, self.output_folder)
            except _subprocess.CalledProcessError as error:
                self.unsuccessful_bundle = True
                self.bundle_report = error.output.decode("utf-8").strip()

        return [self.outfile] + bundle_files

    def redistributable(self):
        self.unsuccessful_redistributable = False
        if _platform.PLATFORM == "osx":
            appfolder = self.redistributable_folder.joinpath(f"{self.outname}.app")
            binfolder = appfolder.joinpath("Contents", "MacOS")
            try:
                binfolder.mkdir(parents=True, exist_ok=True)
                with appfolder.joinpath("Contents", "Info.plist").open(
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
        elif _platform.PLATFORM == "linux":
            try:
                self.redistributable_folder.mkdir(parents=True, exist_ok=True)
                # TODO: gather includes and shared libraries
            except _subprocess.CalledProcessError as error:
                self.unsuccessful_redistributable = True
                self.redistributable_report = error.output.decode("utf-8").strip()
        elif _platform.PLATFORM == "windows":
            try:
                self.redistributable_folder.mkdir(parents=True, exist_ok=True)
                # TODO: gather includes and shared libraries
            except _subprocess.CalledProcessError as error:
                self.unsuccessful_redistributable = True
                self.redistributable_report = error.output.decode("utf-8").strip()

    def add_default_flags(self):
        super().add_default_flags()
        if self.environment.build_type == BuildType.Debug:
            self.link_flags_private += Target.LINK_FLAGS_EXE_SHARED[BuildType.Debug]
        elif self.environment.build_type == BuildType.Coverage:
            self.link_flags_private += Target.LINK_FLAGS_EXE_SHARED[BuildType.Coverage]

    def add_target_flags(self, target):
        self.apply_public_flags(target)
        self.forward_public_flags(target)
        self.apply_interface_flags(target)


class SharedLibrary(Compilable):
    def __init__(self, target_description, files, dependencies=None):

        super().__init__(
            target_description=target_description,
            files=files,
            link_command=[target_description.environment.clangpp, "-shared", "-o"],
            output_folder=_platform.SHARED_LIBRARY_OUTPUT,
            platform_flags=_platform.PLATFORM_EXTRA_FLAGS_SHARED,
            prefix=_platform.SHARED_LIBRARY_PREFIX,
            suffix=_platform.SHARED_LIBRARY_SUFFIX,
            dependencies=dependencies,
        )

        ### Link self
        self.link_command += [
            str(buildable.object_file) for buildable in self.buildables
        ]

        ### Library dependency search paths
        for target in self.dependency_targets:
            if target.__class__ is not HeaderOnly:
                self.link_command += ["-L", str(target.output_folder.resolve())]

        self.link_command += self.link_flags_private + self.link_flags_public

        ### Link dependencies
        for target in self.dependency_targets:
            if target.__class__ is not HeaderOnly:
                self.link_command += ["-l" + target.outname]

        ### Bundling requires some link flags
        if self.environment.bundle:
            if _platform.PLATFORM == "osx":
                ### Install name for OSX
                self.link_command += ["-install_name", f"@rpath/{self.outfilename}"]
            elif _platform.PLATFORM == "linux":
                pass
            elif _platform.PLATFORM == "windows":
                pass

    def bundle(self):
        self.unsuccessful_bundle = False

        ### Gather
        self_bundle_files = [self.outfile]
        if _platform.PLATFORM == "windows":
            self_bundle_files.append(_Path(str(self.outfile)[:-3] + "exp"))
            self_bundle_files.append(_Path(str(self.outfile)[:-3] + "lib"))

        bundle_files = []
        for dependency in self.dependency_targets:
            bundle_files += dependency.bundle()

        ### Copy
        for bundle_file in bundle_files:
            try:
                _shutil.copy(bundle_file, self.output_folder)
            except _subprocess.CalledProcessError as error:
                self.unsuccessful_bundle = True
                self.bundle_report = error.output.decode("utf-8").strip()

        return self_bundle_files + bundle_files

    def add_default_flags(self):
        super().add_default_flags()
        if self.environment.build_type == BuildType.Debug:
            self.link_flags_private += Target.LINK_FLAGS_EXE_SHARED[BuildType.Debug]
        elif self.environment.build_type == BuildType.Coverage:
            self.link_flags_private += Target.LINK_FLAGS_EXE_SHARED[BuildType.Coverage]

    def add_target_flags(self, target):
        self.apply_public_flags(target)
        self.forward_public_flags(target)
        self.apply_interface_flags(target)


class StaticLibrary(Compilable):
    def __init__(self, target_description, files, dependencies=None):

        super().__init__(
            target_description=target_description,
            files=files,
            link_command=[target_description.environment.clang_ar, "rc"],
            output_folder=_platform.STATIC_LIBRARY_OUTPUT,
            platform_flags=_platform.PLATFORM_EXTRA_FLAGS_STATIC,
            prefix=_platform.STATIC_LIBRARY_PREFIX,
            suffix=_platform.STATIC_LIBRARY_SUFFIX,
            dependencies=dependencies,
        )

        ### Link self
        self.link_command += [
            str(buildable.object_file) for buildable in self.buildables
        ]
        self.link_command += self.link_flags_private + self.link_flags_public

        ### Link dependencies
        for target in self.dependency_targets:
            if not target.__class__ is HeaderOnly:
                self.link_command += [
                    str(buildable.object_file) for buildable in target.buildables
                ]

    def add_target_flags(self, target):
        self.apply_public_flags(target)
        self.forward_public_flags(target)
        self.forward_interface_flags(target)




def _get_dependencies(target_description, project_tree):
    dependencies = [
        project_tree.nodes()[dependency]["data"]
        for dependency in project_tree.successors(target_description)
    ]

    # Are there executables named as dependencies?
    executable_dependencies = [
        target for target in dependencies if target.__class__ is Executable
    ]
    if executable_dependencies:
        exelist = ", ".join([f"[{dep.name}]" for dep in executable_dependencies])
        error_message = target_description.log_message(
            f"The following targets are linking dependencies but were identified as executables:\n    {exelist}"
        )
        self._logger.error(error_message)
        raise RuntimeError(error_message)

    return dependencies


_TARGET_MAP = {
    "executable": Executable,
    "shared library": SharedLibrary,
    "static library": StaticLibrary,
    "header only": HeaderOnly,
}

class TargetDescription(_NamedLogger, _TreeEntry):
    """A hollow Target used for dependency checking.

    Before Projects actually configure targets, they first
    make sure that all dependencies etc are correctly defined.
    For this initial step, these TargetDescriptions are used.
    This is also necessary, because some of the target properties
    like the build folder, depend on the entire project structure
    and thus the two step procedure is necessary.
    """

    def __init__(self, name: str, config: dict, identifier: str, parent, environment):
        """Generate a TargetDescription.

        Parameters
        ----------
        name: str
            The name of this target as it will also later be named
        config : dict
            The config for this target (e.g. read from a toml)
        identifier : str
            Unique str representation of this target
        parent : Project
            The parent project of this target

        """
        if "." in name:
            error_message = self.log_message(
                f"Name contains illegal character '.': {name}"
            )
            self._logger.error(error_message)
            raise RuntimeError(error_message)

        self.name = name
        self.config = config
        self.parent = parent
        self.identifier = identifier
        self.environment = environment

        self.root_directory = self.parent.directory.joinpath(self.config.get("directory", ""))

    @property
    def build_directory(self):
        return self.parent.build_directory.joinpath(
            self.environment.build_type.name.lower()
        )

    def download_target(self):
        url = self.config.get("url", None)
        if url:
            self._logger.info("Is an external URL target.")
            version = self.config.get("version", None)
            download_directory = self.build_directory.joinpath("external_sources")
            # Check if directory is already present and non-empty
            if _needs_download(url, download_directory, version):
                self._logger.info(f"external target sources found in {str(download_directory)}")

            # Otherwise we download the sources
            else:
                _clone_repository(
                    url, download_directory, self.environment.clone_recursive
                )

            # self.includeDirectories.append(download_directory)
            self.root_directory = download_directory



def make_target(target_description, project_tree):
    """Return the appropriate target given the target description.

    A target type can either be speicified in the ``target_description.config``
    or a target is determined based on which files are found on the hard disk.
    If only header files are found, a header-only target is assumed. Else,
    an executable target will be generated.

    Targets need to be build from a bottom-up traversal of the project tree so
    that all the dependencies of targets are already generated.

    Parameters
    ----------
    target_description : :any:`TargetDescription`
        A shallow description class of the target
    project_tree : :any:`networkx.DiGraph`
        The entire project tree from which to extract
        dependencies

    Returns
    -------
    HeaderOnly or Executable or SharedLibrary or StaticLibrary
        Returns the correct target type based on input parameters
    """



    dependencies = _get_dependencies(target_description, project_tree)

    # Sources
    files = _get_sources_and_headers(
        target_description.name,
        target_description.config,
        target_description.root_directory,
        target_description.build_directory,
    )

    # Create specific target if the target type was specified
    target_type = target_description.config.get("target_type")
    if target_type is not None:
        target_type = str(target_type).lower()
        if target_type in _TARGET_MAP:
            return _TARGET_MAP[target_type](target_description, files, dependencies)
        else:
            error_message = target_description.log_message(
                f'ERROR: Unsupported target type: "{target_description.config["target_type"].lower()}"'
            )
            _LOGGER.exception(error_message)
            raise RuntimeError(error_message)

    # No target specified so must be executable or header only
    else:
        if not files["sourcefiles"]:
            target_description.log_message(
                "no source files found. Creating header-only target."
            )
            return HeaderOnly(target_description, files, dependencies)

        target_description.log_message(
            f'{len(files["sourcefiles"])} source file(s) found. Creating executable target.'
        )
        return Executable(target_description, files, dependencies)


if __name__ == "__main__":
    _freeze_support()
