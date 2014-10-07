from __future__ import print_function, division, absolute_import
__author__ = "Pierre Barbier de Reuille <pierre@barbierdereuille.net>"
__docformat__ = "restructuredtext"
from PyQt4 import QtCore, QtGui
from .ui_transferfunctiondlg import Ui_TransferFunctionDlg
from .transferfunction import TransferFunction
from pickle import load, dump
from .path import path
from .debug import log_debug

class TransferFunctionDlg( QtGui.QDialog ):
    transferFctChanged = QtCore.Signal(object)
    saveState = QtCore.Signal()

    immutable_fct = ["Hue scale", "Grey scale"]


    def __init__(self, *arg):
        QtGui.QDialog.__init__(self,*arg)

        self.ui = Ui_TransferFunctionDlg()
        self.ui.setupUi(self)

        self.fctViewer = self.ui.fctViewer

        self.transferFctChanged.connect(self.fctViewer.setupGradient)

        self._fctlist = {}

        self._histogram = None
        self._transfer_fct = None
        self.saved_transfer_fct = None
        self.current_fct = ""

        self.setSelectionColor(self.ui.fctViewer.activ_pos_color)

        self.fctViewer.slowChange.connect(self.temporaryChange)

    def setSelectionColor(self, col):
        palette = QtGui.QPalette()
        palette.setColor(self.ui.selectionColor.backgroundRole(), col)
        self.ui.selectionColor.setPalette(palette)

    @property
    def histogram(self):
        return self._histogram

    @histogram.setter
    def histogram(self, histo):
        if self._histogram == histo:
            return
        self._histogram = histo
        self.fctViewer.histogram = histo

    @property
    def use_histogram(self):
        return self.fctViewer.use_histogram

    @use_histogram.setter
    def use_histogram(self, value):
        self.fctViewer.use_histogram = value

    @property
    def stickers(self):
        return self.fctViewer.stickers

    @stickers.setter
    def stickers(self, value):
        self.fctViewer.stickers = value

    @property
    def transfer_fct(self):
        return self._transfer_fct

    @transfer_fct.setter
    def transfer_fct(self, fct):
        if not hasattr(fct, "interpolation"):
            fct = TransferFunction.loads(fct)
        if fct == self._transfer_fct:
            return
        self._transfer_fct = fct
        self.saved_transfer_fct = fct.copy()
        self.fctViewer.transfer_fct = fct
        for fctname in self._fctlist:
            if fct == self._fctlist[fctname]:
                self.ui.functionList.setEditText(fctname)
                break
        else:
            self.ui.functionList.setEditText("")
            self.ui.functionList.setCurrentIndex(-1)

    def transfer_fct_string(self):
        return self.transfer_fct.dumps()

    @QtCore.pyqtSignature("")
    def on_useRGB_clicked(self):
        self.fctViewer.transfer_fct.interpolation = "rgb"
        self.transferFctChanged.emit(self.transfer_fct)

    @QtCore.pyqtSignature("")
    def on_useHSV_clicked(self):
        self.fctViewer.transfer_fct.interpolation = "hsv"
        self.transferFctChanged.emit(self.transfer_fct)

    @QtCore.pyqtSignature("")
    def on_useCyclicHSV_clicked(self):
        self.fctViewer.transfer_fct.interpolation = "cyclic_hsv"
        self.transferFctChanged.emit(self.transfer_fct)

    @QtCore.pyqtSignature("")
    def on_saveFunction_clicked(self):
        name = str(self.ui.functionList.currentText())
        if name not in TransferFunctionDlg.immutable_fct:
            self.setFunction(name, self.transfer_fct)

    @QtCore.pyqtSignature("")
    def on_deleteFunction_clicked(self):
        name = str(self.ui.functionList.currentText())
        if name not in TransferFunctionDlg.immutable_fct:
            self.deleteFunction(name)
        else:
            QtGui.QMessageBox.warning(self, "Deleting immutable function", "Cannot delete function '%s'. It is a default function." % name)

    @QtCore.pyqtSignature("")
    def on_renameFunction_clicked(self):
        name = str(self.ui.functionList.currentText())
        if self.current_fct not in TransferFunctionDlg.immutable_fct:
            self.renameFunction(self.current_fct, name)
        else:
            QtGui.QMessageBox.warning(self, "Renaming immutable function", "Cannot rename function '%s'. It is a default function." % name)
            self.makeCurrent(self.current_fct)

    @QtCore.pyqtSignature("")
    def on_importFunction_clicked(self):
        filename = QtGui.QFileDialog.getOpenFileName( self, "Load a tranfer function" )
        filename = path(filename)
        if filename:
            name, fct = load(filename.open())
            prefix = name
            incr = 1
            while name in self._fctlist:
                name = "%s%d" % (prefix, incr)
                incr += 1
            self.setFunction(name, fct)
            self.makeCurrent(name)

    @QtCore.pyqtSignature("QString")
    def on_functionList_activated(self, name):
        name = str(name)
        self.makeCurrent(name)
        self.update()

    def setFunction(self, fctname, fct):
        fctname = str(fctname)
        if fctname not in self._fctlist:
            self.ui.functionList.addItem(fctname)
            self.ui.functionList.model().sort(0)
        self._fctlist[fctname] = fct.copy()

    def makeCurrent(self, fctname):
        if fctname != self.current_fct:
            i = self.ui.functionList.findText(fctname)
            self.ui.functionList.setCurrentIndex(i)
            self.current_fct = fctname
            fct = self._fctlist[fctname].copy()
            self.transfer_fct = fct
            if fct.interpolation == "rgb":
                self.ui.useRGB.setChecked(True)
            elif fct.interpolation == "hsv":
                self.ui.useHSV.setChecked(True)
            else:
                self.ui.useCyclicHSV.setChecked(True)
            self.transferFctChanged.emit(self.transfer_fct)

    def deleteFunction(self, fctname):
        if fctname in self._fctlist:
            del self._fctlist[fctname]
            i = self.ui.functionList.findText(fctname)
            self.ui.functionList.removeItem(i)
            self.makeCurrent(str(self.ui.functionList.currentText()))

    def renameFunction(self, old_name, new_name):
        if old_name in self._fctlist:
            fct = self._fctlist[old_name]
            del self._fctlist[old_name]
            self._fctlist[new_name] = fct
            i = self.ui.functionList.findText(old_name)
            self.ui.functionList.setItemText(i, new_name)
            self.ui.functionList.model().sort(0)
            self.makeCurrent(new_name)

    @QtCore.pyqtSignature("")
    def on_exportFunction_clicked(self):
        name = str(self.ui.function.currentText())
        if name not in self._fctlist:
            return
        filename = QtGui.QFileDialog.getSaveFileName( self, 'Save transfer function "%s"'% name)
        filename = path(filename)
        if filename:
            fct = self._fctlist[name]
            dump((name,fct), filename.open('w'))

