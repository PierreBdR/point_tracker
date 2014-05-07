"""
:newfield signal: Signal, Signals
"""
__author__ = "Pierre Barbier de Reuille <pbdr@uea.ac.uk>"
__docformat__ = "restructuredtext"

import sys
from PyQt4.QtGui import (QDialog, QImageWriter, QMessageBox, QFileDialog,
        QColor, QDialogButtonBox, QProgressDialog, QPainter, QImage, QPolygonF, QWidget,
        QPushButton, QPen, QTransform, QBrush)
from PyQt4.QtCore import (pyqtSignature, SIGNAL, QObject, QThread, QEvent, QMutex, QCoreApplication, QRectF,
        QPoint, Qt, QRect, QSettings, QVariant, QString)
from ui_plottingdlg import Ui_PlottingDlg
from path import path
from growth_computation_methods import Result
import parameters
import image_cache
from plotting_methods import (createWallColoring, createCellColoring, createPointColoring,
                               EllipsisDraw, saveWallParamClasses, saveCellParamClasses,
                               savePointParamClasses)
import plotting_methods
from sys_utils import setColor, getColor, changeColor
from plot_preview import PlotPreview
from debug import print_debug
from tracking_data import TrackingData, RetryTrackingDataException
from itertools import izip
from plottingoptionsdlg import PlottingOptionsDlg

def createColoring(ctype):
    if ctype == 'cell':
        createColoring = createCellColoring
        parent_attr = 'cellsColoring'
        thread_attr = 'cellColoring'
        method_attr= 'cell_coloring_method'
        config_widget = 'CellConfigWidget'
    elif ctype == 'wall':
        createColoring = createWallColoring
        parent_attr = 'wallsColoring'
        thread_attr = 'wallColoring'
        method_attr= 'wall_coloring_method'
        config_widget = 'WallConfigWidget'
    elif ctype == 'point':
        createColoring = createPointColoring
        parent_attr = 'pointsColoring'
        thread_attr = 'pointColoring'
        method_attr= 'point_coloring_method'
        config_widget = 'PointConfigWidget'
    else:
        raise ValueError('Unknown coloring: %s' % (ctype,))
    def createColoringMethod(self, coloring):
        print_debug("Create new %s coloring of type: %s" % (ctype, coloring))
        parent = getattr(self.ui, parent_attr)
        method = createColoring(coloring, self.thread.result)
        QObject.connect(method, SIGNAL("changed"), self.update_preview)
        self.setupColoringWidget(parent, method, config_widget)
        setattr(self, method_attr, method)
        if self.thread is not None:
            print_debug("Testing thread validity")
            setattr(self.thread, thread_attr, method)
            self.preview_button.setEnabled(self.thread.render_valid())
            self.apply_button.setEnabled(self.thread.valid())
            self.update_preview()
    return createColoringMethod
    
class ResizableMessageBox(QMessageBox):
    def __init__(self, *args):
        QMessageBox.__init__(self, *args)

    def event(self, event):
        ret = QMessageBox.event(self, event)
        self.setMaximumSize(100000,100000)
        return ret

