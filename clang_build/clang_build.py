'''
clang-build:
  TODO: module docstring...
'''



import os as _os
import logging as _logging
from pathlib2 import Path as _Path
import textwrap as _textwrap
import sys
import subprocess
from multiprocessing import Pool
import argparse
from shutil import which as _which
from glob import iglob as _iglob
import toml
import networkx as _nx
from pbr.version import VersionInfo as _VersionInfo

from .dialect_check import get_max_supported_compiler_dialect as _get_max_supported_compiler_dialect
from .build_type import BuildType as _BuildType
from .target import Target as _Target,\
                    Executable as _Executable,\
                    SharedLibrary as _SharedLibrary,\
                    StaticLibrary as _StaticLibrary,\
                    HeaderOnly as _HeaderOnly


_v = _VersionInfo('clang-build').semantic_version()
__version__ = _v.release_string()
version_info = _v.version_tuple


def _find_non_existent_dependencies(project):
    illegal_dependencies = []
    keys = [str(key) for key in project.keys()]
    for nodename, node in project.items():
        for dependency in node.get('dependencies', []):
            if not str(dependency) in keys:
                illegal_dependencies.append((nodename, dependency))

    return illegal_dependencies

def _find_circular_dependencies(project):
    graph = _nx.DiGraph()
    for nodename, node in project.items():
        for dependency in node.get('dependencies', []):
            graph.add_edge(str(nodename), str(dependency))

    return list(_nx.simple_cycles(graph))

def _get_dependency_walk(project):
    graph = _nx.DiGraph()
    for nodename, node in project.items():
        dependencies = node.get('dependencies', [])
        if not dependencies:
            graph.add_node(str(nodename))
        else:
            for dependency in dependencies:
                graph.add_edge(str(nodename), str(dependency))

    return list(reversed(list(_nx.topological_sort(graph))))

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

def _get_sources_and_headers(project, target_directory):
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

def _setup_logger(log_level):
    logger = _logging.getLogger(__name__)
    logger.setLevel(_logging.DEBUG)
    fh = _logging.FileHandler('clang-build.log', mode='w')
    fh.setLevel(_logging.DEBUG)
    # create console ha_ndler with a higher log level
    ch = _logging.StreamHandler()
    ch.setLevel(log_level)
    # create formatter _and add it to the handlers
    formatter = _logging.Formatter('%(message)s')
    fh.setFormatter(formatter)
    ch.setFormatter(formatter)
    # add the handlers to the logger
    logger.addHandler(fh)
    logger.addHandler(ch)




_command_line_description = (
'`clang-build` is a build system to build your C++ projects. It uses the clang '
'compiler/toolchain in the background and python as the build-system\'s scripting '
'language.\n'
'For more information please visit: https://github.com/trick-17/clang-build')

def parse_args(args):
    parser = argparse.ArgumentParser(description=_command_line_description)
    parser.add_argument('-V', '--verbose',
                        help='activate more detailed output',
                        action='store_true')
    parser.add_argument('-d', '--directory', type=_Path,
                        help='set the root source directory')
    parser.add_argument('-b', '--build-type', choices=list(_BuildType), type=_BuildType, default=_BuildType.Default,
                        help='set the build type for this project')
    parser.add_argument('-j', '--jobs', type=int, default=1,
                        help='set the number of concurrent build jobs')
    parser.add_argument('--debug', help='activates additional debug output, overrides verbosity option.', action='store_true')
    return parser.parse_args(args=args)


def main():
    args = parse_args(sys.argv[1:])
    loglevel = _logging.DEBUG
    # Verbosity
    if not args.debug:
        if args.verbose:
            loglevel = _logging.INFO
        else:
            loglevel = _logging.WARNING
    _setup_logger(loglevel)
    #
    # TODO: create try except around build and deal with it.
    #
    build(args)

