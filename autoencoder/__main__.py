# Copyright 2016 Goekcen Eraslan
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
# ==============================================================================

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

import os, sys, argparse
import numpy as np
import six
import tensorflow as tf
slim = tf.contrib.slim

from . import io, train, test, predict


def parse_args():
    parser = argparse.ArgumentParser(description='Autoencoder')
    subparsers = parser.add_subparsers(title='subcommands',
            help='sub-command help', description='valid subcommands', dest='cmd')
    subparsers.required = True

    # Preprocess subparser
    parser_preprocess = subparsers.add_parser('preprocess',
            help='Create a training set from CSV/TSV files')
    parser_preprocess.add_argument('input', type=str,
            help='Input in TSV/CSV format')
    parser_preprocess.add_argument('-o', '--output', type=str,
            help='Output file path', required=True)
    parser_preprocess.add_argument('--normtype', type=str, default='zheng',
            help='Type of size factor estimation. Possible values: deseq, zheng.'
                 ' (default: zheng)')
    parser_preprocess.add_argument('-t', '--transpose', dest='transpose',
            action='store_true', help='Transpose input matrix (default: False)')
    parser_preprocess.add_argument('--testsplit', dest='testsplit',
            action='store_true', help="Use one fold as a test set (default: False)")

    parser_preprocess.set_defaults(func=io.preprocess_with_args)

    # train subparser
    parser_train = subparsers.add_parser('train',
            help='Train an autoencoder using given training set.')
    parser_train.add_argument('trainingset', type=str,
            help="File path of the training set ")
    parser_train.add_argument('-o', '--outputdir', type=str, required=True,
            help="The directory where everything will be will be saved")
    parser_train.add_argument('-t', '--type', type=str, default='zinb-conddisp',
            help="Type of autoencoder. Possible values: normal, poisson, nb, "
                 "nb-shared, nb-conddisp, nb-fork, zinb, "
                 "zinb-shared, zinb-conddisp(default) zinb-fork")
    parser_train.add_argument('-b', '--batchsize', type=int, default=32,
            help="Batch size (default:32)")
    parser_train.add_argument('--sizefactors', dest='sizefactors',
            action='store_true', help="Normalize means by library size (default: True)")
    parser_train.add_argument('--nosizefactors', dest='sizefactors',
            action='store_false', help="Do not normalize means by library size")
    parser_train.add_argument('--norminput', dest='norminput',
            action='store_true', help="Zero-mean normalize input (default: True)")
    parser_train.add_argument('--nonorminput', dest='norminput',
            action='store_false', help="Do not zero-mean normalize inputs")
    parser_train.add_argument('--loginput', dest='loginput',
            action='store_true', help="Log-transform input (default: True)")
    parser_train.add_argument('--nologinput', dest='loginput',
            action='store_false', help="Do not log-transform inputs")
    parser_train.add_argument('-d', '--dropoutrate', type=str, default='0.0',
            help="Dropout rate (default: 0)")
    parser_train.add_argument('--batchnorm', dest='batchnorm', action='store_true',
            help="Batchnorm (default: True)")
    parser_train.add_argument('--nobatchnorm', dest='batchnorm', action='store_false',
            help="Do not use batchnorm")
    parser_train.add_argument('--l2', type=float, default=0.0,
            help="L2 regularization coefficient (default: 0.0)")
    parser_train.add_argument('--l1', type=float, default=0.0,
            help="L1 regularization coefficient (default: 0.0)")
    parser_train.add_argument('--l2enc', type=float, default=0.0,
            help="Encoder-specific L2 regularization coefficient (default: 0.0)")
    parser_train.add_argument('--l1enc', type=float, default=0.0,
            help="Encoder-specific L1 regularization coefficient (default: 0.0)")
    parser_train.add_argument('--ridge', type=float, default=0.0,
            help="L2 regularization coefficient for dropout probabilities (default: 0.0)")
    parser_train.add_argument('--gradclip', type=float, default=5.0,
            help="Clip grad values (default: 5.0)")
    parser_train.add_argument('--activation', type=str, default='elu',
            help="Activation function of hidden units (default: elu)")
    parser_train.add_argument('--optimizer', type=str, default='rmsprop',
            help="Optimization method (default: rmsprop)")
    parser_train.add_argument('--init', type=str, default='glorot_uniform',
            help="Initialization method for weights (default: glorot_uniform)")
    parser_train.add_argument('-e', '--epochs', type=int, default=500,
            help="Max number of epochs to continue training in case of no "
                 "improvement on validation loss (default: 200)")
    parser_train.add_argument('--earlystop', type=int, default=15,
            help="Number of epochs to stop training if no improvement in loss "
                 "occurs (default: 15)")
    parser_train.add_argument('--reducelr', type=int, default=10,
            help="Number of epochs to reduce learning rate if no improvement "
            "in loss occurs (default: 10)")
    parser_train.add_argument('-s', '--hiddensize', type=str, default='32,32,32',
            help="Size of hidden layers (default: 32,32,32)")
    parser_train.add_argument('-r', '--learningrate', type=float, default=None,
            help="Learning rate (default: 0.001)")
    parser_train.add_argument('--reconstruct', dest='reconstruct',
            action='store_true', help="Save mean parameter (default: True)")
    parser_train.add_argument('--no-reconstruct', dest='reconstruct',
            action='store_false', help="Do not save mean parameter")
    parser_train.add_argument('--reduce', dest='dimreduce',
            action='store_true', help="Save dim reduced matrix (default: True)")
    parser_train.add_argument('--no-reduce', dest='dimreduce',
            action='store_false', help="Do not save dim reduced matrix")
    parser_train.add_argument('--saveweights', dest='saveweights',
            action='store_true', help="Save weights (default: False)")
    parser_train.add_argument('--no-saveweights', dest='saveweights',
            action='store_false', help="Do not save weights")

    parser_train.set_defaults(func=train.train_with_args,
                              saveweights=False,
                              dimreduce=True,
                              reconstruct=True,
                              sizefactors=True,
                              batchnorm=True,
                              norminput=True,
                              loginput=True)

    # test subparser
    #parser_test = subparsers.add_parser('test', help='Test autoencoder')
    #parser_test.set_defaults(func=test.test)

    # predict subparser
    parser_predict = subparsers.add_parser('predict',
            help='make predictions on a given dataset using a pre-trained model.')
    parser_predict.add_argument('dataset', type=str,
            help="File path of the input set. It must be preprocessed using "
                 "preprocess subcommand")
    parser_predict.add_argument('modeldir', type=str,
            help="Path of the folder where model weights and arch are saved")
    parser_predict.add_argument('-o', '--outputdir', type=str,
            help="Path of the output", required=True)
    parser_predict.add_argument('-r', '--reduced', dest='reduced',
            action='store_true', help="predict input to the hidden size")
    parser_predict.add_argument('--reconstruct', dest='reconstruct',
            action='store_true', help="Save mean parameter (default: True)")
    parser_predict.add_argument('--noreconstruct', dest='reconstruct',
            action='store_false', help="Do not save mean parameter")
    parser_predict.add_argument('--reduce', dest='dimreduce',
            action='store_true', help="Save dim reduced matrix (default: True)")
    parser_predict.add_argument('--noreduce', dest='dimreduce',
            action='store_false', help="Do not save dim reduced matrix")

    parser_predict.set_defaults(func=predict.predict_with_args,
                                dimreduce=True,
                                reconstruct=True)

    return parser.parse_args()


def main():
    args = parse_args()
    args.func(args)