class PlottingDlg(QDialog):
    def __init__(self, data, *args):
        QDialog.__init__(self, *args)
        self._auto_update = False
        self._file_format = None
        self.thread = None
        self.data = data
        self.ui = Ui_PlottingDlg()
        self.ui.setupUi(self)
        self.options_button = self.ui.buttonBox.addButton("Options", QDialogButtonBox.ActionRole)
        imgs = [ str(i) for i in QImageWriter.supportedImageFormats() ]
        self.ui.fileFormat.addItems(imgs)
        self.img_formats = imgs
        self.result = None
        self.has_cells = False
        self.has_walls = False
        self.has_points = False
        self.point_coloring_method = None
        self.wall_coloring_method = None
        self.cell_coloring_method = None
        ellipsis_draw = EllipsisDraw(None)
        self.ellipsis_draw = ellipsis_draw
        self.preview_button = QPushButton("Preview", self)
        self.preview_button.setCheckable(True)
        self.preview_button.setEnabled(False)
        self.apply_button = self.ui.buttonBox.button(QDialogButtonBox.Apply)
        self.apply_button.setEnabled(False)
        self.reload_button = QPushButton("Reload classes", self)
        self.reload_button.setEnabled(True)
        self.preview = None
        self.ui.buttonBox.addButton(self.reload_button, QDialogButtonBox.ActionRole)
        self.ui.buttonBox.addButton(self.preview_button, QDialogButtonBox.ActionRole)
        QObject.connect(self.preview_button, SIGNAL("toggled(bool)"), self.show_preview)
        QObject.connect(self.reload_button, SIGNAL("clicked()"), self.reload_classes)
        QObject.connect(self.options_button, SIGNAL("clicked()"), self.open_options)
        self.load_preferences()
        self.updateInterface()
        self.reload_classes()

    def load_preferences(self):
        settings = QSettings()
        settings.beginGroup("Plotting")
        os, ok = settings.value("OverSampling").toInt()
        if not ok:
            os = 1
        self._over_sampling = os
        self.ui.overSampling.setValue(os)
        wt, ok = settings.value("WallThickness").toDouble()
        if not ok:
            wt = 0
        self._wall_thickness = wt
        self.ui.wallThickness.setValue(wt)
        ps, ok = settings.value("PointSize").toDouble()
        if not ok:
            ps = 0
        self._point_size = ps
        self.ui.pointSize.setValue(ps)
        plt, ok = settings.value("PointLineThickness").toDouble()
        if not ok:
            plt = 0
        self._point_line_thickness = plt
        plc = QColor(settings.value("PointLineColor"))
        if not plc.isValid():
            plc = QColor(0,0,0)
        self._point_line_color = plc
        bg = QColor(settings.value("BackgroundColor"))
        if not bg.isValid():
            bg = QColor(0,0,0)
        self._bg_color = bg
        #setColor(self.ui.bgColor, bg)
        ff = str(settings.value("FileFormat").toString())
        uiff = self.ui.fileFormat
        img_formats = self.img_formats
        if ff in img_formats:
            uiff.setCurrentIndex(self.img_formats.index(ff))
        else:
            prefered_exts = ["png", "tif", "jpg"]
            for ff in prefered_exts:
                if ff in img_formats:
                    uiff.setCurrentIndex(self.img_formats.index(ff))
                    break
            else:
                uiff.setCurrentIndex(0)
                ff = self.img_formats[0]
        self._file_format = ff
        settings.endGroup()

    def save_preferences(self):
        settings = QSettings()
        settings.beginGroup("Plotting")
        settings.setValue("OverSampling", QVariant(self.over_sampling))
        settings.setValue("WallThickness", QVariant(self.wall_thickness))
        settings.setValue("PointSize", QVariant(self.point_size))
        settings.setValue("PointLineThickness", QVariant(self.point_line_thickness))
        settings.setValue("PointLineColor", QVariant(self.point_line_color))
        settings.setValue("BackgroundColor", QVariant(self.bg_color))
        settings.setValue("FileFormat", QVariant(self.file_format))
        settings.endGroup()

    def _get_file_format(self):
        '''Default file format

        :returntype: str'''
        return self._file_format

    def _set_file_format(self, value):
        value = str(value)
        if self._file_format != value:
            self._file_format = value
            if self.thread is not None:
                self.thread.fileFormat = value
                self.apply_button.setEnabled(self.thread.valid())

    file_format = property(_get_file_format, _set_file_format)

    def _get_over_sampling(self):
        '''
        Over-sampling rate for the rendering

        :returntype: int
        '''
        return self._over_sampling

    def _set_over_sampling(self, value):
        value = int(value)
        if self._over_sampling != value:
            self._over_sampling = value
            if self.thread is not None:
                self.thread.overSampling = value
                self.update_preview()

    over_sampling = property(_get_over_sampling, _set_over_sampling)

    def _get_wall_thickness(self):
        '''
        Thickness used to draw the cell walls

        :returntype: float
        '''
        return self._wall_thickness

    def _set_wall_thickness(self, value):
        value = float(value)
        if self._wall_thickness != value:
            self._wall_thickness = value
            if self.thread is not None:
                self.thread.wallThickness = value
                self.update_preview()

    wall_thickness = property(_get_wall_thickness, _set_wall_thickness)

    def _get_point_size(self):
        """
        Size of the point drawing (i.e. radius of the disk)
        
        :returntype: float
        """
        return self._point_size
    
    def _set_point_size(self, value):
        value = float(value)
        if self._point_size != value:
            self._point_size = value
            if self.thread is not None:
                self.thread.pointSize = value
                self.update_preview()    
   
    point_size = property(_get_point_size, _set_point_size)

    def _get_point_line_thickness(self):
        """
        Thickness of the contour of the points
        
        :returntype: float
        """
        return self._point_line_thickness
    
    def _set_point_line_thickness(self, value):
        value = float(value)
        if self._point_line_thickness != value:
            self._point_line_thickness = value
            if self.thread is not None:
                self.thread.pointLineThickness = value
                self.update_preview()    
   
    point_line_thickness = property(_get_point_line_thickness, _set_point_line_thickness)

    def _get_point_line_color(self):
        """
        Color of the contour of the points
        
        :returntype: QColor
        """
        return self._point_line_color
    
    def _set_point_line_color(self, value):
        value = QColor(value)
        if self._point_line_color != value:
            self._point_line_color = value
            if self.thread is not None:
                self.thread.pointLineColor = value
                self.update_preview()    
   
    point_line_color = property(_get_point_line_color, _set_point_line_color)

    def _get_bg_color(self):
        '''Color of the image background

        :returntype: `QColor`'''
        return self._bg_color

    def _set_bg_color(self, value):
        value = QColor(value)
        if self._bg_color != value:
            self._bg_color = value
            if self.thread is not None:
                self.thread.bgColor = value
                self.update_preview()

    bg_color = property(_get_bg_color, _set_bg_color)

    @pyqtSignature("bool")
    def show_preview(self, value):
        if value:
            self.preview.show()
        else:
            self.preview.hide()

    @pyqtSignature("")
    def open_options(self):
        dlg = PlottingOptionsDlg(self)
        dlg.exec_()

    @pyqtSignature("")
    def reload_classes(self):
        errors = plotting_methods.resetClasses()
        if errors:
            dlg = ResizableMessageBox(self)
            dlg.setWindowTitle("Error while compiling tissue color modules")
            dlg.setSizeGripEnabled(True)
            short_s = "\n".join(f for f,err in errors)
            s = "\n\n".join("Error while loading '%s':\n%s" % (f,err) for f,err in errors)
            dlg.setText("Error while loading files:\n%s" % short_s)
            dlg.setInformativeText(s)
            dlg.exec_()
        self.ui.cellColoring.clear()
        if self.has_cells:
            cell_cls_names = plotting_methods.cellColoringClasses(self.thread.result_type)
            cell_cls_names.sort()
            for cls in cell_cls_names:
                self.ui.cellColoring.addItem(cls.coloring_name)
        self.ui.wallColoring.clear()
        if self.has_walls:
            wall_cls_names = plotting_methods.wallColoringClasses(self.thread.result_type)
            wall_cls_names.sort()
            for cls in wall_cls_names:
                self.ui.wallColoring.addItem(cls.coloring_name)
        if self.has_points:
            point_cls_names = plotting_methods.pointColoringClasses(self.thread.result_type)
            point_cls_names.sort()
            for cls in point_cls_names:
                self.ui.pointColoring.addItem(cls.coloring_name)

    @pyqtSignature("const QString&")
    def on_growthFile_textChanged(self, txt):
        p = path(txt)
        self.loadFile(p)

    def _get_auto_update(self):
        '''If true, the preview is updated automatically everytime a new element is changed'''
        return self._auto_update

    def _set_auto_update(self, value):
        if self._auto_update != value:
            self._auto_update = value

    auto_update = property(_get_auto_update, _set_auto_update)

    def enableControls(self, value = True):
        self.preview_button.setEnabled(value)
        if not value:
            self.preview_button.setChecked(False)
        self.ui.crop_left.setEnabled(value)
        self.ui.crop_top.setEnabled(value)
        self.ui.crop_width.setEnabled(value)
        self.ui.crop_height.setEnabled(value)
        self.ui.resetCrop.setEnabled(value)

    def loadFile(self, filename):
        if not filename.exists():
            self.has_cells = False
            self.has_walls = False
            self.has_points = False
            self.enableControls(False)
            self.apply_button.setEnabled(False)
            self.thread = None
            self.updateInterface()
            return
        self.thread = PlottingThread(self)
        self.progress = self.createProgress("Loading file.")
        self.setEnabled(False)
        print_debug("Plotting window disabled. Starting loading thread.")
        self.thread.load(filename)

    def load_results(self):
        result = self.thread.result
        has_cells = self.thread.has_cells
        has_walls = self.thread.has_walls
        has_points = self.thread.has_points
        self.has_walls = has_walls
        self.has_cells = has_cells
        self.has_points = has_points
        self.ellipsis_draw.result = result
        thread = self.thread
        thread.filePrefix = path(self.ui.filePrefix.text())
        thread.fileFormat = str(self.ui.fileFormat.currentText())
        thread.wallColoring = self.wall_coloring_method
        thread.cellColoring = self.cell_coloring_method
        thread.wallThickness = self.wall_thickness
        thread.pointLineColor = self.point_line_color
        thread.pointLineThickness = self.point_line_thickness
        thread.pointSize = self.point_size
        thread.ellipsisDraw = self.ellipsis_draw
        thread.overSampling = self.over_sampling
        thread.bgColor = self.bg_color
        self.thread = thread
        self.preview = PlotPreview(thread, self)
        self.preview.image_list = self.thread.images
        self.enableControls(self.thread.render_valid())
        self.apply_button.setEnabled(self.thread.valid())

    def hideEvent(self, event):
        saveCellParamClasses()
        saveWallParamClasses()
        savePointParamClasses()
        if self.preview is not None and self.preview.isVisible():
            self.preview.close()

    @pyqtSignature("const QString&")
    def on_filePrefix_textChanged(self, value):
        if self.thread is not None:
            self.thread.filePrefix = str(value)
            self.apply_button.setEnabled(self.thread.valid())

    @pyqtSignature("const QString&")
    def on_fileFormat_currentIndexChanged(self, value):
        self.file_format = value

    @pyqtSignature("int")
    def on_overSampling_valueChanged(self, value):
        self.over_sampling = value

    @pyqtSignature("double")
    def on_wallThickness_valueChanged(self, value):
        self.wall_thickness = value

    @pyqtSignature("double")
    def on_pointSize_valueChanged(self, value):
        self.point_size = value

    def setupColoringWidget(self, parent, method, name):
        child = self.findChild(QWidget, name)
        print_debug('Found children named "%s": %s' % (name, id(child)))
        if child is None:
            raise RuntimeError('There is no widget called "%s' % name)
        parent = child.parent()
        child_index = parent.layout().indexOf(child)
        config_widget = method.config_widget(parent)
        if config_widget is None:
            config_widget = QWidget(parent)
        config_widget.setAttribute(Qt.WA_DeleteOnClose, True)
        config_widget.setObjectName(name)
        parent.layout().insertWidget(child_index, config_widget)
        child.setParent(None)
        child.close()
        return config_widget

    createCellColoring = createColoring('cell')
    createWallColoring = createColoring('wall')
    createPointColoring = createColoring('point')

