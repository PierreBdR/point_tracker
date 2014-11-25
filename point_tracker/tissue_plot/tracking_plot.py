# coding=utf-8
from __future__ import print_function, division, absolute_import
"""
This module contains the bases classes needed for plotting.
"""
__author__ = "Pierre Barbier de Reuille <pierre@barbierdereuille.net>"

from PyQt4.QtGui import (QColor, QDialog, QFontDialog, QFont, QDoubleValidator, QPicture,
                         QPainter, QFileDialog)
from PyQt4.QtCore import QObject, Slot, QTimer, Signal
from ..transferfunction import TransferFunction
from ..transferfunctiondlg import TransferFunctionDlg
from ..scale_bar import ScaleBar as ScaleBarDrawer
from ..sys_utils import setColor, changeColor, getColor, createForm
from ..debug import log_debug
from math import hypot as norm
from ..path import path
from ..tracking_data import RetryTrackingDataException, TrackingData
from ..growth_computation_methods import Result
from ..sys_utils import toBool, cleanQObject

def make_cap_symetric(caps):
    caps = list(caps)
    if caps[0] * caps[1] < 0:
        caps[1] = max(abs(caps[0]), abs(caps[1]))
        caps[0] = -caps[1]
    elif caps[1] > 0:
        caps[0] = 0
    else:
        caps[1] = 0
    return tuple(caps)

cell_colorings_cls = []
"""
List of cell coloring classes.

:type: list of class
"""

wall_colorings_cls = []
"""
List of wall coloring classes.

:type: list of class
"""

point_colorings_cls = []
"""
List of point coloring classes.

:type: list of class
"""

class Struct(object):
    pass

def reset_classes():
    global cell_colorings_cls
    global wall_colorings_cls
    global point_colorings_cls
    del cell_colorings_cls[:]
    del wall_colorings_cls[:]
    del point_colorings_cls[:]

def transfer_fct_dlg():
    """
    This function create a singleton of the transfer function dialog box.
    """
    if transfer_fct_dlg.instance is None:
        dlg = TransferFunctionDlg()
        dlg.use_histogram = False
        dlg.loadSettings("")
        transfer_fct_dlg.instance = dlg
    return transfer_fct_dlg.instance

transfer_fct_dlg.instance = None

class NoParametersObject(QObject):
    changed = Signal()

    """
    Class handling parameters when none are needed.

    It is also useful as a template to create a new parameter class.

    :Parameters:
        params : struct
            Structure holding the parameters for this class
    """
    def __init__(self, params, parent=None):
        QObject.__init__(self, parent)
        pass

    def widget(self, parent):
        """
        :returns: The widget used to get the values or None.
        :returntype: QWidget|None
        """
        return None

    @staticmethod
    def load(params, settings):
        """
        Load the parameters and save them in the `params` argument.

        :Parameters:
            params : struct
                Structure in which to place the parameters.
            settings : `QSettings`
                Settings object where the settings are read. No need to create a group ...
        """
        pass

    @staticmethod
    def save(params, settings):
        """
        Save the parameters contained in the `params` argument.

        :Parameters:
            params : struct
                Structure in which to place the parameters.
            settings : `QSettings`
                Settings object where the settings are read. No need to create a group ...
        """
        pass

class ColoringObject(QObject):
    changed = Signal()
    """
    Base class for all coloring object.

    If the parameters of the object change, the ``changed`` signal is sent.

    :signal: ``changed``
    """

    parameter_class = NoParametersObject
    """
    Object used to store the parameters
    """

    coloring_name = None
    """
    Name of the coloring.
    """

    settings_name = None
    """
    Name used to store in the settings
    """

    def __init__(self, result, parent=None):
        QObject.__init__(self, parent)
        self._result = result
        self._parameters = None
        self._config = None
        self._update_parameters()

    def __del__(self):
        cleanQObject(self)

    @property
    def result(self):
        '''Result object used for coloring'''
        return self._result

    @result.setter
    def result(self, value):
        if self._result != value:
            self._result = value
            self._update_parameters()

    @property
    def parameters(self):
        '''
        Parameter class as a singleton per instance
        '''
        if self._parameters is None:
            self._parameters = self.create_parameters()
            self._parameters.changed.connect(self.changed)
        return self._parameters

