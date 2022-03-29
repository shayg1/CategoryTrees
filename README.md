This code was written as part of the work on the paper titled "Automated Category Tree Construction in E-Commerce" (accepted to SIGMOD 2022). It takes as input a set of (possibly weighted) input sets and produces a category tree based on the CTCR algorithm described in the paper. 

This code is released to facilitate the reproducibility of the results reported in the paper.

## Running instructions:
main.py is the entry point to the code, which includes many tunable parameters such as delta (the threshold parameter of the similarity function), various similarity functions, flags for setting the verbosity level of the outputs and activating verification procedures. One needs to download all other files and put them in the same folder.
bestbuy_apple.json is a small subset of the original publicly available Dataset E (described in the paper), based on BestBuy search queries and Amazon products, that includes an anonymized subset of the product IDs that were returned by Elasticsearch as responses to the queries.


The format of the input file is the following:

{"query1": [["Product11", "Product12", ..., "Product1N"], weight1], "query2": [["Product21", ..., "Product2N"], weight2], ...}

It includes the query text, the result set (returned by the search engine) and the weight. If weights are not provided, the default weight is set to 1, as described in the paper. 

Note: As mentioned in the paper, in all the described experiments the subprocedure of CTCR that solves the Maximum Independent Set problem over graphs leverages the exact solver of [1], whose code can be downloaded from https://github.com/KarlsruheMIS/KaMIS. To, nevertheless, ensure that one can directly run the code we provide here, even without integrating with this solution, we have included in the file independent_set.py an alternative solution that achieves slightly worse performance (yet very comparable) but does not depend on any external code. If one wishes to use the solution of [1], this can be achieved by replacing the call to the algorithm in independent_set.py with a call to this solver. 



[1] Lamm, Sebastian, et al. "Exactly solving the maximum weight independent set problem on large real-world graphs." 2019 Proceedings of the Twenty-First Workshop on Algorithm Engineering and Experiments (ALENEX). Society for Industrial and Applied Mathematics, 2019.