#    def createCellColoring(self, coloring):
#        print_debug("Create new cell coloring of type: %s" % coloring)
#        parent = self.ui.cellsColoring
#        method = createCellColoring(coloring, self.thread.result)
#        QObject.connect(method, SIGNAL("changed"), self.update_preview)
#        self.setupColoringWidget(parent, method, "CellConfigWidget")
#        self.cell_coloring_method = method
#        if self.thread is not None:
#            print_debug("Testing thread validity")
#            self.thread.cellColoring = method
#            self.preview_button.setEnabled(self.thread.render_valid())
#            self.apply_button.setEnabled(self.thread.valid())
#            self.update_preview()
#
#    def createWallColoring(self, coloring):
#        print_debug("Create new wall coloring of type: %s" % coloring)
#        parent = self.ui.wallsColoring
#        method = createWallColoring(coloring, self.thread.result)
#        QObject.connect(method, SIGNAL("changed"), self.update_preview)
#        self.setupColoringWidget(parent, method, "WallConfigWidget")
#        self.wall_coloring_method = method
#        if self.thread is not None:
#            print_debug("Testing thread validity")
#            self.thread.wallColoring = method
#            self.preview_button.setEnabled(self.thread.render_valid())
#            self.apply_button.setEnabled(self.thread.valid())
#            self.update_preview()

    def update_preview(self):
        if self.preview is not None and self.auto_update:
            self.preview.request_render_image()

    def updateInterface(self):
        if self.thread is None:
            self.enableControls(False)
            self.ui.cellsColoring.setEnabled(False)
            self.cell_coloring_method = None
            self.ui.wallsColoring.setEnabled(False)
            self.wall_coloring_method = None
            self.ui.pointsColoring.setEnabled(False)
            self.point_coloring_method = None
            return
        self.enableControls(True)
        self.ui.cellColoring.clear()
        if self.has_cells:
            for cls in plotting_methods.cellColoringClasses(self.thread.result_type):
                self.ui.cellColoring.addItem(cls.coloring_name)
            self.createCellColoring(self.ui.cellColoring.currentText())
            self.ui.cellsColoring.setEnabled(True)
            if self.thread.result_type != "Growth":
                self.ui.plotEllipsis.setEnabled(False)
                self.ui.plotEllipsis.setChecked(False)
                self.ellipsis_draw.plot = False
            else:
                self.ui.plotEllipsis.setEnabled(True)
        else:
            self.ui.cellsColoring.setEnabled(False)
            self.ui.plotEllipsis.setEnabled(False)
            self.cell_coloring_method = None
        self.ui.wallColoring.clear()
        if self.has_walls:
            for cls in plotting_methods.wallColoringClasses(self.thread.result_type):
                self.ui.wallColoring.addItem(cls.coloring_name)
            self.createWallColoring(self.ui.wallColoring.currentText())
            self.ui.wallsColoring.setEnabled(True)
        else:
            self.ui.wallsColoring.setEnabled(False)
            self.wall_coloring_method = None
        if self.has_points:
            for cls in plotting_methods.pointColoringClasses(self.thread.result_type):
                self.ui.pointColoring.addItem(cls.coloring_name)
            self.createPointColoring(self.ui.pointColoring.currentText())
            self.ui.pointsColoring.setEnabled(True)
        if self.thread.render_valid():
            ellipsis_draw = self.ellipsis_draw
            self.ui.plotEllipsis.setChecked(ellipsis_draw.plot)
