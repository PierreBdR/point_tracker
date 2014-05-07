#! /usr/bin/env python
__docformat__ = "restructuredtext"
__author__ = "Pierre Barbier de Reuille <pierre@barbierdereuille.net>"
from PyQt4 import QtGui, QtCore
import sys
import image_cache
import parameters
import debug
from sys_utils import compileForm
from path import path

def setAppConfig():
    QtCore.QCoreApplication.setOrganizationName("PBdR")
    QtCore.QCoreApplication.setApplicationName("VelocityTracking")
    QtCore.QCoreApplication.setOrganizationDomain("barbierdereuille.net")
    QtCore.QSettings.setDefaultFormat(QtCore.QSettings.IniFormat)

def compileUis():
    """
    Compile all the forms
    """
    p = path(__file__).dirname().abspath()
    for f in p.files('*.ui'):
        compileForm(f)

def createWindow():
    global main_win
    debug.init()
    setAppConfig()
    if QtGui.QApplication.startingUp():
        app = QtGui.QApplication(sys.argv)
    else:
        app = QtCore.QCoreApplication.instance()
    if "--nodebug" in sys.argv:
        debug.restore_io()
# Loading the module after the QApplication is launched otherwise the list of
# recognised images (determied when the module is loaded) is incomplete
    image_cache.createCache()
    parameters.createParameters()
    from tracking_window import TrackingWindow
    from project import Project
    Project.initClass()
    main_win = TrackingWindow()
    main_win.show()
    main_win.raise_()
    return app, main_win

def ipython():
    global main_window, app
    import __main__
    if 'IPython' in __main__.__class__.__module__:
        QtCore.pyqtRemoveInputHook()
    compileUis()
    app, main_window = createWindow()
    return app, main_window

def run():
    compileUis()
    app, main_win = createWindow()
    app.exec_()
