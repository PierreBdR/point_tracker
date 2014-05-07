from __future__ import print_function, division, absolute_import
"""
:newfield signal: Signal, Signals
"""
__author__ = "Pierre Barbier de Reuille <pierre@barbierdereuille.net>"
__docformat__ = "restructuredtext"

from PyQt4.QtGui import QColor, QPen
from PyQt4.QtCore import Qt, QPointF, QObject, SIGNAL, QSettings
from . import parameters
from .geometry import gravityCenter
from .debug import print_debug
from . import tissue_plot
from math import pi

#debug_object = object
cell_colorings_dict = {}
"""
Dictionnary version of `cell_colorings_cls`. The key is the class coloring name.
"""

class Struct(object):
    pass

def resetClasses():
    """
    Reset the list of classes.

    Save the current classes preferences and load the new ones.
    """
    saveCellParamClasses()
    saveWallParamClasses()
    savePointParamClasses()
    errors = tissue_plot.loadClasses()
    initCellParamClasses()
    initWallParamClasses()
    initPointParamClasses()
    return errors

def initParamClasses(colorings_dict, colorings_cls, ctype):
    """
    Initialize the cell parameter classes with default settings
    """
    colorings_dict.clear()
    colorings_dict.update((cls.coloring_name, cls) for cls in colorings_cls)
    if not hasattr(parameters.instance, "plotting"):
        parameters.instance.plotting = Struct()
    settings = QSettings()
    settings.beginGroup("Plotting")
    for cls in colorings_cls:
        print_debug("Init class '%s' for %s coloring '%s'" % (cls.__name__, ctype, cls.coloring_name))
        load_params = getattr(cls, "load_parameters", None)
        if load_params is not None:
            load_params(settings)
    settings.endGroup()

def saveParamClasses(colorings_cls):
    """
    Initialize the cell parameter classes with default settings
    """
    if not hasattr(parameters.instance, "plotting"):
        return
    settings = QSettings()
    settings.beginGroup("Plotting")
    for cls in colorings_cls:
        save_params = getattr(cls, "save_parameters", None)
        if save_params is not None:
            save_params(settings)
    settings.endGroup()

def initCellParamClasses():
    """
    Initialize the cell parameter classes with default settings
    """
    initParamClasses(cell_colorings_dict, tissue_plot.cell_colorings_cls, "cell")

def saveCellParamClasses():
    """
    Initialize the cell parameter classes with default settings
    """
    saveParamClasses(tissue_plot.cell_colorings_cls)

wall_colorings_dict = {}
"""
Dictionnary version of `wall_colorings_cls`. The key is the class coloring name.
"""

def initWallParamClasses():
    """
    Initialize the wall parameter classes with default settings
    """
    initParamClasses(wall_colorings_dict, tissue_plot.wall_colorings_cls, "wall")

def saveWallParamClasses():
    saveParamClasses(tissue_plot.wall_colorings_cls)


point_colorings_dict = {}
"""
Dictionnary version of `wall_colorings_cls`. The key is the class coloring name.
"""

def initPointParamClasses():
    """
    Initialize the wall parameter classes with default settings
    """
    initParamClasses(point_colorings_dict, tissue_plot.point_colorings_cls, "wall")

def savePointParamClasses():
    saveParamClasses(tissue_plot.point_colorings_cls)

def createColoring(coloring_dict, coloring, result):
    coloring = str(coloring)
    try:
        cls = coloring_dict[coloring]
    except KeyError:
        raise ValueError("Cell coloring type '%s' not implemented" % coloring)
    return cls(result)

def createCellColoring(coloring, result):
    return createColoring(cell_colorings_dict, coloring, result)

def createWallColoring(coloring, result):
    return createColoring(wall_colorings_dict, coloring, result)

def createPointColoring(coloring, result):
    return createColoring(point_colorings_dict, coloring, result)

def coloringClasses(result_type, colorings_cls, ctype):
    items = []
    for cls in colorings_cls:
        if cls.accept_result_type(result_type):
            items.append(cls)
    print_debug("%s coloring for %s: %s" % (ctype, result_type, [cls.coloring_name for cls in items]))
    return items

def cellColoringClasses(result_type):
    return coloringClasses(result_type, tissue_plot.cell_colorings_cls, 'Cell')

def wallColoringClasses(result_type):
    return coloringClasses(result_type, tissue_plot.wall_colorings_cls, 'Wall')

def pointColoringClasses(result_type):
    return coloringClasses(result_type, tissue_plot.point_colorings_cls, 'Point')

