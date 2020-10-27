"""A class that contains potentially multiple targets and other projects."""

import logging as _logging
import textwrap as _textwrap
from multiprocessing import Pool as _Pool
from pathlib import Path as _Path
from typing import Optional as _Optional
from importlib import util as importlib_util

import networkx as _nx
import toml

from .circle import Circle as _Circle
from .io_tools import get_sources_and_headers as _get_sources_and_headers
from .logging_tools import NamedLogger as _NamedLogger
from .target import TARGET_MAP as _TARGET_MAP
from .target import Target as _Target
from .target import Executable as _Executable
from .target import HeaderOnly as _HeaderOnly
from .target import TargetDescription as _TargetDescription
from .tree_entry import TreeEntry as _TreeEntry
from .git_tools import download_sources as _git_download_sources
from .git_tools import get_latest_changes as _get_latest_changes

_LOGGER = _logging.getLogger(__name__)


def _get_project(directory, environment, parent=None):
    """Returns a Project created from a "clang-build.py" script.

    This is the basis of the scripting API. The "clang-build.py" script is required to
    define a method `get_project(directory, environment, parent) -> Project`.
    """
    module_file_path = directory.resolve() / "clang-build.py"
    module_name = "clang-build"

    module_spec = importlib_util.spec_from_file_location(module_name, module_file_path)
    if module_spec is None:
        raise RuntimeError(f'No "{module_name}" module could be found in "{directory.resolve()}"')

    clang_build_module = importlib_util.module_from_spec(module_spec)
    module_spec.loader.exec_module(clang_build_module)

    if clang_build_module.get_project is None:
        raise RuntimeError(f'Module "{module_name}" in "{directory.resolve()}" does not contain a `get_project` method')

    return clang_build_module.get_project(directory, environment, parent=parent)


