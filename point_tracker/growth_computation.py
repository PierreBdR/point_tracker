from __future__ import print_function, division, absolute_import
"""
:newfield signal: Signal, Signals
"""
__author__ = "Pierre Barbier de Reuille <pbdr@uea.ac.uk>"
__docformat__ = "restructuredtext"

from PyQt4.QtGui import (QDialog, QIcon, QPixmap, QMenu, QItemSelectionModel, QItemSelection,
        QFileDialog, QMessageBox, QProgressDialog, QDialogButtonBox)
from PyQt4.QtCore import pyqtSignature, Qt, QSize, QThread, QEvent, SIGNAL, QMutex, QCoreApplication
from .ui_growth_computation import Ui_GrowthComputationDlg
from .timemodel import TimedImageModel
from . import image_cache
from .path import path
from . import growth_computation_methods
from .sys_utils import retryException, showException
from .tracking_data import TrackingDataException, RetryTrackingDataException

class GrowthComputationDlg(QDialog):
    def __init__(self, data, parent=None):
        QDialog.__init__(self, parent)
        cache = image_cache.cache
        self.ui = Ui_GrowthComputationDlg()
        self.ui.setupUi(self)

        images = data.images_name
        times = data.images_time
        images_path = [ data.image_path(img) for img in images ]
        self.data = data

        icons = []
        for img,pth in zip(images, images_path):
            ico = QIcon(QPixmap.fromImage(cache.image(pth).scaled(QSize(64,64), Qt.KeepAspectRatio)))
            icons.append(ico)

        self.allimages_model = TimedImageModel(icons, images, times)
        self.ui.allImages.setModel(self.allimages_model)
        self.selectedimages_model = TimedImageModel([],[],[])
        self.ui.selectedImages.setModel(self.selectedimages_model)
        self.ui.allImages.resizeColumnToContents(0)
        self.ui.allImages.resizeColumnToContents(1)
        self.load_btn = self.ui.buttonBox.addButton("Load", QDialogButtonBox.ActionRole)
        self.load_btn.clicked.connect(self.loadGrowthFile)

        select_menu = QMenu()
        select_menu.addAction(self.ui.actionSelect_even_images)
        select_menu.addAction(self.ui.actionSelect_odd_images)
        select_menu.addAction(self.ui.actionInvert_selection)
        select_menu.addSeparator()
        select_menu.addAction(self.ui.actionSelect_all_images)
        select_menu.addAction(self.ui.actionSelect_no_image)
        self.select_menu = select_menu

        self.activ_selection = None
        self.method = "Forward"
        self.cells_selection = "AllCells"
        self.withVariation = False
        self.ui.allCells.setChecked(True)
        self.ui.withVariation.setChecked(False)
        self.ui.forwardMethod.setChecked(True)
        self.resample = 100
        self.ui.resample.setChecked(True)

    @pyqtSignature("")
    def loadGrowthFile(self, **opts):
        if 'filename' not in opts:
            startdir = self.data.project_dir
            filename = QFileDialog.getOpenFileName(self, "Open a growth file", startdir, "XLS Files (*.xls);;All files (*.*)")
        else:
            filename = opts['filename']
        if filename:
            try:
                res = growth_computation_methods.Result(None)
                res.load(path(filename), force_load=True, no_data = True) # make sure there is no problem
                # First, load the images
                imgs = set(res.images_used)
                allimages_model = self.allimages_model
                selectedimages_model = self.selectedimages_model
                selectedimages_model.clear()
                for name, time, icon in zip(allimages_model.names,
                                            allimages_model.times,
                                            allimages_model.icons):
                    if name in imgs:
                        selectedimages_model.addImage(icon, name, time)
                if selectedimages_model:
                    self.ui.selectedImages.resizeColumnToContents(0)
                    self.ui.selectedImages.resizeColumnToContents(1)
                # Second, load growth method
                meth = res.method_params
                if meth[0].startswith('Forward'):
                    self.ui.forwardMethod.setChecked(True)
                elif meth[0].startswith('Backward'):
                    self.ui.backwardMethod.setChecked(True)
                if meth[0].endswith('Dense'):
                    self.ui.resample.setChecked(True)
                    self.ui.samplingPoints.setValue(int(meth[1]))
                else:
                    self.ui.resample.setChecked(False)
                # Third, cell selection
                sel = res.cells_selection_params
                if sel[0] == 'AllCells':
                    self.ui.allCells.setChecked(True)
                    if len(sel) > 2:
                        var = int(sel[1].split()[0][:-1])
                        self.maxVariationAllCells.setValue(var)
                elif sel[0] == 'AddDivisionOnly':
                    self.ui.samePoints.setChecked(True)
                elif sel[0] == 'AddPoints':
                    self.ui.addPoints.setChecked(True)
                    var = int(sel[1].split()[0][:-1])
                    self.maxVariationAddPoints.setValue(var)
                if sel[-1] == 'with cell division':
                    self.ui.daughterCells.setChecked(True)
                else:
                    self.ui.daughterCells.setChecked(False)
                # At last, set the current file as target
                self.ui.savePath.setText(filename)
            except TrackingDataException as ex:
                showException(self, "Error while loading data", ex)
                return
            except RetryTrackingDataException as ex:
                if retryException(self, "Problem while loading data", ex):
                    new_opts = dict(opts)
                    new_opts.update(ex.method_args)
                    return self.loadGrowthFile(filename = filename, **new_opts)
                return

    @pyqtSignature("")
    def on_addImages_clicked(self):
        selection = self.ui.allImages.selectionModel()
        allimages_model = self.allimages_model
        selectedimages_model = self.selectedimages_model
        for idx in selection.selectedRows():
            name = allimages_model.name(idx)
            time = allimages_model.time(idx)
            icon = allimages_model.icon(idx)
            selectedimages_model.addImage(icon, name, time)
        if selectedimages_model:
            self.ui.selectedImages.resizeColumnToContents(0)
            self.ui.selectedImages.resizeColumnToContents(1)
        selection.clear()

    @pyqtSignature("")
    def on_removeImages_clicked(self):
        selection = self.ui.selectedImages.selectionModel()
        selectedimages_model = self.selectedimages_model
        poss = [ selectedimages_model.position(idx) for idx in selection.selectedRows() ]
        poss.sort(reverse=True)
        for pos in poss:
            selectedimages_model.removeImage(pos)
        selection.clear()

    def showSelectionMenu(self, widget, pos):
        pos = widget.viewport().mapToGlobal(pos)
        self.activ_selection = widget
        self.select_menu.popup(pos)

    @pyqtSignature("const QPoint&")
    def on_allImages_customContextMenuRequested(self, pos):
        self.showSelectionMenu(self.ui.allImages, pos)

    @pyqtSignature("const QPoint&")
    def on_selectedImages_customContextMenuRequested(self, pos):
        self.showSelectionMenu(self.ui.selectedImages, pos)

    @pyqtSignature("")
    def on_actionSelect_even_images_triggered(self):
        widget = self.activ_selection
        model = widget.model()
        selection = widget.selectionModel()
        sel = QItemSelection()
        for i in  range(1,len(model),2):
            sel.select(model.index(i,0), model.index(i,1))
        selection.select(sel, QItemSelectionModel.ClearAndSelect)
        widget.viewport().update()

    @pyqtSignature("")
    def on_actionSelect_odd_images_triggered(self):
        widget = self.activ_selection
        model = widget.model()
        selection = widget.selectionModel()
        sel = QItemSelection()
        for i in  range(0,len(model),2):
            sel.select(model.index(i,0), model.index(i,1))
        selection.select(sel, QItemSelectionModel.ClearAndSelect)
        widget.viewport().update()

    @pyqtSignature("")
    def on_actionSelect_all_images_triggered(self):
        widget = self.activ_selection
        widget.selectAll()
        widget.viewport().update()

    @pyqtSignature("")
    def on_actionSelect_no_image_triggered(self):
        widget = self.activ_selection
        selection = widget.selectionModel()
        selection.clear()
        widget.viewport().update()

    @pyqtSignature("")
    def on_actionInvert_selection_triggered(self):
        widget = self.activ_selection
        model = widget.model()
        selection = widget.selectionModel()
        root = model.root
        selection.select(QItemSelection(model.index(0,0,root), model.index(model.rowCount(root),1,root)), QItemSelectionModel.Toggle)
        widget.viewport().update()

    @pyqtSignature("")
    def on_chooseFile_clicked(self):
        startdir = self.data.project_dir
        filename = QFileDialog.getSaveFileName(self, "Choose a file to save data", startdir, "XLS Files (*.xls)")
        if filename:
            if '.' not in filename:
                filename += ".xls"
            self.ui.savePath.setText(filename)

    @pyqtSignature("bool")
    def on_forwardMethod_toggled(self, value):
        if value:
            self.method = "Forward"

    @pyqtSignature("bool")
    def on_backwardMethod_toggled(self, value):
        if value:
            self.method = "Backward"

    @pyqtSignature("bool")
    def on_resample_toggled(self, value):
        if value:
            self.resample = self.ui.samplingPoints.value()
        else:
            self.resample = 0

    @pyqtSignature("int")
    def on_samplingPoints_changed(self, value):
        self.resample = int(value)

    @pyqtSignature("bool")
    def on_addPoints_toggled(self, value):
        if value:
            self.cells_selection = "AddPoints"

    @pyqtSignature("bool")
    def on_samePoints_toggled(self, value):
        if value:
            self.cells_selection = "FullCells"

    @pyqtSignature("bool")
    def on_allCells_toggled(self, value):
        if value:
            self.cells_selection = "AllCells"

    @pyqtSignature("bool")
    def on_withVariation_toggled(self, value):
        self.withVariation = bool(value)

    def accept(self):
        model = self.selectedimages_model
        filename = path(self.ui.savePath.text())
        if not filename:
            QMessageBox.critical(self, "Error in processing", "You have to provide a file name to save the computation in.")
            return
        if not filename.dirname().exists():
            QMessageBox.critical(self, "Error in processing", "The directory containing the file path provided do not exist.\nPlease create the directory or provide a path in an existing directory.")
            return
        if not model:
            QMessageBox.critical(self, "Error in processing", "You didn't any image to compute the growth with.")
            return
        if self.resample == 0:
            if self.method == "Forward":
                method = growth_computation_methods.ForwardMethod()
            elif self.method == "Backward":
                method = growth_computation_methods.BackwardMethod()
        else:
            if self.method == "Forward":
                method = growth_computation_methods.ForwardDenseMethod(self.resample)
            elif self.method == "Backward":
                method = growth_computation_methods.BackwardDenseMethod(self.resample)
        use_daughters = self.ui.daughterCells.isChecked()
        if self.cells_selection == "AddPoints":
            cells_selection = growth_computation_methods.AddPointsSelection(use_daughters, self.ui.maxVariationAddPoints.value()/100.)
        elif self.cells_selection == "AllCells":
            if self.withVariation:
                cells_selection = growth_computation_methods.AllCellsSelection(use_daughters, self.ui.maxVariationAllCells.value()/100.)
            else:
                cells_selection = growth_computation_methods.AllCellsSelection(use_daughters, None)
        elif self.cells_selection == "FullCells":
            cells_selection = growth_computation_methods.FullCellsOnlySelection(use_daughters)
        else:
            raise "Cells selection method '%s' is not implemented" % self.cells_selection
        thread = GrowthComputationThread(self)
        thread.data = self.data
        thread.list_img = model.names
        thread.method = method
        thread.cells_selection = cells_selection
        thread.filename = filename
        self.thread = thread
        nb_images = thread.nbOutputImages()
        progress = QProgressDialog("Computing the growth on %d images" % nb_images, "Abort", 0, nb_images-1, self)
        progress.setMinimumDuration(2000)
        self.progress = progress
        self.connect(progress, SIGNAL("canceled()"), thread.stop)
        thread.start()

    def event(self, event):
        if isinstance(event, NextImageGrowthEvent):
            self.progress.setValue(self.progress.value()+1)
            return True
        elif isinstance(event, FinishImageGrowthEvent):
            self.progress.reset()
            del self.thread
            del self.progress
            QMessageBox.information(self, "Growth computation", "The growth has been correctly computed and saved")
            #QDialog.accept(self)
            return True
        elif isinstance(event, AbortImageGrowthEvent):
            self.progress.reset()
            del self.thread
            del self.progress
            QMessageBox.information(self, "Growth computation", "The growth computation has been aborted.\nNothing was saved.")
            return True
        return QDialog.event(self, event)

