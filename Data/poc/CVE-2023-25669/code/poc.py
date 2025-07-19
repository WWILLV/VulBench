import tensorflow as tf
import numpy as np

@tf.function(jit_compile=True)
def test():
   y = tf.raw_ops.AvgPoolGrad(orig_input_shape=[1,0,0,0], grad=[[[[0.39117979]]]], ksize=[1,0,0,0], strides=[1,0,0,0], padding="SAME", data_format="NCHW")
   return y

print(test())