#            self.ui.scalingFactor.setValue(ellipsis_draw.scaling)
#            setColor(self.ui.ellipsisColor, ellipsis_draw.color)
#            self.ui.ellipsisThickness.setValue(ellipsis_draw.thickness)
#            setColor(self.ui.ellipsisPositiveColor, ellipsis_draw.positive_color)
#            setColor(self.ui.ellipsisNegativeColor, ellipsis_draw.negative_color)
            img_size = self.thread.img_size
            self.ui.crop_left.setMaximum(img_size.width()-1)
            self.ui.crop_top.setMaximum(img_size.height()-1)
            self.ui.crop_width.setMaximum(img_size.width())
            self.ui.crop_height.setMaximum(img_size.height())
            self.ui.crop_left.setValue(self.thread.crop.left())
            self.ui.crop_top.setValue(self.thread.crop.top())
            self.ui.crop_width.setValue(self.thread.crop.width())
            self.ui.crop_height.setValue(self.thread.crop.height())
            if self.thread.result_type == "Growth":
                self.ui.endImagePlot.setEnabled(True)
                self.ui.endImagePlot.setChecked(self.thread.end_image_plot)
            else:
                self.ui.endImagePlot.setEnabled(False)

    @pyqtSignature("")
    def on_resetCrop_clicked(self):
        self.thread.reset_crop()
        self.ui.crop_left.setValue(self.thread.crop.left())
        self.ui.crop_top.setValue(self.thread.crop.top())
        self.ui.crop_width.setValue(self.thread.crop.width())
        self.ui.crop_height.setValue(self.thread.crop.height())

    @pyqtSignature("int")
    def on_crop_left_valueChanged(self, value):
        self.thread.crop_left = value
        self.ui.crop_width.setMaximum(self.thread.img_size.width() - value)
        self.update_preview()

    @pyqtSignature("int")
    def on_crop_top_valueChanged(self, value):
        self.thread.crop_top = value
        self.ui.crop_height.setMaximum(self.thread.img_size.height() - value)
        self.update_preview()

    @pyqtSignature("int")
    def on_crop_width_valueChanged(self, value):
        self.thread.crop_width = value
        self.update_preview()

    @pyqtSignature("int")
    def on_crop_height_valueChanged(self, value):
        self.thread.crop_height = value
        self.update_preview()

    @pyqtSignature("")
    def on_selectGrowthFile_clicked(self):
        params = parameters.instance
        if self.data is not None:
            startdir = self.data.project_dir
        else:
            startdir = params.last_dir
        filename = QFileDialog.getOpenFileName(self, "Choose a file containing growth data", startdir, "All Data Files (*.xls *.csv);;XLS Files (*.xls);;CSV Files (*.csv);;All Files (*)")
        if not filename.isEmpty():
            fn = path(filename).dirname()
            params.last_dir = fn
            if '.' not in filename:
                filename += ".xls"
            self.ui.growthFile.setText(filename)

    @pyqtSignature("")
    def on_selectFilePrefix_clicked(self):
        params = parameters.instance
        startdir = params.last_dir
        filter = QString()
        filename = QFileDialog.getSaveFileName(self, "Choose a file prefix for saving images", startdir, "Image Files (*.%s)" % self.ui.fileFormat.currentText(), filter, QFileDialog.DontConfirmOverwrite | QFileDialog.DontResolveSymlinks)
        if not filename.isEmpty():
            fn = path(filename).dirname()
            params.last_dir = fn
            if '.' in filename:
                ext_pos = filename.indexOf('.')
                ext = filename[ext_pos:]
                if ext in filter:
                    filename = filename[:ext_pos]
            self.ui.filePrefix.setText(filename)

    @pyqtSignature("const QString&")
    def on_wallColoring_activated(self, value):
        value = str(value)
        self.createWallColoring(value)

    @pyqtSignature("const QString&")
    def on_cellColoring_activated(self, value):
        value = str(value)
        self.createCellColoring(value)

    @pyqtSignature("const QString&")
    def on_pointColoring_activated(self, value):
        value = str(value)
        self.createPointColoring(value)

    @pyqtSignature("bool")
    def on_plotEllipsis_toggled(self, value):
        self.ellipsis_draw.plot = value

    @pyqtSignature("bool")
    def on_endImagePlot_toggled(self, value):
        self.thread.end_image_plot = value

