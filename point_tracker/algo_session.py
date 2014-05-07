from __future__ import print_function, division, absolute_import
__docformat__ = "restructuredtext"
from numpy import *
import normcross
image = arange(1, 10001, dtype = float)
image.shape = (100,100)
template = array([[0,1,1,1,0],[1,1,1,1,1],[1,1,1,1,1],[1,1,1,1,1],[0,1,1,1,0.0]])
res = normcross.normcross2d(template, image)
