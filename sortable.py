#!/usr/local/bin/python

import json, logging, itertools, operator
from time import time, gmtime, strftime

# taken from docs.python-guide.org/en/latest/writing/logging
logger = logging.getLogger()
handler = logging.StreamHandler()
formatter = logging.Formatter(
        '%(asctime)s %(name)-12s %(levelname)-8s %(message)s')
handler.setFormatter(formatter)
logger.addHandler(handler)
# logger.setLevel(logging.DEBUG)
logger.setLevel(logging.INFO)

results = {}
product_manufacturer_dict = {}
product_family_dict = {}
product_model_dict = {}
model_family_set = set()

MAX_FAMILY_PERM_R = 4
MAX_MODEL_PERM_R = 4 
MAX_MANUFACTURER_PERM_R = 5 # unlikely that name of manufacturer can be grater than 5

MANUFACTURER = 'manufacturer'
LISTING_TITLE = 'title'
PRODUCT_FAMILY = 'family'
PRODUCT_MODEL = 'model'
PRODUCT_NAME = 'product_name'


def score_manufacturer_listing_vs_products(listing):
	listing_matches_dict = {}
	listing_manufacturer = listing.get(MANUFACTURER).lower()
	product_manufacturer_match = product_manufacturer_dict.get(listing_manufacturer, None)
	if  product_manufacturer_match is not None:
		# if the full manufacturer name match is found, don't bother with tokenization
		for matched_product_name in product_manufacturer_match:
			listing_matches_dict[matched_product_name] = 1000			
	else:		
		listing_manufacturer_tokens = listing_manufacturer.split()
		# due to line 6455 - ASSUMPTION that max length of a manufacturer is 5 words - anything longer is likely not a manufacturer
		# otherwise, computing all permutations becomes prohibitively expensive
		for i in range(5, 0, -1):
			# taken from http://stackoverflow.com/questions/104420/how-to-generate-all-permutations-of-a-list-in-python
			manufacturer_perms = list(itertools.permutations(listing_manufacturer_tokens,i)) # because order matters
			for permutation in manufacturer_perms:
				permutation_match = product_manufacturer_dict.get(" ".join(permutation), None)
				if permutation_match is not None:
					for product_match in permutation_match:
						matched_product_name = listing_matches_dict.get(product_match, None)
						if matched_product_name is None:
							listing_matches_dict[product_match] = 1000*i
						else:
							listing_matches_dict[product_match] += 1000*i # may indicate the presence of extraneous information in listing manufacturer field

	return listing_matches_dict


def speed_optimization(listing_title_tokenized):
	"""remove any word from the listing title that is not a possible model or family name"""

	sanitized_listing_title = set()
	for token in listing_title_tokenized:
		if token in model_family_set:
			sanitized_listing_title.add(token)

	return sanitized_listing_title


def score_family_product_vs_listing(listing):
	listing_matches_dict = {}
	listing_title = listing.get(LISTING_TITLE).lower()
	listing_title_tokens = listing_title.split()
	listing_title_tokens = speed_optimization(listing_title_tokens)

	for i in range(MAX_FAMILY_PERM_R, 0, -1):
		title_perms = list(itertools.permutations(listing_title_tokens,i)) # because order matters
		for permutation in title_perms:
			permutation_match = product_family_dict.get(" ".join(permutation), None)
			if permutation_match is not None:
				for product_match in permutation_match:
					matched_product_name = listing_matches_dict.get(product_match, None)
					if matched_product_name is None:
						listing_matches_dict[product_match] = 10*i
					else:
						listing_matches_dict[product_match] += 10*i # larger value indicates stronger match

	return listing_matches_dict


def score_model_product_vs_listing(listing):
	listing_matches_dict = {}
	listing_title = listing.get(LISTING_TITLE).lower()
	listing_title_tokens = listing_title.split()
	listing_title_tokens = speed_optimization(listing_title_tokens)

	for i in range(MAX_MODEL_PERM_R, 0, -1):
		title_perms = list(itertools.permutations(listing_title_tokens,i)) # because order matters
		for permutation in title_perms:
			permutation_match = product_model_dict.get(" ".join(permutation), None)
			if permutation_match is not None:
				for product_match in permutation_match:
					matched_product_name = listing_matches_dict.get(product_match, None)
					if matched_product_name is None:
						listing_matches_dict[product_match] = 100*i # model match is more valuable than family match
					else:
						listing_matches_dict[product_match] += 100*i # larger value indicates stronger match

	return listing_matches_dict


def matching_optimization(original_dict):
	"""this optimization is specific to the challenge, but encapsulates the concept 
	of trying to expand the model and family names instead of expanding the listing title"""

	expanded_dict = {}

	# expand the set of possible models by tokenizing
	for key in original_dict:
		expanded_dict[key] = original_dict[key]
		tokenized = key.split('-')
		for token in tokenized:
			expanded_dict_key_value = expanded_dict.get(token, None)
			if expanded_dict_key_value is None:
				expanded_dict[token] = original_dict[key]
			else:
				expanded_dict[token] = expanded_dict_key_value | original_dict[key]

	# expand the set of possible models by joining words separated by hyphen
	for key in original_dict:
		token = key.replace('-','')
		expanded_dict_key_value = expanded_dict.get(token, None)
		if expanded_dict_key_value is None:
			expanded_dict[token] = original_dict[key]
		else:
			expanded_dict[token] = expanded_dict_key_value | original_dict[key]

	# expand the set of possible models by replacing hyphen with a space
	for key in original_dict:
		token = key.replace('-',' ')
		expanded_dict_key_value = expanded_dict.get(token, None)
		if expanded_dict_key_value is None:
			expanded_dict[token] = original_dict[key]
		else:
			expanded_dict[token] = expanded_dict_key_value | original_dict[key]

	return expanded_dict