class NextImageGrowthEvent(QEvent):
    def __init__(self):
        QEvent.__init__(self, NextImageGrowthEvent.event_type)
    event_type = QEvent.Type(QEvent.registerEventType())

class AbortImageGrowthEvent(QEvent):
    def __init__(self):
        QEvent.__init__(self, AbortImageGrowthEvent.event_type)
    event_type = QEvent.Type(QEvent.registerEventType())

class FinishImageGrowthEvent(QEvent):
    def __init__(self):
        QEvent.__init__(self, FinishImageGrowthEvent.event_type)
    event_type = QEvent.Type(QEvent.registerEventType())

class GrowthComputationThread(QThread):
    def __init__(self, parent):
        QThread.__init__(self)
        self.parent = parent
        self.data = None
        self.list_img = None
        self._method = None
        self._cells_selection = None
        self.mutex = QMutex()
        self.filename = None
        self._stop = False

    def _get_method(self):
        return self._method

    def _set_method(self, method):
        assert hasattr(method, "__call__"), "Invalid computation method, no '__call__' method"
        assert hasattr(method, "thread"), "Invalid computation method, no 'thread' attribute"
        assert hasattr(method, "parameters"), "Invalid computation method, no 'parameters' method"
        self._method = method

    method = property(_get_method, _set_method)

    def _get_cells_selection(self):
        return self._cells_selection

    def _set_cells_selection(self, cells_selection):
        assert hasattr(cells_selection, "__call__"), "Invalid cells selection method, no '__call__' method"
        assert hasattr(cells_selection, "parameters"), "Invalid cells selection method, no 'parameters' method"
        self._cells_selection = cells_selection

    cells_selection = property(_get_cells_selection, _set_cells_selection)

    def valid(self):
        if self.parent is None:
            return False
        if self.data is None:
            return False
        if self.list_img is None:
            return False
        if self.method is None:
            return False
        if self.filename is None:
            return False
        return True

    def run(self):
        self._stop = False
        if not self.valid():
            self.abort()
            return
        method = self.method
        method.thread = self
        result = method(self.list_img, self.data, self.cells_selection)
        if result is None:
            self.abort()
            return
        self.save(result)
        self.finished()

    def start(self):
        from .parameters import instance
        if instance.use_thread:
            QThread.start(self)
        else:
            self.run()

    def save(self, result):
        result.method_params = self.method.parameters()
        result.cells_selection_params = self.cells_selection.parameters()
        return result.save(self.filename)

    def stop(self):
        self.mutex.lock()
        self._stop = True
        self.mutex.unlock()

    def stopped(self):
        self.mutex.lock()
        stop = self._stop
        self.mutex.unlock()
        return stop

    def nbOutputImages(self):
        return  self.method.nbOutputImages(self.list_img, self.data)

    def abort(self):
        QCoreApplication.postEvent(self.parent, AbortImageGrowthEvent())

    def nextImage(self):
        QCoreApplication.postEvent(self.parent, NextImageGrowthEvent())

    def finished(self):
        QCoreApplication.postEvent(self.parent, FinishImageGrowthEvent())


