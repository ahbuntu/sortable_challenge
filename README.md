# Sortable Coding Challenge 
Repository for the coding challenge for Sortable 

## Current Approach

- Using permutations to identify matches
- Exact string matching is performed
- Focused on speed and precision at the expense of recall
- Optimization of removing extraneous information from the listing title reduced execution time from 4 min to 4 sec

## Future Work

- Recall could be increased significantly by using string similarity measures (Levenshtein distance)
- Leverage existing full-text search engine (Elasticsearch, SOLR) to implement a more generalized and extensible solution