#    @pyqtSignature("")
#    def on_selectBgColor_clicked(self):
#        if changeColor(self.ui.bgColor):
#            self.bg_color = getColor(self.ui.bgColor)

    def accept(self):
        """
        This dialog box is NEVER accepted
        """
        return

    def reject(self):
        self.save_preferences()
        return QDialog.reject(self)

    def createProgress(self, title):
        progress = QProgressDialog(title, "Abort", 0, 10)
        progress.setAttribute(Qt.WA_DeleteOnClose)
        progress.setAutoClose(True)
        progress.setMinimumDuration(500)
        progress.setValue(0)
        return progress

    @pyqtSignature("QAbstractButton*")
    def on_buttonBox_clicked(self, btn):
        if self.ui.buttonBox.buttonRole(btn) == QDialogButtonBox.ApplyRole:
            thread = self.thread
            self.progress = self.createProgress("Rendering plot")
            self.progress.open(self.abortProgress)
            thread.render_all()

    def abortProgress(self):
        if self.thread is not None:
            self.thread.stop()

    def event(self, event):
        if event.type() == NextImageEvent.event_type:
            self.progress.setValue(self.progress.value()+1)
            return True
        elif event.type() == AbortPlottingEvent.event_type:
            if parameters.instance.use_thread:
                self.progress.cancel()
                self.thread.wait()
                del self.progress
            if self.thread.loading:
                QMessageBox.critical(self, "Invalid file", "File %s could not be loaded.\nError: '%s'" % (self.thread.result, event.reason.message))
                self.has_cells = False
                self.has_walls = False
                self.has_points = False
                self.enableControls(False)
                self.apply_button.setEnabled(False)
                self.setEnabled(True)
                self.updateInterface()
            else:
                QMessageBox.critical(self, "Error during plot rendering", "The plotting was aborted for the following reason: %s" % event.reason)
            return True
        elif event.type() == FinishPlottingEvent.event_type:
            self.progress.reset()
            self.thread.wait()
            self.progress.close()
            del self.progress
            QMessageBox.information(self, "Plot rendering", "The rendering is finished.")
            return True
        elif event.type() == FinishLoadingEvent.event_type:
            if self.thread.retryObject is not None:
                msg = self.thread.retryObject.question
                answer = QMessageBox.question(self, "Error loading data file", msg, buttons=QMessageBox.Yes | QMessageBox.No)
                if answer == QMessageBox.No:
                    self.ui.growthFile.setText("")
                    self.progress.reset()
                    del self.progress
                    self.has_cells = False
                    self.has_walls = False
                    self.has_points = False
                    self.enableControls(False)
                    self.apply_button.setEnabled(False)
                    self.setEnabled(True)
                    self.updateInterface()
                else:
                    self.thread.reload()
            else:
                self.progress.reset()
                self.thread.wait()
                del self.progress
                self.setEnabled(True)
                self.load_results()
                self.updateInterface()
                print_debug("Loading thread finished. Plotting window enabled again.")
            return True
        elif event.type() == ImageReadyPlottingEvent.event_type:
            self.thread.wait()
            if self.preview is not None:
                self.preview.pic_w = self.thread.pic_w
                self.preview.pic_c = self.thread.pic_c
                self.preview.pix = self.thread.pix
        elif event.type() == UpdateNbImageEvent.event_type:
            nb = event.nb
            print_debug("Number of events to process: %d" % nb)
            self.progress.setMaximum(nb)
        return QDialog.event(self, event)

class NextImageEvent(QEvent):
    def __init__(self):
        QEvent.__init__(self, self.event_type)
    event_type = QEvent.Type(QEvent.registerEventType())

class AbortPlottingEvent(QEvent):
    def __init__(self, reason):
        QEvent.__init__(self, self.event_type)
        self.reason = reason

    event_type = QEvent.Type(QEvent.registerEventType())

class FinishPlottingEvent(QEvent):
    def __init__(self):
        QEvent.__init__(self, self.event_type)
    event_type = QEvent.Type(QEvent.registerEventType())

class FinishLoadingEvent(QEvent):
    def __init__(self):
        QEvent.__init__(self, self.event_type)
    event_type = QEvent.Type(QEvent.registerEventType())

