import math
import time
from itertools import combinations

from oct import add_to_list_in_dict, Category


def compute_tree(components, sim_func, merge_threshold):
    def compute_max_depth(cat):
        if cat.children:
            return max(compute_max_depth(child) for child in cat.children)
        return cat.depth

    def compute_num_categories(cat):
        if cat.children:
            return 1 + sum(compute_num_categories(child) for child in cat.children)
        else:
            return 1

    def compute_core_tree():
        def add_child(p, c):
            p.children.append(c)
            c.parent = p
            c.depth = p.depth + 1

        def compute_direct_parents():
            for c in components:
                indp_ancestors = {}
                indp_children = c.indp_set & c.must_dict.keys()
                for qr in indp_children:
                    parents = set(c.must_dict[qr]) & c.indp_set
                    if parents:
                        indp_ancestors[qr] = parents
                for qr in indp_ancestors:
                    parents = indp_ancestors[qr]
                    grandparents = set()
                    for p in parents:
                        if p in indp_ancestors:
                            grandparents.update(indp_ancestors[p])
                    dir_parents = list(parents - grandparents)
                    assert len(dir_parents) == 1
                    c.direct_parents[qr] = dir_parents[0]

        def compute_elms(catg):
            for ch in catg.children:
                ch_elms = compute_elms(ch)
                catg.elms.update(ch_elms)
            catg.actual_elms = catg.elms.copy()
            return catg.elms

        compute_direct_parents()
        for comp in components:
            qs = sorted(comp.indp_set, reverse=True)
            for q in qs:
                cat = Category(q.name, q)
                comp.categories_index[cat.name] = cat
                if q in comp.direct_parents:
                    parent = comp.categories_index[comp.direct_parents[q].name]
                    add_child(parent, cat)
                else:
                    add_child(comp.root, cat)
            compute_elms(comp.root)

    def compute_total_weight_covered(only_indp_set=False):
        def check_cover(qr, catg, sim_func):
            if qr.elms.isdisjoint(catg.actual_elms):
                return False
            return sim_func.is_covering(qr.elms, catg.actual_elms,sim_func) or any(
                check_cover(qr, ch, sim_func) for ch in catg.children)

        for comp in components:
            comp.covered = comp.covered_before_expand.copy()
            for q in comp.indp_set - comp.covered_before_expand:
                cat = comp.categories_index[q.name]
                if check_cover_of_indp_q(q, cat, sim_func):
                    comp.covered.add(q)
            if not only_indp_set:
                for q in set(comp.queries) - comp.indp_set:
                    if check_cover(q, comp.root, sim_func):
                        comp.covered.add(q)
        return sum(q.w for comp in components for q in comp.covered)

    # build core tree with duplicates
    start_time_of_tree_building = time.process_time()
    compute_core_tree()
    initial_max_depth = max(compute_max_depth(comp.root) for comp in components)

    if sim_func.name not in ['Perfect-Recall', 'Exact']:
        # remove duplicates
        total_elms_in_tree, total_dupl_elms = fix_duplicates(components, sim_func)

        # expand tree
        total_weight_covered_before_expand = compute_total_weight_covered(only_indp_set=True)
        expand_tree(components, merge_threshold)
        after_expand_max_depth = max(compute_max_depth(comp.root) for comp in components)
        after_expand_num_categories = sum(compute_num_categories(comp.root) for comp in components)
        tree_building_running_time = round(time.process_time() - start_time_of_tree_building, 2)
        total_weight_covered = compute_total_weight_covered(only_indp_set=True)
        weight_gained_by_expanding = total_weight_covered - total_weight_covered_before_expand

        # prepare stats
        tree_stats = {'initial depth': initial_max_depth,
                      'depth': after_expand_max_depth,
                      'categories': after_expand_num_categories,
                      'elms in tree': total_elms_in_tree,
                      'dups in tree': total_dupl_elms,
                      'expanding gains': weight_gained_by_expanding,
                      'total time': tree_building_running_time}
    elif sim_func.name == 'Perfect-Recall':
        tree_building_running_time = round(time.process_time() - start_time_of_tree_building, 2)
        num_categories = sum(compute_num_categories(comp.root) for comp in components)
        num_elms = sum(len(set.union(*[q.elms for q in comp.indp_set])) for comp in components)
        total_weight_covered = sum(q.w for comp in components for q in compute_cover_of_indp_set(comp, sim_func))
        tree_stats = {'depth': initial_max_depth,
                      'categories': num_categories,
                      'elms in tree': num_elms,
                      'total time': tree_building_running_time}
    return total_weight_covered, tree_stats


