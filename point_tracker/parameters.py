from __future__ import print_function, division, absolute_import
__author__ = "Pierre Barbier de Reuille <pierre@barbierdereuille.net>"
__docformat__ = "restructuredtext"
from PyQt4.QtCore import (QCoreApplication, QObject, QSettings, QRectF,
                          Qt, Signal)
from PyQt4.QtGui import QColor, QFontMetricsF, QFont
from .path import path
from math import floor, ceil
from .sys_utils import toBool  # , cleanQObject


class Parameters(QObject):

    pointParameterChange = Signal()
    oldPointParameterChange = Signal()
    arrowParameterChange = Signal()
    searchParameterChange = Signal()
    renderingChanged = Signal()
    recentProjectsChange = Signal()
    plottingParameterChange = Signal()
    cellParameterChange = Signal()

    """
    Signal launched when parameters change:
        - pointParameterChange
        - oldPointParameterChange
        - arrowParameterChange
        - searchParameterChange
        - renderingChanged
        - recentProjectsChange
        - cellParameterChange
        - plottingParameterChange
    """
    def __init__(self):
        QObject.__init__(self)
        self.load()

    #def __del__(self):
        #cleanQObject(self)

    # Use thread or not to compute on the background
    use_thread = False

    def load(self):
        settings = QSettings()

        settings.beginGroup("GraphicParameters")
# First, parameters for normal points
        self._point_size = None
        try:
            _point_size = float(settings.value("PointSize"))
        except (ValueError, TypeError):
            _point_size = 5.0
        self.point_size = _point_size
        self._point_thickness = None
        try:
            _point_thickness = int(settings.value("PointThickness"))
        except (ValueError, TypeError):
            _point_thickness = 0
        self.point_thickness = _point_thickness
        self._point_color = None
        _point_color = QColor(settings.value("PointColor"))
        if not _point_color.isValid():
            _point_color = QColor(Qt.red)
        self.point_color = _point_color
        _selected_point_color = QColor(settings.value("SelectedPointColor"))
        if not _selected_point_color.isValid():
            _selected_point_color = QColor(255, 128, 128, 255)
        self._selected_point_color = _selected_point_color
        _new_point_color = QColor(settings.value("NewPointColor"))
        if not _new_point_color.isValid():
            _new_point_color = QColor(Qt.blue)
        self._new_point_color = None
        self.new_point_color = _new_point_color

# Parameter for cells
        self._cell_size = None
        try:
            _cell_size = float(settings.value("CellSize"))
        except (ValueError, TypeError):
            _cell_size = 5.0
        self.cell_size = _cell_size
        self._cell_thickness = None
        try:
            _cell_thickness = int(settings.value("CellThickness"))
        except (ValueError, TypeError):
            _cell_thickness = 1
        self.cell_thickness = _cell_thickness
        self._cell_color = None
        _cell_color = QColor(settings.value("CellColor"))
        if not _cell_color.isValid():
            _cell_color = QColor(Qt.darkCyan)
            _cell_color.setAlphaF(0.5)
        self.cell_color = _cell_color

        self._selected_cell_color = None
        _selected_cell_color = QColor(settings.value("SelectedCellColor"))
        if not _selected_cell_color.isValid():
            _selected_cell_color = QColor(Qt.yellow)
            _selected_cell_color.setAlphaF(0.5)
        self.selected_cell_color = _selected_cell_color

        self._division_wall_color = None
        _division_wall_color = QColor(settings.value("DivisionWallColor"))
        if not _division_wall_color.isValid():
            _division_wall_color = QColor(255, 85, 0)
            _division_wall_color.setAlphaF(0.8)
        self.division_wall_color = _division_wall_color

# Then, parameters for old points
        try:
            self._old_point_size = float(settings.value("OldPointSize"))
        except (ValueError, TypeError):
            self._old_point_size = 5.0
        try:
            self._old_point_thickness = int(settings.value("OldPointThickness"))
        except (ValueError, TypeError):
            self._old_point_thickness = 0
        self._old_point_color = None
        self._old_point_color = QColor(settings.value("OldPointColor"))
        if not self._old_point_color.isValid():
            self._old_point_color = QColor(Qt.yellow)
        self._old_point_matching_color = QColor(settings.value("OldPointMatchingColor"))
        if not self._old_point_matching_color.isValid():
            self._old_point_matching_color = QColor(Qt.darkYellow)
        self._show_id = toBool(settings.value("ShowId", 'false'))
