from __future__ import print_function, division, absolute_import

__author__ = "Pierre Barbier de Reuille <pierre@barbierdereuille.net>"
__docformat__ = "restructuredtext"

from PyQt4.QtCore import (QRectF, QSignalMapper, QObject, SIGNAL, SLOT, pyqtSignature)
from PyQt4.QtGui import (QGraphicsView, QAction, QDialog,
        QMainWindow, QMessageBox, QUndoStack, QKeySequence, QWidget, QActionGroup, QInputDialog,
        QMenu, QLabel, QFileDialog, QImageReader, QImageWriter, QPolygonF)
from PyQt4.QtOpenGL import QGLWidget, QGLFormat, QGL
from .path import path
from .project import Project
from .tracking_data import TrackingDataException, RetryTrackingDataException
from .tracking_scene import TrackingScene, LinkedTrackingScene
from .tracking_undo import (ChangePointsId, ChangeTiming, CleanCells, ResetAlignment, AlignImages, SplitPointsId,
                           MergeCells, SplitCells, ChangeScales)
import sys
if sys.platform == "darwin":
    from .ui_tracking_window_macos import Ui_TrackingWindow
else:
    from .ui_tracking_window import Ui_TrackingWindow
from . import algo
from . import parameters
from .alignmentdlg import AlignmentDlg
from .timeeditdlg import TimeEditDlg
from .editresdlg import EditResDlg
from .growth_computation import GrowthComputationDlg
from .plottingdlg import PlottingDlg
from .sys_utils import createForm, showException, retryException
from .debug import log_debug
from .__init__ import __version__, __revision__

class TrackingWindow(QMainWindow):
    """
    Main window of the application.

    This class is responsible for the global data structures too.

    :IVariables:
        undo_stack : `QUndoStack`
            Undo stack. All actions that can be undone should be pushed on the stack.
        _project : `project.Project`
            Project object managing the loaded data
        _data : `tracking_data.TrackingData`
            Data object keeping track of points and cells
        toolGroup : `QActionGroup`
            Group of actions to be enabled only when actions can be taken on images
        previousSelAct : `QActionGroup`
            Actions enabled when points are selected in the previous pane
        currentSelAct : `QActionGroup`
            Actions enabled when points are selected in the current pane
        projectAct : `QActionGroup`
            Actions to enable once a project is loaded
        _previousScene : `tracking_scene.TrackingScene`
            Object managing the previous pane
        _currentScene : `tracking_scene.LinkedTrackingScene`
            Object managing the current pane
    """
    def __init__(self, *args, **kwords):
        QMainWindow.__init__(self, *args)
        self.undo_stack = QUndoStack(self)
        self.ui = Ui_TrackingWindow()
        self.ui.setupUi(self)
        self._project = None
        self._data = None
        self.toolGroup = QActionGroup(self)
        self.toolGroup.addAction(self.ui.actionAdd_point)
        self.toolGroup.addAction(self.ui.action_Move_point)
        self.toolGroup.addAction(self.ui.actionAdd_cell)
        self.toolGroup.addAction(self.ui.actionRemove_cell)
        self.toolGroup.addAction(self.ui.action_Pan)
        self.toolGroup.addAction(self.ui.actionZoom_out)
        self.toolGroup.addAction(self.ui.actionZoom_in)
        self.previousSelAct = QActionGroup(self)
        self.previousSelAct.addAction(self.ui.actionCopy_selection_from_Previous)
        self.previousSelAct.addAction(self.ui.actionDelete_Previous)
        self.previousSelAct.setEnabled(False)
        self.currentSelAct = QActionGroup(self)
        self.currentSelAct.addAction(self.ui.actionCopy_selection_from_Current)
        self.currentSelAct.addAction(self.ui.actionDelete_Current)
        self.currentSelAct.setEnabled(False)
        self.projectAct = QActionGroup(self)
        self.projectAct.addAction(self.ui.action_Next_image)
        self.projectAct.addAction(self.ui.action_Previous_image)
        self.projectAct.addAction(self.ui.actionAdd_point)
        self.projectAct.addAction(self.ui.action_Move_point)
        self.projectAct.addAction(self.ui.action_Pan)
        self.projectAct.addAction(self.ui.actionAdd_cell)
        self.projectAct.addAction(self.ui.actionRemove_cell)
        self.projectAct.addAction(self.ui.action_Change_data_file)
        self.projectAct.addAction(self.ui.actionNew_data_file)
        self.projectAct.addAction(self.ui.actionZoom_out)
        self.projectAct.addAction(self.ui.actionZoom_in)
        self.projectAct.addAction(self.ui.actionSave_as)
        self.projectAct.addAction(self.ui.action_Fit)
        self.projectAct.addAction(self.ui.actionZoom_100)
        self.projectAct.addAction(self.ui.actionMerge_points)
        self.projectAct.addAction(self.ui.actionCopy_from_previous)
        self.projectAct.addAction(self.ui.actionCopy_from_current)
        self.projectAct.addAction(self.ui.actionReset_alignment)
        self.projectAct.addAction(self.ui.actionAlign_images)
        self.projectAct.addAction(self.ui.actionSelectPreviousAll)
        self.projectAct.addAction(self.ui.actionSelectPreviousNew)
        self.projectAct.addAction(self.ui.actionSelectPreviousNone)
        self.projectAct.addAction(self.ui.actionSelectPreviousNon_associated)
        self.projectAct.addAction(self.ui.actionSelectPreviousAssociated)
        self.projectAct.addAction(self.ui.actionSelectPreviousInvert)
        self.projectAct.addAction(self.ui.actionSelectCurrentAll)
        self.projectAct.addAction(self.ui.actionSelectCurrentNew)
        self.projectAct.addAction(self.ui.actionSelectCurrentNone)
        self.projectAct.addAction(self.ui.actionSelectCurrentNon_associated)
        self.projectAct.addAction(self.ui.actionSelectCurrentAssociated)
        self.projectAct.addAction(self.ui.actionSelectCurrentInvert)
        self.projectAct.addAction(self.ui.actionEdit_timing)
        self.projectAct.addAction(self.ui.actionEdit_scales)
        self.projectAct.addAction(self.ui.actionCompute_growth)
        self.projectAct.addAction(self.ui.actionClean_cells)
        self.projectAct.addAction(self.ui.actionGotoCell)

        self.projectAct.setEnabled(False)

        current_sel_actions = [self.ui.actionSelectCurrentAll,
                               self.ui.actionSelectCurrentNew,
                               self.ui.actionSelectCurrentNone,
                               self.ui.actionSelectCurrentInvert,
                               '-',
                               self.ui.actionSelectCurrentNon_associated,
                               self.ui.actionSelectCurrentAssociated,
                               self.ui.actionCopy_selection_from_Previous
                               ]

        previous_sel_actions = [self.ui.actionSelectPreviousAll,
                                self.ui.actionSelectPreviousNew,
                                self.ui.actionSelectPreviousNone,
                                self.ui.actionSelectPreviousInvert,
                                '-',
                                self.ui.actionSelectPreviousNon_associated,
                                self.ui.actionSelectPreviousAssociated,
                                self.ui.actionCopy_selection_from_Current
                                ]

        self._previousScene = TrackingScene(self.undo_stack, self.ui.actionDelete_Previous, previous_sel_actions, self)
        self._currentScene = LinkedTrackingScene(self._previousScene, self.undo_stack, self.ui.actionDelete_Current, current_sel_actions, self)
        QObject.connect(self._previousScene, SIGNAL("hasSelection(bool)"), self.previousSelAct, SLOT("setEnabled(bool)"))
        QObject.connect(self._currentScene, SIGNAL("hasSelection(bool)"), self.currentSelAct, SLOT("setEnabled(bool)"))
        QObject.connect(self._previousScene, SIGNAL("realSceneSizeChanged"), self.sceneSizeChanged)
        QObject.connect(self._currentScene, SIGNAL("realSceneSizeChanged"), self.sceneSizeChanged)
        QObject.connect(self._previousScene, SIGNAL("ZoomIn"), self.zoomIn)
        QObject.connect(self._currentScene, SIGNAL("ZoomIn"), self.zoomIn)
        QObject.connect(self._previousScene, SIGNAL("ZoomOut"), self.zoomOut)
        QObject.connect(self._currentScene, SIGNAL("ZoomOut"), self.zoomOut)
        self.ui.previousData.setScene(self._previousScene)
        self.ui.currentData.setScene(self._currentScene)
        self.ui.previousData.setDragMode(QGraphicsView.ScrollHandDrag)
        self.ui.currentData.setDragMode(QGraphicsView.ScrollHandDrag)
        #self.ui.previousData.setCacheMode(QGraphicsView.CacheBackground)
        #self.ui.currentData.setCacheMode(QGraphicsView.CacheBackground)

