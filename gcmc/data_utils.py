import numpy as np
import pandas as pd
import os
import json
import pickle
from itertools import islice


def get_superset_of_column_names_from_file(json_file_path):
    """Read in the json dataset file and return the superset of column names."""
    column_names = set()
    with open(json_file_path) as fin:
        for line in fin:
            line_contents = json.loads(line)
            column_names.update(
                    set(get_key_value_pair(line_contents).keys())
                    )
    return list(column_names)



def get_key_value_pair(line_contents, parent_key='', extra_op = False):
    """
    Return a dict of flatten key value pair.
    """
    result = dict()
    for k, v in line_contents.items():
        column_name = "{0}.{1}".format(parent_key, k) if parent_key else k
        
        if k == 'attributes':
            if v is None:
                continue
            sub_result = get_key_value_pair(v, extra_op = True)
            result.update(sub_result)
        else:
            if extra_op and '{' in v:
                v = v.replace('\'', "\"").replace('True', '1').replace('False', '0')
                v = json.loads(v)
                sub_result = get_key_value_pair(v, parent_key = column_name)
                result.update(sub_result)
            else:
                result.update({column_name:v})
    

    return result

def process_restuarant(file_name, column_names):
    '''
    return 
    pd.Dataframe for item features, 
    vocab for categories[list format],
    item size
    '''
    
    result_df = pd.DataFrame(columns=column_names)
    categories = set()
    count = 0
    with open(file_name) as f:
        for line in f:
            line_contents = json.loads(line)
            result = get_key_value_pair(line_contents)
            sub_df = {column:None  for column in column_names}
            for k, v in result.items():
                sub_df[k] = v
            result_df = result_df.append(pd.DataFrame(sub_df, index= [count]))
#             if result['categories'] is not None:
#                 categories.update(set(result['categories'].split(', ')))

            count =count+ 1
    
    return result_df, categories, count
    
def user_loader(file_name):
    result_df = pd.DataFrame()
    count = 0
    with open(file_name) as f:
        for line in f:
            line_contents = json.loads(line)
            sub_result = get_key_value_pair(line_contents)
            del sub_result['friends']
            sub_result['elite'] = len(sub_result['elite'].split(',')) if sub_result['elite'] != ""  else 0
            result_df = result_df.append(pd.DataFrame(sub_result, index= [count]))
            count = count+ 1

    return result_df, count 
    

def remapping(ori_ids):
    '''
    Give new indices from old_id
    '''
    uniq_id = set(ori_ids)

    id_dict=  {old:new for new, old in enumerate(uniq_id)}
    new_ids = np.array([id_dict[id] for id in ori_ids])
    n = len(uniq_id)

    return new_ids, id_dict, n


def create_test_file(file, nline = 10000):
    with open(file + ".json", 'rb') as f:
        data = list(islice(f, nline))
    with open(file + "_test.json", 'wb') as f:
        for line in data:
            f.write(line)

def restuarant_loader(file_name):
    '''
    load restuarant data
    192609 rows in full data 
    flatten all the data in attributes
    categories: 2468 considering embedding    
    only consider restuarant with reviews in our data set
    return: pd.DF for restuarant and different vocabulary_list
    '''
    column_names = get_superset_of_column_names_from_file(file_name)
    return process_restuarant(file_name, column_names)


def data_loading(file_dir, verbose = False, test= False):
    '''
    preliminary data parsing, and save to another file
    '''
    
    
    output_file_names = ['u_features.pkl','v_features.pkl', 'new_reviews.npy', 'miscellany.pkl']
    if test:
        output_file_names = ['test'+i for i in output_file_names]
    output_file_names = [file_dir+i for i in output_file_names]
    
    if output_file_names[0] in os.listdir(file_dir):
        u_features = pd.read_pickle(output_file_names[0])
        v_features = pd.read_pickle(output_file_names[1])
        new_reviews = np.load(output_file_names[2])
        with open(new_reviews, 'rb') as handle:
            miscellany =  pickle.load(handle)

        return u_features, v_features, new_reviews, miscellany
        
    
    file_list = [] 
    if test:
        file_list = [file_dir + i + '.json' for i in ['business_test', 'review_test', 'user_test']]
    else:
        file_list = [file_dir + i + '.json' for i in ['business', 'review', 'user']]
        
    
    #item_column_names = get_superset_of_column_names_from_file(file_list[0])
    v_features, food_category, num_v =  restuarant_loader(file_list[0])
    
    u_features, num_u  = user_loader(file_list[2])
    
    file_name = file_dir + "review_test.json"
    data = pd.read_json(file_name, lines=True)

    new_item_ids, item_id_dict, num_item = remapping(data['business_id'].as_matrix().astype(np.string_))
    new_user_ids, user_id_dict, num_user = remapping(data['user_id'].as_matrix().astype(np.string_))
    
    
    u_features['user_id'] = u_features['user_id'].apply(lambda x: user_id_dict[x] if x in user_id_dict.keys() else None)
    v_features['business_id'] = v_features['business_id'].apply(lambda x: item_id_dict[x] if x in item_id_dict.keys() else None)
    
    u_features = u_features[~u_features['user_id'].isnull()]
    v_features = v_features[~v_features['business_id'].isnull()]
        
    u_features.to_pickle(output_file_names[0])
    v_features.to_pickle(output_file_names[1])
    
    
    new_reviews = np.stack([new_item_ids, new_user_ids, data['stars'].as_matrix().astype(np.int32)], axis = 0)
    
    np.save(output_file_names[2], new_reviews)
    
    miscellany = {}
    miscellany['num_item'] = num_item
    miscellany['num_user'] = num_user
    miscellany['num_u'] = num_user
    miscellany['num_v'] = num_user
    miscellany['item_id_dict'] = item_id_dict
    miscellany['user_id_dict'] = user_id_dict

    with open(output_file_names[3], 'wb') as handle:
        pickle.dump(miscellany, handle, protocol=pickle.HIGHEST_PROTOCOL) 

    return u_features, v_features, new_reviews, miscellany


if __name__ =='__main__':
    file_dir =  "/Users/Dreamland/Documents/University_of_Washington/STAT548/project/GraphGAN/yelp_dataset/"
    
    if 'business_test.json' not in os.listdir(file_dir):
        for file in ['business', 'review', 'user']:
            create_test_file(file_dir + file)
    
    u_features, v_features, new_reviews, miscellany = data_loading(file_dir, verbose = False, test = True)





