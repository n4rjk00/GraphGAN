import os
#os.environ['CUDA_VISIBLE_DEVICES'] = '0'
#os.environ['TF_CPP_MIN_LOG_LEVEL'] = '2'
import logging
#tf.get_logger().setLevel(logging.ERROR)
#logging.getLogger('tensorflow').setLevel(logging.ERROR)

from pipeline import preprocessing, get_input_fn, get_item_feature_columns, get_user_feature_columns, df2tensor, get_type_dict
from estimator_gcmc import gcmc_model_fn


import functools
import sys
import numpy as np


import tensorflow as tf

def main(args):    
    tf.logging.set_verbosity(tf.logging.INFO)    
    #file_dir = '/Users/Dreamland/Documents/University_of_Washington/STAT548/project/GraphGAN/yelp_dataset/'
    file_dir = '/home/FDSM_lhn/GraphGAN/yelp_dataset/'
    #file_dir = 'yelp_dataset/'
    adj_mat_list, user_norm, item_norm,\
                u_features, v_features, new_reviews, miscellany,\
                N, num_train, num_val, num_test, train_idx, val_idx, test_idx = preprocessing(file_dir, verbose=True, test= False)

    session_config = tf.ConfigProto(
        log_device_placement=True,
        inter_op_parallelism_threads=0,
        intra_op_parallelism_threads=0,
        allow_soft_placement=True)

    session_config.gpu_options.allow_growth = True
    session_config.gpu_options.allocator_type = 'BFC'
    run_config=tf.estimator.RunConfig(
            model_dir=FLAGS.model_dir,
    #        session_config = session_config,
            save_checkpoints_secs=20,
            save_summary_steps=100)

    item_type_dict = get_type_dict(v_features)
    user_type_dict = get_type_dict(u_features)
    
    item_feature_columns = get_item_feature_columns(miscellany['business_vocab_list'], item_type_dict)
    user_feature_columns = get_user_feature_columns(user_type_dict)
    
    input_additional_info = {}
    for name in ['adj_mat_list', 'user_norm', 'item_norm', 'new_reviews', 'num_train', 'num_val','num_test', 'train_idx', 'val_idx', 'test_idx']:
        exec("input_additional_info[{0!r}] = {0}".format(name))
    
    input_additional_info['u_features'] = u_features
    input_additional_info['v_features'] = v_features
    input_additional_info['col_mapper'] = miscellany['col_mapper']

    
#     temp_item_feature_columns = item_feature_columns
#     item_feature_columns =[]
#     for feat_col in temp_item_feature_columns:
#         if 'categories' not in feat_col.name:
#             item_feature_columns.append(feat_col)



    model_params = tf.contrib.training.HParams(
    num_users = len(user_norm),
    num_items = len(item_norm),
    batch_size=args.batch_size,
    learning_rate=args.learning_rate,
    dim_user_raw=args.dim_user_raw,
    dim_item_raw=args.dim_item_raw,
    dim_user_conv=args.dim_user_conv,
    dim_item_conv=args.dim_item_conv,
    dim_user_embedding=args.dim_user_embedding,
    dim_item_embedding=args.dim_item_embedding,
    classes=5,
    dropout=args.dropout,
    user_features_columns =user_feature_columns,
    item_features_columns =item_feature_columns)
    

    estimator = tf.estimator.Estimator(
            gcmc_model_fn,
            config=run_config,
            params=model_params)

    train_spec = tf.estimator.TrainSpec(input_fn=get_input_fn(
        tf.estimator.ModeKeys.TRAIN, model_params,
        **input_additional_info), max_steps=FLAGS.max_steps)

    eval_spec = tf.estimator.EvalSpec(input_fn=get_input_fn(
        tf.estimator.ModeKeys.EVAL,
        model_params,
        **input_additional_info))

    tf.estimator.train_and_evaluate(estimator, train_spec, eval_spec)


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--batch_size', default=1024, type=int, help= "assign batchsize for training and eval")
    parser.add_argument('--learning_rate', default=0.001,type=float, help= "learning rate for training")
    parser.add_argument('--dropout', default=0.2, type=float, help= "dropout rate")
    parser.add_argument('--max_steps', default = 10, type=int, help="Max steps to train in trainSpec")
    parser.add_argument('--model_dir', default = "tmp/", help="Directory to save model files")

    parser.add_argument('--dim_user_raw', default=32, type=int, help="num of hidden units")
    parser.add_argument('--dim_item_raw', default=32, type=int, help="num of hidden units")
    parser.add_argument('--dim_user_conv', default=32, type=int, help="num of hidden units")
    parser.add_argument('--dim_item_conv', default=32, type=int, help="num of hidden units")
    parser.add_argument('--dim_user_embedding', default=5*32, type=int, help="num of hidden units")
    parser.add_argument('--dim_item_embedding', default=5*32, type=int, help="num of hidden units")

    # #
    # args = parser.parse_args()
    args = parser.parse_args(['--max_steps=1000',
                              '--batch_size=10000',
                              '--learning_rate=0.01',
                              '--dropout=0.5'
                              ])
    main(args)
