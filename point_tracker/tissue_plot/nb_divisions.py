from __future__ import print_function, division, absolute_import
from .tracking_plot import ColoringClass, TransferFunctionParameters
from PyQt4.QtGui import QColor
from numpy import inf

class NbVerticesDrawing(ColoringClass('cell')):
    coloring_name = "Number of divisions"
    settings_name = "NbDivisions"
    parameter_class = TransferFunctionParameters

    @staticmethod
    def accept_result_type(result_type):
        return result_type == "Data"

    def __init__(self, result):
        ColoringClass('cell').__init__(self, result)

    def init(self):
        caps = self.parameters.value_capping
        if caps is None or caps[0] >= caps[1]:
            caps = (0, self.maxNbDivisions())
        self.caps = caps
        self.shift = caps[0]
        self.delta = 1 / (caps[1] - caps[0])

    def maxNbDivisions(self):
        result = self.result
        nb_divs = {}
        self.nb_divs = nb_divs

        def getNbDivs(cell):
            if cell not in nb_divs:
                ls = result.cells_lifespan[cell]
                if ls.parent is not None:
                    nb_divs[cell] = getNbDivs(ls.parent) + 1
                else:
                    nb_divs[cell] = 0
            return nb_divs[cell]

        return max(getNbDivs(c) for c in self.result.cells_lifespan)

    def _update_parameters(self):
        self.parameters.minmax_values = (0, self.maxNbDivisions())

    def __call__(self, imageid, cid):
        fct = self.parameters.transfer_function
        if fct is None:
            return QColor(0, 0, 0, 0)
        value = self.nb_divs[cid]
        col = QColor()
        col.setRgbF(*fct.rgba((value - self.shift)*self.delta))
        return col

    def finalizeImage(self, painter, imageid, image_transform, size=None):
        return self.parameters.drawScaleBar(painter, self.caps, "", size)
