from glob import iglob as _iglob
from pathlib import Path as _Path

from . import platform as _platform

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
    output = {'headers': [], 'include_directories': [], 'include_directories_public': [], 'sourcefiles': []}

    # TODO: maybe the output should also include the root dir, build dir and potentially download dir?
    # TODO: should warn when a specified directory does not exist!

    # Options for include directories
    include_options = []
    include_options += target_options.get('include_directories', [])

    if 'osx' in target_options and _platform.PLATFORM == 'osx':
        include_options += target_options['osx'].get('include_directories', [])
    if 'windows' in target_options and _platform.PLATFORM == 'windows':
        include_options += target_options['windows'].get('include_directories', [])
    if 'linux' in target_options and _platform.PLATFORM == 'linux':
        include_options += target_options['linux'].get('include_directories', [])

    exclude_options = []
    exclude_options += target_options.get('headers_exclude', [])

    if 'osx' in target_options and _platform.PLATFORM == 'osx':
        exclude_options += target_options['osx'].get('headers_exclude', [])
    if 'windows' in target_options and _platform.PLATFORM == 'windows':
        exclude_options += target_options['windows'].get('headers_exclude', [])
    if 'linux' in target_options and _platform.PLATFORM == 'linux':
        exclude_options += target_options['linux'].get('headers_exclude', [])

    include_patterns = list(set([target_root_directory.joinpath(path) for path in include_options]))
    exclude_patterns = list(set([target_root_directory.joinpath(path) for path in exclude_options]))

    # Find header files
    if include_patterns:
        output['include_directories'] = include_patterns
        output['headers'] += _get_header_files_in_folders(output['include_directories'], exclude_patterns=exclude_patterns, recursive=True)
    else:
        output['include_directories'] += [target_root_directory.joinpath(''), target_root_directory.joinpath('include'), target_root_directory.joinpath('thirdparty')]
        output['headers'] += _get_header_files_in_folders(output['include_directories'], exclude_patterns=exclude_patterns, recursive=False)

    # Options for public include directories
    include_options_public = []
    include_options_public += target_options.get('include_directories_public', [])

    if 'osx' in target_options and _platform.PLATFORM == 'osx':
        include_options_public += target_options['osx'].get('include_directories_public', [])
    if 'windows' in target_options and _platform.PLATFORM == 'windows':
        include_options_public += target_options['windows'].get('include_directories_public', [])
    if 'linux' in target_options and _platform.PLATFORM == 'linux':
        include_options_public += target_options['linux'].get('include_directories_public', [])

    exclude_options = []
    exclude_options += target_options.get('headers_exclude', [])

    if 'osx' in target_options and _platform.PLATFORM == 'osx':
        exclude_options += target_options['osx'].get('headers_exclude', [])
    if 'windows' in target_options and _platform.PLATFORM == 'windows':
        exclude_options += target_options['windows'].get('headers_exclude', [])
    if 'linux' in target_options and _platform.PLATFORM == 'linux':
        exclude_options += target_options['linux'].get('headers_exclude', [])

    include_patterns = list(set([target_root_directory.joinpath(path) for path in include_options_public]))
    exclude_patterns = list(set([target_root_directory.joinpath(path) for path in exclude_options]))

    # Find header files
    if include_patterns:
        output['include_directories_public'] = include_patterns
        output['headers'] += _get_header_files_in_folders(output['include_directories_public'], exclude_patterns=exclude_patterns, recursive=True)
    else:
        output['include_directories_public'] += [target_root_directory.joinpath(''), target_root_directory.joinpath('include')]
        output['headers'] += _get_header_files_in_folders(output['include_directories_public'], exclude_patterns=exclude_patterns, recursive=False)

    # Options for sources
    sources_options = []
    sources_options += target_options.get('sources', [])

    if 'osx' in target_options and _platform.PLATFORM == 'osx':
        sources_options += target_options['osx'].get('sources', [])
    if 'windows' in target_options and _platform.PLATFORM == 'windows':
        sources_options += target_options['windows'].get('sources', [])
    if 'linux' in target_options and _platform.PLATFORM == 'linux':
        sources_options += target_options['linux'].get('sources', [])

    exclude_options = []
    exclude_options += target_options.get('sources_exclude', [])

    if 'osx' in target_options and _platform.PLATFORM == 'osx':
        exclude_options += target_options['osx'].get('sources_exclude', [])
    if 'windows' in target_options and _platform.PLATFORM == 'windows':
        exclude_options += target_options['windows'].get('sources_exclude', [])
    if 'linux' in target_options and _platform.PLATFORM == 'linux':
        exclude_options += target_options['linux'].get('sources_exclude', [])

    sources_patterns = list(set([target_root_directory.joinpath(path) for path in sources_options]))
    exclude_patterns = list(set([target_root_directory.joinpath(path) for path in exclude_options]))

    # Find source files from patterns
    if sources_patterns:
        output['sourcefiles'] += _get_files_in_patterns(sources_patterns, exclude_patterns=exclude_patterns, recursive=True)
    # Else find source files from src folder
    else:
        output['sourcefiles'] += _get_source_files_in_folders([target_root_directory.joinpath('src')], exclude_patterns=exclude_patterns, recursive=True)

    # Search the root folder as last resort
    if not output['sourcefiles']:
        output['sourcefiles'] += _get_source_files_in_folders([target_root_directory], exclude_patterns=exclude_patterns, recursive=False)

    # Fill return dict
    output['include_directories']        = list(set( output['include_directories'] ))
    output['include_directories_public'] = list(set( output['include_directories_public'] ))
    output['headers']                    = list(set( output['headers'] ))
    output['sourcefiles']                = list(set( output['sourcefiles'] ))

    return output