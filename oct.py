import json
import time
from itertools import combinations

import networkx as nx
from networkx.algorithms.components import connected_components

from independent_set import solve_hypergraph_mis, solve_graph_mis


def add_to_list_in_dict(d, k, v):
    if k in d:
        d[k].append(v)
    else:
        d[k] = [v]


class Query(object):
    def __init__(self, name, elms, weight, rank):
        self.name = name
        self.elms = elms
        self.w = weight
        self.size = len(elms)
        self.r = rank  # larger queries have lower rank; rank is unique;

    def intersect(self, other):
        if type(other) is set:
            return not self.elms.isdisjoint(other)
        return not self.elms.isdisjoint(other.elms)

    def issubset(self, other):
        if type(other) is set:
            return self.elms.issubset(other)
        return self.elms.issubset(other.elms)

    def __len__(self):
        return self.size

    def __and__(self, other):
        return self.elms & other.elms

    def __or__(self, other):
        return self.elms | other.elms

    def __sub__(self, other):
        if type(other) is set:
            return self.elms - other
        return self.elms - other.elms

    def __gt__(self, other):
        return self.r < other.r

    def __lt__(self, other):
        return self.r > other.r

    def __eq__(self, other):
        return self.r == other.r

    def __iter__(self):
        return iter(self.elms)

    def __repr__(self):
        return self.name

    def __hash__(self):
        return hash(self.name)


class Category(object):
    def __init__(self, name, query, depth=0):
        self.name = name
        self.query = query
        if query:
            self.elms = query.elms
        else:
            self.elms = set()
        self.actual_elms = set()
        self.children = []
        self.parent = None
        self.depth = depth
        self.covered_queries = set()

    def __repr__(self):
        return self.name

    def __hash__(self):
        return hash(repr(self))


class Component(object):
    def __init__(self, queries, intersecting_pairs, rank, sim_func):
        self.queries = sorted(queries, reverse=True)
        self.intersecting_pairs = intersecting_pairs
        self.rank = rank
        self.sim_func = sim_func
        self.w = sum(q.w for q in self.queries)
        self.num_queries = len(queries)
        # self.names_index = {q.name: q for q in queries}
        self.conflicts = set()
        self.conflicts_dict = {}
        self.triple_conflicts = set()
        self.must_dict = {}  # key is child, value is list of parents
        self.root = Category('ROOT', None, 0)
        self.categories_index = {'ROOT': self.root}
        self.direct_parents = {}

    def __len__(self):
        return self.num_queries

    def __iter__(self):
        return iter(self.queries)

    def __repr__(self):
        return 'component' + str(self.rank)

    def __hash__(self):
        return hash(repr(self))

    def compute_triple_conflicts(self):
        for q in self.must_dict:
            parents = self.must_dict[q]
            for p1, p2 in combinations(parents, 2):
                if p1 < p2:
                    p1, p2 = p2, p1
                if (p2 not in self.must_dict) or (p1 not in self.must_dict[p2]):
                    if p1 not in self.conflicts_dict or p2 not in self.conflicts_dict[p1]:
                        self.triple_conflicts.add((q, p1, p2))

    def compute_relations(self):
        for q1, q2 in self.intersecting_pairs:
            relation = self.sim_func.compute_relation(q1, q2)
            if relation == -1:
                self.conflicts.add((q1, q2))
                add_to_list_in_dict(self.conflicts_dict, q1, q2)
            elif relation == 1:
                    add_to_list_in_dict(self.must_dict, q2, q1)
        if self.sim_func.name != 'Exact' and self.sim_func.delta < 1:
            self.compute_triple_conflicts()


def remove_short_queries(qrs, len_threshold=1):
    """Assumes queries are sorted from longest to shortest."""

    weight_removed = 0
    while qrs and len(qrs[-1]) <= len_threshold:
        short_q = qrs.pop()
        weight_removed += short_q.w
    return weight_removed


def remove_duplicates(qrs):
    """Assumes queries are sorted from longest to shortest."""

    duplicates = set()
    len_qrs = len(qrs)
    for i, q1 in enumerate(qrs):
        if q1 not in duplicates:
            l1 = len(q1)
            for j in range(i + 1, len_qrs):
                q2 = qrs[j]
                if len(q2) != l1:
                    break
                if q2 not in duplicates and q1.elms == q2.elms:
                    q1.w += q2.w
                    duplicates.add(q2)
    new_qrs = [q for q in qrs if q not in duplicates]
    return new_qrs, len(duplicates)


def get_intersecting_pairs(qrs):
    intersecting_pairs = []
    for q1, q2 in combinations(qrs, 2):
        if q1.intersect(q2):
            intersecting_pairs.append((q1, q2))
    return intersecting_pairs


def get_connected_components(qrs, intersecting_pairs):
    """Removes isolated queries, and return list of components from largest to smallest."""
    intersect_graph = nx.Graph()
    intersect_graph.add_nodes_from(qrs)
    intersect_graph.add_edges_from(intersecting_pairs)
    comps = []
    isolated_weight = 0
    for cc in connected_components(intersect_graph):
        if len(cc) == 1:
            isolated_weight += list(cc)[0].w
        else:
            edges = list(intersect_graph.subgraph(cc).edges)
            intersections = [(q1, q2) if q1 > q2 else (q2, q1) for q1, q2 in edges]
            comps.append((cc, intersections))
    comps = sorted(comps, key=lambda c: len(c[0]), reverse=True)
    return comps, isolated_weight