#{ Main interface methods
    def init(self):
        """
        Initialise the object if needed.

        This function is called once after all the parameters of the object are set to allow for precomputing.
        """
        pass

    def startImage(self, painter, imageid):
        """
        This method is called once the image is placed but before any cell or wall is drawn.
        """
        pass

    def finalizeImage(self, painter, imageid, image_transform, size=None):
        """
        This method is called after all cells and walls are drawn.

        Useful to add elements global to the image (i.e. color scale, ...)
        """
        pass

    def __call__(self, imageid, uid):
        """
        :Parameters:
            imageid : int
                Id of the image in the result (i.e. its position in the images list)
            uid : int | (int,int)
                A cell id if integer, a wall id if tuple

        :returns: the color of the object according to the instanciated class.

        :returntype: `QColor`
        """
        raise NotImplemented("This is an abstract method.")

    def config_widget(self, parent):
        """
        Default implementation returns `_config` if it exists, otherwise,
        call `_config_widget` and store the result in `_config` for
        later calls.

        :returns: The configuration widget for the current method
        :returntype: `QWidget`
        """
        if self._config is None:
            log_debug("Creating config widget")
            self._config = self._config_widget(parent)
            self._update_parameters()
        return self._config

    @staticmethod
    def accept_result_type(result_type):
        """
        :returns: true if the result type is handled by the class, False otherwise.
        :returntype: bool

        Default implementation accept nothing.

        :Parameters:
        result_type: str
            For now, it is one of "Data" and "Growth" depending if the object is a growth
            result object or a data object.
        """
        return False

#{ Private methods to implement in subclasses if needed

    def _update_parameters(self):
        """
        Update the parameters according to the current result object.

        Default implementation does nothing.
        """
        pass

    def _config_widget(self, parent):
        """
        Return a new config widget at each call.
        """
        return self.parameters.widget(parent)

    @classmethod
    def load_parameters(cls, settings):
        """
        Load the parameters from settings.

        Default implementation uses the class defined in the `parameter_class`
        class member with the name `settings_name`.
        """
        from ..parameters import instance
        params = instance.plotting
        name = cls.settings_name
        s = Struct()
        settings.beginGroup(name)
        cls.parameter_class.load(s, settings)
        setattr(params, name, s)
        settings.endGroup()

    @classmethod
    def save_parameters(cls, settings):
        """
        Save the parameters into a settings object.

        Default implementation uses the class defined in the `parameter_class`
        class member with the name `settings_name`.
        """
        from ..parameters import instance
        params = instance.plotting
        name = cls.settings_name
        if hasattr(params, name):
            s = getattr(params, name)
            settings.beginGroup(name)
            cls.parameter_class.save(s, settings)
            settings.endGroup()

    @classmethod
    def create_parameters(cls):
        """
        Create an instance of the parameter class `parameter_class`.
        """
        from ..parameters import instance
        params = instance.plotting
        name = cls.settings_name
        p = getattr(params, name)
        return cls.parameter_class(p)
#}

coloring_baseclasses = {}

coloring_classes = {'cell': cell_colorings_cls,
                    'wall': wall_colorings_cls,
                    'point': point_colorings_cls}

coloring_metaclasses = {}

def ColoringObjectType(*objects):
    if not objects:
        objects = ('cell', 'wall', 'point')
    objects = frozenset(objects)
    global coloring_metaclasses
    if objects not in coloring_metaclasses:
        colorings_cls = tuple(coloring_classes[obj] for obj in objects)

        class ObjectColoringObjectType(type(QObject)):
            def __init__(cls, name, bases, dct):
                #print("Adding coloring object {0} for objects {1}".format(cls, ", ".join(objects)))
                type(QObject).__init__(cls, name, bases, dct)
                if cls.coloring_name:
                    for ccls in colorings_cls:
                        ccls.append(cls)
        coloring_metaclasses[objects] = ObjectColoringObjectType
    return coloring_metaclasses[objects]

def ColoringClass(objects=None, base=ColoringObject):
    if objects is None:
        objects = ('cell', 'wall', 'point')
    elif not isinstance(objects, tuple):
        objects = (objects,)
    ids = frozenset(objects + (base,))
    global coloring_baseclasses
    if ids not in coloring_baseclasses:
        name = "{0}ColoringBaseClass".format("".join(t.capitalize() for t in objects))
        ColoringBaseClass = ColoringObjectType(*objects)(name, (base,), {})
        coloring_baseclasses[ids] = ColoringBaseClass
    return coloring_baseclasses[ids]

