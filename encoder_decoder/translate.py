#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Translation model that generates bash commands given natural language descriptions.
"""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

import os
import sys

sys.path.append(os.path.join(os.path.dirname(__file__), "..", "bashlex"))
sys.path.append(os.path.join(os.path.dirname(__file__), "..", "eval"))
sys.path.append(os.path.join(os.path.dirname(__file__), "..", "seq2seq"))
sys.path.append(os.path.join(os.path.dirname(__file__), "..", "seq2tree"))

import cPickle as pickle
import itertools
import math
import numpy as np
import random
import time
from tqdm import tqdm

import tensorflow as tf
from tensorflow.python.util import nest

import data_utils, graph_utils
import decode_tools, hyperparam_range
import eval_tools
import parse_args
from seq2seq_model import Seq2SeqModel
from seq2tree_model import Seq2TreeModel

FLAGS = tf.app.flags.FLAGS

parse_args.define_input_flags()

# We use a number of buckets and pad to the closest one for efficiency.
if FLAGS.decoder_topology in ['basic_tree']:
    _buckets = [(5, 10), (10, 20), (15, 30), (20, 40), (30, 50), (40, 66)]
elif FLAGS.decoder_topology in ['rnn']:
    _buckets = [(5, 5), (10, 10), (15, 15), (20, 20), (30, 30), (40, 40)]
else:
    raise ValueError("Unrecognized decoder topology: {}."
                     .format(FLAGS.decoder_topology))


def create_model(session, forward_only, construct_model_dir=True):
    """
    :param source_vocab_size: size of the source vocabulary.
    :param target_vocab_size: size of the target vocabulary.
    :param max_source_length: maximum length of the source sequence
        (necessary for static graph construction).
    :param max_target_length: maximum length of the target sequence
        (necessary for static graph construction).
    :param dim: dimension of each layer in the model.
    :param num_layers: number of layers in the model.
    :param max_gradient_norm: gradients are clipped to maximally this norm.
    :param batch_size: the size of the batches used during training or decoding.
    :param learning_rate: learning rate to start with.
    :param learning_rate_decay_factor: decay learning rate by this much when needed.
            not import if the adam optimizer is used.
    :param input_keep_prob: proportion of input to keep if dropout is used.
    :param output_keep_prob: proportion of output to keep if dropout is used.
    :param num_samples: number of samples for sampled softmax.

    :param decoder_topology: topology of the tree rnn decoder.
    :param decoding_algorithm: decoding algorithm used.
    :param
    """
    if FLAGS.decoder_topology in ['basic_tree']:
        return graph_utils.create_model(session, FLAGS, Seq2TreeModel, _buckets,
                                                        forward_only, construct_model_dir)
    elif FLAGS.decoder_topology in ['rnn']:
        return graph_utils.create_model(session, FLAGS, Seq2SeqModel, _buckets,
                                                        forward_only, construct_model_dir)
    else:
        raise ValueError("Unrecognized decoder topology: {}."
                         .format(FLAGS.decoder_topology))


def train(train_set, dev_set, construct_model_dir=True):
    with tf.Session(config=tf.ConfigProto(allow_soft_placement=True,
        log_device_placement=FLAGS.log_device_placement)) as sess:
        # Create model.
        model, global_epochs = create_model(sess, forward_only=False,
                                            construct_model_dir=construct_model_dir)

        train_bucket_sizes = [len(train_set[b]) for b in xrange(len(_buckets))]
        train_total_size = float(sum(train_bucket_sizes))

        # A bucket scale is a list of increasing numbers from 0 to 1 that we'll use
        # to select a bucket. Length of [scale[i], scale[i+1]] is proportional to
        # the size if i-th training bucket, as used later.
        train_buckets_scale = [sum(train_bucket_sizes[:i + 1]) / train_total_size
                               for i in xrange(len(train_bucket_sizes))]

        loss, dev_loss, epoch_time = 0.0, 0.0, 0.0
        current_step = 0
        previous_losses = []
        previous_dev_losses = []

        for t in xrange(FLAGS.num_epochs):
            print("Epoch %d" % (t+1))

            start_time = time.time()

            # progress bar
            for _ in tqdm(xrange(FLAGS.steps_per_epoch)):
                time.sleep(0.01)
                random_number_01 = np.random.random_sample()
                bucket_id = min([i for i in xrange(len(train_buckets_scale))
                                 if train_buckets_scale[i] > random_number_01])
                formatted_example = model.get_batch(train_set, bucket_id)
                _, step_loss, _, _ = model.step(sess, formatted_example, bucket_id,
                                             forward_only=False)
                loss += step_loss
                current_step += 1

            epoch_time = time.time() - start_time

            # Once in a while, we save checkpoint, print statistics, and run evals.
            if t % FLAGS.epochs_per_checkpoint == 0:

                # Print statistics for the previous epoch.
                loss /= FLAGS.steps_per_epoch
                ppx = math.exp(loss) if loss < 300 else float('inf')
                print("learning rate %.4f epoch-time %.2f perplexity %.2f" % (
                    model.learning_rate.eval(), epoch_time, ppx))

                # Decrease learning rate if no improvement of loss was seen over last 3 times.
                if len(previous_losses) > 2 and loss > max(previous_losses[-3:]):
                    sess.run(model.learning_rate_decay_op)
                previous_losses.append(loss)

                checkpoint_path = os.path.join(FLAGS.train_dir, "translate.ckpt")
                # Save checkpoint and zero timer and loss.
                model.saver.save(sess, checkpoint_path, global_step=global_epochs+t+1,
                                 write_meta_graph=False)

                epoch_time, loss, dev_loss = 0.0, 0.0, 0.0
                # Run evals on development set and print the metrics.
                for bucket_id in xrange(len(_buckets)):
                    if len(dev_set[bucket_id]) == 0:
                        print("  eval: empty bucket %d" % (bucket_id))
                        continue
                    formatted_example = model.get_batch(dev_set, bucket_id)
                    _, eval_loss, output_logits, _ = model.step(sess, formatted_example, bucket_id,
                                                             forward_only=True)
                    dev_loss += eval_loss
                    eval_ppx = math.exp(eval_loss) if eval_loss < 300 else float('inf')
                    print("  eval: bucket %d perplexity %.2f" % (bucket_id, eval_ppx))

                dev_perplexity = math.exp(dev_loss/len(_buckets)) if dev_loss < 300 else float('inf')
                print("global step %d learning rate %.4f dev_perplexity %.2f" 
                        % (global_epochs+t+1, model.learning_rate.eval(), dev_perplexity))

                # Early stop if no improvement of dev loss was seen over last 3 checkpoints.
                if len(previous_dev_losses) > 2 and dev_loss > max(previous_dev_losses[-3:]):
                    return False
           
                previous_dev_losses.append(dev_loss)

                sys.stdout.flush()
      
    return True


def decode(construct_model_dir=True, verbose=True):
    with tf.Session(config=tf.ConfigProto(allow_soft_placement=True,
        log_device_placement=FLAGS.log_device_placement)) as sess:
        # Create model and load parameters.
        model, _ = create_model(sess, forward_only=True,
                                construct_model_dir=construct_model_dir)

        _, rev_nl_vocab, _, rev_cm_vocab = data_utils.load_vocab(FLAGS)
        _, dev_set, _ = load_data()

        decode_tools.decode_set(sess, model, dev_set, rev_nl_vocab, rev_cm_vocab,
                                                FLAGS, verbose)


def eval(construct_model_dir=True, verbose=True):
    with tf.Session(config=tf.ConfigProto(allow_soft_placement=True,
        log_device_placement=FLAGS.log_device_placement)) as sess:
        # Create model and load parameters.
        model, _ = create_model(sess, forward_only=True,
                                construct_model_dir=construct_model_dir)

        _, rev_nl_vocab, _, rev_cm_vocab = data_utils.load_data(FLAGS)
        _, dev_set, _ = load_data()

        return eval_tools.eval_set(model.model_dir, dev_set, rev_nl_vocab,
                                   verbose=verbose)


def manual_eval(num_eval):
    with tf.Session(config=tf.ConfigProto(allow_soft_placement=True,
        log_device_placement=FLAGS.log_device_placement)) as sess:
        # Create model and load parameters.
        model, _ = create_model(sess, forward_only=True)

        _, rev_nl_vocab, _, rev_cm_vocab = data_utils.load_data(FLAGS)
        _, dev_set, _ = load_data()

        eval_tools.manual_eval(model.model_dir, dev_set, rev_nl_vocab,
                               FLAGS.train_dir, num_eval)


def interactive_decode():
    with tf.Session(config=tf.ConfigProto(allow_soft_placement=True,
        log_device_placement=FLAGS.log_device_placement)) as sess:
        # Create model and load parameters.
        model, _ = create_model(sess, forward_only=True)

        nl_vocab, _, _, rev_cm_vocab = data_utils.load_data(FLAGS)

        decode_tools.interactive_decode(
            sess, model, nl_vocab, rev_cm_vocab, FLAGS)


def train_and_eval(train_set, dev_set):
    train(train_set, dev_set, FLAGS.num_epochs,
          construct_model_dir=False)
    tf.reset_default_graph()
    decode(construct_model_dir=False, verbose=False)
    temp_match_score, eval_match_score = eval(construct_model_dir=False,
                                              verbose=False)
    tf.reset_default_graph()
    return temp_match_score, eval_match_score


def grid_search(train_set, dev_set):
    FLAGS.create_fresh_params = True

    hyperparameters = FLAGS.tuning.split(',')
    num_hps = len(hyperparameters)
    hp_range = hyperparam_range.hyperparam_range

    print("======== Grid Search ========")
    print("%d hyperparameters: " % num_hps)
    for i in xrange(num_hps):
        print("{}: {}".format(hyperparameters[i], hp_range[hyperparameters[i]]))
    print()

    grid = [v for v in hp_range[hyperparameters[0]]]
    for i in xrange(1, num_hps):
        grid = itertools.product(grid, hp_range[hyperparameters[i]])

    best_hp_set = [-1] * num_hps
    best_seed = -1
    best_temp_match_score = 0.0

    model_root_dir = FLAGS.train_dir

    for row in grid:
        row = nest.flatten(row)
        for i in xrange(num_hps):
            setattr(FLAGS, hyperparameters[i], row[i])

        print("Trying parameter set: ")
        for i in xrange(num_hps):
            print("* {}: {}".format(hyperparameters[i], row[i]))

        model_dir = os.path.join(model_root_dir, FLAGS.encoder_topology)
        model_dir += '-{}'.format(FLAGS.rnn_cell)
        if FLAGS.use_attention:
            model_dir += '-attention'
        model_dir += '-{}'.format(FLAGS.batch_size)
        model_dir += '-{}'.format(row)
        setattr(FLAGS, "train_dir", model_dir)

        num_trials = 5 if FLAGS.initialization else 1

        for t in xrange(num_trials):
            seed = random.getrandbits(32)
            tf.set_random_seed(seed)
            temp_match_score, eval_match_score = \
                train_and_eval(train_set, dev_set)
            print("Parameter set: ")
            for i in xrange(num_hps):
                print("* {}: {}".format(hyperparameters[i], row[i]))
            print("random seed: {}".format(seed))
            print("template match score = {}".format(temp_match_score))
            print("Best parameter set so far: ")
            for i in xrange(num_hps):
                print("* {}: {}".format(hyperparameters[i], best_hp_set[i]))
            print("Best random seed so far: {}".format(best_seed))
            print("Best template match score so far = {}".format(best_temp_match_score))
            if temp_match_score > best_temp_match_score:
                best_hp_set = row
                best_seed = seed
                best_temp_match_score = temp_match_score
                print("☺ New best parameter setting found")

    print()
    print("*****************************")
    print("Best parameter set: ")
    for i in xrange(num_hps):
        print("* {}: {}".format(hyperparameters[i], best_hp_set[i]))
    print("Best seed = {}".format(best_seed))
    print("Best emplate match score = {}".format(best_temp_match_score))
    print("*****************************")


# Data
def load_data(use_buckets=True):
    if use_buckets:
        return data_utils.load_data(FLAGS, _buckets)
    else:
        return data_utils.load_data(FLAGS, None)


def process_data():
    print("Preparing data in %s" % FLAGS.data_dir)

    with open(FLAGS.data_dir + "data.by.%s.dat" % FLAGS.data_split) as f:
        data = pickle.load(f)

    numFolds = len(data)
    print("%d folds" % numFolds)

    output_dir = os.path.join(FLAGS.data_dir, "seq2tree.by.%s" % FLAGS.data_split)
    data_utils.prepare_data(data, output_dir, FLAGS.nl_vocab_size, FLAGS.cm_vocab_size)


def data_statistics():
    train_set, dev_set, test_set = load_data(use_buckets=False)
    print(len(data_utils.group_data_by_nl(train_set)))
    print(len(data_utils.group_data_by_nl(dev_set)))
    print(len(data_utils.group_data_by_nl(test_set)))
    print("data count = %d" % len(data_utils.group_data_by_cm(train_set)))
    print("data count = %d" % len(data_utils.group_data_by_cm(dev_set)))
    print("data count = %d" % len(data_utils.group_data_by_cm(test_set)))


def main(_):
    # set GPU device
    os.environ["CUDA_VISIBLE_DEVICES"] = FLAGS.gpu

    if FLAGS.eval:
        eval()
    elif FLAGS.manual_eval:
        manual_eval(100)
    elif FLAGS.decode:
        decode()
    elif FLAGS.interactive_decode:
        interactive_decode()
    elif FLAGS.process_data:
        process_data()
    elif FLAGS.data_stats:
        data_statistics()
    elif FLAGS.sample_train:
        train_set, dev_set, _ = load_data(FLAGS.sample_size)
        train(train_set, dev_set)
    elif FLAGS.grid_search:
        train_set, dev_set, _ = load_data()
        grid_search(train_set, dev_set)
    else:
        train_set, dev_set, _ = load_data()
        train(train_set, dev_set)


if __name__ == "__main__":
    tf.app.run()