def compute_cover_of_indp_set(comp, sim_func):
        covered_queries = set()
        for q in comp.indp_set:
            cat = comp.categories_index[q.name]
            is_covered = check_cover_of_indp_q(q, cat, sim_func)
            if is_covered:
                covered_queries.add(q)
        return covered_queries

def fix_duplicates(components, sim_func):
    def is_duplicate(el, cat):
        if el not in cat.actual_elms:
            return False
        containing_children = [child for child in cat.children if el in child.actual_elms]
        if len(containing_children) > 1:
            return True
        if not containing_children:
            return False
        assert len(containing_children) == 1
        return is_duplicate(el, containing_children[0])

    def remove_dup(el, cat):
        if el in cat.actual_elms:
            cat.actual_elms.remove(el)
            for child in cat.children:
                remove_dup(el, child)

    def find_containing_cats(elm, cat, elms_dict, not_covered):
        if elm in cat.elms:
            if cat.query and cat.depth > 0 and cat.query in not_covered and elm in cat.query.elms:
                add_to_list_in_dict(elms_dict, cat, elm)
            for child in cat.children:
                find_containing_cats(elm, child, elms_dict, not_covered)

    total_dupl_elms = 0
    total_elms_in_tree = sum(len(comp.all_elms) for comp in components)
    total_weight_covered_after_removal = 0
    for comp in components:
        # find all duplicates (elements that appear in multiple branches)
        dups = set()
        for e in comp.all_elms:
            if is_duplicate(e, comp.root):
                dups.add(e)
        total_dupl_elms += len(dups)
        covered_queries_before_removal = compute_cover_of_indp_set(comp, sim_func)

        # find all containing categories for duplicates and remove the duplicates
        for e in dups:
            remove_dup(e, comp.root)
        covered_queries_after_removal = compute_cover_of_indp_set(comp, sim_func)
        total_weight_covered_after_removal += sum(q.w for q in covered_queries_after_removal)
        uncovered = covered_queries_before_removal - covered_queries_after_removal
        dupl_elms_dict = {}  # keys are categories
        for e in dups:
            find_containing_cats(e, comp.root, dupl_elms_dict, uncovered)

        # # VERIFY
        # for cat in dupl_elms_dict:
        #     assert len(dupl_elms_dict[cat]) == len(cat.query.elms - cat.actual_elms)
        #     assert cat.query in uncovered
        #     assert len(uncovered) == len(dupl_elms_dict)

        # place each duplicate in one branch
        place_duplicates(dups, dupl_elms_dict, sim_func)
        if dups:
            distribute_remaining(dups, comp.root)
        covered_queries_final = compute_cover_of_indp_set(comp, sim_func)
        comp.covered_before_expand = covered_queries_final
    return total_elms_in_tree, total_dupl_elms


def distribute_remaining(dups, root):
    def find_leaves(el, cat, lvs):
        assert el in cat.elms
        containing_children = [ch for ch in cat.children if el in ch.elms]
        if not containing_children:
            lvs.append(cat)
        else:
            for ch in containing_children:
                find_leaves(el, ch, lvs)

    for e in dups:
        leaves = []
        find_leaves(e, root, leaves)
        assert leaves
        chosen_leaf = min(leaves, key=lambda ct: len(ct.actual_elms) / ct.query.w)
        add_elm_to_leaf(e, chosen_leaf)


def place_duplicates(dups, dupl_elms_dict, sim_func):
    def get_closeness_score(catg):
        c_elms, q_elms = catg.actual_elms, catg.query.elms
        if sim_func.is_covering(q_elms, c_elms):
            return 0, 0
        x = sim_func.num_missing(q_elms, c_elms)
        num_missing = math.ceil(x)
        if num_missing - x > 0.99999:
            num_missing -= 1
        if num_missing > len(dupl_elms_dict[cat]):
            return 0, 0
        closeness_score = num_missing / catg.query.w
        return closeness_score, num_missing

    closeness_dict = {}
    for cat in set(dupl_elms_dict.keys()):
        result = get_closeness_score(cat)
        if result[0] == 0:
            raise Exception('covered query in uncovered dict')
        else:
            closeness_dict[cat] = result

    while closeness_dict and dups:
        chosen_cat = min(closeness_dict.keys(), key=lambda catgr: closeness_dict[catgr][0])
        missing = closeness_dict[chosen_cat][1]
        chosen_elms = add_elms_to_cat(chosen_cat, missing, dupl_elms_dict)
        affected_cats = set()
        for e in chosen_elms:
            dups.remove(e)
            for ct in dupl_elms_dict.keys():
                if e in dupl_elms_dict[ct]:
                    dupl_elms_dict[ct].remove(e)
                    affected_cats.add(ct)
        for cat in affected_cats:
            result = get_closeness_score(cat)
            if result[0] == 0:
                del dupl_elms_dict[cat]
                del closeness_dict[cat]
            else:
                closeness_dict[cat] = result


