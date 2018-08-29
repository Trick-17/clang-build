from glob import iglob as _iglob
from pathlib import Path as _Path

def _get_header_files(folder, excludes=None, recursive=True):
    headers = []
    for ext in ('*.hpp', '*.hxx', '*.h'):
        h1 = [_Path(f) for f in _iglob(str(folder) + '/**/'+ext, recursive=recursive)]
        h2 = []
        if excludes:
            for exclude in excludes:
                h2 = [_Path(f) for f in _iglob(str(exclude) + '/**/'+ext, recursive=recursive)]
        headers += set(h1) - set(h2)

    return headers

def _get_source_files(folder, excludes=None, recursive=True):
    sources = []
    if recursive:
        for ext in ('*.cpp', '*.cxx', '*.c'):
            s1 = [_Path(f) for f in _iglob(str(folder) + '/**/'+ext, recursive=recursive)]
            s2 = []
            if excludes:
                for exclude in excludes:
                    s2 += [_Path(f) for f in _iglob(str(exclude) + '/**/'+ext, recursive=recursive)]
            sources += set(s1) - set(s2)
    else:
        for ext in ('*.cpp', '*.cxx', '*.c'):
            s1 = [_Path(f) for f in _iglob(str(folder) + '/*'+ext, recursive=recursive)]
            s2 = []
            if excludes:
                for exclude in excludes:
                    s2 += [_Path(f) for f in _iglob(str(exclude) + '/*'+ext, recursive=recursive)]
            sources += set(s1) - set(s2)

    return sources

def get_sources_and_headers(target_options, target_root_directory, target_build_directory):
    output = {'headers': [], 'include_directories': [], 'sourcefiles': []}
    relative_includes = []
    relative_source_directories = []

    # TODO: maybe the output should also include the root dir, build dir and potentially download dir?
    # TODO: should warn when a specified directory does not exist!

    # Find source files
    headers_specified = False
    excludes = []
    if 'sources' in target_options:
        sourcenode = target_options['sources']
        excludes = sourcenode.get('include_exclude', [])
        if 'include_directories' in sourcenode:
            headers_specified = True
            output['include_directories'] += list(set(target_root_directory.joinpath(path) for path in sourcenode['include_directories']))
            for directory in output['include_directories']:
                output['headers'] += _get_header_files(directory, excludes=[target_root_directory.joinpath(path) for path in excludes], recursive=True)
    if not headers_specified:
        output['include_directories'] += [target_root_directory.joinpath(''), target_root_directory.joinpath('include'), target_root_directory.joinpath('thirdparty')]
        for directory in output['include_directories']:
            output['headers'] += _get_header_files(target_root_directory.joinpath(directory), excludes=[target_root_directory.joinpath(path) for path in excludes], recursive=False)



    sources_specified = False
    excludes = []
    if 'sources' in target_options:
        sourcenode = target_options['sources']
        excludes = sourcenode.get('source_exclude', [])
        if 'source_directories' in sourcenode:
            sources_specified = True
            for directory in list(set(target_root_directory.joinpath(path) for path in sourcenode['source_directories'])):
                output['sourcefiles'] += _get_source_files(directory, excludes=[target_root_directory.joinpath(path) for path in excludes], recursive=True)
    if not sources_specified:
        output['sourcefiles'] += _get_source_files(target_root_directory.joinpath('src'), excludes=[target_root_directory.joinpath(path) for path in excludes], recursive=True)
    if not output['sourcefiles']:
        output['sourcefiles'] += _get_source_files(target_root_directory, excludes=[target_root_directory.joinpath(path) for path in excludes], recursive=False)

    output['include_directories'] = list(set(output['include_directories']))
    output['headers']             = list(set(output['headers']))
    output['sourcefiles']         = list(set(output['sourcefiles']))

    return output