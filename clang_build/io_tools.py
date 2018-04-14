from glob import iglob as _iglob
from pathlib2 import Path as _Path

def _get_header_files(folder):
    headers = []
    for ext in ('*.hpp', '*.hxx'):
        headers += [_Path(f) for f in _iglob(str(folder) + '/**/'+ext, recursive=True)]

    return headers

def _get_source_files(folder):
    sources = []
    for ext in ('*.cpp', '*.cxx'):
        sources += [_Path(f) for f in _iglob(str(folder) + '/**/'+ext, recursive=True)]

    return sources

def get_sources_and_headers(project, target_directory):
    output = {'headers': [], 'include_directories': [], 'sourcefiles': []}
    root = _Path('')
    relative_includes = []
    relative_source_directories = []
    if 'sources' in project:
        sourcenode = project['sources']

        if 'root' in sourcenode:
            root = _Path(sourcenode['root'])

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
    output['include_directories'] = list(set(target_directory.joinpath(root, file) for file in relative_includes))

    for directory in output['include_directories']:
        output['headers'] += _get_header_files(directory)

    output['headers'] = list(set(output['headers']))
    # Find source files
    source_directories = list(set(target_directory.joinpath(root, file) for file in relative_source_directories))

    for directory in set(source_directories):
        output['sourcefiles'] += _get_source_files(directory)

    output['sourcefiles'] = list(set(output['sourcefiles']))

    return output