def build(args):
    logger = _logging.getLogger(__name__)
    logger.info(f'clang-build {__version__}')
    # Check for clang++ executable
    clangpp = _which('clang++')
    clang_ar = _which('llvm-ar')
    if clangpp:
        llvm_root = _Path(clangpp).parents[0]
    else:
        logger.error('Couldn\'t find clang++ executable')
        sys.exit(1)
    if not clang_ar:
        logger.error('Couldn\'t find llvm-ar executable')
        sys.exit(1)

    logger.info(f'llvm root directory: {llvm_root}')
    logger.info(f'clang++ executable: {clangpp}')
    logger.info(f'llvm-ar executable: {clang_ar}')
    logger.info(f'Newest supported C++ dialect: {_get_max_supported_compiler_dialect(clangpp)}')


    # Directory this was called from
    callingdir = _Path().resolve()

    # Working directory is where the project root should be - this is searched for 'clang-build.toml'
    if args.directory:
        workingdir = args.directory.resolve()
    else:
        workingdir = callingdir

    if not workingdir.exists():
        logger.error(f'ERROR: specified non-existent directory [{workingdir}]')
        sys.exit(1)

    logger.info(f'Working directory: {workingdir}')

    # Build type (Default, Release, Debug)
    buildType = args.build_type
    logger.info(f'Build type: {buildType.name}')

    # Multiprocessing pool
    processpool = Pool(processes = args.jobs)
    logger.info(f'Running up to {args.jobs} concurrent build jobs')

    build_directory = _Path('build')
    target_list = []

    # Check for build configuration toml file
    toml_file = _Path(workingdir, 'clang-build.toml')
    if toml_file.exists():
        logger.info('Found config file')
        config = toml.load(str(toml_file))

        # Use sub-build directories if multiple targets
        subbuilddirs = False
        if len(config.items()) > 1:
            subbuilddirs = True

        # Parse targets from toml file
        non_existent_dependencies = _find_non_existent_dependencies(config)
        if non_existent_dependencies:
            error_messages = [f'In {target}: the dependency {dependency} does not point to a valid target' for\
                              target, dependency in non_existent_dependencies]

            error_message = _textwrap.indent('\n'.join(error_messages), prefix=' '*3)
            logger.error(error_message)
            sys.exit(1)

        target_names = _get_dependency_walk(config)

        no_source_error_message = 'ERROR: Targt {nodename} was defined as a {type} but no source files were found'

        for nodename in target_names:
            node = config[nodename]
            files = _get_sources_and_headers(node, workingdir)
            dependencies = [target_list[target_names.index(name)] for name in node.get('dependencies', [])]
            executable_dependencies = [target for target in dependencies if target.__class__ is _Executable]
            if executable_dependencies:
                logger.error(f'Error: The following targets are linking dependencies but were identified as executables: {executable_dependencies}')

            target_build_dir = build_directory if not subbuilddirs else build_directory.joinpath(nodename)

            #
            # TODO: Consider if some of the error handling should be done by the classes themselves
            #

            if 'target_type' in node:
                #
                # Add a shared library
                #
                if node['target_type'].lower() == 'sharedlibrary':
                    if not files['sourcefiles']:
                        logger.error(no_source_error_message.format(type='shared library'))
                        sys.exit(1)
                    else:
                        target_list.append(
                            _SharedLibrary(
                                nodename,
                                workingdir,
                                files['headers'],
                                files['include_directories'],
                                files['sourcefiles'],
                                buildType,
                                clangpp,
                                target_build_dir,
                                node,
                                dependencies))

                #
                # Add a static library
                #
                elif node['target_type'].lower() == 'staticlibrary':
                    if not files['sourcefiles']:
                        logger.error(no_source_error_message.format(type='static library'))
                        sys.exit(1)
                    else:
                        target_list.append(
                            _StaticLibrary(
                                nodename,
                                workingdir,
                                files['headers'],
                                files['include_directories'],
                                files['sourcefiles'],
                                buildType,
                                clangpp,
                                clang_ar,
                                target_build_dir,
                                node,
                                dependencies))

                #
                # Here we could allow other custom defined targets?
                #
                else:
                    logger.error(f'ERROR: Unsupported target type: {node["target_type"]}')

            # No target specified so must be executable or header only
            else:
                if not files['sourcefiles']:
                    logger.info(f'No source files found for target {nodename}. Creating header-only target.')
                    target_list.append(
                        _HeaderOnly(
                            nodename,
                            workingdir,
                            files['headers'],
                            files['include_directories'],
                            clangpp,
                            buildType,
                            node,
                            dependencies))
                else:
                    logger.info(f'{len(files["sourcefiles"])} source files found for target {nodename}. Creating executable target.')
                    target_list.append(
                        _Executable(
                            nodename,
                            workingdir,
                            files['headers'],
                            files['include_directories'],
                            files['sourcefiles'],
                            buildType,
                            clangpp,
                            target_build_dir,
                            node,
                            dependencies))


    # Otherwise we try to build it as a simple hello world or mwe project
    else:
        files = _get_sources_and_headers({}, workingdir)

        if not files['sourcefiles']:
            logger.error(f'Error, no sources and no [clang-build.toml] found in folder: {workingdir}')
        # Create target
        target_list.append(
            _Executable(
                'main',
                workingdir,
                files['headers'],
                files['include_directories'],
                files['sourcefiles'],
                buildType,
                clangpp,
                build_directory))

    # Build the targets
    logger.info('Compile')
    for target in target_list:
        target.compile(processpool)

    # No parallel linking atm, could be added via
    # https://stackoverflow.com/a/5288547/2305545
    #
    processpool.close()
    processpool.join()

    logger.info('Link')
    for target in target_list:
        if not target.unsuccesful_builds:
            target.link()
        else:
            logger.error(f'Target {target} did not compile. Errors:\n%s',
                [f'{file}: {output}' for file, output in zip(
                    [t.name for t in target.unsuccesful_builds],
                    [t.output_messages for t in target.unsuccesful_builds])])
            break

    logger.info('clang-build finished.')


if __name__ == '__main__':
    main()
