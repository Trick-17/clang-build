import networkx as _nx

def find_non_existent_dependencies(project):
    illegal_dependencies = []
    keys = [str(key) for key in project.keys()]
    for nodename, node in project.items():
        for dependency in node.get('dependencies', []):
            if str(dependency) not in keys:
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
            graph.add_edge(str(nodename), str(dependency))

    return list(reversed(list(_nx.topological_sort(graph))))