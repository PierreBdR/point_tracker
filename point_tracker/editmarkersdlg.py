from __future__ import print_function, division, absolute_import
from .ui_editmarkersdlg import Ui_EditMarkersDlg
from .transfer_markers import TransferMarkerModel, MarkerColorDelegate
from .sys_utils import cleanQObject

from PyQt4.QtCore import pyqtSignature
from PyQt4 import QtGui

class EditMarkersDlg(QtGui.QDialog):
    def __init__(self, fct, parent):
        QtGui.QDialog.__init__(self, parent)
        self.ui = Ui_EditMarkersDlg()
        self.ui.setupUi(self)
        self.fct = fct
        values = fct.point_list
        colors = [QtGui.QColor.fromRgbF(*pt[1]) for pt in values]
        markers = [pt[0] for pt in values]
        self.colors = colors
        self.markers = markers
        self.model = TransferMarkerModel(markers, colors, fct.interpolation, True)
        self.ui.markersView.setModel(self.model)
        self.delegate = MarkerColorDelegate()
        self.ui.markersView.setItemDelegate(self.delegate)
        self.spread_button = self.ui.buttonBox.addButton("Spread markers", QtGui.QDialogButtonBox.ActionRole)
        self.spread_button.clicked.connect(self.spreadMarkers)
        self.ui.markersView.resizeColumnsToContents()

    def __del__(self):
        cleanQObject(self)

    @property
    def point_list(self):
        return [ (m, (col.redF(), col.greenF(), col.blueF(), col.alphaF())) for (m,col) in zip(self.markers, self.colors)]

    @pyqtSignature("")
    def on_addMarker_clicked(self):
        self.model.addMarker(self.ui.markersView.selectionModel().selection())

    @pyqtSignature("")
    def on_removeMarker_clicked(self):
        self.model.removeMarker(self.ui.markersView.selectionModel().selection())

    def spreadMarkers(self):
        self.model.spreadMarkers(self.ui.markersView.selectionModel().selection())

    @pyqtSignature("bool")
    def on_rgbaMode_toggled(self, value):
        if value:
            self.model.rgbaMode()

    @pyqtSignature("bool")
    def on_hsvaMode_toggled(self, value):
        if value:
            self.model.hsvaMode()