def add_elm_to_leaf(e, leaf):
    leaf.actual_elms.add(e)
    if leaf.parent:
        add_elm_to_leaf(e, leaf.parent)


def add_elms_to_cat(chosen_cat, missing, dupl_elms_dict):
    def get_all_cats_on_same_branch(cat):
        cats = {cat}
        new_cat = cat
        while new_cat.parent:
            new_cat = new_cat.parent
            if new_cat in dupl_elms_dict:
                cats.add(new_cat)
        new_cat = cat
        relevant_children = [ch for ch in new_cat.children if ch in dupl_elms_dict]
        while relevant_children:
            new_cat = relevant_children[0]
            cats.add(new_cat)
            relevant_children = [ch for ch in new_cat.children if ch in dupl_elms_dict]
        return cats

    def add_elm_to_cat(e, cat):
        def find_leaf(el, catg):
            relevant_children = [ch for ch in catg.children if el in ch.elms]
            if not relevant_children or not relevant_children[0]:
                return catg
            else:
                return find_leaf(el, relevant_children[0])

        leaf = find_leaf(e, cat)
        assert leaf and e in leaf.elms
        add_elm_to_leaf(e, leaf)

    branch_cats = get_all_cats_on_same_branch(chosen_cat)
    relevant_elms = {e for e in dupl_elms_dict[chosen_cat]}
    if len(relevant_elms) <= missing:
        chosen_elms = relevant_elms
    else:
        freq_dict = {e: 1 for e in relevant_elms}
        for ct in branch_cats - {chosen_cat}:
            for e in (set(dupl_elms_dict[ct]) & relevant_elms):
                freq_dict[e] += 1
        chosen_elms = sorted(relevant_elms, key=lambda el: freq_dict[el], reverse=True)[: missing]
    for e in chosen_elms:
        add_elm_to_cat(e, chosen_cat)
    return chosen_elms


def check_cover_of_indp_q(q, cat, sim_func):
    is_covered = sim_func.is_covering(q.elms, cat.actual_elms)
    if is_covered:
        return True
    if cat.parent:
        return check_cover_of_indp_q(q, cat.parent, sim_func)
    return False





def expand_tree(components, merge_threshold):
    def add_intermediate_categories(categ):
        def merge_cats(cat1, cat2):
            def update_depths(cat, diff):
                cat.depth += diff
                for ch in cat.children:
                    update_depths(ch, diff)

            new_name = cat1.name + '::' + cat2.name
            new_elms = cat1.elms | cat2.elms
            new_actual_elms = cat1.actual_elms | cat2.actual_elms
            new_depth = cat1.depth
            new_catg = Category(name=new_name, query=None, depth=new_depth)
            new_catg.elms = new_elms
            new_catg.actual_elms = new_actual_elms
            parent = cat1.parent
            new_catg.parent = parent
            new_catg.children = [cat1, cat2]
            parent.children.remove(cat1)
            parent.children.remove(cat2)
            parent.children.append(new_catg)
            update_depths(cat1, 1)
            update_depths(cat2, 1)
            cat1.parent = new_catg
            cat2.parent = new_catg
            return new_catg

        def get_initial_pairs(ct):
            if len(ct.children) < 3:
                return []
            cands = []
            for u, v in combinations(ct.children, 2):
                if not u.elms.isdisjoint(v.elms):
                    inter = len(v.elms & u.elms)
                    min_len = min(len(u.elms), len(v.elms))
                    ratio = inter / min_len
                    if ratio >= merge_threshold:
                        cands.append((frozenset([u, v]), ratio))
            return cands

        def update_candidates(cands, new_cat, ct1, ct2):
            def get_ratio(v, u):
                inter = len(v.elms & u.elms)
                min_l = min(len(u.elms), len(v.elms))
                return inter / min_l

            children = new_cat.parent.children
            if len(children) < 3:
                return []
            new_candidates = [c for c in cands if ct1 not in c[0] and ct2 not in c[0]]
            for ch in children:
                if ch.name != new_cat.name and (not ch.elms.isdisjoint(new_cat.elms)):
                    ratio = get_ratio(new_cat, ch)
                    if ratio >= merge_threshold:
                        new_candidates.append((frozenset([new_cat, ch]), ratio))
            return new_candidates

        candidates = get_initial_pairs(categ)
        while len(categ.children) > 2 and candidates:
            max_pair = max(candidates, key=lambda p: p[1])
            catg1, catg2 = max_pair[0]
            new_category = merge_cats(catg1, catg2)
            candidates = update_candidates(candidates, new_category, catg1, catg2)
        for child in categ.children:
            add_intermediate_categories(child)

    for comp in components:
        add_intermediate_categories(comp.root)
