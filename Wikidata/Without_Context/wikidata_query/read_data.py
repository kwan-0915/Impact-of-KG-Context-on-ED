import os
import random
import requests
import numpy as np
import time
import pandas as pd
import sys
import logging

from gensim.models import KeyedVectors

from wikidata_query.utils import infer_vector_from_word, infer_vector_from_doc
from wikidata_query.utils import get_words
from wikidata_query.utils import _is_relevant
from wikidata_query.utils import _is_not_relevant
from wikidata_query.wikidata_items import wikidata_items
from wikidata_query.sentence_processor import get_adjacency_matrices_and_vectors_given_triplets

_path = os.path.dirname(__file__)
#_model = KeyedVectors.load_word2vec_format(os.path.join('/home/IAIS/cprabhu/Thesis/ned-graphs/', 'data/glove_2.2M.txt'))
_query = '''
SELECT ?rel ?item ?rel2 ?to_item {
  wd:%s ?rel ?item
  OPTIONAL { ?item ?rel2 ?to_item }
  FILTER regex (str(?item), '^((?!statement).)*$') .
  FILTER regex (str(?item), '^((?!https).)*$') .
} LIMIT 1500
'''


def get_wikidata_id_from_wikipedia_id(wikipedia_id):
    url = 'https://en.wikipedia.org/w/api.php?action=query&prop=pageprops&pageids=%s&format=json' % str(
        wikipedia_id)
    try:
        return requests.get(url).json()['query']['pages'][str(wikipedia_id)]['pageprops']['wikibase_item']
    except:
        return ''


def get_graph_from_wikidata_id(wikidata_id, central_item):
    url = 'https://query.wikidata.org/bigdata/namespace/wdq/sparql'
    data = requests.get(url, params={'query': _query % wikidata_id,'format': 'json'})
    if data.status_code != 200:
        time.sleep(40)
        data = requests.get(url, params={'query': _query % wikidata_id,'format': 'json'})
        if data.status_code != 200:
            time.sleep(160)
            data = requests.get(url, params={'query': _query % wikidata_id,'format': 'json'})
    data = data.json()
    print("Reading")
    sys.stdout.flush()
    triplets = ""
    graph_set = set()
    for item in data['results']['bindings']:
        try:
            from_item = wikidata_items.translate_from_url(wikidata_id)
            relation = wikidata_items.translate_from_url(item['rel']['value'])
            to_item = wikidata_items.translate_from_url(item['item']['value'])
            graph_set.add(relation)
            graph_set.add(to_item)
        except Exception as e:
            pass
        """try:
            from_item = wikidata_items.translate_from_url(item['item']['value'])
            relation = wikidata_items.translate_from_url(item['rel2']['value'])
            to_item = wikidata_items.translate_from_url(item['to_item']['value'])
            #triplets.append((from_item, relation, to_item))
            graph_set.add(relation)
            graph_set.add(to_item)
        except Exception as e:
            #print("Here ", e)
            pass"""
            #sys.exit()
    #triplets = sorted(list(set(triplets)))
    triplets = ' '.join(graph_set)
    if triplets == "":
        raise RuntimeError("This graph contains no suitable triplets.")
    return triplets


def convert_text_into_vector_sequence(model, text):
    words = get_words(text)
    vectors = []
    for word in words:
        vectors.append(infer_vector_from_word(model, word))
    return vectors


def get_item_mask_for_words(text, item):
    words = get_words(text)
    types = []
    words_in_item = get_words(item.lower())
    for word in words:
        types.append([1. if word.lower() in words_in_item else 0.] * 200)
    return types


