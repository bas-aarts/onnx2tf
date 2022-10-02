import random
random.seed(0)
import numpy as np
np.random.seed(0)
import tensorflow as tf
import onnx_graphsurgeon as gs
from utils.common_functions import (
    get_constant_or_variable,
    convert_axis,
)


def make_node(
    *,
    graph_node: gs.Node,
    tf_layers_dict: dict,
    **kwargs: dict,
):
    """TopK

    Parameters
    ----------
    graph_node: gs.Node
        graph_surgeon Node

    tf_layers_dict: dict
        optype, shape, dtype, tensorflow graph
    """
    X = get_constant_or_variable(graph_node.inputs[0])
    K = get_constant_or_variable(graph_node.inputs[1])
    Values: gs.Variable = graph_node.outputs[0]
    Indices: gs.Variable = graph_node.outputs[1]
    Values_shape = Values.shape
    Values_dtype = Values.dtype
    Indices_shape = Indices.shape
    Indices_dtype = Indices.dtype

    input_tensor = tf_layers_dict[X.name]['tf_node'] \
        if isinstance(X, gs.Variable) else X
    k_tensor = tf_layers_dict[K.name]['tf_node'] \
        if isinstance(K, gs.Variable) else K
    tensor_rank = len(input_tensor.shape)

    axis = graph_node.attrs.get('axis', -1)
    axis = convert_axis(axis=axis, tensor_rank=tensor_rank)
    largest = bool(graph_node.attrs.get('largest', 1))
    sorted = bool(graph_node.attrs.get('sorted', 1))

    # Preserving Graph Structure (Dict)
    tf_layers_dict[Values.name] = {
        'optype': graph_node.op,
        'shape': Values_shape,
        'dtype': Values_dtype,
    }
    tf_layers_dict[Indices.name] = {
        'optype': graph_node.op,
        'shape': Indices_shape,
        'dtype': Indices_dtype,
    }

    # Generation of TF OP
    topked_values = None
    topked_indices = None
    perm = None
    if axis != (tensor_rank-1):
        perm = [idx for idx in range(tensor_rank) if idx != axis] + [axis]
        input_tensor = \
            tf.transpose(
                a=input_tensor,
                perm=perm,
            )

    if largest:
        topked_values, topked_indices = \
            tf.math.top_k(
                input=input_tensor,
                k=k_tensor,
                sorted=sorted,
                name=graph_node.name,
            )
    else:
        topked_values, topked_indices = \
            tf.math.top_k(
                input=tf.negative(input_tensor),
                k=k_tensor,
                sorted=sorted,
                name=graph_node.name,
            )
        topked_values = tf.negative(topked_values)

    if axis != (tensor_rank-1):
        perm = [perm.index(idx) for idx in range(tensor_rank)]
        topked_values = \
            tf.transpose(
                a=topked_values,
                perm=perm,
            )
        topked_indices = \
            tf.transpose(
                a=topked_indices,
                perm=perm,
            )

    tf_layers_dict[Values.name]['tf_node'] = topked_values
    tf_layers_dict[Indices.name]['tf_node'] = topked_indices