#    @QtCore.pyqtSignature("")
#    def on_setTransparenceScale_clicked(self):
#        fct = self._transfer_fct
#        for pos in fct:
#            col = fct.rgba_point(pos)
#            col = col[:3]+(pos,)
#            fct.add_rgba_point(pos, *col)
#        self.fctViewer.transfer_fct = fct
#        self.emit(QtCore.SIGNAL("transferFctChanged"), self.transfer_fct)

    @QtCore.pyqtSignature("")
    def on_useChecks_clicked(self):
        self.fctViewer.createBackground("checks")

    @QtCore.pyqtSignature("")
    def on_useWhite_clicked(self):
        self.fctViewer.createBackground("white")

    @QtCore.pyqtSignature("")
    def on_useBlack_clicked(self):
        self.fctViewer.createBackground("black")

    @QtCore.pyqtSignature("QAbstractButton*")
    def on_buttonBox_clicked(self, button):
        role = self.ui.buttonBox.buttonRole(button)
        if role == QtGui.QDialogButtonBox.AcceptRole:
            self.validate()
        elif role == QtGui.QDialogButtonBox.ApplyRole:
            self.validate()
        elif role == QtGui.QDialogButtonBox.RejectRole:
            self.reset()
        elif role == QtGui.QDialogButtonBox.ResetRole:
            self.reset()

    def reset(self):
        self.transfer_fct = self.saved_transfer_fct.copy()
        self.transferFctChanged.emit(self.transfer_fct)
        self.saveState.emit()

    def validate(self):
        self.saved_transfer_fct = self.transfer_fct.copy()
        self.transferFctChanged.emit(self.transfer_fct)
        self.saveState.emit()

    def temporaryChange(self):
        self.transferFctChanged.emit(self.transfer_fct)

    @QtCore.pyqtSignature("")
    def on_selectSelectionColor_clicked(self):
        col = self.fctViewer.activ_pos_color.rgba()
        ncol, ok = QtGui.QColorDialog.getRgba(col, self)
        if ok:
            col = QtGui.QColor.fromRgba(ncol)
            self.fctViewer.activ_pos_color = col
            self.setSelectionColor(col)

    @QtCore.pyqtSignature("int")
    def on_tickWidth_valueChanged(self, i):
        self.fctViewer.marker_size = i
        self.fctViewer.update()

    @QtCore.pyqtSignature("int")
    def on_checkSize_valueChanged(self, i):
        self.fctViewer.bg_size = i
        self.fctViewer.createBackground()
        self.fctViewer.update()

    def saveSettings(self, name):
        settings = QtCore.QSettings()
        section = "%sTransferFct" % name
        settings.beginGroup(section)
        settings.setValue("TickWidth", self.fctViewer.marker_size)
        settings.setValue("SelectionColor", self.fctViewer.activ_pos_color)
        settings.setValue("CheckSize", self.fctViewer.bg_size)
        settings.beginGroup("TransferFctList")
        for i in (self._fctlist):
            settings.setValue("%s" % i, self._fctlist[i].dumps())
        settings.endGroup()
        settings.setValue("TransferFct", self.current_fct)
        settings.endGroup()

    def loadSettings(self, name):
        log_debug("Loading settings")
        settings = QtCore.QSettings()
        section = "%sTransferFct" % name
        settings.beginGroup(section)
        try:
            ms = int(settings.value("TickWidth"))
        except (ValueError, TypeError):
            ms = 5
        self.fctViewer.marker_size = ms
        self.ui.tickWidth.setValue(self.fctViewer.marker_size)
        sc = QtGui.QColor(settings.value("SelectionColor"))
        if not sc.isValid():
            sc = QtGui.QColor(200, 200, 200, 200)
        self.fctViewer.activ_pos_color = sc
        self.setSelectionColor(sc)
        try:
            cs = int(settings.value("CheckSize"))
        except (ValueError, TypeError):
            cs = 20
        self.fctViewer.bg_size = cs
        self.ui.checkSize.setValue(self.fctViewer.bg_size)
        current_fct = str(settings.value("TransferFct", "Hue scale"))
        settings.beginGroup("TransferFctList")
        keys = settings.allKeys()
        log_debug("Keys of transfer function: %s" % ",".join(str(s) for s in keys))
        if "Grey scale" not in keys:
            fct = TransferFunction()
            fct.add_rgba_point(0, 0, 0, 0, 0)
            fct.add_rgba_point(1, 1, 1, 1, 1)
            fct.interpolation = "rgb"
            self.setFunction("Grey scale", fct)
        if "Hue scale" not in keys:
            fct = TransferFunction()
            fct.add_hsva_point(0, 0, 1, 1, 0)
            fct.add_hsva_point(0.3, 0.3, 1, 1, 0.3)
            fct.add_hsva_point(0.7, 0.7, 1, 1, 0.7)
            fct.add_hsva_point(1, 1, 1, 1, 1)
            fct.interpolation = "cyclic_hsv"
            self.setFunction("Hue scale", fct)
        if "Jet" not in keys:
            fct = TransferFunction()
            fct.add_rgba_point(0   , 0.5, 0.0, 0.0, 1)
            fct.add_rgba_point(1./8, 1.0, 0.0, 0.0, 1) 
            fct.add_rgba_point(3./8, 1.0, 1.0, 0.0, 1) 
            fct.add_rgba_point(5./8, 0.0, 1.0, 1.0, 1) 
            fct.add_rgba_point(7./8, 0.0, 0.0, 1.0, 1) 
            fct.add_rgba_point(1   , 0.0, 0.0, 0.5, 1) 
            self.setFunction("Jet", fct)
        if keys:
            for key in keys:
                fct = TransferFunction.loads(settings.value(key))
                self.setFunction(key, fct)
        else:
            current_fct = "Hue scale"
        if current_fct in self._fctlist:
            self.transfer_fct = self._fctlist[current_fct].copy()
            self.makeCurrent(current_fct)
        else:
            raise ValueError("Invalid current transfer function: '%s'" % current_fct)
        settings.endGroup()
        self.validate()

    def savePreferences(self, cfg, name):
        section = "%sTransferFct" % name
        cfg.add_section(section)
        cfg.set(section, "TickWidth", str(self.fctViewer.marker_size))
        cfg.set(section, "SelectionColor", str(self.fctViewer.activ_pos_color.rgba()))
        cfg.set(section, "CheckSize", str(self.fctViewer.bg_size))
        cfg.set(section, "TransferFctList", self._fctlist.dumps())
        cfg.set(section, "TransferFct", self.current_fct)

    def loadPreferences(self, cfg, name):
        section = "%sTransferFct" % name
        if cfg.has_section(section):
            if cfg.has_option(section, "TickWidth"):
                self.fctViewer.marker_size = cfg.getint(section, "TickWidth")
                self.ui.tickWidth.setValue(self.fctViewer.marker_size)
            if cfg.has_option(section, "SelectionColor"):
                rgba = cfg.getint(section, "SelectionColor")
                col = QtGui.QColor.fromRgba(rgba)
                self.fctViewer.activ_pos_color = col
                self.setSelectionColor(col)
            if cfg.has_option(section, "CheckSize"):
                self.fctViewer.bg_size = cfg.getint(section, "CheckSize")
                self.ui.checkSize.setValue(self.fctViewer.bg_size)
            if cfg.has_option(section, "TransferFct"):
                current_fct = cfg.get(section, "TransferFct")
            else:
                current_fct = "Hue scale"
            if cfg.has_option(section, "TransferFctList"):
                dct = TransferFunction.loads(cfg.get(section, "TransferFctList"))
                for k in dct:
                    self.setFunction(k, dct[k])
            else:
                fct = TransferFunction()
                fct.add_rgba_point(0, 0, 0, 0, 0)
                fct.add_rgba_point(1, 1, 1, 1, 1)
                fct.interpolation = "rgb"
                self.setFunction("Grey scale", fct)
                fct = TransferFunction()
                fct.add_hsva_point(0, 0, 1, 1, 0)
                fct.add_hsva_point(0.3, 0.3, 1, 1, 0.3)
                fct.add_hsva_point(0.7, 0.7, 1, 1, 0.7)
                fct.add_hsva_point(1, 1, 1, 1, 1)
                fct.interpolation = "cyclic_hsv"
                self.setFunction("Hue scale", fct)
                current_fct = "Hue scale"
            if current_fct in self._fctlist:
                self.transfer_fct = self._fctlist[current_fct].copy()
                self.makeCurrent(current_fct)
            else:
                raise ValueError("Invalid current transfer function: '%s'" % current_fct)
            self.validate()

    def keyPressEvent(self, event):
        if event.key() == QtCore.Qt.Key_Enter:
            event.accept()
            return