"""def get_data(filename, offset, limit):
    with open(filename) as file:
        lines = file.readlines()[2 * offset:2 * limit]
        data = []
        for i in range(int(len(lines) / 2)):
            text_item_graph_dict = {}
            text = lines[2 * i].replace('\n', '')
            item, wikipedia_id = lines[2 * i + 1].replace('\n', '').split('\t')
            wikidata_id = get_wikidata_id_from_wikipedia_id(wikipedia_id)
            if wikidata_id:
                try:
                    text_item_graph_dict['text'] = text
                    text_item_graph_dict['item'] = item
                    text_item_graph_dict['wikidata_id'] = wikidata_id
                    text_item_graph_dict['graph'] = get_graph_from_wikidata_id(wikidata_id, item)
                    text_item_graph_dict['item_vector'] = infer_vector_from_doc(_model, item)
                    text_item_graph_dict['question_vectors'] = convert_text_into_vector_sequence(_model, text)
                    text_item_graph_dict['question_mask'] = get_item_mask_for_words(text, item)
                    data.append(text_item_graph_dict)
                except Exception as e:
                    print(str(e))
    return data"""

def infer_vector_from_vector_nodes(vector_list):
    
    """words = get_words(text)
    vectors = []
    for word in words:
        vectors.append(infer_vector_from_word(model, word))
    return np.mean(vectors, axis = 0)"""    
    
    vector = np.zeros(300)
    return vector


def create_text_item_graph_dict(text, item, wikidata_id):
    #text_item_graph_dict = {}
    #text_item_graph_dict['text'] = text
    #text_item_graph_dict['item'] = item
    #text_item_graph_dict['wikidata_id'] = wikidata_id
    text_item_graph_dict['graph'] = get_graph_from_wikidata_id(wikidata_id, item)
    # text_item_graph_dict['item_vector'] = infer_vector_from_doc(_model, item)
    #text_item_graph_dict['item_vector'] = infer_vector_from_vector_nodes(text_item_graph_dict['graph']['vectors'])
    #text_item_graph_dict['question_vectors'] = convert_text_into_vector_sequence(_model, text)
    #text_item_graph_dict['question_mask'] = get_item_mask_for_words(text, item)
    return text_item_graph_dict


def get_json_data_many_wrong_ids(json_data):
    data = []
    for json_item in json_data:
        try:
            text = json_item['text']
            item = json_item['string']
            wikidata_id = json_item['positive_id']
            text_item_graph_dict = create_text_item_graph_dict(text, item, wikidata_id)
            text_item_graph_dict['answer'] = _is_relevant
            data.append(text_item_graph_dict)
            for wikidata_id in json_item['negative_ids']:
                text_item_graph_dict = create_text_item_graph_dict(text, item, wikidata_id)
                text_item_graph_dict['answer'] = _is_not_relevant
                data.append(text_item_graph_dict)
        except Exception as e:
            print(str(e))
    return data


def get_json_data(json_data):

    df = pd.DataFrame(columns=['id','wikidata_id','text','graph','label'])
    i = 0
    for json_item in json_data:
        text = json_item['text']
        item = json_item['string']
        wikidata_id_correct = json_item['correct_id']
        wikidata_id_wrong = json_item['wrong_id']
        try:
            df.loc[i] = [i,wikidata_id_correct,text,item,_is_relevant]
            i = i + 1
            df.loc[i] = [i,wikidata_id_wrong,text,item,_is_not_relevant]
            i = i + 1
            print("Reading")
            sys.stdout.flush()
        except Exception as e:
            print(str(e))
    return df


def get_wikidata_id_of_item_different_from_given_one_with_boundaries(item_str,
                                                                     wikidata_id,
                                                                     min_number_of_negative_items=1,
                                                                     max_number_of_negative_items=1):
    items = wikidata_items.reverse_lookup(item_str)
    items = list(set(items))
    del items[items.index(wikidata_id)]
    if not items:
        raise RuntimeWarning('No negative items!')
    if len(items) < min_number_of_negative_items:
        raise RuntimeWarning('Not enough negative items!')
    if len(items) > max_number_of_negative_items:
        raise RuntimeWarning('Too many negative items!')
    return items


def get_wikidata_id_of_item_different_from_given_one(item_str,
                                                     wikidata_id):
    items = wikidata_items.reverse_lookup(item_str)
    items = list(set(items))
    del items[items.index(wikidata_id)]
    if not items:
        raise RuntimeWarning('No negative items!')
    return random.choice(items)