from __future__ import print_function, division, absolute_import
"""
This package maintain the classes used for plotting on the tissue.
"""
__author__ = "Pierre Barbier de Reuille <pierre@barbierdereuille.net>"

from ..path import path
from . import tracking_plot
from .tracking_plot import (cell_colorings_cls, wall_colorings_cls, point_colorings_cls, reset_classes)
from ..debug import print_debug
import sys
import traceback

def loadClasses():
    reset_classes()
    system_files = [ __file__, tracking_plot.__file__ ]
    sys_files = []
    for f in system_files:
        if f.endswith(".pyo") or f.endswith(".pyc"):
            f = f[:-3]+"py"
        sys_files.append(path(f).abspath())
    search_path = path(__file__).abspath().dirname()
    errors = []
    for f in search_path.files("*.py"):
        if f not in sys_files:
            module_name = f.basename()[:-3]
            try:
                if "src.tissue_plot.%s" % module_name in sys.modules:
                    print_debug("Reloading classes from module %s" % module_name)
                    exec("reload(%s)" % module_name)
                else:
                    print_debug("Importing classes from module %s" % module_name)
                    exec("import %s" % module_name)
            except Exception as ex:
                tb = sys.exc_info()[2]
                error_loc = "\n".join("In file %s, line %d\n\tIn '%s': %s" % e for e in traceback.extract_tb(tb))
                errors.append((f,"Exception %s:\n%s\n%s" % (type(ex).__name__, str(ex), error_loc)))
    if errors:
        print("Errors: ")
        print("\n\n".join("In file %s:\n%s" % (f,e) for f,e in errors))
    return errors


