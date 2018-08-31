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
    return list(set(included) - set(excluded))

def get_sources_and_headers(target_options, target_root_directory, target_build_directory):
    output = {'headers': [], 'include_directories': [], 'sourcefiles': []}

    # TODO: maybe the output should also include the root dir, build dir and potentially download dir?
    # TODO: should warn when a specified directory does not exist!

    # Find header files
    exclude_patterns = list(set( [target_root_directory.joinpath(path) for path in target_options.get('headers_exclude', [])] ))
    if 'include_directories' in target_options:
        output['include_directories'] += list(set(target_root_directory.joinpath(path) for path in target_options['include_directories'] ))
        output['headers'] += _get_header_files_in_folders(output['include_directories'], exclude_patterns=exclude_patterns, recursive=True)
    else:
        output['include_directories'] += [target_root_directory.joinpath(''), target_root_directory.joinpath('include'), target_root_directory.joinpath('thirdparty')]
        output['headers'] += _get_header_files_in_folders(output['include_directories'], exclude_patterns=exclude_patterns, recursive=False)

    # Find source files from patterns
    exclude_patterns = list(set( [target_root_directory.joinpath(path) for path in target_options.get('sources_exclude', [])] ))
    sources_patterns = list(set( [target_root_directory.joinpath(path) for path in target_options.get('sources', [])] ))
    output['sourcefiles'] += _get_files_in_patterns(sources_patterns, exclude_patterns=exclude_patterns, recursive=True)
    # Else find source files from src folder
    if not sources_patterns:
        output['sourcefiles'] += _get_source_files_in_folders([target_root_directory.joinpath('src')], exclude_patterns=exclude_patterns, recursive=True)
    # Search the root folder as last resort
    if not output['sourcefiles']:
        output['sourcefiles'] += _get_source_files_in_folders([target_root_directory], exclude_patterns=exclude_patterns, recursive=False)

    # Fill return dict
    output['include_directories'] = list(set( output['include_directories'] ))
    output['headers']             = list(set( output['headers'] ))
    output['sourcefiles']         = list(set( output['sourcefiles'] ))

    return output