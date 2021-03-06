# -*-coding:utf-8-*-
from __future__ import print_function
import math
import os
import sys
import timeit
import h5py
import numpy
from keras.layers import Dense, Dropout, Activation, Flatten, Input, Dot, concatenate, Lambda
from keras.layers import Convolution2D, MaxPooling2D, Embedding, Concatenate
import Config as config
import tensorflow as tf
from keras.models import Model
from keras import losses
from keras import backend as K
import Data as data
from Data import load_dataset_le
from Data.transform2_le import Stream
from Data.valid_transform2_le import VStream
from keras.optimizers import SGD, Adam
from keras.models import load_model
import time
rearth = float(6371)
deg2rad = float(3.141592653589793 / 180)
name = 'adam_kaggle_le.hdf5'


def Embedding_Conv_Mlp(batch_size, snapshot_train, snapshot_valid, week_of_year, day_of_week, qhour_of_day, taxi_id
                       , week_of_year_valid, day_of_week_valid, qhour_of_day_valid, taxi_id__valid, train_dest,
                       valid_dest, epoch):
    tf.Session()
    print("hello")
    if (epoch == 0):
        input_1 = Input(shape=(30, 30, 4))
        input_2 = Input(shape=(1,))
        input_3 = Input(shape=(1,))
        input_4 = Input(shape=(1,))
        input_5 = Input(shape=(1,))
        layer1_output = Convolution2D(filters=20, kernel_size=(5, 5), data_format='channels_last',
                                      kernel_initializer='glorot_uniform', activation='relu')(input_1)

        layer1_output = MaxPooling2D(pool_size=(2, 2), strides=(2, 2), padding='valid', data_format='channels_last')(
            layer1_output)

        layer2_output = Convolution2D(filters=50, kernel_size=(5, 5), data_format='channels_last',
                                      kernel_initializer='glorot_uniform', activation='relu')(layer1_output)

        layer2_output = MaxPooling2D(pool_size=(2, 2), strides=(2, 2), padding='valid', data_format='channels_last')(
            layer2_output)

        flatten = Flatten()(layer2_output)
        e_week_of_year = Embedding(52, 10, embeddings_initializer='glorot_uniform')(input_2)
        e_day_of_week = Embedding(7, 10, embeddings_initializer='glorot_uniform')(input_3)
        e_qhour_of_day = Embedding(24 * 4, 10, embeddings_initializer='glorot_uniform')(input_4)
        e_taxi_id = Embedding(448, 10, embeddings_initializer='glorot_uniform')(input_5)

        mlp_input0 = concatenate([flatten, Flatten()(e_week_of_year)])
        mlp_input1 = concatenate([mlp_input0, Flatten()(e_day_of_week)])
        mlp_input2 = concatenate([mlp_input1, Flatten()(e_qhour_of_day)])
        mlp_input = concatenate([mlp_input2, Flatten()(e_taxi_id)])

        # mlp_input = Dropout(0.2)(mlp_input)
        hidden_layer = Dense(500, activation='relu', kernel_initializer='glorot_uniform')(mlp_input)

        #hidden_layer = Dropout(0.1)(hidden_layer)

        output_layer = Dense(config.tgtcls.shape[0], activation='softmax', kernel_initializer='glorot_uniform')(
            hidden_layer)

        output_1 = Lambda(dot, name='output_1')(output_layer)
        # model=Model(inputs=[inputs,inputs_e_week_of_year,inputs_e_day_of_week,inputs_e_qhour_of_day,inputs_e_taxi_id], outputs=output)
        model = Model(inputs=[input_1, input_2, input_3, input_4, input_5], outputs=output_1)
        model.compile(loss=my_loss_train, optimizer=Adam(lr=0.001, beta_1=0.9, beta_2=0.999, epsilon=1e-08))
        result1 = model.predict([snapshot_train, week_of_year, day_of_week, qhour_of_day, taxi_id])
        train_loss = my_loss(result1, train_dest)
        print("train reault is %s" % train_loss)
        model.fit_generator(
            train_data_generator(taxi_id, week_of_year, day_of_week, qhour_of_day, snapshot_train, train_dest,
                                 batch_size), steps_per_epoch=(train_dest.shape[0] // batch_size), epochs=3,
            validation_data=(
            [snapshot_valid, week_of_year_valid, day_of_week_valid, qhour_of_day_valid, taxi_id__valid], [valid_dest]))
        result = model.predict(
            [snapshot_valid, week_of_year_valid, day_of_week_valid, qhour_of_day_valid, taxi_id__valid])
        loss = my_loss(result, valid_dest)
        print("result is %s" % loss)
        if (math.isnan(loss)):
            model = load_model(name, custom_objects={'dot': dot, 'tf': tf, 'numpy': numpy, 'config': config,
                                                     'my_loss_train': my_loss_train})
            print("roll back!!!!!!!!!")

        model.save(name)
    else:
        model = load_model(name,
                           custom_objects={'dot': dot, 'tf': tf, 'numpy': numpy, 'config': config,
                                           'my_loss_train': my_loss_train})
        model.fit_generator(
            train_data_generator(taxi_id, week_of_year, day_of_week, qhour_of_day, snapshot_train, train_dest,
                                 batch_size), steps_per_epoch=(train_dest.shape[0] // batch_size), epochs=3,
            validation_data=(
                [snapshot_valid, week_of_year_valid, day_of_week_valid, qhour_of_day_valid, taxi_id__valid],
                [valid_dest]))
	time_start=time.time()
        result = model.predict(
            [snapshot_valid, week_of_year_valid, day_of_week_valid, qhour_of_day_valid, taxi_id__valid])
        time_end=time.time()
	real_time=time_end-time_start
	loss = my_loss(result, valid_dest)
        print("result is %s" % loss)
	print("real time is %s"%real_time )
        if (math.isnan(loss)):
            model = load_model(name, custom_objects={'dot': dot, 'tf': tf, 'numpy': numpy, 'config': config,
                                                     'my_loss_train': my_loss_train})
            print("roll back!!!!!!!!!")
        # print("result is %s" % loss)
        #model.save(name)

        K.clear_session()


def my_loss(a, b):
    lat1 = a[:, 0] * deg2rad
    lon1 = a[:, 1] * deg2rad
    lat2 = b[:, 0] * deg2rad
    lon2 = b[:, 1] * deg2rad
    x = (lon2 - lon1) * numpy.cos((lat1 + lat2) / 2)
    y = (lat2 - lat1)
    # return numpy.mean(((numpy.square(x) + numpy.square(y)) * 6371*6371))

    return numpy.mean((numpy.sqrt(numpy.square(x) + numpy.square(y)) * 6371))


def my_loss_train(a, b):
    lat1 = a[:, 0] * deg2rad
    lon1 = a[:, 1] * deg2rad
    lat2 = b[:, 0] * deg2rad
    lon2 = b[:, 1] * deg2rad
    x = (lon2 - lon1) * K.cos((lat1 + lat2) / 2)
    y = (lat2 - lat1)
    return K.mean((K.sqrt((K.square(x) + K.square(y))) * rearth))


def loss1(a, b):
    lat1 = a[:, 0] * deg2rad
    lon1 = a[:, 1] * deg2rad
    lat2 = b[:, 0] * deg2rad
    lon2 = b[:, 1] * deg2rad
    x = (lon2 - lon1) * K.cos((lat1 + lat2) / 2)
    y = (lat2 - lat1)
    return K.mean((K.sqrt(K.square(x) + K.square(y)) * rearth))


def dot(inputs):
    a = inputs
    classes = tf.convert_to_tensor(numpy.array(config.tgtcls), name='classes')
    return K.dot(a, classes)


def train_data_generator(taxi_id_train_, week_of_year_train_, day_of_week_train_, qhour_of_day_train,
                         snapshot_train_, dest_train_, batch_size):
    xlen = taxi_id_train_.shape[0]
    steps = xlen // batch_size
    shuffle_index = numpy.arange(dest_train_.shape[0])
    # numpy.random.shuffle(shuffle_index)
    # idx = numpy.arange(xlen)
    # numpy.random.shuffle(idx)
    # batches = [idx[range(batch_size * i, min(xlen, batch_size * (i + 1)))] for i in
    #          range(xlen / batch_size)]
    counter = 0
    while True:
        index_batch = shuffle_index[batch_size * counter:batch_size * (counter + 1)]
        taxi_id_train_list = taxi_id_train_[index_batch]
        week_of_year_train_list = week_of_year_train_[index_batch]
        day_of_week_train_list = day_of_week_train_[index_batch]
        qhour_of_day_train_list = qhour_of_day_train[index_batch]
        snapshot_train_list = snapshot_train_[index_batch, :, :, :]
        dest_train_list = dest_train_[index_batch, :]
        counter += 1
        yield [snapshot_train_list, week_of_year_train_list, day_of_week_train_list, qhour_of_day_train_list,
               taxi_id_train_list], [dest_train_list]
        if (counter == steps - 1):
            # numpy.random.shuffle(shuffle_index)
            counter = 0


def test_conv_mlp(learning_rate=0.01, n_epochs=10, batch_size=5000):
    conv_dim = 30

    dataset = load_dataset_le.Dataset('/home/sqh/workspace/T-CONV/data/',
                                      '/home/sqh/workspace/T-CONV/logs/log_load_file_g')

    [trip_id, call_type, origin_call, origin_stand, taxi_id,
     timestamp, day_type, missing_data, latitude, longitude, dest_latitude,
     dest_longitude] = dataset.load_taxi_data_valid()
    valid_stream = VStream(trip_id, call_type, origin_call, origin_stand, taxi_id,
                           timestamp, day_type, missing_data, latitude, longitude, dest_latitude, dest_longitude,
                           conv_dim)
    start_time=time.time()
    [valid_epoch, origin_call_valid_, origin_stand_valid_, day_type_valid_, taxi_id_valid_, \
     week_of_year_valid_, day_of_week_valid_, qhour_of_day_valid_, \
     snapshot_valid_, first_last_traj_valid, dest_valid_] = valid_stream.get_data_batch_conv(19770)
    end_time=time.time()
    print(end_time-start_time)
    # n_train_batches = train_stream.get_size() // batch_size
    n_valid_batches = valid_stream.get_size() // batch_size
    # print("train_stream is %s" % train_stream.get_size())
    print("valid_stream is %s" % valid_stream.get_size())

    # print("n_train_batches is %s" % n_train_batches)
    print("n_vaild_batches is %s" % n_valid_batches)
    if n_valid_batches < 1:
        n_valid_batches = 1
    [trip_id, call_type, origin_call, origin_stand, taxi_id,timestamp, day_type, missing_data, latitude, longitude] = dataset.load_taxi_data_train()
    train_stream = Stream(trip_id, call_type, origin_call, origin_stand, taxi_id,timestamp, day_type, missing_data, latitude, longitude, conv_dim)

    print('... training')

    epoch = 0
    for i in range(1600000):
        [real_epoch, origin_call_train_, origin_stand_train_, day_type_train_, taxi_id_train_, week_of_year_train_, \
         day_of_week_train_, qhour_of_day_train_, snapshot_train_, first_last_traj_train_,
         dest_train_] = train_stream.get_data_batch_conv(100000)
        Embedding_Conv_Mlp(batch_size, snapshot_train_, snapshot_valid_, week_of_year_train_, day_of_week_train_,
                           qhour_of_day_train_, taxi_id_train_,
                           week_of_year_valid_, day_of_week_valid_, qhour_of_day_valid_, taxi_id_valid_, dest_train_,
                           dest_valid_, epoch)
        epoch += 1


if __name__ == '__main__':
    test_conv_mlp()
