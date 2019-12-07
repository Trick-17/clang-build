"""A class that contains potentially multiple targets and other projects."""

import logging as _logging
import os as _os
import subprocess as _subprocess
import tempfile as _tempfile
import textwrap as _textwrap
from pathlib import Path as _Path

import networkx as _nx
import toml

from .circle import Circle as _Circle
from .git_tools import checkout_version as _checkout_version
from .git_tools import clone_repository as _clone_repository
from .git_tools import needs_download as _needs_download
from .logging_tools import NamedLogger as _NamedLogger
from .progress_bar import IteratorProgress as _IteratorProgress
from .target import make_target as _make_target
from .tree_entry import TreeEntry as _TreeEntry

_LOGGER = _logging.getLogger("clang_build.clang_build")


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
        """Return the set of global settings.


        """
        return self._environment

    @property
    def identifier(self) -> str:
        """Return a unique identifier of this project.

        The unique identifier for a project can be:
        - An emtpy string if this is a basic project and no name was given
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

        All direct descendants of this project (subprojects only, no targets)
        are returned as a list.
        """
        return self._subprojects

    @property
    def target_list(self):
        """Return all targets that were configured and are part of this project.

        This list includes only those targets that were selected to be configured,
        and are also defined inside of this project.
        """
        return self._current_targets

    @property
    def target_list_all(self):
        """Return all targets that were configured.

        This list includes all targets, also dependencies that are not defined
        in this project.
        """
        return self._target_list

    def __init__(self, directory, environment, **kwargs):
        """Initialises a project.

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
        self._directory = _Path(directory)
        self._parent = kwargs.get("parent", None)
        self._environment = environment

        self._set_project_tree()
        self._load_config()
        self._set_name()

        self._subprojects = [
            Project(configuration["directory"], environment, parent=self)
            for configuration in self.config.get("subproject", [])
        ]

        self._fill_dependency_tree()
        self._set_build_directory()

        if not self.parent:
            self._check_for_circular_dependencies()

            targets_to_build = self._get_targets_to_build()

            targets_not_to_build = [
                x
                for x in self.project_tree
                if x not in targets_to_build and not isinstance(x, Project)
            ]

            self.project_tree.remove_nodes_from(targets_not_to_build)
            self._current_targets = [
                target for target in self._current_targets if target in targets_to_build
            ]

            if targets_not_to_build:
                _LOGGER.info(
                    f'Not building target(s) [{"], [".join(targets_not_to_build)}].'
                )

            _target_build_list = [
                target
                for target in reversed(list(_nx.topological_sort(self.project_tree)))
                if target in targets_to_build
            ]

            # Generate the list of target instances
            self._target_list = []
            for target_description in _IteratorProgress(
                _target_build_list,
                environment.progress_disabled,
                len(_target_build_list),
            ):
                target = _make_target(target_description, self.project_tree)
                _nx.relabel_nodes(
                    self.project_tree, {target_description: target}, copy=False
                )
                self._target_list.append(target)

    def _check_for_circular_dependencies(self):
        """Check if targets are defined in a circular dependency.

        Raises an exception if circular dependencies were found pointing
        out where the circular dependencies were found.
        """
        circles = list(_nx.simple_cycles(self.project_tree))

        circles = [_Circle(circle + [circle[-1]]) for circle in circles]
        if circles:
            error_message = self.log_message(
                "Found the following circular dependencies:\n"
                + _textwrap.indent(
                    "\n".join("- " + str(circle) for circle in circles), prefix=" " * 3
                )
            )
            _LOGGER.exception(error_message)
            raise RuntimeError(error_message)

    def _fill_dependency_tree(self):
        """Integrate this project into the global project tree.

        This helper function is part of the initialisation of a project.
        It adds this project, all targets and their dependencies to the
        global project tree. If there are illegal dependencies, this function
        will raise an exception.
        """
        # add self
        self.project_tree.add_node(self)

        # add edges to subprojects
        self.project_tree.add_edges_from(
            (self, sub_project) for sub_project in self.subprojects
        )

        # add targets defined in project and edges for these
        self._current_targets = [
            TargetDescription(
                key, val, self._identifier_from_name(key), self, self.environment
            )
            for key, val in self.config.items()
            if key != "subproject" and isinstance(val, dict)
        ]
        self.project_tree.add_nodes_from(self._current_targets)
        self.project_tree.add_edges_from(
            (self, target) for target in self._current_targets
        )

        # add edges for dependencies in targets defined in project
        for target in self._current_targets:
            dependencies = target.config.get("dependencies", [])
            dependency_objs = []
            for dependency_name in dependencies:
                full_name = self._identifier_from_name(dependency_name)
                try:
                    dependency = self._project_tree[full_name]
                except KeyError:
                    error_message = target.log_message(
                        f"the dependency [{dependency_name}] does not point to a valid target."
                    )
                    _LOGGER.exception(error_message)
                    raise RuntimeError(error_message)

                dependency_objs.append(target)
                self._project_tree.add_edge(target, dependency)

            target.config["dependencies"] = dependency_objs

    def _load_config(self):
        """Try to find a toml file and return a config.

        This helper function is part of the initialisation of a project.
        It searches for a toml file and (if it finds one) loads it. Otherwise
        it generates a default config.
        """
        toml_file = self.directory / "clang-build.toml"

        if toml_file.exists():
            _LOGGER.info("Found config file '%s'.", toml_file)
            self._config = toml.load(toml_file)

        elif self.parent:
            error_message = self.parent.log_message(
                f"the config defines a subproject in folder {self.directory},"
                + " that does not have a project file. It is not allowed to add a"
                + " subproject that does not have a project file."
            )

            _LOGGER.exception(error_message)
            raise RuntimeError(error_message)

        else:
            self._config = {"": {"output_name": "main"}}

    def _get_targets_to_build(self):
        """Return the list of targets to configure.

        This helper function is part of the initialisation of a project.
        Depending on the settings passed to clang build, not all targets
        will be configured. This function returns the list of only those
        targets that were selected and those targets that are dependencies
        of the selected ones.
        """
        if self.environment.build_all:
            targets_to_build = [
                target
                for target in self.project_tree
                if not isinstance(target, Project)
            ]

        elif self.environment.target_list:
            targets = [
                self.project_tree[
                    TargetDescription.identifier_to_tree_str(
                        self._identifier_from_name(target)
                    )
                ]
                for target in self.environment.target_list
            ]

            targets_to_build = set().union(
                *[
                    set(targets),
                    *[
                        x
                        for x in (
                            self.project_tree.descendants(target for target in targets)
                        )
                        if x
                    ],
                ]
            )

            _LOGGER.info(
                f'Only building targets [{"], [".join(self.environment.target_list)}]'
                + f' out of base set of targets [{"], [".join(target.name for target in self._current_targets)}].'
            )

        else:
            targets_to_build = set().union(
                *[
                    set(self._current_targets),
                    *[
                        _nx.descendants(self.project_tree, target)
                        for target in self._current_targets
                    ],
                ]
            )

        return targets_to_build

    def _identifier_from_name(self, target_name: str):
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

    def _set_build_directory(self):
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
        elif (
            "subproject" in self.config
            or len(
                [
                    target
                    for target in self.project_tree
                    if self.project_tree.out_degree(target) == 0
                ]
            )
            > 1
        ):
            self._build_directory /= self.name

    def _set_name(self):
        """Set the name.

        This helper function is part of the initialisation of a project.
        It will try to load the name from the config. If it cannot find it
        it will make sure that not having a name is allowed which is only
        the case if:

        - This project is not a sub-project and
        - This project does not have any sub-projects
        """
        self._name = str(self.config.get("name", ""))

        if not self.name:
            if self.parent:
                error_message = self.parent.log_message(
                    f"the config defines a subproject in folder {self.directory},"
                    + " that does not specify a name. It is not allowed to add a"
                    + " subproject that does not have a name."
                )

                _LOGGER.exception(error_message)
                raise RuntimeError(error_message)

            if "subproject" in self.config:
                error_message = self.log_message(
                    f"defining a top-level project with subprojects but without a name"
                    + " is illegal."
                )

                _LOGGER.exception(error_message)
                raise RuntimeError(error_message)

    def _set_project_tree(self):
        """Set the global project tree for this project.

        Takes it from its parent if the parent project exists.
        Else it creates one.
        """
        if self.parent:
            self._project_tree = self.parent.project_tree
        else:
            self._project_tree = _nx.DiGraph()


class TargetDescription(_NamedLogger, _TreeEntry):
    """A hollow Target used for dependency checking.

    Before Projects actually configure targets, they first
    make sure that all dependencies etc are correctly defined.
    For this initial step, these TargetDescriptions are used.
    This is also necessary, because some of the target properties
    like the build folder, depend on the entire project structure
    and thus the two step procedure is necessary.
    """

    @staticmethod
    def identifier_to_tree_str(identifier: str) -> str:
        """Convert an identifier to a tree key.

        Since :any:`networkx` cannot replace nodes with identical
        hash values, :any:`TargetDescription`s unfortunately must
        have a different label. This function provides this label.

        Returns
        -------
        str
            The identifier modified so that the TargetDescription object
            can be looked up in the project tree.

        """
        return identifier + "[repr]"

    def string_to_hash(self) -> str:
        """Return the string to hash.

        For the same reason described in :any:`identifier_to_tree_str`
        we do not simply use the :any:`__repr__()` function but this
        one, to make sure that the representation of this object is still
        readable for debugging purposes.
        """
        return TargetDescription.identifier_to_tree_str(self.identifier)

    def __init__(self, name: str, config: dict, identifier: str, parent, environment):
        """Generate a TargetDescription.

        Parameters
        ----------
        name: str
            The name of this target as it will also later be named
        config : dict
            The config for this target (e.g. read from a toml)
        identifier : str
            The full identifier for this target
        parent : Project
            The parent project of this target

        """
        if "." in name:
            error_message = self.log_message(
                f"Name contains illegal character '.': {name}"
            )
            _LOGGER.exception(error_message)
            raise RuntimeError(error_message)

        self.name = name
        self.identifier = identifier
        self.config = config
        self.parent = parent
        self.environment = environment

    @property
    def target_root_directory(self):
        """Return the root directory of this target.

        Each target has a root directory from which files are searched
        etc.
        """
        return self.parent.directory.joinpath(self.config.get("directory", ""))

    @property
    def target_build_directory(self):
        """Return the target build directory.

        Returns the build directory into which the output of all
        files are put.
        """
        return self.parent.build_directory.joinpath(self.name).joinpath(
            self.environment.build_type.name.lower()
        )