# Parameters for arrow
        try:
            self._arrow_line_size = float(settings.value("ArrowLineSize"))
        except (ValueError, TypeError):
            self._arrow_line_size = 2
        try:
            self._arrow_head_size = float(settings.value("ArrowHeadSize"))
        except (ValueError, TypeError):
            self._arrow_head_size = .1
        self._arrow_color = QColor(settings.value("ArrowColor"))
        if not self._arrow_color.isValid():
            self._arrow_color = QColor(Qt.lightGray)
        self._draw_arrow = toBool(settings.value("DrawArrow", 'true'))
        self._show_template = toBool(settings.value("ShowTemplate", 'false'))
        self._template_color = QColor(settings.value("TemplateColor"))
        if not self._template_color.isValid():
            self._template_color = QColor(255, 0, 0, 100)
        self._search_color = QColor(settings.value("SearchColor"))
        if not self._search_color.isValid():
            self._search_color = QColor(255, 0, 255, 100)
        settings.endGroup()

# The search parameters
        settings.beginGroup("SearchParameters")
        try:
            self._template_size = int(settings.value("TemplateSize"))
        except (ValueError, TypeError):
            self._template_size = 10
        s = self._template_size
        self.template_rect = QRectF(-s, -s, 2*s, 2*s)
        try:
            self._search_size = int(settings.value("SearchSize"))
        except (ValueError, TypeError):
            self._search_size = 50
        s = self._search_size
        self.search_rect = QRectF(-s, -s, 2*s, 2*s)
        self._estimate = toBool(settings.value("Estimate", 'false'))
        try:
            self._filter_size_ratio = float(settings.value("FilterSizeRatio"))
        except (ValueError, TypeError):
            self._filter_size_ratio = .5
        settings.endGroup()

        settings.beginGroup("GUI")
        self._show_vectors = toBool(settings.value("ShowVectors", 'true'))
        self._link_views = toBool(settings.value("LinkViews", 'true'))
        try:
            cache_size = int(settings.value("CacheSize"))
        except (ValueError, TypeError):
            cache_size = 200
        self.cache_size = cache_size
        self._last_dir = path(settings.value("LastsDir", "."))
        self._use_OpenGL = toBool(settings.value("UseOpenGL", 'false'))
        settings.beginGroup("RecentProjects")
        try:
            numproj = int(settings.value("NumberOfProjects"))
        except (ValueError, TypeError):
            numproj = 0
        self._recent_projects = []
        if numproj > 0:
            for i in range(numproj):
                name = "Project%d" % i
                value = path(settings.value(name))
                self._recent_projects.append(value)
        try:
            self._max_number_of_projects = int(settings.value("MaxNumberOfProjects"))
        except (ValueError, TypeError):
            self._max_number_of_projects = 5
        settings.endGroup()
        settings.endGroup()

