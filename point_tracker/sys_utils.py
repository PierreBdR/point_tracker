from __future__ import print_function, division, absolute_import
# coding=utf-8
__docformat__ = "restructuredtext"
__author__ = "Pierre Barbier de Reuille <pierre@barbierdereuille.net>"
from PyQt4.QtGui import QPalette, QColorDialog, QMessageBox
from .path import path
import sys
from PyQt4 import uic
from .debug import caller

def toBool(s):
    try:
        return s.lower() in ('yes', 'true', 't', '1', 'y')
    except:
        return bool(s)

def changeColor(widget):
    """
    Launch the color dialog box in RGBA mode and update the window color of the widget.

    :returns: True if the color was changed
    :returntype: `bool`
    """
    c = widget.palette().color(QPalette.Window)
    ncc = QColorDialog.getColor(c, widget, "Change color", QColorDialog.ShowAlphaChannel)
    if ncc.isValid():
        setColor(widget, ncc)
        return True
    return False

def getColor(widget):
    """
    :returns: the 'window' color of a widget (i.e. the color used to paint it).

    :returntype: `QColor`
    """
    return widget.palette().color(QPalette.Window)

def setColor(widget, color):
    """
    Set the 'window' color of a widget (i.e. the color used to paint it).
    """
    c = widget.palette()
    c.setColor(QPalette.Window, color)
    widget.setPalette(c)
    widget.update()

def module_dir(module_name):
    p = path(sys.modules[module_name].__file__)
    return p.dirname()

def createForm(uifile, parent):
    p = path(caller()[0]).dirname()/uifile
    widget = uic.loadUi(p, from_imports=True)
    widget.setParent(parent)
    return widget

#def createForm(uifile, parent):
#    global __name__
#    p = path(__name__).dirname()/uifile
#    form, cls = uic.loadUiType(uifile)
#    widget = cls(parent)
#    widget.ui = form()
#    widget.ui.setupUi(widget)
#    for c in dir(widget.ui):
#        if "Ui" not in c and not c.startswith("__"):
#            setattr(widget, c, getattr(widget.ui, c))
#    return widget

inf_char = '∞'

def compileForm(uipath):
    """
    Compile of Qt 'ui' file into a python module, if it doesn't exist already

    Parameters::
        - uipath: path to a Qt 'ui' file

    :returns: the path to the compiled form
    """
    if not uipath.isabs():
        uipath = path(caller()[0]).dirname()/uipath
    modulename = "ui_%s" % (uipath.stripext().basename(),)
    compiled_ui = uipath.dirname() / ("%s.py" % (modulename,))
    if not compiled_ui.exists():# or compiled_ui.getmtime() < uipath.getmtime():
        with compiled_ui.open("wt") as f:
            print("Compiling form '{0}'".format(uipath))
            uic.compileUi(uipath, f, from_imports=True)
    return compiled_ui

def showException(parent, title, ex):
    msg = "%s: %s" % (type(ex).__name__, str(ex))
    QMessageBox.critical(parent, title, msg)

def retryException(parent, title, ex):
    msg = ex.question
    answer = QMessageBox.question(parent, title, msg, buttons=QMessageBox.Yes | QMessageBox.No)
    return answer == QMessageBox.Yes

