from __future__ import print_function, division, absolute_import
from tracking_plot import ColoringClass, TransferFunctionParameters
from PyQt4.QtGui import QColor

class NbVerticesDrawing(ColoringClass('cell')):
    coloring_name = "Number of vertices"
    settings_name = "NbVertices"
    parameter_class = TransferFunctionParameters

    @staticmethod
    def accept_result_type(result_type):
        return result_type == "Data"

    def __init__(self, result):
        ColoringClass('cell').__init__(self, result)
        
    def init(self):
        self.max_nb_vertices = self.maxNbVertices()

    def maxNbVertices(self):
        max_nb_vertices = 0
        for img in self.result:
            for c in img.cells:
                pts = self.result.cellAtTime(c, img.index)
                max_nb_vertices = max(max_nb_vertices, len(pts))
        return max_nb_vertices

    def _update_parameters(self):
        self.parameters.minmax_values = (0, self.maxNbVertices())

    def __call__(self, imageid, cid):
        fct = self.parameters.transfer_function
        result = self.result
        image_data = result[imageid]
        if fct is None:
            return QColor(0,0,0,0)
        pts = result.cellAtTime(cid, image_data.index)
        value = len(pts)
        col = QColor()
        col.setRgbF(*fct.rgba(value/self.max_nb_vertices))
        return col

    def finalizeImage(self, painter, imageid, image_transform, size=None):
        return self.parameters.drawScaleBar(painter, (0, self.max_nb_vertices), "", size)
