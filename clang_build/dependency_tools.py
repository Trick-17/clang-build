import networkx as _nx

def find_non_existent_dependencies(project):
    illegal_dependencies = []
    for nodename, node in project.items():
        for dependency in node.get('dependencies', []):
            # Split string at dots
            subnames = str(dependency).split(".")
            if subnames[0] in project.keys():
                subproject = project
                for i in range(1, len(subnames)):
                    subproject = subproject[subnames[i-1]]
                    if subnames[i] not in subproject.keys():
                        illegal_dependencies.append((nodename, '.'.join(subnames[:i])))
                        i = len(subnames)
            else:
                illegal_dependencies.append((nodename, dependency))

    return illegal_dependencies

def find_circular_dependencies(project):
    graph = _nx.DiGraph()
    for nodename, node in project.items():
        for dependency in node.get('dependencies', []):
            graph.add_edge(str(nodename), str(dependency))

    return list(_nx.simple_cycles(graph))

def get_dependency_graph_from_stubs(environment, project_identifier, target_stubs, subprojects):
    graph = _nx.DiGraph()

    for target_stub in target_stubs:
        if target_stub.build_tests:
            target_tests_identifier = f"{target_stub.identifier}.tests"
            graph.add_edge(target_tests_identifier, str(target_stub.identifier))
            for dependency in target_stub.tests_options.get('dependencies', []):
                dependency_identifier = f"{project_identifier}.{dependency}" if project_identifier else f"{dependency}"
                graph.add_edge(target_tests_identifier, str(dependency_identifier))

        if target_stub.build_examples:
            target_examples_identifier = f"{target_stub.identifier}.examples"
            graph.add_edge(target_examples_identifier, str(target_stub.identifier))
            for dependency in target_stub.examples_options.get('dependencies', []):
                dependency_identifier = f"{project_identifier}.{dependency}" if project_identifier else f"{dependency}"
                graph.add_edge(target_examples_identifier, str(dependency_identifier))

        dependencies = target_stub.options.get('dependencies', [])
        if not dependencies:
            graph.add_node(str(target_stub.identifier))
            continue

        for dependency in dependencies:
            dependency_identifier = f"{project_identifier}.{dependency}" if project_identifier else f"{dependency}"
            graph.add_edge(str(target_stub.identifier), str(dependency_identifier))

    for project in subprojects:
        subgraph = get_dependency_graph_from_stubs(environment, project.identifier, project.target_stubs, project.subprojects)
        graph = _nx.compose(graph, subgraph)

    return graph