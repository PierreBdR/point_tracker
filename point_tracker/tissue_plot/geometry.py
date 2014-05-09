# -*- coding: utf8 -*-
from __future__ import print_function, division, absolute_import

from .tracking_plot import ColoringClass, TransferFunctionParameters, make_cap_symetric
from PyQt4.QtGui import QColor
from numpy import inf
from math import log10, pow, floor
from ..geometry import polygonArea
from ..debug import log_debug

units = [
  u"y", # yocto - 10^-24
  u"z", # zepto - 10^-21
  u"a", # atto  - 10^-18
  u"f", # femto - 10^-15
  u"p", # pico  - 10^-12
  u"n", # nano  - 10^-9
  u"µ", # micro - 10^-6
  u"m", # milli - 10^-3
  u"" , # unit  - 10^0
  u"k", # kilo  - 10^3
  u"M", # mega  - 10^6
  u"G", # giga  - 10^9
  u"T", # tera  - 10^12
  u"P", # peta  - 10^15
  u"E", # exa   - 10^18
  u"Z", # zetta - 10^21
  u"Y"  # yota  - 10^24
  ]

def unit(ref_exp):
    """
    ref_exp is the 'reference exponent', i.e. the increment in the table.
    For linear units, its the exponent divided by 3
    For square units, divided by 6
    For cudes, divided by 9
    etc.
    The result is the symbol and the reference exponent to multiply ...
    """
    ref_exp = int(ref_exp)
    if ref_exp > 8:
        return units[-1], 8
    elif ref_exp < -8:
        return units[0], -8
    return units[ref_exp+8], ref_exp

class CellGeometry(ColoringClass('cell')):
    """
    Needs the subclass to implement a value(imageid, cid) method.
    """
    parameter_class = TransferFunctionParameters

    def __init__(self, result):
        ColoringClass('cell').__init__(self, result)

    @staticmethod
    def accept_result_type(result_type):
        return result_type == "Data"

    def init(self):
        caps = self.parameters.value_capping
        if caps is None:
            caps = self.value_range()
            if self.parameters.symetric_coloring:
                caps = make_cap_symetric(caps)
        self.dc = 1/(caps[1]-caps[0])
        self.shiftc = caps[0]
        self.caps = caps
        unit, ratio = self.bestUnit(caps)
        self.used_caps = (caps[0]/ratio, caps[1]/ratio)
        self.used_unit = unit
        self.ratio = ratio
        #print "Ratio = %s, caps = %s, unit = %s" % (ratio,self.used_caps,unit)

    def value_range(self):
        result = self.result
        caps = (inf,-inf)
        for img in result.images_name:
            data = result[img]
            for cid in data.cells:
                value = self.value(img, cid)
                if value is not None:
                    caps = (min(caps[0], value), max(caps[1], value))
        return caps

    def _update_parameters(self):
        caps = self.value_range()
        self.parameters.minmax_values = caps

    def __call__(self, imageid, cid):
        fct = self.parameters.transfer_function
        if fct is None:
            return QColor(0,0,0,0)
        value = self.value(imageid, cid)
        if value is None:
            return QColor(0,0,0,0)
        col = QColor()
        col.setRgbF(*fct.rgba((value-self.shiftc)*self.dc))
        return col

    def bestUnit(self, _):
        return self.unit, 1
    
    def bestUnitLinear(self, caps):
        ref_value = max(abs(caps[0], abs(caps[1])))
        ref_exp = floor(log10(ref_value)/3)
        sym, exp = unit(ref_exp)
        return sym+self.unit, pow(10, 3*exp)

    def bestUnitSquare(self, caps):
        ref_value = max(abs(caps[0]), abs(caps[1]))
        ref_exp = floor(log10(ref_value)/6)
        sym, exp = unit(ref_exp)
        return sym+self.unit, pow(10, 6*exp)

    def bestUnitCube(self, caps):
        ref_value = max(abs(caps[0], abs(caps[1])))
        ref_exp = floor(log10(ref_value)/9)
        sym, exp = unit(ref_exp)
        return sym+self.unit, pow(10, 9*exp)

    def finalizeImage(self, painter, imageid, image_transform, size=None):
        caps = self.used_caps
        unit = self.used_unit
        return self.parameters.drawScaleBar(painter, caps, unit, size)

class CellArea(CellGeometry):
    coloring_name = u"Cell area"
    settings_name = u"CellArea"
    unit = u"m²"

    bestUnit = CellGeometry.bestUnitSquare

    def value(self, imageid, cid):
        data = self.result[imageid]
        pts = self.result.cellAtTime(cid, data.index)
        if len(pts) < 3:
            return None
        polygon = []
        prev = pts[-1]
        for pid in pts:
            w = data.walls[prev, pid]
            polygon.extend(w)
            polygon.append(data[pid])
            prev = pid
        value = polygonArea(polygon)
        log_debug("Cell area = %g" % (value,))
        return value
