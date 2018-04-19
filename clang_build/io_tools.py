from glob import iglob as _iglob
from pathlib import Path as _Path

def _get_header_files(folder):
    headers = []
    for ext in ('*.hpp', '*.hxx', '*.h'):
        headers += [_Path(f) for f in _iglob(str(folder) + '/**/'+ext, recursive=True)]

    return headers

def _get_source_files(folder):
    sources = []
    for ext in ('*.cpp', '*.cxx', '*.c'):
        sources += [_Path(f) for f in _iglob(str(folder) + '/**/'+ext, recursive=True)]

    return sources

def get_sources_and_headers(target_options, working_directory, target_build_directory):
    output = {'headers': [], 'include_directories': [], 'sourcefiles': []}
    relative_includes = []
    relative_source_directories = []

    # TODO: maybe the output should also include the root dir, build dir and potentially download dir?
    # TODO: should warn when a specified directory does not exist!

    # Root directory of target source tree
    target_root = _Path(working_directory)

    if target_options.get('external', False):
        target_root = target_root.joinpath(target_build_directory, 'external_sources')

    if 'directory' in target_options:
        target_root = target_root.joinpath(target_options['directory'])

    if 'sources' in target_options:
        sourcenode = target_options['sources']

        if 'include_directories' in sourcenode:
            relative_includes = [_Path(file) for file in sourcenode['include_directories']]

        if 'source_directories' in sourcenode:
            relative_source_directories = [_Path(file) for file in sourcenode['source_directories']]


    # Some defaults if nothing was specified
    if not relative_includes:
        relative_includes = [_Path(''), _Path('include'), _Path('thirdparty')]

    if not relative_source_directories:
        relative_source_directories = [_Path(''), _Path('src')]

    # Find headers
    output['include_directories'] = list(set(working_directory.joinpath(target_root, file) for file in relative_includes))

    for directory in output['include_directories']:
        output['headers'] += _get_header_files(directory)

    output['headers'] = list(set(output['headers']))
    # Find source files
    source_directories = list(set(working_directory.joinpath(target_root, file) for file in relative_source_directories))

    for directory in set(source_directories):
        output['sourcefiles'] += _get_source_files(directory)

    output['sourcefiles'] = list(set(output['sourcefiles']))

    return output