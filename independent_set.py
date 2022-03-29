import networkx as nx



def solve_hypergraph_mis(queries, pair_conflicts, hyper_conflicts):
    all_conflicts = pair_conflicts | hyper_conflicts
    edges = {frozenset(cf) for cf in all_conflicts}
    degrees = {}
    for e in edges:
        for v in e:
            degrees[v] = (degrees[v] + 1) if v in degrees else 1
    singletons = set(queries) - set(degrees.keys())
    ind_set_hyper_min = set(hyper_min_alg(edges.copy(), degrees.copy()))
    ind_set_hyper_max = hyper_max_alg(edges.copy(), degrees.copy())
    best_result = max([ind_set_hyper_min, ind_set_hyper_max], key=lambda s: sum(v.w for v in s))
    print('min:', len(ind_set_hyper_min) + len(singletons), '   max:', len(ind_set_hyper_max) + len(singletons))
    ind_set = best_result | singletons
    return ind_set


def solve_graph_mis(nodes, edges):
    g = nx.Graph()
    g.add_nodes_from(nodes)
    g.add_edges_from(edges)
    ind_set_wg = wg_alg(g)
    return ind_set_wg


def hyper_min_alg(edges, degrees):
    ind_set = []
    while degrees:
        min_node = min(degrees.keys(), key=lambda vertex: (degrees[vertex], 1 / vertex.w))
        ind_set.append(min_node)
        del degrees[min_node]
        to_remove = set()
        neig_e = [e for e in edges if min_node in e]
        for e in neig_e:
            edges.remove(e)
            others = frozenset(q for q in e if q != min_node)
            if len(others) == 1:
                for u in others:
                    to_remove.add(u)
            elif others in edges:
                for u in others:
                    degrees[u] -= 1
            else:
                edges.add(others)
        for u in to_remove:
            del degrees[u]
        for e in edges.copy():
            if not e.isdisjoint(to_remove):
                edges.remove(e)
                for v in e:
                    if v not in to_remove and v in degrees:
                        degrees[v] -= 1
        singletons = [q for q in degrees if degrees[q] == 0]
        for q in singletons:
            ind_set.append(q)
            del degrees[q]
    return ind_set


def hyper_max_alg(edges, degrees):
    while edges:
        max_node = max(degrees.keys(), key=lambda vertex: (degrees[vertex], 1 / vertex.w))
        del degrees[max_node]
        to_remove = set()
        neig_e = [e for e in edges if max_node in e]
        for e in neig_e:
            edges.remove(e)
            others = frozenset(q for q in e if q != max_node)
            for u in others:
                degrees[u] -= 1
    return set(degrees.keys())


# AVERAGE WEIGHTED DEGREE ALGORITHM
def wg_alg(conflict_g: nx.Graph):
    g = conflict_g.copy()
    weighted_degrees = {}
    singletons = {n for n, d in g.degree if d == 0}
    g.remove_nodes_from(singletons)
    for v in g.nodes:
        neigs_weight = sum(n.w for n in g.neighbors(v))
        weighted_degrees[v] = neigs_weight / v.w
    ind_set = singletons
    while g.number_of_nodes():
        min_node = min(g.nodes, key=lambda node: weighted_degrees[node])
        ind_set.add(min_node)
        min_node_neighbors = set(g.neighbors(min_node))
        to_remove = min_node_neighbors | {min_node}
        for neig in min_node_neighbors:
            extended_neigs = set(g.neighbors(neig)) - to_remove
            for ext_neg in extended_neigs:
                weighted_degrees[ext_neg] -= neig.w / ext_neg.w
        g.remove_nodes_from(to_remove)
    return ind_set