class ImageReadyPlottingEvent(QEvent):
    def __init__(self):
        QEvent.__init__(self, self.event_type)
    event_type = QEvent.Type(QEvent.registerEventType())

class UpdateNbImageEvent(QEvent):
    def __init__(self, nb):
        QEvent.__init__(self, self.event_type)
        self.nb = nb
    event_type = QEvent.Type(QEvent.registerEventType())

class PlottingThread(QThread):
    def __init__(self, parent):
        QThread.__init__(self)
        self.result = None
        self.parent = parent
        self._stopped = False
        self.mutex = QMutex()
        self.filePrefix = None
        self.fileFormat = None
        self.wallColoring = None
        self.cellColoring = None
        self.pointColoring = None
        self.extraDrawing = []
        self.pointSize = None
        self.pointLineColor = None
        self.pointLineThickness = None
        self.ellipsisDraw = None
        self.overSampling = None
        self.wallThickness = None
        self.bgColor = None
        self.loading = False
        self._crop = QRect(0,0,1,1)
        self._pix = None
        self._end_image_plot = False
        self._loading_arguments = {}
        self.retryObject = None

    def end_step(self):
        return len(self.result)+1

    def stop(self, value = True):
        self.mutex.lock()
        self._stopped = value
        self.mutex.unlock()

    def stopped(self):
        self.mutex.lock()
        val = self._stopped
        self.mutex.unlock()
        return val

    def nextImage(self):
        QCoreApplication.postEvent(self.parent, NextImageEvent())

    def abort(self, reason, **others):
        e = AbortPlottingEvent(reason)
        if others:
            e.others = others
        QCoreApplication.postEvent(self.parent, e)

    def finished(self):
        if self.loading:
            QCoreApplication.postEvent(self.parent, FinishLoadingEvent())
            self.loading = False
        else:
            QCoreApplication.postEvent(self.parent, FinishPlottingEvent())

    def image_ready(self):
        QCoreApplication.postEvent(self.parent, ImageReadyPlottingEvent())

    def update_nb_images(self, nb):
        QCoreApplication.postEvent(self.parent, UpdateNbImageEvent(nb))

    def _get_crop_left(self):
        return self._crop.left()

    def _set_crop_left(self, value):
        self._crop.moveLeft(int(value))

    crop_left = property(_get_crop_left, _set_crop_left)

    def _get_crop_top(self):
        return self._crop.top()

    def _set_crop_top(self, value):
        self._crop.moveTop(int(value))

    crop_top = property(_get_crop_top, _set_crop_top)

    def _get_crop_width(self):
        return self._crop.width()

    def _set_crop_width(self, value):
        self._crop.setWidth(int(value))

    crop_width = property(_get_crop_width, _set_crop_width)

    def _get_crop_height(self):
        return self._crop.height()

    def _set_crop_height(self, value):
        self._crop.setHeight(int(value))

    crop_height = property(_get_crop_height, _set_crop_height)

    def reset_crop(self):
        self._crop = QRect(QPoint(0,0), self.img_size)

    def _get_crop(self):
        return QRect(self._crop)

    crop = property(_get_crop)
    
    def _get_end_image_plot(self):
        '''
        If true, plot the growth data on the end image rather than the start image of the growth calculation.
        '''
        return self._end_image_plot
        
    def _set_end_image_plot(self, value):
        self._end_image_plot = bool(value)
        
    end_image_plot = property(_get_end_image_plot, _set_end_image_plot)

    def _get_pix(self):
        '''Thread-safe image storage.'''
        self.mutex.lock()
        pix = self._pix
        self.mutex.unlock()
        return pix

    def _set_pix(self, value):
        self.mutex.lock()
        self._pix = value
        self.mutex.unlock()

    pix = property(_get_pix, _set_pix)

    def render_valid(self):
        if self.result is None:
            print_debug("result is None")
            return False
        if self.parent is None:
            print_debug("parent is None")
            return False
        if self.ellipsisDraw is None:
            print_debug("ellipsisDraw is None")
            return False
        if self.cellColoring is None:
            print_debug("cellColoring is None")
            return False
        if self.wallColoring is None:
            print_debug("wallColoring is None")
            return False
        if self.pointColoring is None:
            print_debug("pointColoring is None")
            return False
        if self.pointSize is None:
            print_debug("pointSize is None")
            return False
        if self.pointLineThickness is None:
            print_debug("pointSize is None")
            return False
        if self.pointLineColor is None:
            print_debug("pointSize is None")
            return False
        if self.wallThickness is None:
            print_debug("wallThickness is None")
            return False
        if self.overSampling is None:
            print_debug("overSampling is None")
            return False
        if self.bgColor is None:
            print_debug("bgColor is None")
            return False
        return True

    def valid(self):
        if self.filePrefix is None:
            print_debug("filePrefix is None")
            return False
        if not self.filePrefix:
            print_debug("filePrefix is Empty")
            return False
        if self.fileFormat is None:
            print_debug("fileFormat is None")
            return False
        return self.render_valid()

    def drawImage(self, imageid):
        cache = image_cache.cache
        cellColoring = self.cellColoring
        wallColoring = self.wallColoring
        pointColoring = self.pointColoring
        ellipsisDraw = self.ellipsisDraw
        overSampling = self.overSampling
        extraDrawing = self.extraDrawing
        bgColor = self.bgColor.rgb()
        result = self.result
        if self.result_type == "Data":
            data = result
            img_name = result.images_name[imageid]
        else:
            data = result.data
            img_name = result.images[imageid]
        #scale = data.images_scale[img_name]
        min_scale = data.minScale()
        img = cache.image(data.image_path(img_name))
        img_data = data[img_name]
        size = self._crop.size()
        pix = QImage(size*overSampling, QImage.Format_ARGB32)
        pix.fill(bgColor)
        painter = QPainter()
        if not painter.begin(pix):
            self.abort("Cannot create painter on QImage")
            return None, None, None
        painter.setRenderHints(QPainter.SmoothPixmapTransform, True)
        painter.setRenderHints(QPainter.Antialiasing, True)
        painter.translate(-self._crop.topLeft())
        if overSampling > 1:
            painter.scale(overSampling, overSampling)
        painter.save()
        painter.translate(self.translate)
        print_debug("Translating: %gx%g" % (self.translate.x(), self.translate.y()) )
        painter.scale(1/min_scale, 1/min_scale)
        painter.save()
        matrix = img_data.matrix()
        painter.setWorldTransform(matrix, True)
        painter.drawImage(QPoint(0,0), img)
        painter.restore()
        #pt_matrix = QTransform()
        #pt_matrix.scale(1/min_scale, 1/min_scale)
        #painter.setTransform(pt_matrix, True)
        cellColoring.startImage(painter, imageid)
        wallColoring.startImage(painter, imageid)
        for ed in extraDrawing:
            ed.startImage(painter, imageid)
        if self.result_type == "Growth":
            cells = result.cells[imageid]
            walls = result.walls[imageid]
        else:
            cells = img_data.cells
            walls = set()
            for cid in img_data.cells:
                pts = [ pt for pt in data.cells[cid] if pt in img_data ]
                if len(pts) > 1:
                    for i in xrange(len(pts)):
                        walls.add(data.wallId(pts[i-1], pts[i]))
        # Now, draw the cells and the ellipsis
        for cid in cells:
            painter.setPen(Qt.NoPen)
            color = cellColoring(imageid, cid)
            painter.setBrush(color)
            pts = data.cellAtTime(cid, img_data.index)
            if pts:
                pts.append(pts[0])
                ppts = []
                for p1,p2 in izip(pts[:-1], pts[1:]):
                    ppts.append(img_data[p1])
                    ppts.extend(img_data.walls[p1,p2])
                ppts.append(ppts[0])
                poly = QPolygonF(ppts)
                painter.drawPolygon(poly)
        # And draw the walls
        wallThickness = self.wallThickness*min_scale
        for wid in walls:
            color = wallColoring(imageid, wid)
            if color.alpha() > 0:
                pen = QPen(color)
                pen.setWidthF(wallThickness)
                painter.setPen(pen)
                pts = [img_data[wid[0]]] + img_data.walls[wid[0], wid[1]] + [img_data[wid[1]]]
                #painter.drawLine(img_data[wid[0]], img_data[wid[1]])
                painter.drawPolyline(*pts)
        # Then, draw the points
        pointSize = self.pointSize*min_scale
        pointLineColor = self.pointLineColor
        pointLineThickness = self.pointLineThickness*min_scale
        print_debug("pointSize = %g" % pointSize)
        for pid in img_data:
            color = pointColoring(imageid, pid)
            if color.alpha() > 0:
                pen = QPen(pointLineColor)
                pen.setWidthF(pointLineThickness)
                brush = QBrush(color)
                painter.setPen(pen)
                painter.setBrush(brush)
                pos = img_data[pid]
                rect = QRectF(pos.x()-pointSize, pos.y()-pointSize, 2*pointSize, 2*pointSize)
                painter.drawEllipse(rect)
        if ellipsisDraw.plot:
            for cid in cells:
                pts = data.cellAtTime(cid, img_data.index)
                if pts:
                    pts.append(pts[0])
                    ppts = []
                    for p1,p2 in izip(pts[:-1], pts[1:]):
                        ppts.append(img_data[p1])
                        ppts.extend(img_data.walls[p1,p2])
                    ppts.append(ppts[0])
                    #poly = QPolygonF(ppts)
                    #painter.drawPolygon(poly)
                    ellipsisDraw(painter, imageid, cid, ppts, min_scale)
        # At last, draw the extra data
        for ed in extraDrawing:
            ed(painter, imageid)
        tr = painter.worldTransform()
        painter.restore()
        pic_w = wallColoring.finalizeImage(painter, imageid, tr, self.crop)
        pic_c = cellColoring.finalizeImage(painter, imageid, tr, self.crop)
        for ed in extraDrawing:
            ed.finalizeImage(painter, imageid, tr, self.crop)
        painter.end()
        return pix, pic_w, pic_c

    def start(self):
        if self.isRunning():
            assert not self.rendering_all, "Cannot run twice the rendering of all images with the same object."
            return
        if parameters.instance.use_thread:
            print_debug("Starting rendering thread.")
            QThread.start(self)
            return False
        else:
            self.run()
            return True

    def render_all(self):
        self.rendering_all = True
        return self.start()

    def render_single(self, img_id, retry=False):
        if retry:
            while self.isRunning():
                self.wait(10000)
        elif self.isRunning():
            return
        self.rendering_all = False
        self.current_image = img_id
        return self.start()

    def load(self, filename):
        self.loading = True
        self.result = filename
        return self.start()

    def run(self):
        if self.loading:
            self.run_loader()
        elif self.rendering_all:
            self.run_full()
        else:
            self.run_single()

    def run_single(self):
        img = self.current_image
        self.cellColoring.init()
        self.wallColoring.init()
        self.pointColoring.init()
        print_debug("Rendering image %d" % img)
        self.pix, self.pic_w, self.pic_c = self.drawImage(img)
        if self.pic_w is not None:
            print_debug("Has wall image")
        if self.pic_c is not None:
            print_debug("Has cell image")
        if self.pix is not None:
            print_debug("Pix correctly rendered")
        print_debug("Rendered image %d  = %s" % (img, self.pix))
        self.image_ready()

    def reload(self):
        if self.retryObject is None:
            return
        self._loading_arguments.update(self.retryObject.method_args)
        self.load(self.retryObject.filename)

    def run_loader(self):
        filename = self.result
        try:
            self.retryObject = None
