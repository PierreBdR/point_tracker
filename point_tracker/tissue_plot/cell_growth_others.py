from __future__ import print_function, division, absolute_import

from .tracking_plot import (ColoringClass, fixRangeParameters)
from PyQt4.QtCore import Slot
from PyQt4.QtGui import QColor
from ..sys_utils import createForm
import numpy as np
from ..geometry import polygonArea
#from ..debug import log_debug

def significantAnisotropyParameters(m, M):
    superClass = fixRangeParameters(m, M)

    class SignificantAnisotropyParameters(superClass):
        def __init__(self, params):
            superClass.__init__(self, params)
            self._config = None
            self._min_displacement = params.min_displacement
            if self._min_displacement < 1e-6:
                self._unit = 1e-9
                self._value = self._min_displacement * 1e9
            elif self._min_displacement < 1e-3:
                self._unit = 1e-6
                self._value = self._min_displacement * 1e6
            elif self._min_displacement < 1.:
                self._unit = 1e-3
                self._value = self._min_displacement * 1e3
            else:
                self._unit = 1.
                self._value = self._min_displacement

        @property
        def min_displacement(self):
            return self._min_displacement

        @min_displacement.setter
        def min_displacement(self, value):
            value = float(value)
            if value >= 0:
                self._min_displacement = value
                self.changed.emit()

        units = [1e-9, 1e-6, 1e-3, 1.]
        unit_pos = {i: u for i, u in enumerate(units)}

        def widget(self, parent):
            config = createForm("plot_param_anisotropy.ui", parent)
            self._config = config
            config.changeColorMap.clicked.connect(self._changeColorMap)
            config.moveUnit.currentIndexChanged.connect(self._changeUnitIndex)
            config.moveUnit.setCurrentIndex(self.unit_pos.get(self._unit, 1))
            config.moveValue.valueChanged['double'].connect(self._changeMinDisplacement)
            config.moveValue.setValue(self._value)
            self.addScaleBarWidget(config)
            return self._config

        @Slot(int)
        def _changeUnitIndex(self, idx):
            if idx > len(self.units):
                raise ValueError("Error, getting to index {0}, that doesn't exist".format(idx))
            self._unit = self.units[idx]
            self.min_displacement = self._value * self._unit

        @Slot(float)
        def _changeMinDisplacement(self, v):
            self._value = v
            self.min_displacement = v * self._unit

        @staticmethod
        def load(params, settings):
            superClass.load(params, settings)
            try:
                value = float(settings.value('MinDisplacement'))
            except (ValueError, TypeError):
                value = 1e-6
            params.min_displacement = value
            params.symetric_coloring = False
            params.value_capping = None

        @staticmethod
        def save(params, settings):
            superClass.save(params, settings)
            settings.setValue('MinDisplacement', params.min_displacement)

    return SignificantAnisotropyParameters

class CellGrowthSignificantAnisotropy(ColoringClass('cell')):
    coloring_name = u"Significant growth anisotropy"
    settings_name = u"SignificantGrowthAnisotropy"
    parameter_class = significantAnisotropyParameters(0, 2)
    unit = u""

    def __init__(self, result):
        ColoringClass('cell').__init__(self, result)

    def finalizeImage(self, painter, imageid, image_transform, size=None):
        return self.parameters.drawScaleBar(painter, None, self.unit, size)

    def cellArea(self, imageid, cid):
        data = self.result.data[imageid]
        pts = self.result.data.cellAtTime(cid, data.index)
        if len(pts) < 3:
            return None
        polygon = []
        prev = pts[-1]
        for pid in pts:
            w = data.walls[prev, pid]
            polygon.extend(w)
            polygon.append(data[pid])
            prev = pid
        return polygonArea(polygon)

    def __call__(self, imageid, cid):
        fct = self.parameters.transfer_function
        if fct is None:
            return QColor()
        values = self.result.cells[imageid][cid]
        ka = values[1] + values[0]
        area = self.cellArea(imageid, cid)
        is_fwd = True
        for p in self.result.method_params:
            if 'Backward' in p:
                is_fwd = False
                break
        data = self.result.data
        base_id = imageid if is_fwd else imageid - 1
        dt = data.images_time[base_id + 1] - data.images_time[base_id]

        print("area = {2}, ka = {0}, dt = {1}".format(ka, dt, area))

        if np.sqrt(area * np.exp(ka * dt)) < self.parameters.min_displacement:
            return QColor()

        if values[0] == 0:
            value = 0
        else:
            value = 1 - values[1] / values[0]
        col = QColor()
        col.setRgbF(*fct.rgba(value))
        return col

    @staticmethod
    def accept_result_type(result_type):
        return result_type == "Growth"
