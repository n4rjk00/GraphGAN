import numpy as np
from data_utils import data_loading
from scipy.sparse import csr_matrix


import tensorflow as tf
from tensorflow.feature_column import indicator_column,numeric_column, embedding_column, bucketized_column,categorical_column_with_vocabulary_list



        
def get_item_feature_columns(business_vocab_list, item_type_dict):
    
    items_feature_columns = []
    
    bucketized_boundary = {'stars': [2.5, 4]}
    embedding_size = {"categories": 8,
            "city": 4}
    
    for k, v in business_vocab_list.items():
        
        if k in ['review_count']:
            col = numeric_column(k, default_value = 0, dtype= item_type_dict[k])
        elif k in ['stars']:
            col = bucketized_column(numeric_column(k, default_value = 0, dtype= item_type_dict[k]), bucketized_boundary[k])
        elif k in ['categories', 'city']:
            col = embedding_column(categorical_column_with_vocabulary_list(k, sorted(v), default_value = -1, dtype= item_type_dict[k]), dimension = embedding_size[k])
        else:   
            col = indicator_column(categorical_column_with_vocabulary_list(k, sorted(v), default_value = -1, dtype= item_type_dict[k]))

        items_feature_columns.append(col)

    return items_feature_columns


def get_user_feature_columns(user_type_dict):
    items_feature_columns = []
    for k, v in user_type_dict.items():
        col = numeric_column(k, default_value = 0, dtype= v)
        items_feature_columns.append(col)
    return items_feature_columns


def get_user_feature_columns(user_features_list):
    
    useless_features = ['name', 'yelping_since', 'user_id']
    
    user_feature_columns = []
    for k in user_features_list:
        if k not in useless_features:
            col = numeric_column(k, default_value = 0)
            user_feature_columns.append(col)
    
    return user_feature_columns

def list2sparsetensor(list_feat, feat_col_mapper):
    indices = []
    value = []
    
    for row, cur_list in enumerate(list_feat):
        if isinstance(cur_list, list):
            for cate in cur_list:
                if cate != '' and cate != -1:
                    indices.append([row, feat_col_mapper[cate]])
                    value.append(cate)
        else:
            # for case where each element is not list but single one
            if cur_list != '' and cur_list != -1: 
                indices.append([row, feat_col_mapper[cur_list]])
                value.append(cur_list)
            

    indices = tf.convert_to_tensor(indices, tf.int64)
    value = tf.convert_to_tensor(value, tf.string) 
    
    return tf.SparseTensor(indices, value, dense_shape = [len(list_feat), len(feat_col_mapper)])
    

def df2tensor(features, col_mapper):
    
    item_datatypes = features.dtypes.iteritems()
    result_dict = features.to_dict(orient = 'list')

    #col_mapper is only useful for item feature
    for k, v in item_datatypes:
        if k in ['categories', 'city'] :
            result_dict[k] = list2sparsetensor(result_dict[k], col_mapper[k])
            continue
        if v == np.object:
            result_dict[k] = tf.convert_to_tensor(result_dict[k], dtype = tf.string)
        elif v == np.float and k in ['stars', 'average_stars']:
            result_dict[k] = tf.convert_to_tensor(result_dict[k], dtype = tf.float64)
        else:
            result_dict[k] = tf.convert_to_tensor(np.array(result_dict[k]).astype(np.int64), dtype = tf.int64)
    
    return result_dict


def create_trainvaltest_split(N, verbose):
    """
    we have 6million links total
    
    """
    
    all_idx = np.arange(N)
    np.random.seed(129)
    np.random.shuffle(all_idx)
    test_prop = 0.1
    val_prop = 0.05
    split2 = int(N * (1- test_prop))
    num_val = int(split2 * 0.05)
    
    split1 = split2 - num_val
    
    
    train_idx, val_idx, test_idx = np.split(all_idx, [split1, split2])
    if verbose:
        print("We have {} training rating, {} val rating and {}".format(split1, split2-split1, N- split2))
    
    

    return split1, split2-split1, N- split2, train_idx, val_idx, test_idx



def preprocessing(file_dir, verbose = True ,test= False):

    u_features, v_features, new_reviews, miscellany = data_loading(file_dir, verbose = verbose, test = test)
    N = new_reviews.shape[0]
    num_item = miscellany['num_item']
    num_user = miscellany['num_user']
    
    num_train, num_val, num_test, train_idx, val_idx, test_idx = create_trainvaltest_split(N, verbose= verbose)
    
    train_reviews = new_reviews[train_idx]
    adj_mat = csr_matrix((train_reviews[:,2], (train_reviews[:,0], train_reviews[:,1])), shape = (num_user, num_item))
    adj_mat_list = []
    
    for star in range(1, 6):
        new_sparse = csr_matrix(adj_mat ==star, dtype = np.int)
        adj_mat_list.append(new_sparse)
        
    #normalization 
    tot_adj = np.sum(adj_mat_list)
    
    user_node_degree = np.array(tot_adj.sum(axis= 1)).squeeze().astype(np.float)
    item_node_degree = np.array(tot_adj.sum(axis= 0)).squeeze().astype(np.float)
    
    user_node_degree[user_node_degree==0] = np.inf
    item_node_degree[item_node_degree==0] = np.inf
    
    user_norm = 1/user_node_degree
    item_norm = 1/item_node_degree
    
    
    for colname in v_features.columns:
        if v_features[colname].dtype == np.object:
            v_features[colname].fillna("", inplace=True)
        else:
            v_features[colname].fillna(-1, inplace=True)
    v_features['categories']= v_features['categories'].str.split(', ')
    
    u_features.fillna(0, inplace=True)

    #Note the categories part for item will still be list type inorder for the furthur slice processing

    # return adj_mat_list, user_norm, item_norm,\
    #         u_features, v_features, new_reviews, miscellany,\
    #         N, num_train, num_val, num_test, train_idx, val_idx, test_idx

    
    #This implementation slice after input  
    
    return adj_mat_list, user_norm, item_norm,\
            u_features, v_features, new_reviews, miscellany,\
            N, num_train, num_val, num_test, train_idx, val_idx, test_idx
    


