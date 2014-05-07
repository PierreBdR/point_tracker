from __future__ import print_function, division, absolute_import

__author__ = "Pierre Barbier de Reuille <pierre@barbierdereuille.net>"
__docformat__ = "restructuredtext"
import scipy
from scipy import zeros, concatenate, asarray, array, dtype
import sys

def padding(A, pad):
    """
    Pad A, adding pad[i] 0's to the ith axis of A
    """
    if len(pad) > len(A.shape):
        A = A.reshape(A.shape + (1,)*(len(pad)-len(A.shape)))
    shape_A = A.shape
    for i,d in enumerate(pad):
        shape_pad = list(shape_A)
        shape_pad[i] = d
        pad = zeros(shape_pad, dtype=A.dtype)
        A = concatenate((pad, A, pad), axis=i)
        shape_A = A.shape
    return A

def eps(value):
    """
    Give the smallest epsilon that value can accept as a change.

    It depends both on value and type.
    """
    tv = type(value)
    t = scipy.dtype(type(value))
    tv = t.type
    return value*eps.values[tv]

eps.values = {}

def find_eps(vtype):
    v = vtype(2)
    for i in range(v.nbytes*8):
        diff = (v*vtype(1+v**(-i))-v)
        if diff == 0:
            return v**(-i+1)
    return 0

for v in scipy.floating.__subclasses__():
    eps.values[v] = find_eps(v)

def centered(arr, newsize):
    # Return the center newsize portion of the array.
    newsize = asarray(newsize)
    currsize = array(arr.shape)
    startind = (currsize - newsize) / 2
    endind = startind + newsize
    myslice = [slice(startind[k], endind[k]) for k in range(len(endind))]
    return arr[tuple(myslice)]

__bigendian = dtype("=i") == dtype(">i")
def bigendian():
    return __bigendian

def compare_versions(v1, v2):
    n1 = [ int(i) for i in v1.split('.') ]
    n2 = [ int(i) for i in v2.split('.') ]
    for i1,i2 in zip(n1, n2):
        if i1 < i2:
            return -1
        elif i1 > i2:
            return 1
    if len(n1) < len(n2):
        return -1
    elif len(n1) > len(n2):
        return 1
    return 0

