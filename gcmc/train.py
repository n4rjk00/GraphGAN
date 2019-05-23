from pipeline import preprocessing, get_input_fn
from model import get_model_fn


import tensorflow as tf
import functools
import sys
import numpy as np

def main():
    tf.logging.set_verbosity(tf.logging.INFO)
    
    run_config=tf.estimator.RunConfig(
            model_dir=FLAGS.model_dir,
            save_checkpoints_secs=20,
            save_summary_steps=100)

    
    #file_dir = '/Users/Dreamland/Documents/University_of_Washington/STAT548/project/GraphGAN/yelp_dataset/'

    adj_mat_list, user_norm, item_norm,\
                u_features_tensor_dict, v_features_tensor_dict, new_reviews, miscellany,\
                N, num_train, num_val, num_test, train_idx, val_idx, test_idx = preprocessing(file_dir, verbose=True, test= True)

    
    
    model_params = tf.contrib.training.HParams(
    batch_size = FLAGS.batch_size, 
    dropout=FLAGS.dropout)
    
    
    item_type_dict = {k:v.dtype for k, v in v_features_tensor_dict.items()}
    item_feature_columns = get_item_feature_columns(miscellany['business_vocab_list'], item_type_dict)

    user_type_dict = {k:v.dtype for k, v in u_features_tensor_dict.items()}
    user_feature_columns = get_user_feature_columns(user_type_dict)
    
    input_additional_info = {}
    for name in ['adj_mat_list', 'user_norm', 'item_norm', 'new_reviews', 'num_train', 'num_val','num_test', 'train_idx', 'val_idx', 'test_idx']:
        exec("input_additional_info[{0!r}] = {0}".format(name))
    
    input_fn=  get_input_fn(tf.estimator.ModeKeys.TRAIN, model_params, **input_additional_info)
    
    model_additional_info = {}
    model_additional_info['u_features'] = u_features_tensor_dict
    model_additional_info['v_features'] = v_features_tensor_dict
    
    
    estimator = tf.estimator.Estimator(
            model_fn=get_model_fn(
                model_additional_info
            ),
            config=run_config,
            params=model_params)

    train_spec = tf.estimator.TrainSpec(input_fn=get_input_fn(
        tf.estimator.ModeKeys.TRAIN, params,
        input_additional_info), max_steps=FLAGS.max_steps)

    eval_spec = tf.estimator.EvalSpec(input_fn=get_input_fn(
        tf.estimator.ModeKeys.EVAL,
        params,
        input_addtional_info))

    tf.estimator.train_and_evaluate(estimator, train_spec, eval_spec)

    
    
if __name__ == "__main__":
    
    
    #TODO: add parameters needed later on.
    flags = tf.app.flags
    FLAGS = flags.FLAGS

    flags.DEFINE_integer('dim_embedding', 2
    "dimension of user and item embedding")
    flags.DEFINE_integer('max_steps',10,
    "Number of training steps.")
    flags.DEFINE_integer('batch_size', 1024,
    "Number of observations in a sample")
    
    #directory of various files
    flags.DEFINE_string('model_dir', 'tmp/',
    "Path for storing the model checkpoints.")

    flags.DEFINE_float('dropout',0.2,
    "Dropout used for lstm layers.")

    tf.app.run(main=main)