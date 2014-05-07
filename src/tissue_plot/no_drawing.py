from tracking_plot import ColoringClass
from PyQt4.QtGui import QColor

class NoDrawing(ColoringClass()):
    coloring_name = "Invisible"
    settings_name = "NoDrawing"

    @staticmethod
    def accept_result_type(result_type):
        return True

    def __call__(self, imageid, uid):
        return QColor(0,0,0,0)