# The plotting parameters
        settings.beginGroup("PlottingParameters")
        settings.beginGroup("Ellipsis")
        try:
            self._ellipsis_scaling = float(settings.value("Scaling", 1.0))
        except (ValueError, TypeError):
            self._ellipsis_scaling = 1.0
        self._ellipsis_color = QColor(settings.value("Color"))
        if not self._ellipsis_color.isValid():
            self._ellipsis_color = QColor(0, 0, 0)
        try:
            self._ellipsis_thickness = int(settings.value("Thickness", 0))
        except (ValueError, TypeError):
            self._ellipsis_thickness = 0
        try:
            self._ellipsis_min_anisotropy = float(settings.value("MinAnisotropy", 1e-3))
        except (ValueError, TypeError):
            self._ellipsis_min_anisotropy = 1e-3
        self._ellipsis_positive_color = QColor(settings.value("PositiveColor"))
        if not self._ellipsis_positive_color.isValid():
            self._ellipsis_positive_color = QColor(0, 0, 255)
        self._ellipsis_negative_color = QColor(settings.value("NegativeColor"))
        if not self._ellipsis_negative_color.isValid():
            self._ellipsis_negative_color = QColor(255, 0, 0)
        self._ellipsis_plot = toBool(settings.value("Plot", 'false'))
        self._ellipsis_scale_axis = toBool(settings.value("ScaleAxis", 'false'))
        settings.endGroup()
        settings.endGroup()
        self._point_editable = True
        self._point_selectable = True
        self._cell_editable = False

    def save(self):
        settings = QSettings()
        settings.beginGroup("GraphicParameters")
        settings.setValue("PointSize", self._point_size)
        settings.setValue("PointColor", self._point_color)
        settings.setValue("PointThickness", self._point_thickness)
        settings.setValue("SelectedPointColor", self._selected_point_color)
        settings.setValue("NewPointColor", self._new_point_color)
        settings.setValue("CellSize", self._cell_size)
        settings.setValue("CellColor", self._cell_color)
        settings.setValue("CellThickness", self._cell_thickness)
        settings.setValue("SelectedCellColor", self._selected_cell_color)
        settings.setValue("DivisionWallColor", self._division_wall_color)
        settings.setValue("OldPointSize", self._old_point_size)
        settings.setValue("OldPointColor", self._old_point_color)
        settings.setValue("OldPointMatchingColor", self._old_point_matching_color)
        settings.setValue("ShowId", self._show_id)
        settings.setValue("ArrowLineSize", self._arrow_line_size)
        settings.setValue("ArrowHeadSize", self._arrow_head_size)
        settings.setValue("ArrowColor", self._arrow_color)
        settings.setValue("DrawArrow", self._draw_arrow)
        settings.setValue("ShowTemplate", self._show_template)
        settings.setValue("TemplateColor", self._template_color)
        settings.setValue("SearchColor", self._search_color)
        settings.endGroup()

        settings.beginGroup("SearchParameters")
        settings.setValue("TemplateSize", self._template_size)
        settings.setValue("SearchSize", self._search_size)
        settings.setValue("Estimate", self._estimate)
        settings.setValue("FilterSizeRatio", self._filter_size_ratio)
        settings.endGroup()

        settings.beginGroup("GUI")
        settings.setValue("UseOpenGL", self._use_OpenGL)
        settings.setValue("ShowVectors", self._show_vectors)
        settings.setValue("LinkViews", self._link_views)
        settings.setValue("CacheSize", self._cache_size)
        settings.setValue("LastsDir", unicode(self._last_dir))

        settings.beginGroup("RecentProjects")
        settings.setValue("MaxNumberOfProjects", self._max_number_of_projects)
        settings.setValue("NumberOfProjects", len(self._recent_projects))
        for i, p in enumerate(self._recent_projects):
            name = "Project%d" % i
            settings.setValue(name, unicode(p))
        settings.endGroup()
        settings.endGroup()
# The plotting parameters
        settings.beginGroup("PlottingParameters")
        settings.beginGroup("Ellipsis")
        settings.setValue("Scaling", self._ellipsis_scaling)
        settings.setValue("Color", self._ellipsis_color)
        settings.setValue("Thickness", self._ellipsis_thickness)
        settings.setValue("MinAnisotropy", self._ellipsis_min_anisotropy)
        settings.setValue("PositiveColor", self._ellipsis_positive_color)
        settings.setValue("NegativeColor", self._ellipsis_negative_color)
        settings.setValue("Plot", self._ellipsis_plot)
        settings.setValue("ScaleAxis", self._ellipsis_scale_axis)
        settings.endGroup()
        settings.endGroup()

