#!/bin/sh

# script to reproduce seq2seq with attention model on the bash dataset

ARGS=${@:1}

./run.sh --batch_size 16 --encoder_input_keep 0.5 --decoder_input_keep 0.5 --encoder_output_keep 0.5 --decoder_output_keep 0.5 --dataset bash.final --attention_input_keep 0.5 --attention_output_keep 0.5 --decoding_algorithm beam_search --beam_size 100 --alpha 1.0 --encoder_topology birnn --dim 400 --num_epochs 14 --steps_per_epoch 4000 --num_layers 1 --learning_rate 0.0001 --beta 0 --create_fresh_params --normalized --use_attention --num_nn_slot_filling 10 ${ARGS}