class ScaleBar(QObject):
    changed = Signal()
    """
    The scale bar has to be inherited.

    It assumes there is a `transfer_function` property defined when the scale bar might be drawn.

    If any parameter change, the ``changed`` signal is sent.

    :signal: ``changed``
    """
    def __init__(self, params, parent=None):
        QObject.__init__(self, parent)
        self._scale_config = None
        self._scale_config_param = None
        self._scale_text = params.scale_text
        self._scale_line = params.scale_line
        self._scale_line_thickness = params.scale_line_thickness
        self._scale_position = params.scale_position
        self._scale_font = params.scale_font
        self._scale_show = params.scale_show
        self._scale_bar_outside_image = params.scale_bar_outside_image
        self._params = params

    def _showConfig(self):
        self._scale_config_param.exec_()

    def addScaleBarWidget(self, parent):
        config = createForm("plot_scale.ui", parent)
        config_params = createForm("plot_scale_config.ui", None)
        self._scale_config = config
        self._scale_config_param = config_params

        config.configuration.clicked.connect(self._showConfig)
        config.scaleBar.toggled.connect(self.set_scale_show)
        config_params.selectTextColor.clicked.connect(self._changeScaleTextColor)
        config_params.selectLineColor.clicked.connect(self._changeScaleLineColor)
        config_params.selectPosition.highlighted['QString'].connect(self.set_scale_position)
        config_params.selectFont.clicked.connect(self._changeFont)
        config_params.lineThickness.valueChanged[int].connect(self._changeScaleLineThickness)
        config_params.outsideImage.toggled.connect(self._set_scaleBarOutsideImage)

        config.scaleBar.setChecked(self.scale_show)
        scaled_font = QFont(self.scale_font)
        scaled_font.setPointSizeF(config_params.selectFont.font().pointSizeF())
        config_params.selectFont.setFont(scaled_font)
        setColor(config_params.textColor, self.scale_text)
        setColor(config_params.lineColor, self.scale_line)
        config_params.outsideImage.setChecked(self.scale_bar_outside_image)
        for i in range(config_params.selectPosition.count()):
            txt = config_params.selectPosition.itemText(i)
            if txt == self.scale_position:
                config_params.selectPosition.setCurrentIndex(i)
                break
        else:
            self.scale_position = config_params.selectPosition.itemText(0)
            config_params.selectPosition.setCurrentIndex(0)
        parent.layout().addWidget(config)

    @Slot()
    def _changeFont(self):
        fnt, ok = QFontDialog.getFont(self.scale_font, self._scale_config_param, "Font for the color scale bar")
        if ok:
            self.scale_font = fnt
            normal_size = self._scale_config_param.selectFont.font().pointSizeF()
            scaled_font = QFont(fnt)
            scaled_font.setPointSizeF(normal_size)
            self._scale_config_param.selectFont.setFont(scaled_font)

    @Slot()
    def _changeScaleLineColor(self):
        if changeColor(self._scale_config_param.lineColor):
            self.scale_line = getColor(self._scale_config_param.lineColor)

    @Slot(int)
    def _changeScaleLineThickness(self, value):
        self.scale_line_thickness = value

    @Slot(bool)
    def _set_scaleBarOutsideImage(self, value):
        self.scale_bar_outside_image = value

    @Slot()
    def _changeScaleTextColor(self):
        if changeColor(self._scale_config_param.textColor):
            self.scale_text = getColor(self._scale_config_param.textColor)

    @property
    def scale_text(self):
        """
        Color of the text on the scale bar

        :returntype: QColor
        """
        return self._scale_text

    @scale_text.setter
    def scale_text(self, value):
        value = QColor(value)
        if self._scale_text != value:
            self._scale_text = value
            self._params.scale_text = value
            self.changed.emit()

    @property
    def scale_line(self):
        """
        Color of the line around the scale bar and the ticks of the scale bar.

        :returntype: QColor
        """
        return self._scale_line

    @scale_line.setter
    def scale_line(self, value):
        value = QColor(value)
        if self._scale_line != value:
            self._scale_line = value
            self._params.scale_line = value
            self.changed.emit()

    @property
    def scale_line_thickness(self):
        """
        Thickness of the line around the scale bar and the ticks of the scale bar.

        :returntype: QColor
        """
        return self._scale_line_thickness

    @scale_line_thickness.setter
    def scale_line_thickness(self, value):
        value = int(value)
        if self._scale_line_thickness != value:
            self._scale_line_thickness = value
            self._params.scale_line_thickness = value
            self.changed.emit()

    @property
    def scale_position(self):
        """
        Position of the scale bar with respect to the image. Must be one of "Top", "Right", "Bottom" or "Left".

        :returntype: str
        """
        return self._scale_position

    @scale_position.setter
    def scale_position(self, value):
        value = str(value)
        if self._scale_position != value:
            self._scale_position = value
            self._params.scale_position = value
            self.changed.emit()

    @Slot(str)
    def set_scale_position(self, value):
        self.scale_position = value

    @property
    def scale_show(self):
        """
        Wether or not to show the scale bar

        :returntype: bool
        """
        return self._scale_show

    @scale_show.setter
    def scale_show(self, value):
        value = bool(value)
        if self._scale_show != value:
            self._scale_show = value
            self._params.scale_show = value
            self.changed.emit()

    @Slot(bool)
    def set_scale_show(self, value):
        self.scale_show = value

    @property
    def scale_bar_outside_image(self):
        """
        Wether or not to show the scale bar

        :returntype: bool
        """
        return self._scale_bar_outside_image

    @scale_bar_outside_image.setter
    def scale_bar_outside_image(self, value):
        value = bool(value)
        if self._scale_bar_outside_image != value:
            self._scale_bar_outside_image = value
            self._params.scale_bar_outside_image = value
            self.changed.emit()

    @property
    def scale_font(self):
        """
        Font used for the text of the scale bar.

        :returntype: QFont
        """
        return self._scale_font

    @scale_font.setter
    def scale_font(self, value):
        value = QFont(value)
        if self._scale_font != value:
            self._scale_font = value
            self._params.scale_font = value
            self.changed.emit()

    def drawScaleBar(self, painter, value_range, unit="", size=None):
        if self.scale_show:
            sc = ScaleBarDrawer(position=self.scale_position,
                                transfer_function=self.transfer_function,
                                font=self.scale_font,
                                text_color=self.scale_text,
                                line_color=self.scale_line,
                                line_thickness=self.scale_line_thickness,
                                value_range=value_range,
                                unit=unit)
            log_debug("Drawing scale bar!")
            if not self.scale_bar_outside_image:
                sc.draw(painter, size)
            else:
                if size is None:
                    viewport = painter.viewport()  # viewport rectangle
                    mat, ok = painter.worldMatrix().inverted()
                    if not ok:
                        raise ValueError("Transformation matrix of painter is singular.")
                    size = mat.mapRect(viewport)
                pic = QPicture()
                new_painter = QPainter()
                new_painter.begin(pic)
                bounding_rect = sc.draw(new_painter, size)
                new_painter.end()
                pic.setBoundingRect(pic.boundingRect() | bounding_rect.toRect())
                log_debug("Returning picture %s" % (pic,))
                return pic

    @staticmethod
    def load(params, settings):
        col = QColor(settings.value("ScaleText"))
        if not col.isValid():
            col = QColor(0, 0, 0)
        params.scale_text = col
        col = QColor(settings.value("ScaleLine"))
        if not col.isValid():
            col = QColor(0, 0, 0)
        params.scale_line = col
        try:
            params.scale_line_thickness = int(settings.value("ScaleLineThickness"))
        except (ValueError, TypeError):
            params.scale_line_thickness = 0
        params.scale_position = settings.value("ScalePosition", "Top")
        fnt = QFont(settings.value("ScaleFont", QFont()))
        params.scale_font = fnt
        params.scale_show = toBool(settings.value("ScaleShow", "True"))
        params.scale_bar_outside_image = toBool(settings.value("ScaleBarOutsideImage", "False"))

    @staticmethod
    def save(params, settings):
        settings.setValue("ScaleText", params.scale_text)
        settings.setValue("ScaleLine", params.scale_line)
        settings.setValue("ScaleLineThickness", params.scale_line_thickness)
        settings.setValue("ScalePosition", params.scale_position)
        settings.setValue("ScaleFont", params.scale_font)
        settings.setValue("ScaleShow", params.scale_show)
        settings.setValue("ScaleBarOutsideImage", params.scale_bar_outside_image)

