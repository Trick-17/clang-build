"""Module for source file discovery and include directories."""

from itertools import chain as _chain


def _get_files_from_folders(
    directories, extensions, target_directory, exclude_patterns, recursive
):
    """Get files from a given list of directories.

    Parameters
    ----------
    directories : iterable
        set of directories to browse for files
    extensions : iterable
        list of file extensions to search for
    target_directory : pathlib.Path
        the directory of the target for which to search files for
    exclude_patterns : iterable
        list of patterns specifying which files not to include
        (relative to the target directory)
    recursive : bool
        whether to search for files recursively

    Returns
    -------
    set of pathlib.Path
        the files discovered

    """
    delimiter = "**/" if recursive else ""
    patterns = [delimiter + ext for ext in extensions]

    return _get_files_from_patterns(patterns, directories) - _get_files_from_patterns(
        exclude_patterns, [target_directory]
    )


def _get_header_files_in_folders(
    directories, target_directory, exclude_patterns, recursive
):
    """Get header files from a given list of directories.

    The extensions used to find these files are:

     - *.hpp
     - *.hxx
     - *.h

    Parameters
    ----------
    directories : iterable
        set of directories to browse for files
    target_directory : pathlib.Path
        the directory of the target for which to search files for
    exclude_patterns : iterable
        list of patterns specifying which files not to include
        (relative to the target directory)
    recursive : bool
        whether to search for files recursively

    Returns
    -------
    set of pathlib.Path
        the header files discovered

    """
    return _get_files_from_folders(
        directories,
        ("*.hpp", "*.hxx", "*.h"),
        target_directory,
        exclude_patterns,
        recursive,
    )


def _get_source_files_in_folders(
    directories, target_directory, exclude_patterns, recursive
):
    """Get source files from a given list of directories.

    The extensions used to find these files are:

     - *.cpp
     - *.cxx
     - *.c

    Parameters
    ----------
    directories : iterable
        set of directories to browse for files
    target_directory : pathlib.Path
        the directory of the target for which to search files for
    exclude_patterns : list
        list of patterns specifying which files not to include
        (relative to the target directory)
    recursive : bool
        whether to search for files recursively

    Returns
    -------
    set of pathlib.Path
        the source files discovered

    """
    return _get_files_from_folders(
        directories,
        ("*.cpp", "*.cxx", "*.c"),
        target_directory,
        exclude_patterns,
        recursive,
    )


def _get_files_from_patterns(patterns, directories):
    """Get files from given patterns for given directories.

    Each pattern is passed to to the :any:`pathlib.Path.glob`
    function of each given directory and all files are accumulated
    in a set.

    Parameters
    ----------
    patterns: iterables
        patterns to pass to `pathlib.Path.glob`.
    directories: list of pathlib.Path
        directories in which to glob for files

    Returns
    -------
    set of pathlib.Path
        the files discovered

    """
    return set(
        _chain(
            *tuple(directory.glob(pattern) for pattern in patterns for directory in directories)
        )
    )


def _get_global_and_platform_option(target_config, key, platform):
    """Check a target dictionary for global and platform specific options.

    As include directory for example might be platform specific,
    this function looks into a target configuration and returns both,
    the global and the platform specific configuration for a given key.

    Parameters
    ----------
    target_config : dict
        configuration dict of a target
    key : str
        the key to look up in the dict
    platform : str
        the platform for which to get the configuration

    Returns
    -------
    set
        all found options
    """
    option = set(target_config.get(key, []))
    option.update(target_config.get(platform, {}).get(key, []))

    return option


def _existing_directories(relative_folders, target_root_directory):
    """Return absolute paths of all given folders which exist.

    Parameters
    ----------
    relative_folders : iterable
        folders to check
    target_root_directory : pathlib.Path
        target root path the relative folders are referring to

    Returns
    -------
    set
        all existing folders as absolute paths

    """
    directories = {
        path
        for folder in relative_folders
        if (path := (target_root_directory / folder).resolve()).is_dir()
    }

    return directories


def get_sources_and_headers(
    target_name,
    platform,
    target_config,
    target_root_directory
):
    """Get sources, headers, and include folders (public and private) of a target.

    Parameters
    ----------
    target_name : str
        name of the target for which to obtain files
    platform : str
        the platform for which to build
    target_config : dict
        the configuration dict of the target
    target_root_directory : pathlib.Path
        the directory of the project that owns this target

    Returns
    -------
    dict
        With keys "headers", "include_directories", "public_include_directories", and
        "sourcefiles" and lists as values

    """
    output = {
        "headers": set(),
        "include_directories": set(),
        "public_include_directories": set(),
        "sourcefiles": set(),
    }

    # TODO: maybe the output should also include the root dir, build dir and potentially download dir?
    # TODO: should warn when a specified directory does not exist!

    # Behaviour of the search lateron depends on whether there is a dedicated target directory
    if (
        in_project_root := not (
            target_root_directory := (target_root_directory / target_name).resolve()
        ).is_dir()
    ) :
        target_root_directory = target_root_directory

    # Options for include directories
    custom_include_directories = _existing_directories(
        _get_global_and_platform_option(target_config, "include_directories", platform),
        target_root_directory,
    )

    exclude_patterns_headers = _get_global_and_platform_option(
        target_config, "headers_exclude", platform
    )

    # Find header files
    if custom_include_directories:
        include_directories = custom_include_directories
        recursive = True
    else:
        if (include_folder := (target_root_directory / "include").resolve()).exists():
            include_directories = {include_folder}
            recursive = True
        else:
            include_directories = {target_root_directory}
            recursive = not in_project_root

    output["include_directories"] |= include_directories
    output["headers"] |= _get_header_files_in_folders(
        include_directories,
        target_root_directory,
        exclude_patterns_headers,
        recursive=recursive,
    )

    # Options for public include directories, exclude patterns are the same
    custom_include_directories_public = _existing_directories(
        _get_global_and_platform_option(
            target_config, "public_include_directories", platform
        ),
        target_root_directory,
    )

    # Find header files for public directories, no default paths for public dirs
    if custom_include_directories_public:
        output["public_include_directories"] |= custom_include_directories_public
        output["headers"] |= _get_header_files_in_folders(
            custom_include_directories_public,
            target_root_directory,
            exclude_patterns=exclude_patterns_headers,
            recursive=True,
        )

    # Options for sources
    sources_patterns = _get_global_and_platform_option(
        target_config, "sources", platform
    )
    exclude_patterns = _get_global_and_platform_option(
        target_config, "sources_exclude", platform
    )

    # Find source files from patterns (recursivity specified by patterns)
    if sources_patterns:
        output["sourcefiles"] |= _get_files_from_patterns(
            sources_patterns, [target_root_directory]
        ) - _get_files_from_patterns(exclude_patterns, [target_root_directory])

    # Else search source files in folder with same name as target and src folder
    else:
        if (src_folder := (target_root_directory / "src").resolve()).exists():
            source = {src_folder}
            recursive = True

        else:
            source = {target_root_directory}
            recursive = not in_project_root

        output["sourcefiles"] |= _get_source_files_in_folders(
            source,
            target_root_directory,
            exclude_patterns,
            recursive=recursive,
        )

    return {key: list(val) for key, val in output.items()}