# Redefine shortcuts to standard key sequences
        self.ui.action_Save.setShortcut(QKeySequence.Save)
        self.ui.actionSave_as.setShortcut(QKeySequence.SaveAs)
        self.ui.action_Open_project.setShortcut(QKeySequence.Open)
        self.ui.action_Undo.setShortcut(QKeySequence.Undo)
        self.ui.action_Redo.setShortcut(QKeySequence.Redo)
        self.ui.action_Next_image.setShortcut(QKeySequence.Forward)
        self.ui.action_Previous_image.setShortcut(QKeySequence.Back)

# Connecting undo stack signals
        QObject.connect(self.ui.action_Undo, SIGNAL("triggered()"), self.undo)
        QObject.connect(self.ui.action_Redo, SIGNAL("triggered()"), self.redo)
        QObject.connect(self.undo_stack, SIGNAL("canRedoChanged(bool)"), self.ui.action_Redo, SLOT("setEnabled(bool)"))
        QObject.connect(self.undo_stack, SIGNAL("canUndoChanged(bool)"), self.ui.action_Undo, SLOT("setEnabled(bool)"))
        QObject.connect(self.undo_stack, SIGNAL("redoTextChanged(const QString&)"), self.changeRedoText)
        QObject.connect(self.undo_stack, SIGNAL("undoTextChanged(const QString&)"), self.changeUndoText)
        QObject.connect(self.undo_stack, SIGNAL("cleanChanged(bool)"), self.ui.action_Save, SLOT("setDisabled(bool)"))

#        link_icon = QIcon()
#        pix = QPixmap(":/icons/link.png")
#        link_icon.addPixmap(pix, QIcon.Normal, QIcon.On)
#        pix = QPixmap(":/icons/link_broken.png")
#        link_icon.addPixmap(pix, QIcon.Normal, QIcon.Off)
#        self.link_icon = link_icon
#        #self.ui.linkViews.setIconSize(QSize(64,32))
#        self.ui.linkViews.setIcon(link_icon)

        self._recent_projects_menu = QMenu(self)
        self.ui.actionRecent_projects.setMenu(self._recent_projects_menu)

        self._recent_projects_act = []
        self._projects_mapper = QSignalMapper(self)
        QObject.connect(self._projects_mapper, SIGNAL("mapped(int)"), self.loadRecentProject)

        self.param_dlg = None

# Setting up the status bar
        bar = self.statusBar()
# Adding current directory
        cur_dir = QLabel("")
        bar.addPermanentWidget(cur_dir)
        self._current_dir_label = cur_dir
