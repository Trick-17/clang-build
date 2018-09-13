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

def get_dependency_walk(project):
    graph = _nx.DiGraph()
    for nodename, node in project.items():
        dependencies = node.get('dependencies', [])
        if not dependencies:
            graph.add_node(str(nodename))
            continue

        for dependency in dependencies:
            # Split string at dots
            subnames = str(dependency).split(".")
            graph.add_edge(str(nodename), str(subnames[-1]))

    return list(reversed(list(_nx.topological_sort(graph))))

def get_dependency_graph(project):
    graph = _nx.DiGraph()
    for nodename, node in project.items():
        dependencies = node.get('dependencies', [])
        if not dependencies:
            graph.add_node(str(nodename))
            continue

        for dependency in dependencies:
            # Split string at dots
            subnames = str(dependency).split(".")
            graph.add_edge(str(nodename), str(subnames[-1]))

    return graph