# First, prepare the data by getting the images and computing how big they 
# should be
            f = file(filename)
            first_line = f.readline()
            f.close()
            if first_line.startswith("TRKR_VERSION"):
                result = Result(None)
                result.load(self.result, **self._loading_arguments)
                result_type = "Growth"
            else:
                result = TrackingData()
                result.load(self.result, **self._loading_arguments)
                result_type = "Data"
            self.result = result
            self.result_type = result_type
            if result_type == "Data":
                data = result
                images = data.images_name
                if data.cells:
                    self.has_cells = True
                    self.has_walls = True
                else:
                    self.has_cells = False
                    self.has_walls = False
                self.has_points = bool(data.cell_points)
            else:
                data = result.data
                images = result.images
                self.has_cells = False
                self.has_walls = False
                self.has_points = False
            self.images = images
            cache = image_cache.cache
            self.update_nb_images(len(result))
            bbox = QRectF()
            ms = data.minScale()
            for i in xrange(len(result)):
                img_name = images[i]
                img_data = data[img_name]
                img = cache.image(data.image_path(img_name))
                matrix = QTransform()
                matrix = img_data.matrix()
                sc = QTransform()
                sc.scale(1.0/ms, 1.0/ms)
                matrix *= sc
                r = QRectF(img.rect())
                rbox = matrix.map(QPolygonF(r)).boundingRect()
                bbox |= rbox
                print_debug("Image '%s':\n\tSize = %gx%g\n\tTransformed = %gx%g %+g %+g\n\tGlobal bbox = %gx%g %+g %+g\n" %
                             (img_name, r.width(), r.height(), rbox.width(), rbox.height(), rbox.left(), rbox.top(),
                              bbox.width(), bbox.height(), bbox.left(), bbox.top()))
                print_debug("Matrix:\n%g\t%g\t%g\n%g\t%g\t%g\n" %
                            (matrix.m11(), matrix.m12(), matrix.dx(), matrix.m21(), matrix.m22(), matrix.dy()))
                if result_type == "Growth":
                    if result.cells[i]:
                        self.has_cells = True
                    if result.walls[i]:
                        self.has_walls = True
                    self.has_points = bool(result.data.cell_points)
                self.nextImage()
            translate = bbox.topLeft()
            translate *= -1
            self.translate = translate
            size = bbox.size().toSize()
            self.img_size = size
            self._crop = QRect(QPoint(0,0), size)
            self.finished()
            self._loading_arguments = {} # All done, we don't need that anymore
        except RetryTrackingDataException, ex:
            ex.filename = filename
            self.retryObject = ex
            self.finished()
            return
        except Exception, ex:
            _, _, exceptionTraceback = sys.exc_info()
            self.abort(ex, traceback=exceptionTraceback)
            raise

    def run_full(self):
        if not self.valid():
            self.abort("Object was not correctly initialized")
            return
        self.stop(False)
        painter = None
        try:
            result = self.result
            self.update_nb_images(len(result))