def fixRangeParameters(m, M):
    range = (m, M)

    class FixRangeParameters(ScaleBar):
        """
        Parameters for the theta object.
        """
        def __init__(self, params):
            ScaleBar.__init__(self, params)
            self.range = range
            self._transfer_function = params.transfer_function
            self._config = None

        @property
        def transfer_function(self):
            '''Transfer function used to convert values into colors

            :returntype: `TransferFunction`'''
            return self._transfer_function

        @transfer_function.setter
        def transfer_function(self, value):
            if self._transfer_function != value:
                self._transfer_function = TransferFunction(value)
                self._params.transfer_function = self._transfer_function
                self.changed.emit()

        @property
        def value_capping(self):
            return None

        @value_capping.setter
        def value_capping(self, value):
            pass

        @property
        def symetric_coloring(self):
            return False

        def widget(self, parent):
            config = createForm("plot_param_theta.ui", parent)
            self._config = config
            config.changeColorMap.clicked.connect(self._changeColorMap)
            self.addScaleBarWidget(config)
            return self._config

        def drawScaleBar(self, painter, value_range, unit, size=None):
            return ScaleBar.drawScaleBar(self, painter, self.range, unit, size)

        @Slot()
        def _changeColorMap(self):
            dlg = transfer_fct_dlg()
            dlg.transfer_fct = self.transfer_function
            if dlg.exec_() == QDialog.Accepted:
                self.transfer_function = dlg.transfer_fct
            dlg.saveSettings("")

        @staticmethod
        def load(params, settings):
            ScaleBar.load(params, settings)
            tr = settings.value("TransferFunction", "")
            if tr:
                params.transfer_function = TransferFunction.loads(tr)
            else:
                params.transfer_function = TransferFunction.hue_scale()
            params.symetric_coloring = False
            params.value_capping = None

        @staticmethod
        def save(params, settings):
            ScaleBar.save(params, settings)
            settings.setValue("TransferFunction", params.transfer_function.dumps())
    return FixRangeParameters

