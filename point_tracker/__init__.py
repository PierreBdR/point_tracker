from __future__ import print_function, division, absolute_import
# If running python2, change the meaning of zip and range
from . import python2

import sip
sip.setapi('QString', 2)
sip.setapi('QVariant', 2)

__version__ = "0.7"
__revision__ = "1"
