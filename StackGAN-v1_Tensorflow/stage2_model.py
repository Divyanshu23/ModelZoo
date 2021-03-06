"""
Stage-2 model of StackGAN
"""

from os import PRIO_PGRP
import tensorflow as tf
from tensorflow import keras
from tensorflow.keras import Input, Model, layers


class Stage2_Model:

  def __init__(self) -> None:
      pass


  def generate_c(self,x): 
    """
    Obtain Text Conditioning Variable 
    """
    mean = x[:, :128]
    log_sigma = x[:, 128:]
    stddev = tf.math.exp(log_sigma)
    epsilon = tf.random.normal(shape=(mean.shape[1],), dtype=tf.dtypes.float32)
    c = mean + epsilon*stddev
    return c


  def build_stage1_generator(self):
      """
      Stage-I Generator Model

      Input:
        Embedded Text Description of shape (1024,)
        Random Noise of shape (100,)

      Output:
        Generated Image of shape (64,64,3) and concatenated mean and logsigma of shape (256,)
      """
      input_layer1 = Input(shape=(1024,))
      x = layers.Dense(256)(input_layer1)
      mean_logsigma = layers.LeakyReLU(alpha=0.2)(x)
  
      c = layers.Lambda(self.generate_c)(mean_logsigma)
  
      input_layer2 = Input(shape=(100,))      # Random noise vector of shape (100,)
  
      concat_input = layers.Concatenate(axis=1)([c, input_layer2])
  
      x = layers.Dense(128 * 8 * 4 * 4, kernel_initializer="glorot_normal")(concat_input)
      x = layers.ReLU()(x)
  
      x = layers.Reshape((4, 4, 128 * 8), input_shape=(128 * 8 * 4 * 4,))(x)
  
      x = layers.UpSampling2D(size=(2, 2))(x)
      x = layers.Conv2D(512, kernel_size=3, padding="same", strides=1, kernel_initializer="glorot_normal")(x)
      x = layers.BatchNormalization()(x)
      x = layers.ReLU()(x)
  
      x = layers.UpSampling2D(size=(2, 2))(x)
      x = layers.Conv2D(256, kernel_size=3, padding="same", strides=1, kernel_initializer="glorot_normal")(x)
      x = layers.BatchNormalization()(x)
      x = layers.ReLU()(x)
  
      x = layers.UpSampling2D(size=(2, 2))(x)
      x = layers.Conv2D(128, kernel_size=3, padding="same", strides=1, kernel_initializer="glorot_normal")(x)
      x = layers.BatchNormalization()(x)
      x = layers.ReLU()(x)
  
      x = layers.UpSampling2D(size=(2, 2))(x)
      x = layers.Conv2D(64, kernel_size=3, padding="same", strides=1, kernel_initializer="glorot_normal")(x)
      x = layers.BatchNormalization()(x)
      x = layers.ReLU()(x)
  
      x = layers.Conv2D(3, kernel_size=3, padding="same", strides=1, kernel_initializer="glorot_normal")(x)
      x = layers.Activation(activation='tanh')(x)
  
      stage1_gen = Model(inputs=[input_layer1, input_layer2], outputs=[x, mean_logsigma])
      return stage1_gen


  def residual_block(self,input):
      """
      Residual block in the generator network
      """
      x = layers.Conv2D(128 * 4, kernel_size=(3, 3), padding='same', strides=1)(input)
      x = layers.BatchNormalization()(x)
      x = layers.ReLU()(x)

      x = layers.Conv2D(128 * 4, kernel_size=(3, 3), strides=1, padding='same')(x)
      x = layers.BatchNormalization()(x)

      x = layers.add([x, input])
      x = layers.ReLU()(x)

      return x


  def joint_block(self,inputs):
      """
      Block to concat Two tensors in Generator
      """

      c = inputs[0]
      x = inputs[1]

      c = tf.expand_dims(c, axis=1)
      c = tf.expand_dims(c, axis=1)
      c = tf.tile(c, [1, 16, 16, 1])
      return layers.concatenate([c, x], axis=-1)


  def build_stage2_generator(self):
      """
      Stage-II generator Model
      
      Input:
        Embedded Text Description of shape (1024,)
        Image generated by Stage-I Generator of shape (64,64,3)

      Output:
        Generated Image of shape (256,256,3) and concatenated mean and logsigma of shape (256,)
      """

      # 1. CA Augmentation Network
      input_layer = Input(shape=(1024,))
      input_lr_images = Input(shape=(64, 64, 3))

      ca = layers.Dense(256)(input_layer)
      mean_logsigma = layers.LeakyReLU(alpha=0.2)(ca)
      c = layers.Lambda(self.generate_c)(mean_logsigma)


      x = layers.ZeroPadding2D(padding=(1, 1))(input_lr_images)
      x = layers.Conv2D(128, kernel_size=(3, 3), strides=1, kernel_initializer="glorot_normal")(x)
      x = layers.ReLU()(x)

      x = layers.ZeroPadding2D(padding=(1, 1))(x)
      x = layers.Conv2D(256, kernel_size=(4, 4), strides=2, kernel_initializer="glorot_normal")(x)
      x = layers.BatchNormalization()(x)
      x = layers.ReLU()(x)

      x = layers.ZeroPadding2D(padding=(1, 1))(x)
      x = layers.Conv2D(512, kernel_size=(4, 4), strides=2, kernel_initializer="glorot_normal")(x)
      x = layers.BatchNormalization()(x)
      x = layers.ReLU()(x)

      # 3. Joint
      c_code = layers.Lambda(self.joint_block)([c, x])

      x = layers.ZeroPadding2D(padding=(1, 1))(c_code)
      x = layers.Conv2D(512, kernel_size=(3, 3), strides=1, kernel_initializer="glorot_normal")(x)
      x = layers.BatchNormalization()(x)
      x = layers.ReLU()(x)

      # 4. Residual blocks
      x = self.residual_block(x)
      x = self.residual_block(x)
      x = self.residual_block(x)
      x = self.residual_block(x)

      # 5. Upsampling blocks
      x = layers.UpSampling2D(size=(2, 2))(x)
      x = layers.Conv2D(512, kernel_size=3, padding="same", strides=1, kernel_initializer="glorot_normal")(x)
      x = layers.BatchNormalization()(x)
      x = layers.ReLU()(x)

      x = layers.UpSampling2D(size=(2, 2))(x)
      x = layers.Conv2D(256, kernel_size=3, padding="same", strides=1, kernel_initializer="glorot_normal")(x)
      x = layers.BatchNormalization()(x)
      x = layers.ReLU()(x)

      x = layers.UpSampling2D(size=(2, 2))(x)
      x = layers.Conv2D(128, kernel_size=3, padding="same", strides=1, kernel_initializer="glorot_normal")(x)
      x = layers.BatchNormalization()(x)
      x = layers.ReLU()(x)

      x = layers.UpSampling2D(size=(2, 2))(x)
      x = layers.Conv2D(64, kernel_size=3, padding="same", strides=1, kernel_initializer="glorot_normal")(x)
      x = layers.BatchNormalization()(x)
      x = layers.ReLU()(x)

      x = layers.Conv2D(3, kernel_size=3, padding="same", strides=1, kernel_initializer="glorot_normal")(x)
      x = layers.Activation('tanh')(x)

      model = Model(inputs=[input_layer, input_lr_images], outputs=[x, mean_logsigma])
      return model


  def build_stage2_discriminator(self):
      """
      Stage-II Discriminator model

      Input:
        Text Embedding of shape (1024,)
        Fake Image of shape (256,256,3) generated by Generator of Stage-I

      Output:
        Classification whether the image is real (1) or fake (0)
      """
      input_layer = Input(shape=(256, 256, 3))

      x = layers.ZeroPadding2D(padding=(1, 1))(input_layer)
      x = layers.Conv2D(64, (4, 4), padding='valid', strides=2, input_shape=(256, 256, 3), kernel_initializer="glorot_normal")(x)
      x = layers.LeakyReLU(alpha=0.2)(x)

      x = layers.ZeroPadding2D(padding=(1, 1))(x)
      x = layers.Conv2D(128, (4, 4), padding='valid', strides=2, kernel_initializer="glorot_normal")(x)
      x = layers.BatchNormalization()(x)
      x = layers.LeakyReLU(alpha=0.2)(x)

      x = layers.ZeroPadding2D(padding=(1, 1))(x)
      x = layers.Conv2D(256, (4, 4), padding='valid', strides=2, kernel_initializer="glorot_normal")(x)
      x = layers.BatchNormalization()(x)
      x = layers.LeakyReLU(alpha=0.2)(x)

      x = layers.ZeroPadding2D(padding=(1, 1))(x)
      x = layers.Conv2D(512, (4, 4), padding='valid', strides=2, kernel_initializer="glorot_normal")(x)
      x = layers.BatchNormalization()(x)
      x = layers.LeakyReLU(alpha=0.2)(x)

      x = layers.ZeroPadding2D(padding=(1, 1))(x)
      x = layers.Conv2D(1024, (4, 4), padding='valid', strides=2, kernel_initializer="glorot_normal")(x)
      x = layers.BatchNormalization()(x)
      x = layers.LeakyReLU(alpha=0.2)(x)

      x = layers.ZeroPadding2D(padding=(1, 1))(x)
      x = layers.Conv2D(2048, (4, 4), padding='valid', strides=2, kernel_initializer="glorot_normal")(x)
      x = layers.BatchNormalization()(x)
      x = layers.LeakyReLU(alpha=0.2)(x)

      x = layers.Conv2D(1024, (1, 1), padding='same', strides=1, kernel_initializer="glorot_normal")(x)
      x = layers.BatchNormalization()(x)
      x = layers.LeakyReLU(alpha=0.2)(x)

      x = layers.Conv2D(512, (1, 1), padding='same', strides=1, kernel_initializer="glorot_normal")(x)
      x = layers.BatchNormalization()(x)
      x = layers.LeakyReLU(alpha=0.2)(x)

      input_layer2 = Input(shape=(1024,))
      compressed_embedding = layers.Dense(128)(input_layer2)
      compressed_embedding = layers.ReLU()(compressed_embedding)
      compressed_embedding = tf.reshape(compressed_embedding, (-1, 1, 1, 128))
      compressed_embedding = tf.tile(compressed_embedding, (1, 4, 4, 1))

      merged_input = layers.concatenate([x, compressed_embedding])

      x3 = layers.Conv2D(64 * 8, kernel_size=1, padding="same", strides=1, kernel_initializer="glorot_normal")(merged_input)
      x3 = layers.BatchNormalization()(x3)
      x3 = layers.LeakyReLU(alpha=0.2)(x3)
      x3 = layers.Flatten()(x3)
      x3 = layers.Dense(1)(x3)
      x3 = layers.Activation('sigmoid')(x3)

      stage2_dis = Model(inputs=[input_layer, input_layer2], outputs=[x3])
      return stage2_dis

  def build_adversarial_model(self, gen_model2, dis_model, gen_model1):
    
      input_layer1 = Input(shape=(1024,))
      input_layer2 = Input(shape=(100,))
      input_layer3 = Input(shape=(1024,))

      gen_model1.trainable = False
      dis_model.trainable = False

      lr_images, mean_logsigma1 = gen_model1([input_layer1, input_layer2])
      hr_images, mean_logsigma2 = gen_model2([input_layer1, lr_images])
      valid = dis_model([hr_images, input_layer3])

      model = Model(inputs=[input_layer1, input_layer2, input_layer3], outputs=[valid, mean_logsigma2])
      return model