#{ On Screen Drawing

    @property
    def point_size(self):
        """
        Size of a points on the scene
        """
        return self._point_size

    @point_size.setter
    def point_size(self, size):
        if size > 0 and size != self._point_size:
            self._point_size = size
            self._find_font()
            self.pointParameterChange.emit()

    @property
    def point_color(self):
        """
        Color used to draw points
        """
        return self._point_color

    @point_color.setter
    def point_color(self, color):
        col = QColor(color)
        if col.isValid() and col != self._point_color:
            self._point_color = col
            self.point_hover_color = col.lighter(150)
            if self.point_hover_color == col:
                self.point_hover_color = col.lighter(50)
            self.pointParameterChange.emit()

    @property
    def selected_point_color(self):
        """
        Set the color of a selected point
        """
        return self._selected_point_color

    @selected_point_color.setter
    def selected_point_color(self, color):
        col = QColor(color)
        if col.isValid() and col != self._selected_point_color:
            self._selected_point_color = col
            self.pointParameterChange.emit()

    @property
    def new_point_color(self):
        """
        Set the color of a new point
        """
        return self._new_point_color

    @new_point_color.setter
    def new_point_color(self, color):
        col = QColor(color)
        if col.isValid() and col != self._new_point_color:
            self._new_point_color = col
            self.new_point_hover_color = col.lighter(150)
            if self.new_point_hover_color == col:
                self.new_point_hover_color = col.lighter(50)
            self.pointParameterChange.emit()

    @property
    def cell_size(self):
        """
        Set the size of a cell graphic item
        """
        return self._cell_size

    @cell_size.setter
    def cell_size(self, new_size):
        if new_size > 0 and new_size != self._cell_size:
            self._cell_size = new_size
            self.cellParameterChange.emit()

    @property
    def cell_thickness(self):
        """
        Set the thickness of the line used to draw the cell graphic item
        """
        return self._cell_thickness

    @cell_thickness.setter
    def cell_thickness(self, th):
        thick = int(th)
        if thick >= 0 and thick != self._cell_thickness:
            self._cell_thickness = thick
            self.cellParameterChange.emit()

    @property
    def cell_color(self):
        """
        Set the color used to draw the cell
        """
        return self._cell_color

    @cell_color.setter
    def cell_color(self, color):
        col = QColor(color)
        if col.isValid() and col != self._cell_color:
            self._cell_color = col
            self.cell_hover_color = col.lighter(150)
            if self.cell_hover_color == col:
                self.cell_hover_color = col.lighter(50)
            self.cellParameterChange.emit()

    @property
    def selected_cell_color(self):
        """
        Set the color used to draw the selected cell
        """
        return self._selected_cell_color

    @selected_cell_color.setter
    def selected_cell_color(self, color):
        col = QColor(color)
        if col.isValid() and col != self._selected_cell_color:
            self._selected_cell_color = col
            self.cellParameterChange.emit()

    @property
    def division_wall_color(self):
        """
        Set the color used to draw the selected cell
        """
        return self._division_wall_color

    @division_wall_color.setter
    def division_wall_color(self, color):
        col = QColor(color)
        if col.isValid() and col != self._division_wall_color:
            self._division_wall_color = col
            self.cellParameterChange.emit()

    @property
    def old_point_size(self):
        """
        Size of a old points on the scene
        """
        return self._old_point_size

    @old_point_size.setter
    def old_point_size(self, size):
        if size > 0 and size != self._old_point_size:
            self._old_point_size = size
            self.oldPointParameterChange.emit()

    @property
    def old_point_color(self):
        """
        Color used to draw old points
        """
        return self._old_point_color

    @old_point_color.setter
    def old_point_color(self, color):
        col = QColor(color)
        if col.isValid() and col != self._old_point_color:
            self._old_point_color = col
            self.oldPointParameterChange.emit()

    @property
    def old_point_matching_color(self):
        """
        Color used to draw old point matching the current hovered point
        """
        return self._old_point_matching_color

    @old_point_matching_color.setter
    def old_point_matching_color(self, color):
        col = QColor(color)
        if col.isValid() and col != self._old_point_matching_color:
            self._old_point_matching_color = col
            self.oldPointParameterChange.emit()

    @property
    def arrow_line_size(self):
        """
        Width of the pen used to draw arrows.
        """
        return self._arrow_line_size

    @arrow_line_size.setter
    def arrow_line_size(self, size):
        if size > 0 and size != self._arrow_line_size:
            self._arrow_line_size = size
            self.arrowParameterChange.emit()

    @property
    def arrow_head_size(self):
        """
        Size of the arrow head in proportion to the length of the arrow
        """
        return self._arrow_head_size

    @arrow_head_size.setter
    def arrow_head_size(self, size):
        if 0 < size <= 1 and size != self._arrow_head_size:
            self._arrow_head_size = size
            self.arrowParameterChange.emit()

    @property
    def arrow_color(self):
        """
        Color used to draw arrows
        """
        return self._arrow_color

    @arrow_color.setter
    def arrow_color(self, color):
        col = QColor(color)
        if col.isValid() and col != self._arrow_color:
            self._arrow_color = col
            self.arrowParameterChange.emit()

    @property
    def draw_arrow(self):
        """
        Decide to make the arrows visible or not
        """
        return self._draw_arrow

    @draw_arrow.setter
    def draw_arrow(self, value):
        value = bool(value)
        if value != self._draw_arrow:
            self._draw_arrow = value
            self.arrowParameterChange.emit()

    @property
    def use_OpenGL(self):
        """
        Force the use of OpenGL for rendering images
        """
        return self._use_OpenGL

    @use_OpenGL.setter
    def user_OpenGL(self, value):
        if value != self._use_OpenGL:
            self._use_OpenGL = value
            self.renderingChanged.emit()

    @property
    def point_thickness(self):
        """Thickness of the line used to draw points"""
        return self._point_thickness

    @point_thickness.setter
    def point_thickness(self, value):
        value = int(value)
        if value >= 0 and self._point_thickness != value:
            self._point_thickness = value
            self.pointParameterChange.emit()

    @point_thickness.deleter
    def point_thickness(self):
        del self._point_thickness

    @property
    def old_point_thickness(self):
        """Thickness of the line used to draw old points"""
        return self._old_point_thickness

    @old_point_thickness.setter
    def old_point_thickness(self, value):
        value = int(value)
        if self._old_point_thickness != value:
            self._old_point_thickness = value
            self.oldPointParameterChange.emit()

    @property
    def show_vectors(self):
        """Are the vectors from old to now points shown?"""
        return self._show_vectors

    @show_vectors.setter
    def show_vectors(self, value):
        self._show_vectors = value

    @property
    def link_views(self):
        """Link the viewports of the two panes in the main GUI"""
        return self._link_views

    @link_views.setter
    def link_views(self, value):
        self._link_views = value

    @property
    def show_template(self):
        """
        Whether the template should be shown or not

        :returntype: bool
        """
        return self._show_template

    @show_template.setter
    def show_template(self, value):
        if value != self._show_template:
            self._show_template = value
            self.searchParameterChange.emit()

    @property
    def show_id(self):
        """
        If true, the id of the points should be shown as well.

        :returntype: bool
        """
        return self._show_id

    @show_id.setter
    def show_id(self, value):
        value = bool(value)
        if value != self._show_id:
            self._show_id = value
            self.pointParameterChange.emit()

    def _find_font(self):
        font = QFont()
        wanted_size = self._point_size
        font.setStyleStrategy(QFont.StyleStrategy(QFont.OpenGLCompatible | QFont.PreferAntialias))
        fm = QFontMetricsF(font)
        width = fm.width("888")
        ratio = 1.8*wanted_size/max(width, fm.ascent())
        self._font = font
        self._font_zoom = ratio

    @property
    def font(self):
        """
        Font used to display the points id in the points.

        :returntype: `QFont`
        """
        return self._font

    @property
    def font_zoom(self):
        """
        Zoom used to display the points id in the points.

        :returntype: float
        """
        return self._font_zoom