class TransferFunctionParameters(ScaleBar):
    """
    Parameters for continuous objects.
    """
    def __init__(self, params):
        ScaleBar.__init__(self, params)
        self._transfer_function = params.transfer_function
        self._symetric_coloring = params.symetric_coloring
        self._value_capping = params.value_capping
        self._minmax_values = (-100.0, 100.0)
        self._config = None

    @property
    def transfer_function(self):
        '''Transfer function used to convert values into colors

        :returntype: `TransferFunction`'''
        return self._transfer_function

    @transfer_function.setter
    def transfer_function(self, value):
        if self._transfer_function != value:
            self._transfer_function = TransferFunction(value)
            self._params.transfer_function = self._transfer_function
            self.changed.emit()

    @property
    def symetric_coloring(self):
        '''
        If true, the color scheme is forced to be symetric. i.e. If all
        values are of the same sign, then 0 is forced into the range.
        Otherwise, 0 is the middle color of the transfer function.

        :returntype: `bool`
        '''
        return self._symetric_coloring

    @symetric_coloring.setter
    def symetric_coloring(self, value):
        value = bool(value)
        if self._symetric_coloring != value:
            self._symetric_coloring = value
            self._params.symetric_coloring = value
            self.changed.emit()

    @Slot(bool)
    def set_symetric_coloring(self, value):
        self.symetric_coloring = value

    @property
    def value_capping(self):
        """
        If not None, value_capping gives the min and max of the color used.
        If symetric_coloring is True, the actual capping will be adjusted
        to a symetric one.

        :returntype: (float,float)|None
        """
        return self._value_capping

    @value_capping.setter
    def value_capping(self, value):
        if value is not None:
            value = (float(value[0]), float(value[1]))
        if self._value_capping != value:
            self._value_capping = value
            self._params.value_capping = value
            self.changed.emit()

    @property
    def minmax_values(self):
        '''
        Get the min and max of the values for the capping

        :returntype: (float,float)
        '''
        return self._minmax_values

    @minmax_values.setter
    def minmax_values(self, value):
        value = (float(value[0]), float(value[1]))
        if self._minmax_values != value:
            self._minmax_values = value
            self.changed.emit()
            if self._config is not None:
                self.resetMinMax(value)

    def resetMinMax(self, bounds):
        self._config.minCap.setText(u"{:.5g}".format(bounds[0]))
        self._config.maxCap.setText(u"{:.5g}".format(bounds[1]))

    def widget(self, parent):
        config = createForm("plot_param_fct.ui", parent)
        self._config = config
        config.changeColorMap.clicked.connect(self._changeColorMap)
        config.symetricColoring.toggled[bool].connect(self.set_symetric_coloring)
        config.capping.toggled[bool].connect(self._cappingChanged)
        config.minCap.setValidator(QDoubleValidator(config.minCap))
        config.maxCap.setValidator(QDoubleValidator(config.minCap))
        config.minCap.textChanged["const QString&"].connect(self._minCapStringChanged)
        config.maxCap.textChanged["const QString&"].connect(self._maxCapStringChanged)
        value = self.minmax_values
        self.resetMinMax(value)
        config.symetricColoring.setChecked(self._symetric_coloring)
        if self._value_capping is not None:
            config.capping.setChecked(True)
            config.minCap.setText(u"{:.5g}".format(self._value_capping[0]))
            config.maxCap.setText(u"{:.5g}".format(self._value_capping[1]))
        self.addScaleBarWidget(config)
        return self._config

    @Slot()
    def _changeColorMap(self):
        dlg = transfer_fct_dlg()
        if self._symetric_coloring:
            dlg.stickers = [0.5]
        dlg.transfer_fct = self.transfer_function
        if dlg.exec_() == QDialog.Accepted:
            self.transfer_function = dlg.transfer_fct
        dlg.stickers = []
        dlg.saveSettings("")

    @Slot(bool)
    def _cappingChanged(self, value):
        if value:
            self.value_capping = (float(self._config.minCap.text()), float(self._config.maxCap.text()))
        else:
            self.value_capping = None

    @Slot("const QString&")
    def _minCapStringChanged(self, value):
        try:
            value_double = float(value)
        except ValueError:
            return
        cap = self.value_capping
        if cap is not None:
            if value_double != cap[0]:
                cap = (value_double, cap[1])
                self.value_capping = cap

    @Slot("const QString&")
    def _maxCapStringChanged(self, value):
        try:
            value_double = float(value)
        except ValueError:
            return
        cap = self.value_capping
        if cap is not None:
            if value_double != cap[1]:
                cap = (cap[0], value_double)
                self.value_capping = cap

    @staticmethod
    def load(params, settings):
        ScaleBar.load(params, settings)
        tr = settings.value("TransferFunction", "")
        if tr:
            params.transfer_function = TransferFunction.loads(str(tr))
        else:
            params.transfer_function = TransferFunction.hue_scale()
        params.symetric_coloring = toBool(settings.value("SymetricColoring", "False"))
        isc = toBool(settings.value("IsCapping", "False"))
        if isc:
            vc = [0, 0]
            try:
                vc[0] = float(settings.value("ValueCappingMin"))
            except (ValueError, TypeError):
                vc[0] = 0
            try:
                vc[1] = float(settings.value("ValueCappingMax"))
            except (ValueError, TypeError):
                vc[1] = 1
            params.value_capping = vc
        else:
            params.value_capping = None

    @staticmethod
    def save(params, settings):
        ScaleBar.save(params, settings)
        tf = params.transfer_function.dumps()
        settings.setValue("TransferFunction", tf)
        settings.setValue("SymetricColoring", params.symetric_coloring)
        if params.value_capping is not None:
            settings.setValue("IsCapping", True)
            settings.setValue("ValueCappingMin", params.value_capping[0])
            settings.setValue("ValueCappingMax", params.value_capping[1])
        else:
            settings.setValue("IsCapping", False)