#            if self.result_type == "Data":
#                data = result
#                images = result.images_name
#            else:
#                data = result.data
#                images = result.images
#            cache = image_cache.cache
            cellColoring = self.cellColoring
            wallColoring = self.wallColoring
            pointColoring = self.pointColoring
            file_format = self.fileFormat
            file_pattern = "%s%%0%dd.%s" % (self.filePrefix, len(str(len(result))), file_format)
            wall_file_pattern = "%s%%0%dd_wall.%s" % (self.filePrefix, len(str(len(result))), file_format)
            cell_file_pattern = "%s%%0%dd_cell.%s" % (self.filePrefix, len(str(len(result))), file_format)
            cellColoring.init()
            wallColoring.init()
            pointColoring.init()
            self.nextImage()
            for i in xrange(len(result)):
                if self.stopped():
                    self.abort("User interruption")
                    return
                pix, pic_w, pic_c = self.drawImage(i)
                pix.save(file_pattern % (i+1), file_format)
                if pic_w is not None:
                    self.saveExtra(pic_w, wall_file_pattern % (i+1), file_format)
                if pic_c is not None:
                    self.saveExtra(pic_c, cell_file_pattern % (i+1), file_format)
                self.nextImage()
            self.finished()
        except Exception, ex:
            if painter is not None:
                painter.end()
            _, _, exceptionTraceback = sys.exc_info()
            self.abort(ex, traceback=exceptionTraceback)
            raise

    def saveExtra(self, picture, file_name, file_format):
        rect = picture.boundingRect()
        pix = QImage(rect.size(), QImage.Format_ARGB32)
        pix.fill(QColor(0, 0, 0, 0).rgba())
        paint = QPainter()
        paint.begin(pix)
        paint.drawPicture(rect.topLeft()*-1, picture)
        paint.end()
        pix.save(file_name, file_format)
