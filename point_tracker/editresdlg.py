from __future__ import print_function, division, absolute_import
"""
:newfield signal: Signal, Signals
"""
__author__ = "Pierre Barbier de Reuille <pbdr@uea.ac.uk>"
__docformat__ = "restructuredtext"

from PyQt4.QtGui import (QDialog, QPixmap, QIcon, QMessageBox, QTreeWidgetItem,
                         QDoubleValidator, QItemEditorFactory, QDoubleSpinBox,
                         QItemDelegate)
from PyQt4.QtCore import QSize, Qt, QVariant, pyqtSignature
from .ui_editresdlg import Ui_EditResDlg
from . import image_cache
from numpy import inf
from .scalemodel import ScaleModel
from .sys_utils import cleanQObject

class ScaleEditorFactory(QItemEditorFactory):
    def __init__(self):
        QItemEditorFactory.__init__(self)

    def __del__(self):
        cleanQObject(self)

    def createEditor(self, type, parent):
        if type != QVariant.Double:
            raise ValueError("This factory only creates editor for doubles")
        w = QDoubleSpinBox(parent)
        w.setDecimals(5)
        w.setMinimum(0.0001)
        w.setMaximum(10000)
        return w

class EditResDlg(QDialog):
    def __init__(self, images, scales, images_path, *args):
        QDialog.__init__(self, *args)
        cache = image_cache.cache
        self.ui = Ui_EditResDlg()
        self.ui.setupUi(self)
        icons = []
        for pth in images_path:
            ico = QIcon(QPixmap.fromImage(cache.image(pth).scaled(QSize(64,64), Qt.KeepAspectRatio)))
            icons.append(ico)
        self.model = ScaleModel(icons, images, scales)
        self.ui.pixelSizes.setModel(self.model)
        self.ui.pixelSizes.resizeColumnToContents(0)
        self.ui.pixelSizes.resizeColumnToContents(1)
        self.ui.pixelSizes.resizeColumnToContents(2)
        self.item_delegate = QItemDelegate()
        self.item_delegate.setItemEditorFactory(ScaleEditorFactory())
        self.ui.pixelSizes.setItemDelegate(self.item_delegate)
        self.ui.width.setValidator(QDoubleValidator(0, 1e300, 100, self))
        self.ui.height.setValidator(QDoubleValidator(0, 1e300, 100, self))
        # Find smallest scale
        minx = inf
        miny = inf
        for img in scales:
            sc = scales[img]
            if sc[0] > 0 and sc[0] < minx:
                minx = sc[0]
            if sc[1] > 0 and sc[1] < miny:
                miny = sc[1]
        if minx == inf:
            minx = 1e-6
        if miny == inf:
            miny = 1e-6
        # And set the default unit
        self.ui.unit.setCurrentIndex(self.model.findUnit(min(minx, miny)))

    def __del__(self):
        cleanQObject(self)

    @pyqtSignature("int")
    def on_unit_currentIndexChanged(self, idx):
        self.model.setUnit(self.ui.unit.currentText())

    @pyqtSignature("")
    def on_setAll_clicked(self):
        sel = self.ui.pixelSizes.selectionModel()
        w = float(self.ui.width.text())
        h = float(self.ui.height.text())
        if sel.hasSelection():
            self.model.setSubset(w, h, sel)
        else:
            self.model.setAll(w, h)