#}
#{ Search parameters

    @property
    def estimate(self):
        """
        True if the copy functions estimate the position using normalized cross-correlation
        """
        return self._estimate

    @estimate.setter
    def estimate(self, value):
        self._estimate = bool(value)

    @property
    def template_size(self):
        """
        Size of the template to search for (i.e. number of pixel around the position to extract)
        """
        return self._template_size

    @template_size.setter
    def template_size(self, size):
        size = int(size)
        if size > 0 and size != self._template_size:
            self._template_size = size
            self.template_rect = QRectF(-size, -size, 2*size, 2*size)
            if 1.5*size > self._search_size:
                self.search_size = int(ceil(1.5*size+0.1))
            self.searchParameterChange.emit()

    @property
    def search_size(self):
        """
        Area around the point to look for the template
        """
        return self._search_size

    @search_size.setter
    def search_size(self, size):
        size = int(size)
        if size > self._template_size and size != self._search_size:
            self._search_size = size
            self.search_rect = QRectF(-size, -size, 2*size, 2*size)
            if size < 1.5*self._template_size:
                self.template_size = int(floor(2./3.*size-0.1))
            self.searchParameterChange.emit()

    @property
    def search_color(self):
        """
        Color used to draw the searched area
        """
        return self._search_color

    @search_color.setter
    def search_color(self, color):
        col = QColor(color)
        if col.isValid() and col != self._search_color:
            self._search_color = col
            self.searchParameterChange.emit()

    @property
    def template_color(self):
        """
        Color used to draw the template around a point
        """
        return self._template_color

    @template_color.setter
    def template_color(self, color):
        col = QColor(color)
        if col.isValid() and col != self._template_color:
            self._template_color = col
            self.searchParameterChange.emit()

    @property
    def filter_size_ratio(self):
        """Ratio of the template size used to create the filter"""
        return self._filter_size_ratio

    @filter_size_ratio.setter
    def filter_size_ratio(self, value):
        if value != self._filter_size_ratio:
            self._filter_size_ratio = value
            self.searchParameterChange.emit()

    @property
    def filter_size_ratio_percent(self):
        """Ratio of the template size used to create the filter in percent

        This property is garantied to return an integer"""
        return int(self._filter_size_ratio*100)

    @filter_size_ratio_percent.setter
    def filter_size_ratio_percent(self, value):
        self.filter_size_ratio = int(value)/100.0

    @property
    def filter_size(self):
        """
        Size of the filter to use for the images
        """
        return int(self._template_size * self._filter_size_ratio)

    @property
    def estimate_position(self):
        """
        Boolean telling if the position of the points have to be estimated or just copied.

        :returntype: bool
        """
        return self._estimate_position

    @estimate_position.setter
    def estimate_position(self, value):
        self._estimate_position = value

