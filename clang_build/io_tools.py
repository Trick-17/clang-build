from glob import iglob as _iglob
from pathlib import Path as _Path

from . import platform as _platform
from .build_type import BuildType as _BuildType

# Parse compile and link flags of any kind ('flags', 'interface-flags', ...)
def parse_flags_options(options, build_type, flags_kind='flags'):
    flags_dicts   = []
    compile_flags = []
    link_flags    = []

    flags_dicts.append(options.get(flags_kind, {}))

    flags_dicts.append(options.get(_platform.PLATFORM, {}).get(flags_kind, {}))

    for fdict in flags_dicts:
        compile_flags += fdict.get('compile', [])
        link_flags    += fdict.get('link', [])

    if build_type != _BuildType.Default:
        compile_flags += fdict.get(f'compile_{build_type}', [])

    return compile_flags, link_flags

def _get_header_files_in_folders(folders, exclude_patterns=[], recursive=True):
    delimiter = '/**/' if recursive else '/'
    full_folders_patterns = [str(pattern) + delimiter + ext for ext in ('*.hpp', '*.hxx', '*.h') for pattern in folders]
    return _get_files_in_patterns(full_folders_patterns, exclude_patterns=exclude_patterns, recursive=recursive)

def _get_source_files_in_folders(folders, exclude_patterns=[], recursive=True):
    delimiter = '/**/' if recursive else '/'
    full_folders_patterns = [str(pattern) + delimiter + ext for ext in ('*.cpp', '*.cxx', '*.c') for pattern in folders]
    return _get_files_in_patterns(full_folders_patterns, exclude_patterns=exclude_patterns, recursive=recursive)

def _get_files_in_patterns(patterns, exclude_patterns=[], recursive=True):
    included = [_Path(f).resolve() for pattern in patterns         for f in _iglob(str(pattern), recursive=recursive) if _Path(f).is_file()]
    excluded = [_Path(f).resolve() for pattern in exclude_patterns for f in _iglob(str(pattern), recursive=recursive) if _Path(f)]
    return list(set(included) - set(excluded))

def get_sources_and_headers(target_name, target_options, target_root_directory, target_build_directory):
    output = {'headers': [], 'include_directories': [], 'include_directories_public': [], 'sourcefiles': []}

    # TODO: maybe the output should also include the root dir, build dir and potentially download dir?
    # TODO: should warn when a specified directory does not exist!

    # Options for include directories
    include_options = []
    include_options += target_options.get('include_directories', [])

    include_options += target_options.get(_platform.PLATFORM, {}).get('include_directories', [])

    exclude_options = []
    exclude_options += target_options.get('headers_exclude', [])

    exclude_options += target_options.get(_platform.PLATFORM, {}).get('headers_exclude', [])

    include_patterns = list(set(target_root_directory.joinpath(path) for path in include_options))
    exclude_patterns = list(set(target_root_directory.joinpath(path) for path in exclude_options))

    # Find header files
    if include_patterns:
        output['include_directories'] = include_patterns
        output['headers'] += _get_header_files_in_folders(output['include_directories'], exclude_patterns=exclude_patterns, recursive=True)
    else:
        output['include_directories'] += [target_root_directory.joinpath(''), target_root_directory.joinpath('include'),
                                        target_root_directory.joinpath(target_name)]
        output['headers'] += _get_header_files_in_folders(output['include_directories'], exclude_patterns=exclude_patterns, recursive=False)

    # Options for public include directories, exclude patterns are the same
    include_options_public = []
    include_options_public += target_options.get('include_directories_public', [])

    include_options_public += target_options.get(_platform.PLATFORM, {}).get('include_directories_public', [])

    include_patterns = list(dict.fromkeys(target_root_directory.joinpath(path) for path in include_options_public))
    exclude_patterns = list(dict.fromkeys(target_root_directory.joinpath(path) for path in exclude_options))

    # Find header files
    if include_patterns:
        output['include_directories_public'] = include_patterns
        output['headers'] += _get_header_files_in_folders(output['include_directories_public'], exclude_patterns=exclude_patterns, recursive=True)
    else:
        output['include_directories_public'] += [target_root_directory.joinpath(''), target_root_directory.joinpath('include'),
                                                target_root_directory.joinpath(target_name, 'include')]
        output['headers'] += _get_header_files_in_folders(output['include_directories_public'], exclude_patterns=exclude_patterns, recursive=False)

    # Keep only include directories which exist
    output['include_directories'] = [directory for directory in output['include_directories'] if directory.exists()]
    output['include_directories_public'] = [directory for directory in output['include_directories_public'] if directory.exists()]

    # Options for sources
    sources_options = []
    sources_options += target_options.get('sources', [])

    sources_options += target_options.get(_platform.PLATFORM, {}).get('sources', [])

    exclude_options = []
    exclude_options += target_options.get('sources_exclude', [])

    exclude_options += target_options.get(_platform.PLATFORM, {}).get('sources_exclude', [])

    sources_patterns = list(dict.fromkeys(target_root_directory.joinpath(path) for path in sources_options))
    exclude_patterns = list(dict.fromkeys(target_root_directory.joinpath(path) for path in exclude_options))

    # Find source files from patterns (recursively)
    if sources_patterns:
        output['sourcefiles'] += _get_files_in_patterns(sources_patterns, exclude_patterns=exclude_patterns, recursive=True)
    # Else search source files in folder with same name as target and src folder (recursively)
    else:
        output['sourcefiles'] += _get_source_files_in_folders([target_root_directory.joinpath(target_name), target_root_directory.joinpath('src')], exclude_patterns=exclude_patterns, recursive=True)

    # Search the root folder as last resort (non-recursively)
    if not output['sourcefiles']:
        output['sourcefiles'] += _get_source_files_in_folders([target_root_directory], exclude_patterns=exclude_patterns, recursive=False)

    # Fill return dict
    output['include_directories']        = list(dict.fromkeys( output['include_directories'] ))
    output['include_directories_public'] = list(dict.fromkeys( output['include_directories_public'] ))
    output['headers']                    = list(dict.fromkeys( output['headers'] ))
    output['sourcefiles']                = list(dict.fromkeys( output['sourcefiles'] ))

    return output