# Adding up zoom
        zoom = QLabel("")
        bar.addPermanentWidget(zoom)
        self._zoom_label = zoom
        self.changeZoom(1)

        self.loadConfig()

        QObject.connect(parameters.instance, SIGNAL("renderingChanged"), self.changeRendering)
        self.changeRendering()

    def changeRendering(self):
        if parameters.instance.use_OpenGL:
            self.ui.previousData.setViewport(QGLWidget(QGLFormat(QGL.SampleBuffers)))
            self.ui.currentData.setViewport(QGLWidget(QGLFormat(QGL.SampleBuffers)))
        else:
            self.ui.previousData.setViewport(QWidget())
            self.ui.currentData.setViewport(QWidget())

    def undo(self):
        self.undo_stack.undo()

    def redo(self):
        self.undo_stack.redo()

    def changeRedoText(self, text):
        self.ui.action_Redo.setText(text)
        self.ui.action_Redo.setToolTip(text)
        self.ui.action_Redo.setStatusTip(text)

    def changeUndoText(self, text):
        self.ui.action_Undo.setText(text)
        self.ui.action_Undo.setToolTip(text)
        self.ui.action_Undo.setStatusTip(text)

    def closeEvent(self, event):
        self.saveConfig()
        if not self.ensure_save_data("Exiting whith unsaved data", "The last modifications you made were not saved. Are you sure you want to exit?"):
            event.ignore()
            return
        QMainWindow.closeEvent(self, event)
        #sys.exit(0)

    def loadConfig(self):
        params = parameters.instance
        self.ui.action_Show_vector.setChecked(params.show_vectors)
        self.ui.linkViews.setChecked(params.link_views)
        self.ui.action_Show_template.setChecked(parameters.instance.show_template)
        self.ui.actionShow_id.setChecked(parameters.instance.show_id)
        self.ui.action_Estimate_position.setChecked(parameters.instance.estimate)
        self.updateRecentFiles()
        QObject.connect(params, SIGNAL("recentProjectsChange"), self.updateRecentFiles)

    def updateRecentFiles(self):
        for a in self._recent_projects_act:
            self._projects_mapper.removeMappings(a)
        del self._recent_projects_act[:]
        menu = self._recent_projects_menu
        menu.clear()
        recent_projects = parameters.instance.recent_projects
        for i,p in enumerate(recent_projects):
            act = QAction(self)
            act.setText("&%d %s"%(i+1,p))
            self._recent_projects_act.append(act)
            QObject.connect(act, SIGNAL("triggered()"), self._projects_mapper, SLOT("map()"))
            self._projects_mapper.setMapping(act, i)
            menu.addAction(act)

    def saveConfig(self):
        parameters.instance.save()

    def check_for_data(self):
        if self._project is None:
            QMessageBox.critical(self, "No project loaded", "You have to load a project before performing this operation")
            return False
        return True

    def loadRecentProject(self, i):
        if self.ensure_save_data("Leaving unsaved data", "The last modifications you made were not saved. Are you sure you want to change project?"):
            self.loadProject(parameters.instance.recent_projects[i])

    @pyqtSignature("")
    def on_action_Open_project_triggered(self):
        if self.ensure_save_data("Leaving unsaved data", "The last modifications you made were not saved. Are you sure you want to change project?"):
            dir_ = QFileDialog.getExistingDirectory(self, "Select a project directory", parameters.instance._last_dir)
            if dir_:
                self.loadProject(dir_)

    def loadProject(self, dir_):
        dir_ = path(dir_)
        project = Project(dir_)
        if project.valid:
            self._project = project
        else:
            create = QMessageBox.question(self, "Invalid project directory", "This directory does not contain a valid project. Turn into a directory?", QMessageBox.No, QMessageBox.Yes)
            if create == QMessageBox.No:
                return
            project.create()
            self._project = project
        self._project.use()
        parameters.instance.add_recent_project(dir_)
        parameters.instance._last_dir = dir_
        if self._data is not None:
            _data = self._data
            QObject.disconnect(_data, SIGNAL("saved"), self.undo_stack, SLOT("setClean()"))
        try:
            #self._project.load()
            self.load_data()
            _data = self._project.data
            QObject.connect(_data, SIGNAL("saved"), self.undo_stack, SLOT("setClean()"))
            QObject.connect(self._project, SIGNAL("changedDataFile"), self.dataFileChanged)
            self._data = _data
            self._previousScene.changeDataManager(self._data)
            self._currentScene.changeDataManager(self._data)
            self.initFromData()
            self.projectAct.setEnabled(True)
        except TrackingDataException as ex:
            showException(self, "Error while loaded data", ex)

    def dataFileChanged(self, new_file):
        if new_file is None:
            self._current_dir_label.setText("")
        else:
            self._current_dir_label.setText(new_file)

    def initFromData(self):
        """
        Initialize the interface using the current data
        """
        self.ui.previousState.clear()
        self.ui.currentState.clear()
        for name in self._data.images_name:
            self.ui.previousState.addItem(name)
            self.ui.currentState.addItem(name)
        self.ui.previousState.setCurrentIndex(0)
        self.ui.currentState.setCurrentIndex(1)
        self._previousScene.changeImage(self._data.image_path(self._data.images_name[0]))
        self._currentScene.changeImage(self._data.image_path(self._data.images_name[1]))
        self.dataFileChanged(self._project.data_file)

    @pyqtSignature("int")
    def on_previousState_currentIndexChanged(self, index):
        #print "Previous image loaded: %s" % self._data.images[index]
        self.changeScene(self._previousScene, index)
        self._currentScene.changeImage(None)

    @pyqtSignature("int")
    def on_currentState_currentIndexChanged(self, index):
        #print "Current image loaded: %s" % self._data.images[index]
        self.changeScene(self._currentScene,index)

    def changeScene(self, scene, index):
        """
        Set the scene to use the image number index.
        """
        scene.changeImage(self._data.image_path(self._data.images_name[index]))

    @pyqtSignature("")
    def on_action_Save_triggered(self):
        self.save_data()

    @pyqtSignature("")
    def on_actionSave_as_triggered(self):
        fn = QFileDialog.getSaveFileName(self, "Select a data file to save in", self._project.data_dir,
                                               "CSV Files (*.csv);;All files (*.*)")
        if fn:
            self.save_data(path(fn))

    def save_data(self, data_file = None):
        if self._data is None:
            raise TrackingDataException("Trying to save data when none have been loaded")
        try:
            self._project.save(data_file)
            return True
        except TrackingDataException as ex:
            showException(self, "Error while saving data", ex)
            return False

    def load_data(self, **opts):
        if self._project is None:
            raise TrackingDataException("Trying to load data when no project have been loaded")
        try:
            if self._project.load(**opts):
                log_debug("Data file was corrected. Need saving.")
                self.ui.action_Save.setEnabled(True)
            else:
                log_debug("Data file is clean.")
                self.ui.action_Save.setEnabled(False)
            return True
        except TrackingDataException as ex:
            showException(self, "Error while loading data", ex)
            return False
        except RetryTrackingDataException as ex:
            if retryException(self, "Problem while loading data", ex):
                new_opts = dict(opts)
                new_opts.update(ex.method_args)
                return self.load_data(**new_opts)
            return False

    def ensure_save_data(self, title, reason):
        if self._data is not None and not self.undo_stack.isClean():
            button = QMessageBox.warning(self, title, reason, QMessageBox.Yes | QMessageBox.Save | QMessageBox.Cancel)
            if button == QMessageBox.Save:
                return self.save_data()
            elif button == QMessageBox.Cancel:
                return False
            self.undo_stack.clear()
        return True

    @pyqtSignature("")
    def on_action_Change_data_file_triggered(self):
        if self.ensure_save_data("Leaving unsaved data", "The last modifications you made were not saved. Are you sure you want to change the current data file?"):
            fn = QFileDialog.getOpenFileName(self, "Select a data file to load", self._project.data_dir,
                                                   "CSV Files (*.csv);;All files (*.*)")
            if fn:
                self._project.data_file = str(fn)
                if self.load_data():
                    self._previousScene.resetNewPoints()
                    self._currentScene.resetNewPoints()

    @pyqtSignature("bool")
    def on_action_Show_vector_toggled(self, value):
        parameters.instance.show_vector = value
        self._currentScene.showVector(value)

    @pyqtSignature("bool")
    def on_action_Show_template_toggled(self, value):
        parameters.instance.show_template = value

    @pyqtSignature("bool")
    def on_actionShow_id_toggled(self, value):
        parameters.instance.show_id = value

    @pyqtSignature("")
    def on_action_Next_image_triggered(self):
        cur = self.ui.currentState.currentIndex()
        pre = self.ui.previousState.currentIndex()
        l = len(self._data.images_name)
        if cur < l-1 and pre < l-1:
            self.ui.previousState.setCurrentIndex(pre+1)
            self.ui.currentState.setCurrentIndex(cur+1)

    @pyqtSignature("")
    def on_action_Previous_image_triggered(self):
        cur = self.ui.currentState.currentIndex()
        pre = self.ui.previousState.currentIndex()
        if cur > 0 and pre > 0:
            self.ui.previousState.setCurrentIndex(pre-1)
            self.ui.currentState.setCurrentIndex(cur-1)

    @pyqtSignature("")
    def on_copyToPrevious_clicked(self):
        self._currentScene.copyFromLinked(self._previousScene)

    @pyqtSignature("")
    def on_copyToCurrent_clicked(self):
        self._previousScene.copyToLinked(self._currentScene)

    @pyqtSignature("bool")
    def on_action_Estimate_position_toggled(self, value):
        parameters.instance.estimate = value