def load_and_preprocess(file_name):
    start_time_of_loading = time.process_time()
    # load data
    with open(file_name) as json_file:
        json_data = json.load(json_file)
    raw_queries = {q: set(json_data[q][0]) for q in json_data}
    raw_weights = {q: json_data[q][1]  if len(json_data[q]) == 2 else 1 for q in json_data}
    total_weight = sum(raw_weights.values())  # this is only correct for unweighted inputs
    print(f'TOTAL WEIGHT: {total_weight}')
    total_num_elements = len(set.union(*[elms for q, elms in raw_queries.items()]))

    # create query objects in sorted order from large to small and remove queries of length 1
    sorted_queries = sorted(raw_queries.keys(), key=lambda q: len(raw_queries[q]), reverse=True)
    Q = [Query(name, raw_queries[name], raw_weights[name], rank) for rank, name in enumerate(sorted_queries)]

    # remove short queries
    short_weight = remove_short_queries(Q)

    # remove duplicates and adjust weights
    Q, num_duplicates = remove_duplicates(Q)

    # get list of tuples of all intersecting pairs
    intersecting_pairs = get_intersecting_pairs(Q)

    # partition into connected components and remove isolated queries
    comps, isolated_weight = get_connected_components(Q, intersecting_pairs)

    trivial_weight = short_weight + isolated_weight
    # Q_weight = total_weight - trivial_weight
    comp_lengths = [len(c[0]) for c in comps if len(c[0]) > 9]
    preprocessing_running_time = round(time.process_time() - start_time_of_loading, 2)
    data_stats = {'file': file_name,
                  'short': short_weight,
                  'isolated': isolated_weight,
                  'trivial': trivial_weight,
                  'total': total_weight,
                  'duplicates': num_duplicates,
                  'components': len(comps),
                  'lengths >9': comp_lengths,
                  'elements': total_num_elements,
                  'time: ': preprocessing_running_time}

    return comps, data_stats


def compute_relations(comps, sim_func):
    start_time_of_computing_relations = time.process_time()
    components = []
    total_pair_conflicts, total_triple_conflicts = 0, 0
    for rank, (queries, intersecting_pairs) in enumerate(comps):
        comp = Component(queries, intersecting_pairs, rank, sim_func)
        components.append(comp)
        comp.compute_relations()
        total_pair_conflicts += len(comp.conflicts)
        total_triple_conflicts += len(comp.triple_conflicts)
    computing_relations_running_time = round(time.process_time() - start_time_of_computing_relations, 2)
    relations_stats = {'pair conflicts': total_pair_conflicts,
                       'triple conflicts': total_triple_conflicts,
                       'relations time': computing_relations_running_time}
    return components, relations_stats


def compute_independent_set(components):
    start_time_of_computing_indp_set = time.process_time()
    total_indp_set_weight = 0
    total_vertices_weight = 0
    for comp in components:
        if comp.triple_conflicts:
            comp.indp_set = solve_hypergraph_mis(comp.queries, comp.conflicts, comp.triple_conflicts)
        else:
            comp.indp_set = solve_graph_mis(comp.queries, comp.conflicts)
        comp.all_elms = set.union(*[q.elms for q in comp.indp_set])
        total_vertices_weight += comp.w
        total_indp_set_weight += sum(q.w for q in comp.indp_set)
    indp_set_running_time = round(time.process_time() - start_time_of_computing_indp_set, 2)
    indp_set_stats = {'weight of independent set': total_indp_set_weight,
                      'total weight of graph': total_vertices_weight,
                      'ratio of IS to V': round(total_indp_set_weight / total_vertices_weight, 3),
                      'indp_set time': indp_set_running_time}
    return indp_set_stats


def verify(components):
    def verify_union_rule(cat):
        union = set()
        for ch in cat.children:
            union |= ch.actual_elms
        assert union.issubset(cat.actual_elms)
        for child in cat.children:
            verify_union_rule(child)

    def verify_copy_bound(elm, cats):
        containing_cats = [cat for cat in cats if elm in cat.actual_elms]
        assert len(containing_cats) < 2
        if containing_cats:
            cont_cat = containing_cats[0]
            children = cont_cat.children
            if children:
                verify_copy_bound(elm, children)

    for comp in components:
        verify_union_rule(comp.root)
        for e in comp.all_elms:
            verify_copy_bound(e, [comp.root])
    print('Verified!')


def print_tree(components):
    def print_tree_recursively(cat):
        if cat.depth > 0:
            print('--' * cat.depth, cat.name)
        for child in cat.children:
            print_tree_recursively(child)

    for comp in components:
        print_tree_recursively(comp.root)


def compute_tree_score(components, sim_func, total_weight, trivial_weight):
    covered_weight = trivial_weight
    for comp in components:
        for q in comp.queries:
            if check_if_covered(q, comp.root, sim_func):
                covered_weight += q.w
    score = covered_weight / total_weight
    return round(score, 3)


def check_if_covered(q, cat, sim_func):
    q_elms, cat_elms = q.elms, cat.actual_elms
    if cat_elms.isdisjoint(q_elms):
        return False
    return sim_func.is_covering(q_elms, cat_elms) or any(
        check_if_covered(q, ch, sim_func) for ch in cat.children)



