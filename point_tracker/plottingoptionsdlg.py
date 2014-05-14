from __future__ import print_function, division, absolute_import
"""
:newfield signal: Signal, Signals
"""
__author__ = "Pierre Barbier de Reuille <pierre@barbierdereuille.net>"
__docformat__ = "restructuredtext"

from PyQt4.QtGui import QDialog
from PyQt4.QtCore import pyqtSignature
from .sys_utils import setColor, getColor, changeColor, cleanQObject

from .ui_plottingoptionsdlg import Ui_PlottingOptionsDlg

class PlottingOptionsDlg(QDialog):
    def __init__(self, parent):
        QDialog.__init__(self, parent)
        self.parent = parent
        self.ui = Ui_PlottingOptionsDlg()
        self.ui.setupUi(self)
        self.ui.scaleAxis.setChecked(parent.ellipsis_draw.scale_axis)
        self.ui.majorAxis.setChecked(parent.ellipsis_draw.major_axis)
        self.ui.minorAxis.setChecked(parent.ellipsis_draw.minor_axis)
        self.ui.scalingFactor.setValue(parent.ellipsis_draw.scaling)
        self.ui.ellipsisThickness.setValue(parent.ellipsis_draw.thickness)
        self.ui.minAnisotropy.setValue(parent.ellipsis_draw.min_anisotropy)
        setColor(self.ui.ellipsisColor, parent.ellipsis_draw.color)
        setColor(self.ui.ellipsisPositiveColor, parent.ellipsis_draw.positive_color)
        setColor(self.ui.ellipsisNegativeColor, parent.ellipsis_draw.negative_color)
        setColor(self.ui.bgColor, parent.bg_color)
        self.ui.pointLineThickness.setValue(parent.point_line_thickness)
        setColor(self.ui.pointLineColor, parent.point_line_color)

    def __del__(self):
        cleanQObject(self)

    @pyqtSignature("")
    def on_selectBgColor_clicked(self):
        changeColor(self.ui.bgColor)

    @pyqtSignature("")
    def on_selectEllipsisPositiveColor_clicked(self):
        changeColor(self.ui.ellipsisPositiveColor)

    @pyqtSignature("")
    def on_selectEllipsisNegativeColor_clicked(self):
        changeColor(self.ui.ellipsisNegativeColor)

    @pyqtSignature("")
    def on_selectEllipsisColor_clicked(self):
        changeColor(self.ui.ellipsisColor)

    @pyqtSignature("")
    def on_selectPointLineColor_clicked(self):
        changeColor(self.ui.pointLineColor)

    def accept(self):
        parent = self.parent
        parent.ellipsis_draw.scale_axis = self.ui.scaleAxis.isChecked()
        parent.ellipsis_draw.major_axis = self.ui.majorAxis.isChecked()
        parent.ellipsis_draw.minor_axis = self.ui.minorAxis.isChecked()
        parent.ellipsis_draw.scaling = self.ui.scalingFactor.value()
        parent.ellipsis_draw.thickness = self.ui.ellipsisThickness.value()
        parent.ellipsis_draw.min_anisotropy = self.ui.minAnisotropy.value()
        parent.ellipsis_draw.color = getColor(self.ui.ellipsisColor)
        parent.ellipsis_draw.positive_color = getColor(self.ui.ellipsisPositiveColor)
        parent.ellipsis_draw.negative_color = getColor(self.ui.ellipsisNegativeColor)
        parent.point_line_thickness = self.ui.pointLineThickness.value()
        parent.point_line_color = getColor(self.ui.pointLineColor)
        parent.bg_color = getColor(self.ui.bgColor)
        QDialog.accept(self)
