from __future__ import print_function, division, absolute_import

from tracking_plot import (ColoringClass, TransferFunctionParameters, fixRangeParameters, make_cap_symetric, DirectionGrowthParameters)
from PyQt4.QtGui import QColor, QPen
from PyQt4.QtCore import QString, Qt
from numpy import inf, log, pi, dot
from ..growth_algo import params2Tensor
from ..debug import print_debug

class CellAreaGrowth(ColoringClass('cell')):
    coloring_name = "Area growth rate"
    settings_name = "CellAreaGrowthRate"
    parameter_class = TransferFunctionParameters
    unit = QString.fromUtf8("1/h")

    def __init__(self, result, doubling_time = False):
        self.doubling_time = doubling_time
        ColoringClass('cell').__init__(self, result)

    def init(self):
        caps = self.parameters.value_capping
        if caps is None:
            caps = self.value_range()
            if self.parameters.symetric_coloring:
                caps = make_cap_symetric(caps)
        self.caps = caps
        self.dc = 1/(caps[1]-caps[0])
        self.shiftc = caps[0]

    def finalizeImage(self, painter, imageid, image_transform, size = None):
        caps = self.caps
        if self.doubling_time:
            caps = (caps[0]/log(2), caps[1]/log(2))
        return self.parameters.drawScaleBar(painter, caps, QString.fromUtf8("1/h"), size)

    def _update_parameters(self):
        caps = self.value_range()
        if self.doubling_time:
            caps = (caps[0]/log(2), caps[1]/log(2))
        self.parameters.minmax_values = caps

    def value_range(self):
        result = self.result
        caps = [inf,-inf]
        for i in range(len(result)):
            if result.cells_area[i]:
                caps[0] = min(caps[0], min(result.cells_area[i].values()))
                caps[1] = max(caps[1], max(result.cells_area[i].values()))
        return caps

    def __call__(self, imageid, uid):
        fct = self.parameters.transfer_function
        if fct is None:
            return QColor()
        value = self.result.cells_area[imageid][uid]
        col = QColor()
        col.setRgbF(*fct.rgba((value-self.shiftc)*self.dc))
        return col

    @staticmethod
    def accept_result_type(result_type):
        return result_type == "Growth"

class CellGrowthAlongDirection(ColoringClass('cell')):
    coloring_name = "Growth along a direction"
    settings_name = "GrowthDirection"
    parameter_class = DirectionGrowthParameters
    unit = QString.fromUtf8("1/h")
    
    def __init__(self, result):
        ColoringClass('cell').__init__(self, result)

    def init(self):
        f = self.parameters.data_file
        caps = self.parameters.value_capping
        if caps is None:
            caps = self.value_range()
            if self.parameters.symetric_coloring:
                caps = make_cap_symetric(caps)
        self.caps = caps
        self.dc = 1/(caps[1]-caps[0])
        self.shiftc = caps[0]
        if self.parameters.orthogonal:
            self.unit = QString.fromUtf8("Orthogonal (1/h)")
        else:
            self.unit = QString.fromUtf8("Parallel (1/h)")

    def startImage(self, painter, imageid):
        params = self.parameters
        image_name = self.result.images[imageid]
        img_data = params.data[image_name]
        self.current_image = image_name
        p1, p2 = params.data_points
        pt1 = img_data[p1]
        pt2 = img_data[p2]
        self.pts = (pt1, pt2)
        u = self.parameters.direction(img_data)
        if self.parameters.orthogonal:
            u = [u.y(), -u.x()]
        else:
            u = [u.x(), u.y()]
        self.direction = u

    def finalizeImage(self, painter, imageid, image_transform, size = None):
        caps = self.caps
        image_name = self.result.images[imageid]
        params = self.parameters
        if params.draw_line:
            pt1, pt2 = self.pts
            painter.save()
            painter.setWorldTransform(image_transform)
            pen = QPen()
            pen.setCosmetic(True)
            pen.setColor(params.line_color)
            pen.setWidth(params.line_width)
            painter.setPen(pen)
            painter.drawLine(pt1, pt2)
            painter.restore()
        del self.direction
        del self.pts
        del self.current_image
        return self.parameters.drawScaleBar(painter, caps, self.unit, size)

    def _update_parameters(self):
        params = self.parameters
        params.result = self.result
        if hasattr(self.result, "current_filename"):
            params.data_file = self.result.current_filename
        caps = self.value_range()
        params.minmax_values = caps

    def value_range(self):
        result = self.result
        caps = [inf,-inf]
        for i in range(len(result)):
            if result.cells[i]:
                caps[0] = min(caps[0], min(min(v[0:2]) for v in result.cells[i].itervalues()))
                caps[1] = max(caps[1], max(max(v[0:2]) for v in result.cells[i].itervalues()))
        return caps

    def __call__(self, imageid, uid):
        fct = self.parameters.transfer_function
        if fct is None:
            return QColor()
        image_name = self.current_image
        params = self.result.cells[imageid][uid]
        T = params2Tensor(*params)
        u = self.direction
        value = dot(dot(T, u), u)
        col = QColor()
        col.setRgbF(*fct.rgba((value-self.shiftc)*self.dc))
        return col

    @staticmethod
    def accept_result_type(result_type):
        return result_type == "Growth"

