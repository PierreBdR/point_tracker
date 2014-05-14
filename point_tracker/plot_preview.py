from __future__ import print_function, division, absolute_import
__author__ = "Pierre Barbier de Reuille <pbdr@uea.ac.uk>"
__docformat__ = "restructuredtext"
from PyQt4.QtGui import (QDialog, QPushButton, QGraphicsView, QTransform, QMessageBox, QIcon,
        QDialogButtonBox, QPixmap, QGraphicsScene, QLabel)
from PyQt4.QtCore import QObject, pyqtSignature, QRectF, Qt, QTimer
from PyQt4.QtOpenGL import QGLWidget, QGLFormat, QGL

from .ui_plot_preview import Ui_PlotPreview
from . import parameters
from .debug import log_debug
from .sys_utils import cleanQObject

class PlotPreview(QDialog):
    def __init__(self, thread, parent):
        QDialog.__init__(self, parent)
        self.ui = Ui_PlotPreview()
        self.ui.setupUi(self)
        self.parent = parent
        icon = QIcon()
        icon.addPixmap(QPixmap(":/icons/reload.png"), QIcon.Normal, QIcon.Off)
        self.update_btn = QPushButton(icon, "Update")
        self.ui.buttonBox.addButton(self.update_btn, QDialogButtonBox.ApplyRole)
        self.update_btn.clicked.connect(self.render_image)
        self._pix = None
        self._image_list = None
        self._thread = thread
        self.scene = QGraphicsScene()
        self.scene.setSceneRect(0,0,1,1)
        self.ui.imageView.setScene(self.scene)
        self.pix_item = None
        self.ui.imageView.setEnabled(False)
        self.ui.imageView.setInteractive(False)
        self.ui.imageView.setDragMode(QGraphicsView.ScrollHandDrag)
        self.pic_w = None
        self.pic_c = None
        self.show_pic_w = None
        self.show_pic_c = None
        timer = QTimer(self)
        timer.setSingleShot(True)
        timer.setInterval(500)
        self.timer = timer
        timer.timeout.connect(self.render_image)
        if parameters.instance.use_OpenGL:
            self.ui.imageView.setViewport(QGLWidget(QGLFormat(QGL.SampleBuffers)))

    def __del__(self):
        self.ui.imageView.setScene(None)
        cleanQObject(self)

    @property
    def thread(self):
        '''Thread object drawing the img'''
        return self._thread

    @thread.setter
    def thread(self, value):
        if self._thread != value:
            self._thread = value

    @property
    def pix(self):
        '''Image to be previewed.

        :returntype: `QImage`'''
        return self._pix

    @pix.setter
    def pix(self, pix):
        self.ui.imageView.setEnabled(True)
        self._pix = pix
        if self.pix_item is not None:
            self.scene.removeItem(self.pix_item)
        self.pix_item = self.scene.addPixmap(QPixmap.fromImage(pix))
        self.scene.setSceneRect(QRectF(self.pix.rect()))
        if self.show_pic_w:
            self.show_pic_w.close()
            self.show_pic_w = None
        if self.pic_w:
            self.show_pic_w = QLabel(self, Qt.Window)
            #self.show_pic_w.setAttribute(Qt.WA_DeleteOnClose)
            self.show_pic_w.setPicture(self.pic_w)
            self.show_pic_w.show()
            self.show_pic_w.raise_()
        if self.show_pic_c:
            self.show_pic_c.close()
            self.show_pic_c = None
        if self.pic_c:
            self.show_pic_c = QLabel(self, Qt.Window)
            #self.show_pic_c.setAttribute(Qt.WA_DeleteOnClose)
            self.show_pic_c.setPicture(self.pic_c)
            self.show_pic_c.show()
            self.show_pic_c.raise_()
        log_debug("Received image")

    @property
    def image_list(self):
        '''List of images to paint'''
        return tuple(self._image_list)

    @image_list.setter
    def image_list(self, value):
        value = list(value)
        if self._image_list != value:
            self._image_list = value
            self.ui.imageList.clear()
            for img in value:
                self.ui.imageList.addItem(img)
            self.ui.autoUpdate.setEnabled(True)
            self.ui.zoomIn.setEnabled(True)
            self.ui.zoomOut.setEnabled(True)
            self.ui.zoom1.setEnabled(True)
            self.ui.zoomFit.setEnabled(True)
            self.ui.imageList.setEnabled(True)

    @pyqtSignature("")
    def on_zoomIn_clicked(self):
        self.ui.imageView.scale(2,2)

    @pyqtSignature("")
    def on_zoomOut_clicked(self):
        self.ui.imageView.scale(.5,.5)

    @pyqtSignature("")
    def on_zoom1_clicked(self):
        self.ui.imageView.setTransform(QTransform())

    @pyqtSignature("")
    def on_zoomFit_clicked(self):
        self.ui.imageView.fitInView(QRectF(self.pix.rect()), Qt.KeepAspectRatio)

    @pyqtSignature("")
    def request_render_image(self):
        if self.isVisible():
            if parameters.instance.use_thread:
                self.timer.start()
            else:
                self.render_image()

    @pyqtSignature("")
    def render_image(self):
        if self.isVisible():
            i = self.ui.imageList.currentIndex()
            log_debug("Launch computing for image %d" % i)
            if self.thread.render_single(i) is None:
                QMessageBox.information(self, "Failed rendering image", "The renderer is busy and could not render the image.\nTry again later")
            else:
                self.ui.imageView.setEnabled(False)

    @pyqtSignature("int")
    def on_imageList_currentIndexChanged(self, value):
        self.render_image()

    @pyqtSignature("bool")
    def on_autoUpdate_toggled(self, value):
        self.parent.auto_update = value
        if value:
            self.request_render_image()

    def showEvent(self, event):
        self.render_image()

    def reject(self):
        self.close()

    def closeEvent(self, event):
        self.parent.preview_button.setChecked(False)
        if self.show_pic_w is not None:
            self.show_pic_w.close()
            self.show_pic_w = None
        if self.show_pic_c is not None:
            self.show_pic_c.close()
            self.show_pic_c = None