class EllipsisDraw(QObject):
    """
    Object holding ellipsis parameters.

    :signals: ``changed``
    """
    def __init__(self, result, parent=None):
        QObject.__init__(self, parent)
        self.result = result
        params = parameters.instance
        self._scaling = params.ellipsis_scaling
        self._thickness = params.ellipsis_thickness
        self._positive_color = params.ellipsis_positive_color
        self._negative_color = params.ellipsis_negative_color
        self._color = params.ellipsis_color
        self._plot = params.ellipsis_plot
        self._min_anisotropy = params.ellipsis_min_anisotropy
        self._scale_axis = True
        self._major_axis = True
        self._minor_axis = True

    def _get_color(self):
        '''Color used to draw the ellipsis itself
        
        :returntype: QColor'''
        return self._color

    def _set_color(self, value):
        value = QColor(value)
        if self._color != value:
            self._color = value
            parameters.instance.ellipsis_color = value
            self.emit(SIGNAL("changed"))

    color = property(_get_color, _set_color)

    def _get_scaling(self):
        '''Scaling factor for ellipsis drawing
        
        :returntype: float'''
        return self._scaling

    def _set_scaling(self, value):
        value = float(value)
        if self._scaling != value:
            self._scaling = value
            parameters.instance.ellipsis_scaling = value
            self.emit(SIGNAL("changed"))

    scaling = property(_get_scaling, _set_scaling)
    
    def _get_scale_axis(self):
        '''Are the axis scaled or do they just represent direction?
        
        :returntype: bool'''
        return self._scale_axis
    
    def _set_scale_axis(self, value):
        value = bool(value)
        if self._scale_axis != value:
            self._scale_axis = value
            parameters.instance.ellipsis_scale_axis = value
            self.emit(SIGNAL("changed"))

    scale_axis = property(_get_scale_axis, _set_scale_axis)

    def _get_major_axis(self):
        '''Draw the major axis of the ellipsis?
        
        :returntype: bool'''
        return self._major_axis
    
    def _set_major_axis(self, value):
        value = bool(value)
        if self._major_axis != value:
            self._major_axis = value
            parameters.instance.ellipsis_major_axis = value
            self.emit(SIGNAL("changed"))

    major_axis = property(_get_major_axis, _set_major_axis)

    def _get_minor_axis(self):
        '''Draw the minor axis of the ellipsis?
        
        :returntype: bool'''
        return self._minor_axis
    
    def _set_minor_axis(self, value):
        value = bool(value)
        if self._minor_axis != value:
            self._minor_axis = value
            parameters.instance.ellipsis_minor_axis = value
            self.emit(SIGNAL("changed"))

    minor_axis = property(_get_minor_axis, _set_minor_axis)

    def _get_thickness(self):
        '''Thickness of the ellipsis drawing
        
        :returntype: float'''
        return self._thickness

    def _set_thickness(self, value):
        value = float(value)
        if self._thickness != value:
            self._thickness = value
            parameters.instance.ellipsis_thickness = value
            self.emit(SIGNAL("changed"))

    thickness = property(_get_thickness, _set_thickness)

    def _get_min_anisotropy(self):
        '''Minimum anisotropy under which the axis of the ellipsis are not drawned anymore
        
        :returntype: float'''
        return self._min_anisotropy

    def _set_min_anisotropy(self, value):
        value = float(value)
        if self._min_anisotropy != value:
            self._min_anisotropy = value
            parameters.instance.ellipsis_min_anisotropy = value
            self.emit(SIGNAL("changed"))

    min_anisotropy = property(_get_min_anisotropy, _set_min_anisotropy)

    def _get_positive_color(self):
        '''Color used to draw the axis if positive
        
        :returntype: QColor'''
        return self._positive_color

    def _set_positive_color(self, value):
        value = QColor(value)
        if self._positive_color != value:
            self._positive_color = value
            parameters.instance.ellipsis_positive_color = value
            self.emit(SIGNAL("changed"))

    positive_color = property(_get_positive_color, _set_positive_color)

    def _get_negative_color(self):
        '''Color used to draw the axis if negative
        
        :returntype: QColor'''
        return self._negative_color

    def _set_negative_color(self, value):
        value = QColor(value)
        if self._negative_color != value:
            self._negative_color = value
            parameters.instance.ellipsis_negative_color = value
            self.emit(SIGNAL("changed"))

    negative_color = property(_get_negative_color, _set_negative_color)

    def _get_plot(self):
        '''True if the ellipsis is to be plotted at all
        
        :returntype: bool'''
        return self._plot

    def _set_plot(self, value):
        value = bool(value)
        if self._plot != value:
            self._plot = value
            parameters.instance.ellipsis_plot = value
            self.emit(SIGNAL("changed"))

    plot = property(_get_plot, _set_plot)

    def __call__(self, painter, imageid, cid, pts, image_scale):
        center = gravityCenter(pts)
        (kmaj, kmin, theta, _) = self.result.cells[imageid][cid]
        scaling = image_scale*self.scaling
        if abs(1-kmin/kmaj) < self.min_anisotropy:
            return # Don't draw the ellipsis
        elif self.scale_axis:
            kmaj *= scaling
            kmin *= scaling
        else:
            kmaj = scaling
            kmin = -scaling/2
        painter.save()
        pen = QPen()
        pen.setWidthF(self.thickness*image_scale)
        pen.setColor(self.color)
        pen_positive = QPen(pen)
        pen_positive.setColor(self.positive_color)
        pen_negative = QPen(pen)
        pen_negative.setColor(self.negative_color)
        painter.setPen(pen)
        painter.setBrush(Qt.NoBrush)
        painter.translate(center)
        painter.rotate(theta*180/pi)
        if self.major_axis:
            if kmaj >= 0:
                painter.setPen(pen_positive)
            else:
                painter.setPen(pen_negative)
            painter.drawLine(QPointF(-kmaj, 0), QPointF(kmaj, 0))
        if self.minor_axis:
            if kmin >= 0:
                painter.setPen(pen_positive)
            else:
                painter.setPen(pen_negative)
            painter.drawLine(QPointF(0, -kmin), QPointF(0, kmin))
        painter.setPen(pen)
        painter.drawEllipse(QPointF(0, 0), kmaj, kmin)
        painter.restore()
