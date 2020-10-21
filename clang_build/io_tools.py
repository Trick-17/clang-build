from glob import iglob as _iglob
from pathlib import Path as _Path

def _get_header_files_in_folders(folders, exclude_patterns=[], recursive=True):
    delimiter = '/**/' if recursive else '/*'
    patterns  = [str(folder) + delimiter + ext for ext in ('*.hpp', '*.hxx', '*.h') for folder in folders]
    return _get_files_in_patterns(patterns)

def _get_source_files_in_folders(folders, exclude_patterns=[], recursive=True):
    delimiter = '/**/' if recursive else '/*'
    patterns  = [str(folder) + delimiter + ext for ext in ('*.cpp', '*.cxx', '*.c') for folder in folders]
    return _get_files_in_patterns(patterns)

def _get_files_in_patterns(patterns, exclude_patterns=[], recursive=True):
    included = [_Path(f) for pattern in patterns         for f in _iglob(str(pattern), recursive=recursive) if _Path(f).is_file()]
    excluded = [_Path(f) for pattern in exclude_patterns for f in _iglob(str(pattern), recursive=recursive) if _Path(f).is_file()]
    return list(f.resolve() for f in (set(included) - set(excluded)))

def get_sources_and_headers(target_name, platform, target_options, target_root_directory, target_build_directory):
    output = {'headers': [], 'include_directories': [], 'include_directories_public': [], 'sourcefiles': []}

    # TODO: maybe the output should also include the root dir, build dir and potentially download dir?
    # TODO: should warn when a specified directory does not exist!

    # Options for include directories
    include_options = []
    include_options += target_options.get('include_directories', [])

    include_options += target_options.get(platform, {}).get('include_directories', [])

    exclude_options = []
    exclude_options += target_options.get('headers_exclude', [])

    exclude_options += target_options.get(platform, {}).get('headers_exclude', [])

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

    include_options_public += target_options.get(platform, {}).get('include_directories_public', [])

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

    sources_options += target_options.get(platform, {}).get('sources', [])

    exclude_options = []
    exclude_options += target_options.get('sources_exclude', [])

    exclude_options += target_options.get(platform, {}).get('sources_exclude', [])

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
    output['include_directories']        = list(dict.fromkeys(output['include_directories'] ))
    output['include_directories_public'] = list(dict.fromkeys(output['include_directories_public'] ))
    output['headers']                    = list(dict.fromkeys(output['headers'] ))
    output['sourcefiles']                = list(dict.fromkeys(output['sourcefiles'] ))

    return output