#}
#{ Main configuration

    @property
    def last_dir(self):
        """Last directory used in file dialog box"""
        return self._last_dir

    @last_dir.setter
    def last_dir(self, value):
        self._last_dir = value

    @property
    def cache_size(self):
        """Size of the image cache in MB"""
        return self._cache_size

    @cache_size.setter
    def cache_size(self, value):
        self._cache_size = value
        from . import image_cache
        image_cache.cache.max_size = value

    @property
    def recent_projects(self):
        """List of the most recent projects loaded"""
        return self._recent_projects

    @recent_projects.setter
    def _set_recent_projects(self, value):
        if self._recent_projects != value:
            self._recent_projects = value
            self.recentProjectsChange.emit()

    def add_recent_project(self, project):
        recent_projects = self._recent_projects
        if project in recent_projects:
            recent_projects.remove(project)
        recent_projects.insert(0,  project)
        while len(recent_projects) > self._max_number_of_projects:
            recent_projects.pop()
        self.recentProjectsChange.emit()

#}
#{ User interaction parameters

    @property
    def is_point_editable(self):
        """
        True if the points can be edited.

        :returntype: bool
        """
        return self._point_editable

    @is_point_editable.setter
    def is_point_editable(self, value):
        value = bool(value)
        if value != self._point_editable:
            self._point_editable = value
            self.pointParameterChange.emit()

    @property
    def is_point_selectable(self):
        """
        True if the cells can be selected.

        :returntype: bool
        """
        return self._point_selectable

    @is_point_selectable.setter
    def is_point_selectable(self, value):
        value = bool(value)
        if value != self._point_selectable:
            self._point_selectable = value
            self.pointParameterChange.emit()

    @property
    def is_cell_editable(self):
        """
        True if the cells can be edited.

        :returntype: bool
        """
        return self._cell_editable

    @is_cell_editable.setter
    def is_cell_editable(self, value):
        value = bool(value)
        if value != self._cell_editable:
            self._cell_editable = value
            self.cellParameterChange.emit()

#}