#  @pyqtSignature("")
#  def on_action_Undo_triggered(self):
#    print "Undo"

#  @pyqtSignature("")
#  def on_action_Redo_triggered(self):
#    print "Redo"

    @pyqtSignature("bool")
    def on_action_Parameters_toggled(self, value):
        if value:
            from .parametersdlg import ParametersDlg
            self._previousScene.showTemplates()
            self._currentScene.showTemplates()
            #tracking_scene.saveParameters()
            parameters.instance.save()
            max_size = max(self._currentScene.width(), self._currentScene.height(),
                    self._previousScene.width(), self._previousScene.height(), 400)
            self.param_dlg = ParametersDlg(max_size, self)
            self.param_dlg.setModal(False)
            self.ui.action_Pan.setChecked(True)
            self.ui.actionAdd_point.setEnabled(False)
            self.ui.action_Move_point.setEnabled(False)
            self.ui.actionAdd_cell.setEnabled(False)
            self.ui.actionRemove_cell.setEnabled(False)
            self.ui.action_Undo.setEnabled(False)
            self.ui.action_Redo.setEnabled(False)
            self.ui.action_Open_project.setEnabled(False)
            self.ui.actionRecent_projects.setEnabled(False)
            self.ui.action_Change_data_file.setEnabled(False)
            self.ui.copyToCurrent.setEnabled(False)
            self.ui.copyToPrevious.setEnabled(False)
            QObject.connect(self.param_dlg, SIGNAL("finished(int)"), self.closeParam)
            self.param_dlg.show()
        elif self.param_dlg:
            self.param_dlg.accept()

    def closeParam(self, value):
        if value == QDialog.Rejected:
            parameters.instance.load()
        self.ui.actionAdd_point.setEnabled(True)
        self.ui.action_Move_point.setEnabled(True)
        self.ui.actionAdd_cell.setEnabled(True)
        self.ui.actionRemove_cell.setEnabled(True)
        self.ui.action_Undo.setEnabled(True)
        self.ui.action_Redo.setEnabled(True)
        self.ui.action_Open_project.setEnabled(True)
        self.ui.actionRecent_projects.setEnabled(True)
        self.ui.action_Change_data_file.setEnabled(True)
        self.ui.copyToCurrent.setEnabled(True)
        self.ui.copyToPrevious.setEnabled(True)
        self._previousScene.showTemplates(False)
        self._currentScene.showTemplates(False)
        self._previousScene.update()
        self._currentScene.update()
        self.param_dlg = None
        self.ui.action_Parameters.setChecked(False)

    @pyqtSignature("bool")
    def on_actionZoom_in_toggled(self, value):
        if value:
            self._previousScene.mode = TrackingScene.ZoomIn
            self._currentScene.mode = TrackingScene.ZoomIn

    @pyqtSignature("bool")
    def on_actionZoom_out_toggled(self, value):
        if value:
            self._previousScene.mode = TrackingScene.ZoomOut
            self._currentScene.mode = TrackingScene.ZoomOut

    #def resizeEvent(self, event):
    #    self.ensureZoomFit()

    def ensureZoomFit(self):
        if self._data:
            prev_rect = self._previousScene.sceneRect()
            cur_rect = self._currentScene.sceneRect()
            prev_wnd = QRectF(self.ui.previousData.childrenRect())
            cur_wnd = QRectF(self.ui.currentData.childrenRect())
            prev_matrix = self.ui.previousData.matrix()
            cur_matrix = self.ui.currentData.matrix()

            prev_mapped_rect = prev_matrix.mapRect(prev_rect)
            cur_mapped_rect = cur_matrix.mapRect(cur_rect)

            if (prev_mapped_rect.width() < prev_wnd.width() or
                    prev_mapped_rect.height() < prev_wnd.height() or
                    cur_mapped_rect.width() < cur_wnd.width() or
                    cur_mapped_rect.height() < cur_wnd.height()):
                self.on_action_Fit_triggered()

    @pyqtSignature("")
    def on_action_Fit_triggered(self):
        prev_rect = self._previousScene.sceneRect()
        cur_rect = self._currentScene.sceneRect()
        prev_wnd = self.ui.previousData.childrenRect()
        cur_wnd = self.ui.currentData.childrenRect()

        prev_sw = prev_wnd.width() / prev_rect.width()
        prev_sh = prev_wnd.height() / prev_rect.height()

        cur_sw = cur_wnd.width() / cur_rect.width()
        cur_sh = cur_wnd.height() / cur_rect.height()

        s = max(prev_sw, prev_sh, cur_sw, cur_sh)

        self.ui.previousData.resetMatrix()
        self.ui.previousData.scale(s,s)
        self.ui.currentData.resetMatrix()
        self.ui.currentData.scale(s,s)
        self.changeZoom(s)

    def zoomOut(self, point=None):
        self.ui.currentData.scale(0.5, 0.5)
        self.ui.previousData.scale(0.5, 0.5)
        self.changeZoom(self.ui.previousData.matrix().m11())
        if point is not None:
            self.ui.previousData.centerOn(point)
            self.ui.currentData.centerOn(point)
        #self.ensureZoomFit()

    def zoomIn(self, point=None):
        self.ui.currentData.scale(2,2)
        self.ui.previousData.scale(2,2)
        self.changeZoom(self.ui.previousData.matrix().m11())
        if point is not None:
            self.ui.previousData.centerOn(point)
            self.ui.currentData.centerOn(point)


    def changeZoom(self, zoom):
        self._zoom_label.setText("Zoom: %.5g%%" % (100*zoom))

    @pyqtSignature("")
    def on_actionZoom_100_triggered(self):
        self.ui.previousData.resetMatrix()
        self.ui.currentData.resetMatrix()
        self.changeZoom(1)

    @pyqtSignature("bool")
    def on_actionAdd_point_toggled(self, value):
        if value:
            self._previousScene.mode = TrackingScene.Add
            self._currentScene.mode = TrackingScene.Add

    @pyqtSignature("bool")
    def on_actionAdd_cell_toggled(self, value):
        if value:
            self._previousScene.mode = TrackingScene.AddCell
            self._currentScene.mode = TrackingScene.AddCell

    @pyqtSignature("bool")
    def on_actionRemove_cell_toggled(self, value):
        if value:
            self._previousScene.mode = TrackingScene.RemoveCell
            self._currentScene.mode = TrackingScene.RemoveCell

    @pyqtSignature("bool")
    def on_action_Move_point_toggled(self, value):
        if value:
            self._previousScene.mode = TrackingScene.Move
            self._currentScene.mode = TrackingScene.Move

    @pyqtSignature("bool")
    def on_action_Pan_toggled(self, value):
        if value:
            self._previousScene.mode = TrackingScene.Pan
            self._currentScene.mode = TrackingScene.Pan

    @pyqtSignature("bool")
    def on_linkViews_toggled(self, value):
        parameters.instance.link_views = value
        phor = self.ui.previousData.horizontalScrollBar()
        pver = self.ui.previousData.verticalScrollBar()
        chor = self.ui.currentData.horizontalScrollBar()
        cver = self.ui.currentData.verticalScrollBar()
        if value:
            QObject.connect(phor, SIGNAL("valueChanged(int)"), chor, SLOT("setValue(int)"))
            QObject.connect(pver, SIGNAL("valueChanged(int)"), cver, SLOT("setValue(int)"))
            QObject.connect(chor, SIGNAL("valueChanged(int)"), phor, SLOT("setValue(int)"))
            QObject.connect(cver, SIGNAL("valueChanged(int)"), pver, SLOT("setValue(int)"))
            QObject.connect(self._previousScene, SIGNAL("templatePosChange"), self._currentScene.setTemplatePos)
            QObject.connect(self._currentScene, SIGNAL("templatePosChange"), self._previousScene.setTemplatePos)
            phor.setValue(chor.value())
            pver.setValue(cver.value())
        else:
            QObject.disconnect(phor, SIGNAL("valueChanged(int)"), chor, SLOT("setValue(int)"))
            QObject.disconnect(pver, SIGNAL("valueChanged(int)"), cver, SLOT("setValue(int)"))
            QObject.disconnect(chor, SIGNAL("valueChanged(int)"), phor, SLOT("setValue(int)"))
            QObject.disconnect(cver, SIGNAL("valueChanged(int)"), pver, SLOT("setValue(int)"))
            QObject.disconnect(self._previousScene, SIGNAL("templatePosChange"), self._currentScene.setTemplatePos)
            QObject.disconnect(self._currentScene, SIGNAL("templatePosChange"), self._previousScene.setTemplatePos)

    def copyFrom(self, start, items):
        if parameters.instance.estimate:
            dlg = createForm('copy_progress.ui', None)
            QObject.connect(dlg.buttonBox, SIGNAL("clicked(QAbstractButton*)"), self.cancelCopy)
            params = parameters.instance
            ts = params.template_size
            ss = params.search_size
            fs = params.filter_size
            self.copy_thread = algo.FindInAll(self._data, start, items, ts, ss, fs, self)
            dlg.imageProgress.setMaximum(self.copy_thread.num_images)
            self.copy_thread.start()
            self.copy_dlg = dlg
            dlg.exec_()
        else:
            algo.copyFromImage(self._data, start, items, self.undo_stack)

    def cancelCopy(self, *args):
        self.copy_thread.stop = True
        dlg = self.copy_dlg
        QObject.disconnect(dlg.buttonBox, SIGNAL("clicked(QAbstractButton*)"), self.cancelCopy)
        self._previousScene.changeImage(None)
        self._currentScene.changeImage(None)

    def event(self, event):
        if isinstance(event, algo.NextImage):
            dlg = self.copy_dlg
            if dlg is not None:
                dlg.imageProgress.setValue(event.currentImage)
                dlg.pointProgress.setMaximum(event.nbPoints)
                dlg.pointProgress.setValue(0)
            return True
        elif isinstance(event, algo.NextPoint):
            dlg = self.copy_dlg
            if dlg is not None:
                dlg.pointProgress.setValue(event.currentPoint)
            return True
        elif isinstance(event, algo.FoundAll):
            dlg = self.copy_dlg
            if dlg is not None:
                self.cancelCopy()
                dlg.accept()
            return True
        elif isinstance(event, algo.Aborted):
            dlg = self.copy_dlg
            if dlg is not None:
                self.cancelCopy()
                dlg.accept()
            return True
        return QMainWindow.event(self,event)

    def itemsToCopy(self, scene):
        items = scene.getSelectedIds()
        if items:
            answer = QMessageBox.question(self, "Copy of points", "Some points were selected in the previous data window. Do you want to copy only these point on the successive images?", QMessageBox.Yes, QMessageBox.No)
            if answer == QMessageBox.Yes:
                return items
        return scene.getAllIds()

    @pyqtSignature("")
    def on_actionCopy_from_previous_triggered(self):
        items = self.itemsToCopy(self._previousScene)
        if items:
            self.copyFrom(self.ui.previousState.currentIndex(), items)

    @pyqtSignature("")
    def on_actionCopy_from_current_triggered(self):
        items = self.itemsToCopy(self._currentScene)
        if items:
            self.copyFrom(self.ui.currentState.currentIndex(), items)

    @pyqtSignature("")
    def on_actionSelectPreviousAll_triggered(self):
        self._previousScene.selectAll()

    @pyqtSignature("")
    def on_actionSelectPreviousNew_triggered(self):
        self._previousScene.selectNew()

    @pyqtSignature("")
    def on_actionSelectPreviousNone_triggered(self):
        self._previousScene.selectNone()

    @pyqtSignature("")
    def on_actionSelectPreviousNon_associated_triggered(self):
        self._previousScene.selectNonAssociated()

    @pyqtSignature("")
    def on_actionSelectPreviousAssociated_triggered(self):
        self._previousScene.selectAssociated()

    @pyqtSignature("")
    def on_actionSelectPreviousInvert_triggered(self):
        self._previousScene.selectInvert()

    @pyqtSignature("")
    def on_actionSelectCurrentAll_triggered(self):
        self._currentScene.selectAll()

    @pyqtSignature("")
    def on_actionSelectCurrentNew_triggered(self):
        self._currentScene.selectNew()

    @pyqtSignature("")
    def on_actionSelectCurrentNone_triggered(self):
        self._currentScene.selectNone()

    @pyqtSignature("")
    def on_actionSelectCurrentNon_associated_triggered(self):
        self._currentScene.selectNonAssociated()

    @pyqtSignature("")
    def on_actionSelectCurrentAssociated_triggered(self):
        self._currentScene.selectAssociated()

    @pyqtSignature("")
    def on_actionSelectCurrentInvert_triggered(self):
        self._currentScene.selectInvert()

    def whichDelete(self):
        """
        Returns a function deleting what the user wants
        """
        dlg = createForm("deletedlg.ui", None)
        ret = dlg.exec_()
        if ret:
            if dlg.inAllImages.isChecked():
                return TrackingScene.deleteInAllImages
            if dlg.toImage.isChecked():
                return TrackingScene.deleteToImage
            if dlg.fromImage.isChecked():
                return TrackingScene.deleteFromImage
        return lambda x: None

    @pyqtSignature("")
    def on_actionDelete_Previous_triggered(self):
        del_fct = self.whichDelete()
        del_fct(self._previousScene)

    @pyqtSignature("")
    def on_actionDelete_Current_triggered(self):
        del_fct = self.whichDelete()
        del_fct(self._currentScene)

    @pyqtSignature("")
    def on_actionMerge_points_triggered(self):
        if self._previousScene.mode == TrackingScene.AddCell:
            old_cell = self._previousScene.selected_cell
            new_cell = self._currentScene.selected_cell
            if old_cell is None or new_cell is None:
                QMessageBox.critical(self, "Cannot merge cells", "You have to select exactly one cell in the old state and one in the new state to merge them.")
                return
            try:
                if old_cell != new_cell:
                    self.undo_stack.push(MergeCells(self._data, self._previousScene.image_name, old_cell, new_cell))
                else:
                    self.undo_stack.push(SplitCells(self._data, self._previousScene.image_name, old_cell, new_cell))
            except AssertionError as error:
                QMessageBox.critical(self, "Cannot merge the cells", str(error))
        else:
            old_pts = self._previousScene.getSelectedIds()
            new_pts = self._currentScene.getSelectedIds()
            if len(old_pts) != 1 or len(new_pts) != 1:
                QMessageBox.critical(self, "Cannot merge points", "You have to select exactly one point in the old state and one in the new state to link them.")
                return
            try:
                if old_pts != new_pts:
                    self.undo_stack.push(ChangePointsId(self._data, self._previousScene.image_name, old_pts, new_pts))
                else:
                    log_debug("Splitting point of id %d" % old_pts[0])
                    self.undo_stack.push(SplitPointsId(self._data, self._previousScene.image_name, old_pts))
            except AssertionError as error:
                QMessageBox.critical(self, "Cannot merge the points", str(error))

    @pyqtSignature("")
    def on_actionCopy_selection_from_Current_triggered(self):
        cur_sel = self._currentScene.getSelectedIds()
        self._previousScene.setSelectedIds(cur_sel)

    @pyqtSignature("")
    def on_actionCopy_selection_from_Previous_triggered(self):
        cur_sel = self._previousScene.getSelectedIds()
        self._currentScene.setSelectedIds(cur_sel)

    @pyqtSignature("")
    def on_actionNew_data_file_triggered(self):
        if self.ensure_save_data("Leaving unsaved data", "The last modifications you made were not saved. Are you sure you want to change the current data file?"):
            fn = QFileDialog.getSaveFileName(self, "Select a new data file to create", self._project.data_dir,
                                                   "CSV Files (*.csv);;All files (*.*)")
            if fn:
                fn = path(fn)
                if fn.exists():
                    button = QMessageBox.question(self, "Erasing existing file", "Are you sure yo want to empty the file '%s' ?" % fn, QMessageBox.Yes, QMessageBox.No)
                    if button == QMessageBox.No:
                        return
                    fn.remove()
                self._data.clear()
                self._previousScene.resetNewPoints()
                self._currentScene.resetNewPoints()
                self._project.data_file = fn
                self.initFromData()
                log_debug("Data file = %s" % (self._project.data_file,))

    @pyqtSignature("")
    def on_actionAbout_triggered(self):
        dlg = QMessageBox(self)
        dlg.setWindowTitle("About Point Tracker")
        dlg.setIconPixmap(self.windowIcon().pixmap(64,64))
        #dlg.setTextFormat(Qt.RichText)

        dlg.setText("""Point Tracker Tool version %s rev %s
Developper: Pierre Barbier de Reuille <pierre.barbier-de-reuille@cmp.uea.ac.uk>
Copyright 2008
""" % (__version__, __revision__))

        img_read = ", ".join(str(s) for s in QImageReader.supportedImageFormats())
        img_write = ", ".join(str(s) for s in QImageWriter.supportedImageFormats())

        dlg.setDetailedText("""Supported image formats:
  - For reading: %s

  - For writing: %s
""" % (img_read, img_write))
        dlg.exec_()

    @pyqtSignature("")
    def on_actionAbout_Qt_triggered(self):
        QMessageBox.aboutQt(self, "About Qt")

    @pyqtSignature("")
    def on_actionReset_alignment_triggered(self):
        self.undo_stack.push(ResetAlignment(self._data))

    @pyqtSignature("")
    def on_actionAlign_images_triggered(self):
        fn = QFileDialog.getOpenFileName(self, "Select a data file for alignment", self._project.data_dir,
                                               "CSV Files (*.csv);;All files (*.*)")
        if fn:
            d = self._data.copy()
            fn = path(fn)
            try:
                d.load(fn)
            except TrackingDataException as ex:
                showException(self, "Error while loading data file", ex)
                return
            #points = [str(i) for i in range(d._last_pt_id+1)]
            #points.insert(0, "Barycenter")
            #ref, ok = QInputDialog.getItem(self, "Alignment data parameter", "Choose the reference point", points, 0, False)
            if d._last_pt_id > 0:
                dlg = AlignmentDlg(d._last_pt_id+1, self)
                if dlg.exec_():
                    ref = dlg.ui.referencePoint.currentText()
                    try:
                        ref = int(ref)
                    except ValueError:
                        ref = str(ref)
                    if dlg.ui.twoPointsRotation.isChecked():
                        r1 = int(dlg.ui.rotationPt1.currentText())
                        r2 = int(dlg.ui.rotationPt2.currentText())
                        rotation = ("TwoPoint", r1, r2)
                    else:
                        rotation = None
                else:
                    return
            else:
                ref = 0
                rotation = None
            try:
                shifts, angles = algo.alignImages(self._data, d, ref, rotation)
                self.undo_stack.push(AlignImages(self._data, shifts, angles))
            except algo.AlgoException as ex:
                showException(self, "Error while aligning images", ex)

    def sceneSizeChanged(self):
        previous_rect = self._previousScene.real_scene_rect
        current_rect = self._currentScene.real_scene_rect
        rect = previous_rect | current_rect
        self._previousScene.setSceneRect(rect)
        self._currentScene.setSceneRect(rect)

    @pyqtSignature("")
    def on_actionEdit_timing_triggered(self):
        data = self._data
        dlg = TimeEditDlg(data.images_name, data.images_time, [data.image_path(n) for n in data.images_name], self)
        self.current_dlg = dlg
        if dlg.exec_() == QDialog.Accepted:
            self.undo_stack.push(ChangeTiming(data, [t for n,t in dlg.model]))
        del self.current_dlg

    @pyqtSignature("")
    def on_actionEdit_scales_triggered(self):
        data = self._data
        dlg = EditResDlg(data.images_name, data.images_scale, [data.image_path(n) for n in data.images_name], self)
        self.current_dlg = dlg
        if dlg.exec_() == QDialog.Accepted:
            self.undo_stack.push(ChangeScales(data, [sc for n,sc in dlg.model]))
        del self.current_dlg

    @pyqtSignature("")
    def on_actionCompute_growth_triggered(self):
        data = self._data
        dlg = GrowthComputationDlg(data, self)
        self.current_dlg = dlg
        dlg.exec_()
        del self.current_dlg

    @pyqtSignature("")
    def on_actionPlot_growth_triggered(self):
        data = self._data
        dlg = PlottingDlg(data, self)
        self.current_dlg = dlg
        dlg.exec_()
        del self.current_dlg

    @pyqtSignature("")
    def on_actionClean_cells_triggered(self):
        self.undo_stack.push(CleanCells(self._data))

    @pyqtSignature("")
    def on_actionGotoCell_triggered(self):
        cells = [ str(cid) for cid in self._data.cells ]
        selected, ok = QInputDialog.getItem(self, "Goto cell", "Select the cell to go to", cells, 0)
        if ok:
            cid = int(selected)
            self.ui.actionAdd_cell.setChecked(True)
            data = self._data
            if cid not in data.cells:
                return
            ls = data.cells_lifespan[cid]
            prev_pos = self._previousScene.current_data._current_index
            cur_pos = self._currentScene.current_data._current_index
            full_poly = data.cells[cid]
            poly = [ pid for pid in full_poly if pid in data[prev_pos] ]
            #log_debug("Cell %d on time %d: %s" % (cid, prev_pos, poly))
            if prev_pos < ls.start or prev_pos >= ls.end or not poly:
                for i in range(*ls.slice().indices(len(data))):
                    poly = [ pid for pid in full_poly if pid in data[i] ]
                    if poly:
                        log_debug("Found cell %d on image %d with polygon %s" % (cid, i, poly))
                        new_prev_pos = i
                        break
                else:
                    log_debug("Cell %d found nowhere in range %s!!!" % (cid, ls.slice()))
            else:
                new_prev_pos = prev_pos
            new_cur_pos = min(max(cur_pos + new_prev_pos - prev_pos, 0), len(data))
            self.ui.previousState.setCurrentIndex(new_prev_pos)
            self.ui.currentState.setCurrentIndex(new_cur_pos)
            self._previousScene.current_cell = cid
            self._currentScene.current_cell = cid
            prev_data = self._previousScene.current_data
            poly = data.cells[cid]
            prev_poly = QPolygonF([prev_data[ptid] for ptid in poly if ptid in prev_data])
            prev_bbox = prev_poly.boundingRect()
            log_debug("Previous bounding box = %dx%d+%d+%d" % (prev_bbox.width(), prev_bbox.height(), prev_bbox.left(), prev_bbox.top()))
            self.ui.previousData.ensureVisible(prev_bbox)

    @pyqtSignature("")
    def on_actionGotoPoint_triggered(self):
        data = self._data
        points = [ str(pid) for pid in data.cell_points ]
        selected, ok = QInputDialog.getItem(self, "Goto point", "Select the point to go to", points, 0)
        if ok:
            pid = int(selected)
            self.ui.action_Move_point.setChecked(True)
            if pid not in data.cell_points:
                return
            prev_pos = self._previousScene.current_data._current_index
            cur_pos = self._currentScene.current_data._current_index
            prev_data = self._previousScene.current_data
            if not pid in prev_data:
                closest = -1
                best_dist = len(data)+1
                for img_data in data:
                    if pid in img_data:
                        dist = abs(img_data._current_index - prev_pos)
                        if dist < best_dist:
                            best_dist = dist
                            closest = img_data._current_index
                new_prev_pos = closest
            else:
                new_prev_pos = prev_pos
            new_cur_pos = min(max(cur_pos + new_prev_pos - prev_pos, 0), len(data))
            self.ui.previousState.setCurrentIndex(new_prev_pos)
            self.ui.currentState.setCurrentIndex(new_cur_pos)
            self._previousScene.setSelectedIds([pid])
            self._currentScene.setSelectedIds([pid])
            self.ui.previousData.centerOn(self._previousScene.current_data[pid])

