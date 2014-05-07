from __future__ import print_function, division, absolute_import

from tracking_plot import (ColoringObject, ColorParameters, ColoringObjectType)

class ConstantColor(ColoringObject):
    parameter_class = ColorParameters

    def __init__(self, result):
        ColoringObject.__init__(self, result)

    def __call__(self, imageid, uid):
        return self.parameters.color

    @staticmethod
    def accept_result_type(result_type):
        return True

class CellConstantColor(ConstantColor):
    coloring_name = "Constant color"
    settings_name = "CellConstantColor"

    __metaclass__ = ColoringObjectType('cell')

    def __init__(self, result):
        ConstantColor.__init__(self, result)

class WallConstantColor(ConstantColor):
    coloring_name = "Constant color"
    settings_name = "WallConstantColor"

    __metaclass__ = ColoringObjectType('wall')

    def __init__(self, result):
        ConstantColor.__init__(self, result)

class PointConstantColor(ConstantColor):
    coloring_name = "Constant color"
    settings_name = "PointConstantColor"
    
    __metaclass__ = ColoringObjectType('point')

    def __init__(self, result):
        ConstantColor.__init__(self, result)
