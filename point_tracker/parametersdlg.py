from __future__ import print_function, division, absolute_import
__author__ = "Pierre Barbier de Reuille <pierre@barbierdereuille.net>"
__docformat__ = "restructuredtext"
from .ui_parametersdlg import Ui_ParametersDlg
from PyQt4.QtGui import QDialog, QPalette, QColor, QColorDialog, QMessageBox
from PyQt4.QtCore import QObject, SLOT
from PyQt4 import QtCore
from math import ceil
from . import image_cache
from . import parameters
from .sys_utils import changeColor, setColor, getColor, cleanQObject

class ParametersDlg(QDialog):
    def __init__(self, max_size, *args):
        QDialog.__init__(self, *args)
        self.ui = Ui_ParametersDlg()
        self.ui.setupUi(self)
        params = parameters.instance
        self.params = params
        max_size = max(max_size, params.template_size, params.search_size)
        self.ui.searchSize.setMaximum(max_size)
        self.ui.searchSizeSlider.setMaximum(max_size/2)
        self.ui.templateSize.setMaximum(max_size)
        self.ui.templateSizeSlider.setMaximum(max_size/2)
        self.setupTemplateParameters()

        self.ui.cacheSize.setValue(image_cache.cache.max_size)

        setColor(self.ui.templateColorView, params.template_color)
        setColor(self.ui.searchColorView, params.search_color)

        self.ui.oldPointsSize.setValue(params.old_point_size)
        self.ui.pointsSize.setValue(params.point_size)
        self.ui.arrowsLineSize.setValue(params.arrow_line_size)
        self.ui.arrowHeadSize.setValue(params.arrow_head_size*100)
        self.ui.oldPointsThickness.setValue(params.old_point_thickness)
        self.ui.pointsThickness.setValue(params.point_thickness)
        self.ui.cellsSize.setValue(params.cell_size)
        self.ui.cellsThickness.setValue(params.cell_thickness)
        setColor(self.ui.oldPointsColorView, params.old_point_color)
        setColor(self.ui.oldPointsMatchingColorView, params.old_point_matching_color)
        setColor(self.ui.pointsColorView, params.point_color)
        setColor(self.ui.newPointsColorView, params.new_point_color)
        setColor(self.ui.selectedPointsColorView, params.selected_point_color)
        setColor(self.ui.arrowsColorView, params.arrow_color)
        setColor(self.ui.cellsColorView, params.cell_color)
        setColor(self.ui.selectedCellsColorView, params.selected_cell_color)
        setColor(self.ui.divisionWallColorView, params.division_wall_color)

        self.ui.useOpenGL.setChecked(params.use_OpenGL)

        self.ui.filterSize.setValue(params.filter_size_ratio_percent)

        self.params.searchParameterChange.connect(self.setupTemplateParameters)

    def __del__(self):
        cleanQObject(self)

    def setupTemplateParameters(self):
        self.ui.searchSize.setValue(self.params.search_size)
        self.ui.templateSize.setValue(self.params.template_size)

    def accept(self):
        tem = self.ui.templateSize.value()
        if 1.5*tem > self.ui.searchSize.value():
            btn = QMessageBox.warning(self, "Incompatible template and search sizes",
            '''The search area must be at least 1.5 bigger than the template size.
            Click "Ok" to set the search area to 1.5 the template size, or "Cancel" to go back to the dialog box''',
            QMessageBox.Ok, QMessageBox.Cancel)
            if btn == QMessageBox.Ok:
                self.ui.searchSize.setValue(int(ceil(1.5*tem+0.1)))
            else:
                return
        #image_cache.createCache(self.ui.cacheSize.value())
        parameters.instance.cache_size = self.ui.cacheSize.value()
        QDialog.accept(self)

    @QtCore.pyqtSignature("bool")
    def on_useOpenGL_toggled(self, value):
        self.params.use_OpenGL = value

    @QtCore.pyqtSignature("int")
    def on_templateSize_valueChanged(self, value):
        self.params.template_size = value

    @QtCore.pyqtSignature("int")
    def on_searchSize_valueChanged(self, value):
        self.params.search_size = value

    @QtCore.pyqtSignature("int")
    def on_filterSize_valueChanged(self, value):
        self.params.filter_size_ratio_percent = value

    @QtCore.pyqtSignature("double")
    def on_oldPointsSize_valueChanged(self, value):
        self.params.old_point_size = value

    @QtCore.pyqtSignature("double")
    def on_pointsSize_valueChanged(self, value):
        self.params.point_size = value

    @QtCore.pyqtSignature("double")
    def on_arrowsLineSize_valueChanged(self, value):
        self.params.arrow_line_size = value

    @QtCore.pyqtSignature("int")
    def on_oldPointsThickness_valueChanged(self, value):
        self.params.old_point_thickness = value

    @QtCore.pyqtSignature("int")
    def on_pointsThickness_valueChanged(self, value):
        self.params.point_thickness = value

    @QtCore.pyqtSignature("int")
    def on_arrowHeadSize_valueChanged(self, value):
        self.params.arrow_head_size = value/100.0

    @QtCore.pyqtSignature("double")
    def on_cellsSize_valueChanged(self, value):
        self.params.cell_size = value

    @QtCore.pyqtSignature("int")
    def on_cellsThickness_valueChanged(self, value):
        self.params.cell_thickness = value

    @QtCore.pyqtSignature("")
    def on_changeOldPointsColor_clicked(self):
        if changeColor(self.ui.oldPointsColorView):
            self.params.old_point_color = getColor(self.ui.oldPointsColorView)

    @QtCore.pyqtSignature("")
    def on_changeOldPointsMatchingColor_clicked(self):
        if changeColor(self.ui.oldPointsMatchingColorView):
            self.params.old_point_matching_color = getColor(self.ui.oldPointsMatchingColorView)

    @QtCore.pyqtSignature("")
    def on_changePointsColor_clicked(self):
        if changeColor(self.ui.pointsColorView):
            self.params.point_color = getColor(self.ui.pointsColorView)

    @QtCore.pyqtSignature("")
    def on_changeNewPointsColor_clicked(self):
        if changeColor(self.ui.newPointsColorView):
            self.params.new_point_color = getColor(self.ui.newPointsColorView)

    @QtCore.pyqtSignature("")
    def on_changeSelectedPointsColor_clicked(self):
        if changeColor(self.ui.selectedPointsColorView):
            self.params.selected_point_color = getColor(self.ui.selectedPointsColorView)

    @QtCore.pyqtSignature("")
    def on_changeArrowsColor_clicked(self):
        if changeColor(self.ui.arrowsColorView):
            self.params.arrow_color = getColor(self.ui.arrowsColorView)

    @QtCore.pyqtSignature("")
    def on_changeTemplateColor_clicked(self):
        if changeColor(self.ui.templateColorView):
            self.params.template_color = getColor(self.ui.templateColorView)

    @QtCore.pyqtSignature("")
    def on_changeSearchColor_clicked(self):
        if changeColor(self.ui.searchColorView):
            self.params.search_color = getColor(self.ui.searchColorView)

    @QtCore.pyqtSignature("")
    def on_changeCellsColor_clicked(self):
        if changeColor(self.ui.cellsColorView):
            self.params.cell_color = getColor(self.ui.cellsColorView)

    @QtCore.pyqtSignature("")
    def on_changeSelectedCellsColor_clicked(self):
        if changeColor(self.ui.selectedCellsColorView):
            self.params.selected_cell_color = getColor(self.ui.selectedCellsColorView)

    @QtCore.pyqtSignature("")
    def on_divisionWallColor_clicked(self):
        if changeColor(self.ui.divisionWallColorView):
            self.params.division_wall_color = getColor(self.ui.divisionWallColorView)