def get_input_fn(mode, params, **input_additional_info):
    """Creates an input_fn that stores all the data in memory.
    Args:
     mode: one of tf.contrib.learn.ModeKeys.{TRAIN, INFER, EVAL}
    params: tf.contrib.training.HParams including batch_size, etc
    Returns:
      A valid input_fn for the model estimator.
    """
    
    #input_additional_info
    adj_mat_list = input_additional_info['adj_mat_list']
    user_norm = input_additional_info['user_norm']
    item_norm = input_additional_info['item_norm']
    new_reviews = input_additional_info['new_reviews']
    num_train = input_additional_info['num_train']
    num_val = input_additional_info['num_val']
    num_test = input_additional_info['num_test']
    train_idx = input_additional_info['train_idx']
    val_idx = input_additional_info['val_idx']
    test_idx = input_additional_info['test_idx']

    u_features = input_additional_info['u_features']
    v_features = input_additional_info['v_features']
    col_mapper = input_additional_info['col_mapper']
    
    
    def _input_fn():
        """Estimator's input_fn.
        Returns:
        A tuple of:
        - Dictionary of string feature name to `Tensor`.
        - `Tensor` of target labels.
        """
        if mode == tf.estimator.ModeKeys.TRAIN:
            cur_size = num_train
            cur_idx = train_idx
        elif mode == tf.estimator.ModeKeys.EVAL:
            cur_size = num_val
            cur_idx = val_idx
        else:
            cur_size = num_test
            cur_idx = test_idx
        
        dataset = tf.data.Dataset.range(cur_size)
        dataset = dataset.repeat()
        dataset = dataset.shuffle(buffer_size=cur_size)
        dataset = dataset.batch(params.batch_size)
        idx = dataset.make_one_shot_iterator().get_next()

        # TODO: check this
        with tf.Session().as_default():
            idx = idx.eval().squeeze()

        # idx = idx.eval().squeeze()
        
        size = len(idx)
        rating_idx = cur_idx[idx]
        
        features = {}
        miscellany_data = dict()
        cur_review = new_reviews[rating_idx]
        
        user_id = cur_review[:, 0]
        item_id = cur_review[:, 1]
        
        
        num_users = params.num_users
        num_items = params.num_items
    
        for star, adj_mat in enumerate(adj_mat_list):
            item_sparse = adj_mat[:, item_id]
            user_sparse = adj_mat[user_id, :]
            
            item_neigh_id = item_sparse.getH().nonzero()[1]
            user_neigh_id = user_sparse.nonzero()[1]
                        
            item_neigh_num = item_sparse.sum(axis=0).A1
            user_neigh_num = user_sparse.sum(axis=1).A1
            
            item_row = np.repeat(np.arange(len(item_id)), item_neigh_num)
            item_indices = np.stack([item_row, item_neigh_id], axis = 1)
            #left normalization
            item_value = np.ones(len(item_neigh_id))* np.repeat(item_norm[item_id], item_neigh_num)
            
            
            user_row = np.repeat(np.arange(len(user_id)), user_neigh_num)
            user_indices = np.stack([user_row, user_neigh_id], axis = 1)
            #left normalization
            user_value = np.ones(len(user_neigh_id)) * np.repeat(user_norm[user_id], user_neigh_num)
            
            features['item_neigh_conv{}'.format(star)] = \
                tf.SparseTensor(item_indices, item_value, dense_shape = [len(item_id), num_users])
            features['user_neigh_conv{}'.format(star)] = \
                tf.SparseTensor(user_indices, user_value, dense_shape = [len(user_id), num_items])

        
        user_indices = np.stack([np.arange(len(user_id)), user_id], axis = 1)
        user_value = np.ones(len(user_id))

        item_indices = np.stack([np.arange(len(item_id)), item_id], axis = 1)
        item_value = np.ones(len(item_id))

        features['user_id'] = tf.SparseTensor(user_indices, user_value, dense_shape = [len(user_id), num_users])
        features['item_id'] = tf.SparseTensor(item_indices, item_value, dense_shape = [len(item_id), num_items])
        features['u_features'] = df2tensor(u_features, col_mapper)
        features['v_features'] = df2tensor(v_features, col_mapper)
        
        
        return features, tf.convert_to_tensor(cur_review[:,2], tf.int64)

    return _input_fn
    
    
    