class DirectionGrowthParameters(ScaleBar):
    """
    Parameters for growth along a direction.
    """
    def __init__(self, params):
        ScaleBar.__init__(self, params)
        self._transfer_function = params.transfer_function
        self._symetric_coloring = params.symetric_coloring
        self._value_capping = params.value_capping
        self._minmax_values = (-100.0, 100.0)
        self._config = None
        self._data_file = ""
        self.data = None
        self._direction = None
        self._data_points = (0, 1)
        self._next_data_file = None
        self._orthogonal = params.orthogonal
        self._draw_line = params.draw_line
        self._line_width = params.line_width
        self._line_color = params.line_color
        self.edit_timer = QTimer(self)
        self.edit_timer.setSingleShot(True)
        self.edit_timer.setInterval(500)
        self.edit_timer.timeout.connect(self.loadEdit)

    @property
    def data_file(self):
        """Data file holding the points for the direction"""
        return self._data_file

    @data_file.setter
    def data_file(self, value):
        value = path(value)
        if self._data_file != value:
            self._data_file = value
            self.load_data()
            self.changed.emit()

    def load_data(self, **loading_arguments):
        try:
            if self.data_file == self.result.current_filename:
                self.data = self.result.data
            else:
# First, prepare the data by getting the images and computing how big they
# should be
                f = open(self.data_file)
                first_line = f.readline()
                f.close()
                if first_line.startswith("TRKR_VERSION"):
                    result = Result(None)
                    result.load(self.data_file, **loading_arguments)
                    data = result.data
                else:
                    data = TrackingData()
                    data.load(self.data_file, **loading_arguments)
                data.copyAlignementAndScale(self.result.data)
                self.data = data
            self.points = list(self.data.cell_points)
            if self._config is not None:
                config = self._config
                config.point1.clear()
                config.point2.clear()
                for i in self.points:
                    log_debug("i = %s" % i)
                    config.point1.addItem(str(i))
                    config.point2.addItem(str(i))
                config.point1.setCurrentIndex(0)
                config.point2.setCurrentIndex(1)
        except RetryTrackingDataException as ex:
            loading_arguments.update(ex.method_args)
            self.load_data(**loading_arguments)

    def direction(self, img_data):
        i1, i2 = self.data_points
        p1 = img_data[i1]
        p2 = img_data[i2]
        u = p2 - p1
        u /= norm(u.x(), u.y())
        return u

    @Slot("const QString&")
    def _changePoint1(self, value):
        try:
            value = int(value)
            if value != self.data_points[0]:
                self.data_points = (value, self.data_points[1])
        except ValueError as err:
            log_debug("Error while changing point1 = %s" % str(err))

    @Slot("const QString&")
    def _changePoint2(self, value):
        try:
            value = int(value)
            if value != self.data_points[1]:
                self.data_points = (self.data_points[0], value)
        except ValueError as err:
            log_debug("Error while changing point1 = %s" % str(err))

    @property
    def data_points(self):
        """Ids of the data points defining the direction in the data file"""
        return self._data_points

    @data_points.setter
    def data_points(self, value):
        value = (int(value[0]), int(value[1]))
        if self._data_points != value:
            self._data_points = value
            self.changed.emit()

    @property
    def transfer_function(self):
        '''Transfer function used to convert values into colors

        :returntype: `TransferFunction`'''
        return self._transfer_function

    @transfer_function.setter
    def transfer_function(self, value):
        if self._transfer_function != value:
            self._transfer_function = TransferFunction(value)
            self._params.transfer_function = self._transfer_function
            self.changed.emit()

    @property
    def symetric_coloring(self):
        '''
        If true, the color scheme is forced to be symetric. i.e. If all
        values are of the same sign, then 0 is forced into the range.
        Otherwise, 0 is the middle color of the transfer function.

        :returntype: `bool`
        '''
        return self._symetric_coloring

    @symetric_coloring.setter
    def symetric_coloring(self, value):
        value = bool(value)
        if self._symetric_coloring != value:
            self._symetric_coloring = value
            self._params.symetric_coloring = value
            self.changed.emit()

    @property
    def orthogonal(self):
        """If true, the points mark the line orthogonal to the direction wanted"""
        return self._orthogonal

    @orthogonal.setter
    @Slot(bool)
    def orthogonal(self, value):
        value = bool(value)
        if self._orthogonal != value:
            self._orthogonal = value
            self._params.orthogonal = value
            self.changed.emit()

    @property
    def draw_line(self):
        """If truem draw the line defining the direction"""
        return self._draw_line

    @draw_line.setter
    @Slot(bool)
    def draw_line(self, value):
        value = bool(value)
        if self._draw_line != value:
            self._draw_line = value
            self._params.draw_line = value
            self.changed.emit()

    @property
    def line_color(self):
        """Color of the line defining the direction"""
        return self._line_color

    @line_color.setter
    def line_color(self, value):
        value = QColor(value)
        if self._line_color != value:
            self._line_color = value
            self._params.line_color = value
            self.changed.emit()

    @property
    def line_width(self):
        """Width of the line in pixels"""
        return self._line_width

    @line_width.setter
    @Slot(int)
    def line_width(self, value):
        value = int(value)
        if self._line_width != value:
            self._line_width = value
            self._params.line_width = value
            self.changed.emit()

    @property
    def value_capping(self):
        """
        If not None, value_capping gives the min and max of the color used.
        If symetric_coloring is True, the actual capping will be adjusted
        to a symetric one.

        :returntype: (float,float)|None
        """
        return self._value_capping

    @value_capping.setter
    def value_capping(self, value):
        if value is not None:
            value = (float(value[0]), float(value[1]))
        if self._value_capping != value:
            self._value_capping = value
            self._params.value_capping = value
            self.changed.emit()

    @property
    def minmax_values(self):
        '''
        Get the min and max of the values for the capping

        :returntype: (float,float)
        '''
        return self._minmax_values

    @minmax_values.setter
    def minmax_values(self, value):
        value = (float(value[0]), float(value[1]))
        if self._minmax_values != value:
            self._minmax_values = value
            self.changed.emit()
            if self._config is not None:
                self.resetMinMax(value)

    def resetMinMax(self, bounds):
        self._config.minCap.setText(u"{:.5g}".format(bounds[0]))
        self._config.maxCap.setText(u"{:.5g}".format(bounds[1]))

    @Slot()
    def _changeLineColor(self):
        if changeColor(self._config.lineColor):
            self.line_color = getColor(self._config.lineColor)

    def widget(self, parent):
        config = createForm("plot_param_dir_fct.ui", parent)
        self._config = config
        config.selectDataFile.clicked.connect(self._selectDataFile)
        config.changeColorMap.clicked.connect(self._changeColorMap)
        config.dataFile.textChanged.connect(self._checkAndLoad)
        config.orthogonal.toggled.connect(self._set_orthogonal)
        config.symetricColoring.toggled[bool].connect(self._set_symetric_coloring)
        config.capping.toggled[bool].connect(self._cappingChanged)
        config.minCap.setValidator(QDoubleValidator(config.minCap))
        config.maxCap.setValidator(QDoubleValidator(config.minCap))
        config.minCap.textChanged['QString'].connect(self._minCapStringChanged)
        config.maxCap.textChanged['QString'].connect(self._maxCapStringChanged)
        config.point1.currentIndexChanged['QString'].connect(self._changePoint1)
        config.point2.currentIndexChanged['QString'].connect(self._changePoint2)
        config.drawLine.toggled.connect(self._set_draw_line)
        config.lineWidth.valueChanged.connect(self._set_line_width)
        config.selectLineColor.clicked.connect(self._changeLineColor)

        config.dataFile.setText(self.data_file)
        value = self.minmax_values
        self.resetMinMax(value)
        config.orthogonal.setChecked(self.orthogonal)
        config.symetricColoring.setChecked(self._symetric_coloring)
        config.drawLine.setChecked(self.draw_line)
        config.lineWidth.setValue(self.line_width)
        setColor(config.lineColor, self.line_color)
        if self._value_capping is not None:
            config.capping.setChecked(True)
            config.minCap.setText(u"{:.5g}".format(self._value_capping[0]))
            config.maxCap.setText(u"{:.5g}".format(self._value_capping[1]))
        if self.data is not None:
            config = self._config
            config.point1.clear()
            config.point2.clear()
            for i in self.points:
                config.point1.addItem(str(i))
                config.point2.addItem(str(i))
            config.point1.setCurrentIndex(0)
            config.point2.setCurrentIndex(1)
        self.addScaleBarWidget(config)
        return self._config

    @Slot()
    def _selectDataFile(self):
        fn = QFileDialog.getOpenFileName(self._config, "Select the data file defining your line", self.data_file,
                                         "All data files (*.csv *.xls);;CSV Files (*.csv);;"
                                         "XLS files (*.xls);;"
                                         "All files (*.*)")
        if fn:
            self._config.dataFile.setText(fn)

    @Slot("const QString&")
    def _checkAndLoad(self, txt):
        pth = path(txt)
        if pth.exists() and pth.isfile():
            self._next_data_file = pth
            self.edit_timer.start()
        else:
            self._next_data_file = None
            self.edit_timer.stop()

    @Slot()
    def loadEdit(self):
        if self._next_data_file is not None:
            self.data_file = self._next_data_file

    @Slot()
    def _changeColorMap(self):
        dlg = transfer_fct_dlg()
        if self._symetric_coloring:
            dlg.stickers = [0.5]
        dlg.transfer_fct = self.transfer_function
        if dlg.exec_() == QDialog.Accepted:
            self.transfer_function = dlg.transfer_fct
        dlg.stickers = []
        dlg.saveSettings("")

    @Slot(bool)
    def _cappingChanged(self, value):
        if value:
            self.value_capping = (float(self._config.minCap.text()), float(self._config.maxCap.text()))
        else:
            self.value_capping = None

    @Slot("const QString&")
    def _minCapStringChanged(self, value):
        try:
            value_double = float(value)
        except ValueError:
            return
        cap = self.value_capping
        if cap is not None:
            if value_double != cap[0]:
                cap = (value_double, cap[1])
                self.value_capping = cap

    @Slot("const QString&")
    def _maxCapStringChanged(self, value):
        try:
            value_double = float(value)
        except ValueError:
            return
        cap = self.value_capping
        if cap is not None:
            if value_double != cap[1]:
                cap = (cap[0], value_double)
                self.value_capping = cap

    @staticmethod
    def load(params, settings):
        ScaleBar.load(params, settings)
        df = settings.value("DataFile", "")
        if df:
            params.data_file = path(df)
        else:
            params.data_file = None
        try:
            p0 = int(settings.value("DataPoint0"))
        except (ValueError, TypeError):
            p0 = 0
        try:
            p1 = int(settings.value("DataPoint1"))
        except (ValueError, TypeError):
            p1 = 1
        params.data_points = (p0, p1)
        tr = settings.value("TransferFunction", "")
        if tr:
            params.transfer_function = TransferFunction.loads(str(tr))
        else:
            params.transfer_function = TransferFunction.hue_scale()
        params.orthogonal = toBool(settings.value("Orthogonal"))
        params.symetric_coloring = toBool(settings.value("SymetricColoring", False))
        params.draw_line = toBool(settings.value("DrawLine", False))
        col = QColor(settings.value("LineColor"))
        if not col.isValid():
            col = QColor(0, 0, 0)
        params.line_color = col
        try:
            lw = int(settings.value("LineWidth", 0))
        except (ValueError, TypeError):
            lw = 0
        params.line_width = lw
        isc = toBool(settings.value("IsCapping"))
        if isc:
            vc = [0, 0]
            try:
                vc[0] = float(settings.value("ValueCappingMin"))
            except (ValueError, TypeError):
                vc[0] = 0
            try:
                vc[1] = float(settings.value("ValueCappingMax"))
            except (ValueError, TypeError):
                vc[1] = 1
            params.value_capping = vc
        else:
            params.value_capping = None

    @staticmethod
    def save(params, settings):
        ScaleBar.save(params, settings)
        settings.setValue("DataFile", params.data_file)
        settings.setValue("DataPoint0", params.data_points[0])
        settings.setValue("DataPoint1", params.data_points[1])
        settings.setValue("Orthogonal", params.orthogonal)
        settings.setValue("DrawLine", params.draw_line)
        settings.setValue("LineWidth", params.line_width)
        settings.setValue("LineColor", params.line_color)
        tf = params.transfer_function.dumps()
        settings.setValue("TransferFunction", tf)
        settings.setValue("SymetricColoring", params.symetric_coloring)
        if params.value_capping is not None:
            settings.setValue("IsCapping", True)
            settings.setValue("ValueCappingMin", params.value_capping[0])
            settings.setValue("ValueCappingMax", params.value_capping[1])
        else:
            settings.setValue("IsCapping", False)


class ColorParameters(QObject):
    changed = Signal()
    """
    Parameters for continuous objects.
    """
    def __init__(self, params, parent=None):
        QObject.__init__(self, parent)
        log_debug("Parameter object: %s" % id(params))
        self._color = params.color
        self._params = params

    def widget(self, parent):
        config = createForm("plot_param_color.ui", parent)
        setColor(config.color, self._color)
        config.selectColor.clicked.connect(self._changeColor)
        self._config = config
        return config

    @Slot()
    def _changeColor(self):
        if changeColor(self._config.color):
            self.color = getColor(self._config.color)

    @property
    def color(self):
        '''Color used for the rendering of the property.

        :returntype: `QColor`'''
        return self._color

    @color.setter
    def color(self, value):
        value = QColor(value)
        if self._color != value:
            self._color = value
            self._params.color = value
            self.changed.emit()

    @staticmethod
    def load(params, settings):
        log_debug("Loading with parameter object: %s" % id(params))
        color = QColor(settings.value("Color"))
        if not color.isValid():
            color = QColor(0, 0, 0)
        params.color = color

    @staticmethod
    def save(params, settings):
        settings.setValue("Color", params.color)