#{ Growth representation parameters

    @property
    def walls_coloring(self):
        """
        Mode used to color walls.

        :returntype: `str`
        """
        return self._walls_coloring

    @walls_coloring.setter
    def walls_coloring(self, value):
        value = unicode(value)
        if value != self._walls_coloring:
            self._walls_coloring = value
            self.plottingParameterChange.emit()

    @property
    def walls_symetric_coloring(self):
        """
        True if the coloring scheme must be symetric around 0.

        :returntype: bool
        """
        return self._walls_symetric_coloring

    @walls_symetric_coloring.setter
    def walls_symetric_coloring(self, value):
        value = bool(value)
        if value != self._walls_symetric_coloring:
            self._walls_symetric_coloring = value
            self.plottingParameterChange.emit()

    @property
    def walls_cap_values(self):
        '''
        True if the values used to color the walls must be caped.

        :returntype: bool
        '''
        return self._walls_cap_values

    @walls_cap_values.setter
    def walls_cap_values(self, value):
        if self._walls_cap_values != value:
            self._walls_cap_values = value
            self.plottingParameterChange.emit()

    @property
    def walls_values_min(self):
        '''
        Minimum cap.

        :returntype: float
        '''
        return self._walls_values_min

    @walls_values_min.setter
    def walls_values_min(self, value):
        value = float(value)
        if self._walls_values_min != value:
            self._walls_values_min = value
            self.plottingParameterChange.emit()

    @property
    def walls_values_max(self):
        '''
        Maximum cap.

        :returntype: float
        '''
        return self._walls_values_max

    @walls_values_max.setter
    def walls_values_max(self, value):
        value = float(value)
        if self._walls_values_max != value:
            self._walls_values_max = value
            self.plottingParameterChange.emit()

    @property
    def cells_coloring(self):
        """
        Mode used to color cells

        :returntype: `str`
        """
        return self._cells_coloring

    @cells_coloring.setter
    def cells_coloring(self, value):
        value = unicode(value)
        if value != self._cells_coloring:
            self._cells_coloring = value
            self.plottingParameterChange.emit()

    @property
    def cells_symetric_coloring(self):
        """
        True if the coloring scheme must be symetric around 0.

        :returntype: bool
        """
        return self._cells_symetric_coloring

    @cells_symetric_coloring.setter
    def cells_symetric_coloring(self, value):
        value = bool(value)
        if value != self._cells_symetric_coloring:
            self._cells_symetric_coloring = value
            self.plottingParameterChange.emit()

    @property
    def cells_cap_values(self):
        '''
        True if the values used to color the cells must be caped.

        :returntype: bool
        '''
        return self._cells_cap_values

    @cells_cap_values.setter
    def cells_cap_values(self, value):
        value = bool(value)
        if self._cells_cap_values != value:
            self._cells_cap_values = value
            self.plottingParameterChange.emit()

    @property
    def cells_values_min(self):
        '''
        Minimum cap.

        :returntype: float
        '''
        return self._cells_values_min

    @cells_values_min.setter
    def cells_values_min(self, value):
        value = float(value)
        if self._cells_values_min != value:
            self._cells_values_min = value
            self.plottingParameterChange.emit()

    @property
    def cells_values_max(self):
        '''
        Maximum cap.

        :returntype: float
        '''
        return self._cells_values_max

    @cells_values_max.setter
    def cells_values_max(self, value):
        value = float(value)
        if self._cells_values_max != value:
            self._cells_values_max = value
            self.plottingParameterChange.emit()

    @property
    def ellipsis_scaling(self):
        '''
        Scaling applied to the kmin and kmaj to plot the ellipsis

        :returntype: float
        '''
        return self._ellipsis_scaling

    @ellipsis_scaling.setter
    def ellipsis_scaling(self, value):
        value = float(value)
        if self._ellipsis_scaling != value:
            self._ellipsis_scaling = value
            self.plottingParameterChange.emit()

    @property
    def ellipsis_color(self):
        '''
        Color used to draw the ellipsis.

        :returntype: `QColor`
        '''
        return self._ellipsis_color

    @ellipsis_color.setter
    def ellipsis_color(self, value):
        value = QColor(value)
        if self._ellipsis_color != value:
            self._ellipsis_color = value
            self.plottingParameterChange.emit()

    @property
    def ellipsis_thickness(self):
        '''
        Thickness used to draw the growth tensor ellipsis

        :returntype: int
        '''
        return self._ellipsis_thickness

    @ellipsis_thickness.setter
    def ellipsis_thickness(self, value):
        value = int(value)
        if self._ellipsis_thickness != value:
            self._ellipsis_thickness = value
            self.plottingParameterChange.emit()

    @property
    def ellipsis_min_anisotropy(self):
        '''
        Minimum anisotropy required to draw axes of an ellipsis.

        :returntype: float
        '''
        return self._ellipsis_min_anisotropy

    @ellipsis_min_anisotropy.setter
    def ellipsis_min_anisotropy(self, value):
        value = float(value)
        if self._ellipsis_min_anisotropy != value:
            self._ellipsis_min_anisotropy = value
            self.plottingParameterChange.emit()

    @property
    def ellipsis_positive_color(self):
        '''
        Color used to draw growth tensor ellipsis axis if the value is positive.

        :returntype: `QColor`
        '''
        return self._ellipsis_positive_color

    @ellipsis_positive_color.setter
    def ellipsis_positive_color(self, value):
        value = QColor(value)
        if self._ellipsis_positive_color != value:
            self._ellipsis_positive_color = value
            self.plottingParameterChange.emit()

    @property
    def ellipsis_negative_color(self):
        '''
        Color used to draw growth tensor ellipsis axis if the value is negative.

        :returntype: `QColor`
        '''
        return self._ellipsis_negative_color

    @ellipsis_negative_color.setter
    def ellipsis_negative_color(self, value):
        value = QColor(value)
        if self._ellipsis_negative_color != value:
            self._ellipsis_negative_color = value
            self.plottingParameterChange.emit()

    @property
    def ellipsis_plot(self):
        '''True if the ellipsis is to be plotted.

        :returntype: bool'''
        return self._ellipsis_plot

    @ellipsis_plot.setter
    def ellipsis_plot(self, value):
        value = bool(value)
        if self._ellipsis_plot != value:
            self._ellipsis_plot = value
            self.plottingParameterChange.emit()

    @property
    def ellipsis_scale_axis(self):
        '''True if the ellipsis is to be plotted.

        :returntype: bool'''
        return self._ellipsis_scale_axis

    @ellipsis_scale_axis.setter
    def ellipsis_scale_axis(self, value):
        value = bool(value)
        if self._ellipsis_scale_axis != value:
            self._ellipsis_scale_axis = value
            self.plottingParameterChange.emit()

    @property
    def growth_cell_color(self):
        '''
        Color used to draw cells without function.

        :returntype: `QColor`
        '''
        return self._growth_cell_color

    @growth_cell_color.setter
    def growth_cell_color(self, value):
        value = QColor(value)
        if self._growth_cell_color != value:
            self._growth_cell_color = value
            self.plottingParameterChange.emit()

    @property
    def growth_wall_color(self):
        '''
        Color used to draw walls without function.

        :returntype: `QColor`
        '''
        return self._growth_wall_color

    @growth_wall_color.setter
    def growth_wall_color(self, value):
        value = QColor(value)
        if self._growth_wall_color != value:
            self._growth_wall_color = value
            self.plottingParameterChange.emit()

    @property
    def growth_cell_function(self):
        '''
        Transfer function used to draw cells. This is actually the pickled form of the transfer function.

        :returntype: `str`
        '''
        return self._growth_cell_function

    @growth_cell_function.setter
    def growth_cell_function(self, value):
        if self._growth_cell_function != value:
            self._growth_cell_function = value
            self.plottingParameterChange.emit()

    @property
    def growth_wall_function(self):
        '''
        Transfer function used to draw walls. This is actually the pickled form of the transfer function.

        :returntype: `str`
        '''
        return self._growth_wall_function

    @growth_wall_function.setter
    def growth_wall_function(self, value):
        if self._growth_wall_function != value:
            self._growth_wall_function = value
            self.plottingParameterChange.emit()

#}


def createParameters():
    if QCoreApplication.startingUp():
        raise ImportError("The parameters module has been loaded before the creation of a Qt application")
    global instance
    if instance is None:
        instance = Parameters()
    else:
        instance.load()


def saveParameters():
    global instance
    instance.save()

# To be instantiated after Qt has been initialized
instance = None
#createParameters()
