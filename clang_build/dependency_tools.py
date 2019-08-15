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

def get_dependency_graph(project_identifier, targets_config, subprojects):
    graph = _nx.DiGraph()
    for target_name, node in targets_config.items():
        # Target dependencies
        target_identifier = f"{project_identifier}.{target_name}" if project_identifier else f"{target_name}"
        dependencies = node.get('dependencies', [])
        for dependency in dependencies:
            dependency_identifier = f"{project_identifier}.{dependency}" if project_identifier else f"{dependency}"
            graph.add_edge(str(target_identifier), str(dependency_identifier))

        # Target tests dependencies
        tests_dependencies = [target_name] + node.get('tests', {}).get('dependencies', [])
        target_tests_identifier = f"{project_identifier}.{target_name}.tests" if project_identifier else f"{target_name}.tests"
        for dependency in tests_dependencies:
            dependency_identifier = f"{project_identifier}.{dependency}" if project_identifier else f"{dependency}"
            graph.add_edge(str(target_tests_identifier), str(dependency_identifier))

        # Target examples dependencies
        examples_dependencies = [target_name] + node.get('examples', {}).get('dependencies', [])
        target_examples_identifier = f"{project_identifier}.{target_name}.examples" if project_identifier else f"{target_name}.examples"
        for dependency in examples_dependencies:
            dependency_identifier = f"{project_identifier}.{dependency}" if project_identifier else f"{dependency}"
            graph.add_edge(str(target_examples_identifier), str(dependency_identifier))

        # # If there is no edge to this node, we add it manually
        # if not dependencies and not tests_dependencies and not examples_dependencies:
        #     graph.add_node(str(target_identifier))

    for project in subprojects:
        subgraph = get_dependency_graph(project.identifier, project.targets_config, project.subprojects)
        graph = _nx.compose(graph, subgraph)

    return graph