#class CellAreaDoublingTime(CellAreaGrowth):
#    coloring_name = "Area binary growth rate"
#    settings_name = "CellAreaDoublingTime"
#    unit = QString.fromUtf8("h")

#    def __init__(self, result):
#        CellAreaGrowth.__init__(self, result, True)

class CellGrowthAnisotropy(ColoringClass('cell')):
    coloring_name = "Growth anisotropy"
    settings_name = "GrowthAnisotropy"
    parameter_class = fixRangeParameters(0,1)
    unit = QString.fromUtf8("")
    
    def __init__(self, result):
        ColoringClass('cell').__init__(self, result)
        self.parameters.symetric_coloring = False
        self.parameters.value_capping = None
    
    def finalizeImage(self, painter, imageid, image_transform, size=None):
        return self.parameters.drawScaleBar(painter, None, self.unit, size)

    def __call__(self, imageid, cid):
        fct = self.parameters.transfer_function
        if fct is None:
            return QColor()
        values = self.result.cells[imageid][cid]
        if values[0] == 0:
            value = 0
        else:
            value = 1 - values[1]/values[0]
        col = QColor()
        col.setRgbF(*fct.rgba(value))
        return col

    @staticmethod
    def accept_result_type(result_type):
        return result_type == "Growth"

class CellGrowth(ColoringClass('cell')):
    parameter_class = TransferFunctionParameters

    def __init__(self, result, info_pos, doubling_time = False, ratio=1):
        self.info_pos = info_pos
        self.doubling_time = doubling_time
        self.ratio = ratio
        ColoringClass('cell').__init__(self, result)

    def init(self):
        #info_pos = self.info_pos
        caps = self.parameters.value_capping
        if caps is None:
            caps = self.value_range()
            if self.parameters.symetric_coloring:
                caps = make_cap_symetric(caps)
        self.dc = 1/(caps[1]-caps[0])
        self.shiftc = caps[0]
        self.caps = caps

    def finalizeImage(self, painter, imageid, image_transform, size=None):
        caps = self.caps
        if self.doubling_time:
            caps = (caps[0]/log(2), caps[1]/log(2))
        return self.parameters.drawScaleBar(painter, caps, self.unit, size)

    def _update_parameters(self):
        caps = self.value_range()
        if self.doubling_time:
            caps = (caps[0]/log(2), caps[1]/log(2))
        self.parameters.minmax_values = caps

    def value_range(self):
        info_pos = self.info_pos
        result = self.result
        caps = [inf,-inf]
        ratio = self.ratio
        for i in range(len(result)):
            if result.cells[i]:
                caps[0] = min(caps[0], min(ratio*v[info_pos] for v in result.cells[i].itervalues()))
                caps[1] = max(caps[1], max(ratio*v[info_pos] for v in result.cells[i].itervalues()))
        return caps

    def __call__(self, imageid, cid):
        info_pos = self.info_pos
        fct = self.parameters.transfer_function
        if fct is None:
            return QColor()
        value = self.ratio*self.result.cells[imageid][cid][info_pos]
        col = QColor()
        col.setRgbF(*fct.rgba((value-self.shiftc)*self.dc))
        return col

    @staticmethod
    def accept_result_type(result_type):
        return result_type == "Growth"

class CellKMaj(CellGrowth):
    coloring_name = "Major growth rate"
    settings_name = "CellMajorGrowthRate"
    unit = QString.fromUtf8("1/h")

    def __init__(self, result):
        CellGrowth.__init__(self, result, 0)

#class CellKMajDoublingTime(CellGrowth):
#    coloring_name = "Major binary growth rate"
#    settings_name = "CellMajorDoublingTime"
#    unit = QString.fromUtf8("1/h")
#
#    def __init__(self, result):
#        CellGrowth.__init__(self, result, 0, True)

class CellKMin(CellGrowth):
    coloring_name = "Minor growth rate"
    settings_name = "CellMinorGrowthRate"
    unit = QString.fromUtf8("1/h")

    def __init__(self, result):
        CellGrowth.__init__(self, result, 1)

#class CellKMinDoublingTime(CellGrowth):
#    coloring_name = "Minor binary growth rate"
#    settings_name = "CellMinorDoublingTime"
#    unit = QString.fromUtf8("1/h")
#
#    def __init__(self, result):
#        CellGrowth.__init__(self, result, 1, True)

class CellTheta(CellGrowth):
    coloring_name = "Major axis orientation"
    settings_name = "CellTheta"
    parameter_class = fixRangeParameters(-90, 90)
    unit = QString.fromUtf8("")

    def __init__(self, result):
        CellGrowth.__init__(self, result, 2, ratio=180/pi)
        self.parameters.symetric_coloring = True
        self.parameters.value_capping = None

class CellPhi(CellGrowth):
    coloring_name = "Vorticity"
    settings_name = "CellPhi"
    unit = QString.fromUtf8("1/h")

    def __init__(self, result):
        CellGrowth.__init__(self, result, 3)


