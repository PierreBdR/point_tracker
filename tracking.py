#! /usr/bin/env python
from __future__ import print_function, division, absolute_import
import sys
import os.path
import os

sys.argv.append('--nodebug')

if sys.platform == 'win32':
    sp = os.path.join(os.path.abspath('.'),'site-packages')
    sys.path.insert(0,sp)
    os.environ["PATH"] = "%s;%s" % (os.path.join(sp, "PyQt4", "bin"), os.environ["PATH"])
    from PyQt4.QtCore import QCoreApplication
    lp = QCoreApplication.libraryPaths()
    lp << os.path.join(os.path.abspath('.'), 'site-packages', 'PyQt4', 'plugins')
    QCoreApplication.setLibraryPaths(lp)

from point_tracker import tracking

def run():
    return tracking.ipython()

if __name__ == "__main__":
    if "interactive" in sys.argv:
        print("Starting interactive session")
        app, main_win = tracking.ipython()
    else:
        tracking.run()
