from __future__ import print_function, division, absolute_import
import sys

if sys.version_info.major < 3:
    import __builtin__
    import itertools
    __builtin__.zip = itertools.izip
    __builtin__.range = xrange
else:
    import builtins
    builtins.unicode = str