matches = 0
def add_listing_to_results(product_name, listing):
	global matches
	temp_listings = []
	matched_listings = results.get(product_name, None)

	if matched_listings is None:
		matches += 1
		results[product_name] = [listing]
	else:
		matches += 1
		matched_listings.append(listing)
		results[product_name] = matched_listings


def write_results_to_file(output_file):
	with open(output_file, 'w') as outfile:
		for item in results.items():
			line_output= {}
			line_output['product_name'] = item[0]
			line_output['listings'] = item[1]
			json.dump(line_output, outfile)
			outfile.write('\n')


def intialize_products(products_file):
	global product_family_dict
	global product_model_dict

	with open(products_file, 'r') as f:
		for line in f:
			# taken from http://stackoverflow.com/questions/12451431/loading-and-parsing-a-json-file-in-python
			line_json_obj = json.loads(line)
			if line_json_obj.get(MANUFACTURER, None) is None:
				logger.debug('Violating assumption that manufacturer will always be present')
			else:
				key = product_manufacturer_dict.get(json.loads(line)[MANUFACTURER].lower(), None) 
				if key is None:
					product_manufacturer_dict[json.loads(line)[MANUFACTURER].lower()] = {json.loads(line)[PRODUCT_NAME].lower()}
				else :
					key.add(json.loads(line)[PRODUCT_NAME].lower().strip())
			
			if line_json_obj.get(PRODUCT_MODEL, None) is None:
				logger.debug('Violating assumption that model will always be present')
			else:
				product_model_value = json.loads(line)[PRODUCT_MODEL].lower().strip()
				key = product_model_dict.get(product_model_value, None) 
				if key is None:
					product_model_dict[product_model_value] = {json.loads(line)[PRODUCT_NAME].lower()}
				else :
					key.add(json.loads(line)[PRODUCT_NAME].lower().strip())

			if line_json_obj.get(PRODUCT_FAMILY, None) is None:
				logger.debug('Asserting assumption that family may be empty')
			else:
				product_family_value = json.loads(line)[PRODUCT_FAMILY].lower().strip()
				key = product_family_dict.get(product_family_value, None) 
				if key is None:
					product_family_dict[product_family_value] = {json.loads(line)[PRODUCT_NAME].lower()}
				else :
					key.add(json.loads(line)[PRODUCT_NAME].lower().strip())
			
	product_family_dict = matching_optimization(product_family_dict)
	product_model_dict = matching_optimization(product_model_dict)

	model_family_set.update(product_model_dict.keys())
	model_family_set.update(product_family_dict.keys())


def perform_classification(product_file, listings_file, output_file):
	logger.info('Start time ' + strftime("%Y-%m-%d %H:%M:%S", gmtime()))

	intialize_products(product_file)
	# line_counter = 0
	with open(listings_file, 'r') as f:
		for line in f:
			# line_counter += 1
			line_json_obj = json.loads(line)

			listing_matching_manufacturer_products = score_manufacturer_listing_vs_products(line_json_obj)
			if listing_matching_manufacturer_products:
				# making the assumption that if a listing will be attempted to be identified only if a matching manufacturer is found

				listing_matching_family_products = score_family_product_vs_listing(line_json_obj)
				listing_matching_model_products = score_model_product_vs_listing(line_json_obj)

				common_product_manuf_models = set(listing_matching_manufacturer_products.keys()) & set(listing_matching_model_products.keys())

				if len(common_product_manuf_models) == 1:
					# only 1 product name that has a common model and manufacturer - high probability this is the right one
					for product_name in common_product_manuf_models:
						add_listing_to_results(product_name, line_json_obj)

				elif len(common_product_manuf_models) > 1:
					common_product_manuf_models_family = common_product_manuf_models & set(listing_matching_family_products.keys()) 

					if len(common_product_manuf_models_family) == 1:
						# only 1 product that has a common manufacturer, model and family - high probability this is the right one
						add_listing_to_results(product_name, line_json_obj)
					elif len(common_product_manuf_models_family) > 1:
						# need at least two elements to compare against each other
						match_scoring_dict = {}
						for common_product_name in common_product_manuf_models_family:
							match_scoring_dict[common_product_name] = listing_matching_model_products[common_product_name] + \
							listing_matching_family_products[common_product_name]

						desc_match_scores = sorted(match_scoring_dict.items(), key=operator.itemgetter(1), reverse=True)
						if desc_match_scores[0] > desc_match_scores[1]:
							# high probability this is the right one
							add_listing_to_results(product_name, line_json_obj)
						# else:
							# unable to distinguish between them - candidates for fuzzy, slower matching 
				# else:
					# candidates for fuzzy, slower matching 

	write_results_to_file(output_file)
	logger.info('End time ' + strftime("%Y-%m-%d %H:%M:%S", gmtime()))
	logger.info('Output written to ' + output_file)
	logger.debug('matched listings = ' + str(matches))
	logger.debug('matched products = ' + str(len(results)))
	

if __name__ == "__main__":
    # perform_classification('products.txt', 'listings_test.txt', 'results.txt')
    perform_classification('products.txt', 'listings.txt', 'results.txt')
