from oct import load_and_preprocess, compute_relations, compute_independent_set, verify, print_tree, \
    compute_tree_score
from oct_placement import compute_tree
from similarity_functions import Jaccard, F1, PerfectRecall, Exact


DATA_FILE = 'bestbuy_apple.json'


connected_comps, data_stats = load_and_preprocess(DATA_FILE)
total_weight, trivial_weight = data_stats['total'], data_stats['trivial']
print(data_stats)

FUNC = Jaccard(0.0) # the parameter is just a default, that is overriden below

DELTAS = [0.95] #[0.7, 0.75, 0.8, 0.85, 0.9, 0.95, 0.99] #[0.5, 0.6, 0.7, 0.75, 0.8, 0.85, 0.9, 0.95, 0.99]

MERGE_THRESHOLD = 0.01
PRINT_TREE = True
VERIFY = True

results = {}
for delta in DELTAS:
    FUNC.delta = delta
    delta_results = {}
    print('\n' + '*' * 10, 'delta =', delta, '*' * 10)

    components, relations_stats = compute_relations(connected_comps, FUNC)
    print(relations_stats)

    independent_set_stats = compute_independent_set(components)
    print(independent_set_stats)

    if FUNC.name == 'Exact':
        indp_set_weight = independent_set_stats['weight of independent set']
        final_score = round((indp_set_weight + trivial_weight) / total_weight, 3)
        results[delta] = final_score
    else: # *not* Exact variant
        total_weight_covered, tree_stats = compute_tree(components, FUNC, MERGE_THRESHOLD)
        print(tree_stats)
        final_score = round((total_weight_covered + trivial_weight) / total_weight, 3)
        print('FINAL SCORE:', final_score)
        results[delta] = final_score

        if VERIFY:
            print('verified score:', compute_tree_score(components, FUNC, total_weight, trivial_weight))
            verify(components)

        if PRINT_TREE:
            print_tree(components)

if len(DELTAS) > 1:
    print('\nFinal Results:')
    print(results)