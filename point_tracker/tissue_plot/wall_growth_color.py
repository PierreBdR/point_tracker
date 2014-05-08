from __future__ import print_function, division, absolute_import
from .tracking_plot import ColoringClass, TransferFunctionParameters
from PyQt4.QtGui import QColor
from numpy import inf, log

def make_cap_symetric(caps):
    caps = list(caps)
    if caps[0]*caps[1] < 0:
        caps[1] = max(abs(caps[0]), abs(caps[1]))
        caps[0] = -caps[1]
    elif caps[1] > 0:
        caps[0] = 0
    else:
        caps[1] = 0
    return tuple(caps)

class WallGrowth(ColoringClass('wall')):
    coloring_name = u"Wall growth rate"
    settings_name = u"WallGrowthRate"
    parameter_class = TransferFunctionParameters

    def __init__(self, result, doubling_time = False):
        self.doubling_time = doubling_time
        ColoringClass('wall').__init__(self, result)

    def init(self):
        caps = self.parameters.value_capping
        if caps is None:
            caps = self.value_range()
        if self.parameters.symetric_coloring:
            caps = make_cap_symetric(caps)
        self.dc = 1/(caps[1]-caps[0])
        self.shiftc = caps[0]
        self.caps = caps

    def finalizeImage(self, painter, imageid, image_transform, size = None):
        caps = self.caps
        if self.doubling_time:
            caps = (caps[0]/log(2), caps[1]/log(2))
        self.parameters.drawScaleBar(painter, caps, u"1/h", size)

    def _update_parameters(self):
        caps = self.value_range()
        if self.doubling_time:
            caps = (caps[0]/log(2), caps[1]/log(2))
        self.parameters.minmax_values = caps

    def value_range(self):
        result = self.result
        caps = [inf,-inf]
        for i in range(len(result)):
            if result.walls[i]:
                caps[0] = min(caps[0], min(result.walls[i].values()))
                caps[1] = max(caps[1], max(result.walls[i].values()))
        return caps

    def __call__(self, imageid, wid):
        fct = self.parameters.transfer_function
        if fct is None:
            return QColor()
        value = self.result.walls[imageid][wid]
        col = QColor()
        col.setRgbF(*fct.rgba((value-self.shiftc)*self.dc))
        return col

    @staticmethod
    def accept_result_type(result_type):
        return result_type == "Growth"

class WallDoublingTime(WallGrowth):
    coloring_name = u"Wall binary growth rate"
    settings_name = u"WallDoublingTime"

    def __init__(self, result):
        WallGrowth.__init__(self, result, True)