class Project(_NamedLogger, _TreeEntry):
    """The Project class is all about organising targets and managing folder structures.

    Every start of clang-build, a Project is created that scans a given folder for what
    could potentially be a large multi-subproject structure. The project will find and
    configure all targets as specified by the parameters given. Once it is created, the
    structure that was discovered can be explored and targets can be built.
    """

    @property
    def build_directory(self):
        """Return the output directory for build objects for this project.

        Apart from a folder where the project files are stored, a project
        also has a separate folder where build files (like compiled object
        files or executables, etc.) are stored.
        """
        return self._build_directory

    @property
    def config(self):
        """Return the config dict of this project.

        Non-trivial projects will normally define project details in a toml file.
        This dict is a :any:`dict` version of this file.
        """
        return self._config

    @property
    def directory(self):
        """Return the directory of this project.

        Every project is located in a directory that has to be specified.
        The directory is the one that either contains a toml file or for
        trivial projects just the default folder structure that can be
        searched by clang-build.
        """
        return self._directory

    @property
    def environment(self):
        """Return the set of global settings."""
        return self._environment

    @property
    def identifier(self) -> str:
        """Returns the unique identifier of this project.

        The unique identifier for a project can be:
        - "project" if this is a basic project and no name was given
        - A simple string if a name was given to this project
        - A string with one or more "." if this is a subproject
        """
        return (
            self.name
            if self._parent is None
            else f"{self._parent.identifier}.{self.name}"
        )

    @property
    def name(self) -> str:
        """Return the name of this project.

        Every project can be given a name. A name is a string
        that does not contain "."s. For basic project no name
        has to be provided.
        """
        return self._name

    @property
    def parent(self):
        """Return the parent of this project.

        Projects are organised in a tree like structure. This project
        will return the parent project except for the case where this
        project is the top level project.
        """
        return self._parent

    @property
    def project_tree(self):
        """Return a :any:`networkx` tree representation of all selected targets.

        Targets can have dependencies on each other. This can be represented
        in a tree structure. Therefore, the targets that were selected during
        the initialization of the Project are available as a DiGraph. This
        graph is the global project tree. If you are only interested in subgraphs
        you have to use the :any:`networkx` functionality.
        """
        return self._project_tree

    @property
    def subprojects(self):
        """Return a list of subprojects.

        All direct children of this project (subprojects only, no targets)
        are returned as a list.
        """
        return self._subprojects

    @property
    def target_list(self):
        """Return all targets that are defined in this project.

        This list includes only those targets that were defined in this
        project and not those defined in subprojects.
        """
        return self._current_targets

    def __init__(self, name, config, directory, environment, **kwargs):
        """Initialise a project.

        The procedure for initialisation is:

        #. Setting some instance attributes
        #. Initialising sub-projects and filling the dependency tree recursively
        #. Determining the targets to configure
        #. Configuring the targets

        Parameters
        ----------
        directory : str or :any:`pathlib.Path`
            The directory to search for a ``toml`` file or source files
        environment : any:`clang_build.clang_build.Environment`
            An any:`clang_build.clang_build.Environment` instance defining some global
            settings for this run of clang-build.
        kwargs
            Used for internal purposes only.
        """
        _NamedLogger.__init__(self, _LOGGER)
        self._name = name
        self._config = config
        self._directory = _Path(directory)
        if not self._directory.exists():
            error_message = (
                f"ERROR: specified non-existent directory '{self._directory}'"
            )
            _LOGGER.error(error_message)
            raise RuntimeError(error_message)

        self._environment = environment
        self._parent = kwargs.get("parent", None)
        self._current_targets = []

        if not self.name:
            if self.parent:
                error_message = self.parent.log_message(
                    f"the config defines a subproject in folder {self.directory},"
                    + " that does not specify a name. It is not allowed to add a"
                    + " subproject that does not have a name."
                )

                self._logger.exception(error_message)
                raise RuntimeError(error_message)

            if "subprojects" in self.config:
                error_message = self.log_message(
                    "defining a top-level project with subprojects but without a name"
                    + " is illegal."
                )

                self._logger.exception(error_message)
                raise RuntimeError(error_message)

            self._name = "project"

        if self._parent:
            self._project_tree = self._parent.project_tree
        else:
            self._project_tree = _nx.DiGraph()

        self._set_directories()

        self._subprojects = self._parse_subprojects()

        self._project_tree.add_node(self, data=self)
        # Add edges to subprojects
        self._project_tree.add_edges_from(
            (self, sub_project) for sub_project in self.subprojects
        )

        # TODO: the following function name `_get_target_descriptions` is not descriptive
        self.add_targets(self._get_target_descriptions() + kwargs.get("targets", []))

    def __repr__(self) -> str:
        return f"clang_build.project.Project('{self.identifier}')"

    def __str__(self) -> str:
        return f"[[{self.identifier}]]"

    @classmethod
    def from_directory(cls, directory, environment, **kwargs):
        """Generate a project from a directory.

        This method covers the following cases in order:
        1. initialization from a "clang-build.py", if present
        2. initialization from a "clang-build.toml", if present
        3. defaults without any configuration
        """
        ### ----- Get the config
        toml_file = directory / "clang-build.toml"
        py_file = directory / "clang-build.py"
        parent = kwargs.get("parent", None)

        if parent:
            logger = parent._logger
            message_suffix = " for subproject"
        else:
            logger = _LOGGER
            message_suffix = ""

        if py_file.exists():
            logger.info(f"Using python project file \"{py_file}\"{message_suffix}")
            project = _get_project(directory, environment, parent=parent)
            if not isinstance(project, Project):
                raise RuntimeError(f'Unable to initialize project:\nThe `get_project` method in "{py_file}" did not return a valid `clang_build.project.Project`, its type is "{type(project)}"')
            return project

        elif toml_file.exists():
            logger.info(f"Found config file '{toml_file}'.")
            config = toml.load(toml_file)

        elif parent:
            error_message = parent.log_message(
                f"the config defines a subproject in folder {directory},"
                + " which does not have a project file. It is not allowed to add a"
                + " subproject that does not have a project file."
            )
            logger.exception(error_message)
            raise RuntimeError(error_message)

        else:
            config = {"target": {"output_name": "main"}}
        ### -----

        return cls.from_config(config, directory, environment, **kwargs)

    @classmethod
    def from_config(cls, config: dict, directory, environment, **kwargs):
        """Generate a project from a config dictionary.

        optional kwarg `targets`: Any of the `targets` may be a `Target` or `TargetDescription`
        """
        name = str(config.get("name", ""))
        project = cls(name, config, directory, environment, **kwargs)

        return project

    def add_targets(self, target_list: list):
        """Add a list of targets to this project.

        This method does the following:
        - check the validity of targets in the given list
        - add to the project's target_list
        - amend the dependency tree:
          - Add nodes and edges for targets in self
          - Add edges for dependencies in targets defined in project
        - optionally create a new dotfile
        - check for circular dependencies in the project

        This method integrates this project into the global project tree.

        This helper function is part of the initialisation of a project.
        It adds this project, all targets and their dependencies to the
        global project tree. If there are illegal dependencies, this function
        will raise an exception.
        """
        for target in target_list:
            if not (isinstance(target, _TargetDescription) or isinstance(target, _Target)):
                raise RuntimeError(f"clang_build.project.Project.add_targets: cannot add instance of type {type(target)}, it should be either a TargetDescription or Target.")

        self._current_targets += target_list

        # Add nodes and edges for targets in self
        for target in target_list:
            self._project_tree.add_node(target, data=target)
        self._project_tree.add_edges_from((self, target) for target in target_list)

        # Create a dotfile of the dependency graph
        create_dotfile = False
        if self._environment.create_dependency_dotfile and not self._parent:
            try:
                import pydot
                create_dotfile = True
            except:
                self._logger.error(f'Could not create dependency dotfile, as pydot is not installed')

        # Create initial dotfile without full dependency resolution
        if create_dotfile:
            _Path(self._environment.build_directory).mkdir(parents=True, exist_ok=True)
            _nx.drawing.nx_pydot.write_dot(self._project_tree, str(self._environment.build_directory / 'dependencies.dot'))

        # Add edges for dependencies in targets defined in project
        for target in target_list:
            dependencies = target.config.get("dependencies", [])
            dependency_objs = []
            for dependency_name in dependencies:
                full_name = self._identifier_from_name(dependency_name)

                try:
                    dependency = self._project_tree.nodes[full_name]["data"]
                except KeyError:
                    error_message = target.log_message(
                        f"the dependency [{dependency_name}] (expanded to [{full_name}]) does not point to a valid target."
                    )
                    self._logger.exception(error_message)
                    raise RuntimeError(error_message)

                dependency_objs.append(dependency)
                self._project_tree.add_edge(target, dependency)

            target.config["dependencies"] = dependency_objs

        # Create new dotfile with full dependency graph
        if create_dotfile:
            _nx.drawing.nx_pydot.write_dot(self._project_tree, str(self._environment.build_directory / 'dependencies.dot'))

        # Check the dependency graph for cycles
        if not self.parent:
            self._check_for_circular_dependencies()

        # Update the `only_target` flag of the targets in this project
        n_targets = len(self._current_targets)
        only_target = n_targets == 1 and len(self.config.get("subprojects", [])) == 0

        for target in self._current_targets:
            target.only_target = only_target


    def _parse_subprojects(self):
        """Generate all subprojects recursively.

        Recursively walks through all subprojects and parses
        them.

        Returns
        -------
        list
            List of Project objects.
        """
        subproject_list = []
        for directory in self.config.get("subprojects", []):
            subproject_dir = self._directory / directory
            subproject_list.append(Project.from_directory(subproject_dir, self._environment, parent=self))
        return subproject_list

    def _get_target_descriptions(self):
        """Get the list of targets for this project.

        Will return only those targets that are defined in
        this project. No subproject targets will be returned.

        Returns
        -------
        list
            List of TargetDescription objects
        """
        return [
            _TargetDescription(
                key, val, self
            )
            for key, val in self.config.items()
            if isinstance(val, dict)
        ]

    def _check_for_circular_dependencies(self):
        """Check if targets are defined in a circular dependency.

        Raises an exception if circular dependencies were found pointing
        out where the circular dependencies were found.
        """
        circles = list(_nx.simple_cycles(self._project_tree))

        circles = [_Circle(circle + [circle[0]]) for circle in circles]
        if circles:
            error_message = "Found the following circular dependencies:\n" + _textwrap.indent(
                    "\n".join("- " + str(circle) for circle in circles), prefix=" " * 3)
            self._logger.exception(error_message)
            raise RuntimeError(self.log_message(error_message))

    def build(
        self,
        build_all: bool = False,
        target_list: _Optional[list] = None,
        number_of_threads: _Optional[int] = None,
    ):
        """Build targets of this project.

        By default, this function builds all targets in this project as well
        as all their dependencies. This function will configure all targets
        that haven't been configured in a previous call.

        Parameters
        ----------
        build_all : bool
            If set to true, will not only build all targets in this project
            and their dependencies, but also all targets of all sub-projects.
        target_list : list
            If given, will build all targets in this project that are in the
            given list, as well as all their dependencies.
        number_of_threads : int
            If given will compile targets with the given number of threads. Otherwise
            it will use the default number of CPU cores visible to Python.

        """
        # Get targets to build
        targets_to_build = self._get_targets_to_build(build_all, target_list)

        # Sort targets in build order
        target_build_description_list = [
            target
            for target in reversed(list(_nx.topological_sort(self._project_tree)))
            if target in targets_to_build
            and not isinstance(self._project_tree.nodes[target]["data"], Project)
        ]

        # Get project sources, if any
        project_build_list = []
        for target_description in target_build_description_list:
            for predecessor in self._project_tree.predecessors(target_description):
                if isinstance(predecessor, Project):
                    project_build_list.append(predecessor)
        project_build_list = list(dict.fromkeys(project_build_list))
        for project in project_build_list:
            project.get_sources()

        for target in target_build_description_list:
            parent_project = next(self._project_tree.predecessors(target))
            target.parent_directory = parent_project._directory
            target.parent_build_directory = parent_project._build_directory

        ### Note: the project_tree needs to be updated directly for dependencies
        ### to be used correctly in the `_target_from_description` function
        target_build_list = []
        for target in target_build_description_list:
            if isinstance(target, _TargetDescription):
                target_instance = self._target_from_description(
                        self._project_tree.nodes[target]["data"]#, self._project_tree
                    )
                target_build_list.append(target_instance)
                self._project_tree.nodes[target]["data"] = target_instance
            else:
                target_build_list.append(target)

        if not target_build_list:
            self._logger.info("No targets to be built")

        # Compile
        with _Pool(processes=number_of_threads) as process_pool:
            for target in target_build_list:
                target.compile(process_pool, False)

        # Link
        for target in target_build_list:
            target.link()

        # Bundle
        if self._environment.bundle:
            with _Pool(processes=number_of_threads) as process_pool:
                for target in target_build_list:
                    target.bundle()

        # Redistributable bundle
        if self._environment.redistributable:
            with _Pool(processes=number_of_threads) as process_pool:
                for target in target_build_list:
                    target.redistributable()

    def _get_targets_to_build(
        self, build_all: bool = False, target_list: _Optional[list] = None
    ):
        """Return the list of targets to configure.

        This helper function is part of the initialisation of a project.
        Depending on the settings passed to clang build, not all targets
        will be configured. This function returns the list of only those
        targets that were selected and those targets that are dependencies
        of the selected ones.
        """
        if build_all:
            build_descendants_of = [self]
            _LOGGER.info("Building all targets...")
            if target_list:
                error_message = f"Cannot build [all] targets and only [{target_list}]!"
                _LOGGER.error(error_message)
                raise ValueError(error_message)
        elif target_list:
            build_descendants_of = target_list
        else:
            build_descendants_of = self._current_targets

        targets_to_build = set().union(
            set(build_descendants_of),
            *[
                set(
                    _nx.get_node_attributes(
                        self._project_tree.subgraph(
                            _nx.descendants(self._project_tree, target)
                        ),
                        "data",
                    ).values()
                )
                for target in build_descendants_of
            ]
        )

        return [
            target
            for target in targets_to_build
            if not isinstance(self._project_tree.nodes[target]["data"], Project)
        ]

    def _identifier_from_name(self, target_name: str) -> str:
        """Convert a name into an identifier.

        This works only if the name is defined for this project. If the
        target name is from a subproject, the method of the sub-project
        has to be called.

        Parameters
        ----------
        target_name : str
            The target name of the target for which to get the identifier.
            Has to be a target of this project.

        """
        prefix = f"{self.identifier}." if self.identifier else ""

        return f"{prefix}{target_name}"

    def _set_directories(self):
        """Set the build file output directory.

        This helper function is part of the initialisation of a project.
        It determines the build output directory which depends on if there
        are subprojects and more than one target. If that is the case, all
        output files will be in a hirarchical structure identical to the
        project tree structure. Else, the output for a trivial project will
        be directly in the build directory.
        """
        self._build_directory = self.environment.build_directory
        if self.parent:
            self._build_directory = self.parent.build_directory / self.name
        if self._config.get("url", None):
            self._directory = self.build_directory / "external_sources" / str(self._config.get("directory", ""))

    def _set_name(self, name=""):
        """Set the name.

        This helper function is part of the initialisation of a project.
        It will try to load the name from the config. If it cannot find it
        it will make sure that not having a name is allowed which is only
        the case if:

        - This project is not a sub-project and
        - This project does not have any sub-projects
        """
        self._name = name

        if not self.name:
            if self.parent:
                error_message = self.parent.log_message(
                    f"the config defines a subproject in folder {self.directory},"
                    + " that does not specify a name. It is not allowed to add a"
                    + " subproject that does not have a name."
                )

                self._logger.exception(error_message)
                raise RuntimeError(error_message)

            if "subprojects" in self.config:
                error_message = self.log_message(
                    "defining a top-level project with subprojects but without a name"
                    + " is illegal."
                )

                self._logger.exception(error_message)
                raise RuntimeError(error_message)

            self._name = "project"

    def _get_dependencies(self, target_description):
        dependencies = [
            self._project_tree.nodes()[dependency]["data"]
            for dependency in self._project_tree.successors(target_description)
        ]

        # Are there executables named as dependencies?
        executable_dependencies = [
            target for target in dependencies if isinstance(target, _Executable)
        ]
        if executable_dependencies:
            exelist = ", ".join([f"[{dep.name}]" for dep in executable_dependencies])
            error_message = target_description.log_message(
                f"The following targets are linking dependencies but were identified as executables:\n    {exelist}"
            )
            self._logger.error(error_message)
            raise RuntimeError(error_message)

        return dependencies

    def _target_from_description(self, target_description):
        """Return the appropriate target given the target description.

        A target type can either be speicified in the ``target_description.config``
        or a target is determined based on which files are found on the hard disk.
        If only header files are found, a header-only target is assumed. Else,
        an executable target will be generated.

        Targets need to be built from a bottom-up traversal of the project tree so
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

        dependencies = self._get_dependencies(target_description)#, self._project_tree)

        # Sources
        target_description.get_sources()
        files = _get_sources_and_headers(
            target_description.name,
            self._environment.toolchain.platform,
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
                self._logger.exception(error_message)
                raise RuntimeError(error_message)

        # No target specified so must be executable or header only
        else:
            if not files["sourcefiles"]:
                target_description.log_message(
                    "no source files found. Creating header-only target."
                )
                return _HeaderOnly(target_description, files, dependencies)

            target_description.log_message(
                f'{len(files["sourcefiles"])} source file(s) found. Creating executable target.'
            )
            return _Executable(target_description, files, dependencies)

    def get_sources(self):
        """External sources, if present, will be downloaded to build_directory/external_sources.
        """
        url = self._config.get("url", None)
        if url:
            version = self._config.get("version", None)
            download_directory = self.build_directory / "external_sources"
            _git_download_sources(url, download_directory, self._logger, version, self._environment.clone_recursive)

            self._directory = download_directory / self._config.get("directory", "")