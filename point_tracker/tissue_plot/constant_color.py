from __future__ import print_function, division, absolute_import

from .tracking_plot import (ColoringObject, ColorParameters, ColoringClass)

class ConstantColor(ColoringObject):
    parameter_class = ColorParameters

    def __init__(self, result):
        ColoringObject.__init__(self, result)

    def __call__(self, imageid, uid):
        return self.parameters.color

    @staticmethod
    def accept_result_type(result_type):
        return True

class CellConstantColor(ColoringClass('cell', base=ConstantColor)):
    coloring_name = "Constant color"
    settings_name = "CellConstantColor"

    def __init__(self, result):
        ConstantColor.__init__(self, result)

class WallConstantColor(ColoringClass('wall', base=ConstantColor)):
    coloring_name = "Constant color"
    settings_name = "WallConstantColor"

    def __init__(self, result):
        ConstantColor.__init__(self, result)

class PointConstantColor(ColoringClass('point', base=ConstantColor)):
    coloring_name = "Constant color"
    settings_name = "PointConstantColor"

    def __init__(self, result):
        ConstantColor.__init__(self, result)
