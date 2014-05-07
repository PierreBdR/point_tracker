__author__ = "Pierre Barbier de Reuille <pbdr@uea.ac.uk>"
__docformat__ = "restructuredtext"
from PyQt4 import QtGui, QtCore
#from transferfunction import TransferFunction
from math import log
from itertools import chain
from editmarkersdlg import EditMarkersDlg


def invalid(r,g,b,a):
    return r < 0 or r > 1 or g < 0 or g > 1 or b < 0 or b > 1 or a < 0 or a > 1

class QTransferFunctionViewer(QtGui.QWidget):
    def __init__(self, *args):
        QtGui.QWidget.__init__(self, *args)
        self._transfer_fct = None
        self.transfer_fct = None
        self._histogram = None
        self._nb_values = 2
        self._hist_values = None
        self._use_histogram = True
        self._stickers = []
        self._sticking = False
        self.marker_size = 5 # Size of the marker for color positions
        self.current_pos = None # Position selected
# Create background brush pixmap
        self.bg_size = 20
        self.bg_bright = 150
        self.bg_dark = 100
        self.setEnabled(True)
        self.setFocusPolicy(QtCore.Qt.ClickFocus)
        self.setMouseTracking(True)
        self.activ_pos_color = QtGui.QColor(200, 200, 200, 200)
        self.createBackground()
        self.saved_color = None
        self.saved_pos = None
        self.edit_color = False
        self.reverse_act = QtGui.QAction("Reverse function", self)
        self.reverse_act.triggered.connect(self.reverseFunction)
        self.edit_markers = QtGui.QAction("Edit markers", self)
        self.edit_markers.triggered.connect(self.editMarkers)
        self.addAction(self.reverse_act)
        self.addAction(self.edit_markers)
        self.setContextMenuPolicy(QtCore.Qt.ActionsContextMenu)

    def createBackground(self, type = "checks"):
        pal = QtGui.QPalette()
        if type == "white":
            pal.setColor(self.backgroundRole(), QtGui.QColor(QtCore.Qt.white))
        elif type == "black":
            pal.setColor(self.backgroundRole(), QtGui.QColor(QtCore.Qt.black))
        else:
            bg_pix = self.createChecks()
            pal.setBrush(self.backgroundRole(), QtGui.QBrush(bg_pix))
        self.setPalette(pal)

    def createChecks( self ):
        size = self.bg_size
        bright = self.bg_bright
        dark = self.bg_dark
        bg_pix = QtGui.QPixmap(2*size, 2*size)
        bg_pix.fill(QtGui.QColor(bright, bright, bright))
        paint_bg = QtGui.QPainter(bg_pix)
        paint_bg.setPen(QtCore.Qt.NoPen)
        paint_bg.setBrush(QtGui.QColor(dark, dark, dark))
        paint_bg.drawRect(0, size, size, size)
        paint_bg.drawRect(size, 0, size, size)
        return bg_pix

    def _SetHistogram(self, histogram):
        if self._histogram is histogram:
            return
        self._histogram = histogram
        if histogram is not None:
            self.prepareHistogram()
            self.setupGradient()

    def _GetHistogram(self):
        return self._histogram

    histogram = property(_GetHistogram, _SetHistogram)

    def _SetUseHistogram(self, value):
        value = bool(value)
        if value is self._use_histogram:
            return
        self._use_histogram = value
        if not value:
            self.setupGradient()

    def _GetUseHistogram(self):
        return self._use_histogram

    use_histogram = property(_GetUseHistogram, _SetUseHistogram)

    def _GetStickers(self):
        return tuple(self._stickers)

    def _SetStickers(self, value):
        value = list(float(v) for v in value)
        value.sort()
        if value != self._stickers:
            self._stickers = value

    stickers = property(_GetStickers, _SetStickers)

    def _GetNbValues(self):
        if self._use_histogram:
            return self._nb_values
        else:
            return 256

    def _SetNbValues(self, value):
        value = int(value)
        self._nb_values = value

    nb_values = property(_GetNbValues, _SetNbValues)

    def _SetTransferFct(self, map):
        if map is self._transfer_fct:
            return
        if self._transfer_fct is not None:
            QtCore.QObject.disconnect(self._transfer_fct, QtCore.SIGNAL("changed()"), self.update)
        self._transfer_fct = map
        if map is not None:
            QtCore.QObject.connect(self._transfer_fct, QtCore.SIGNAL("changed()"), self.update)
        if not self.use_histogram or self._hist_values:
            self.setupGradient()
        self.update()

    def _GetTransferFct(self):
        return self._transfer_fct

    transfer_fct = property(_GetTransferFct, _SetTransferFct)

    @QtCore.pyqtSignature("")
    def setupGradient(self):
        transfer_fct = self.transfer_fct
        if transfer_fct is None or (self.use_histogram and not self._hist_values):
            self.gradient = None
            return
        brush_color = QtGui.QColor()
        gr = QtGui.QLinearGradient(QtCore.QPointF(0, 0), QtCore.QPointF(1, 0))
        n = float(self.nb_values-1)
        for i in xrange(self.nb_values):
            brush_color.setRgbF(*transfer_fct.rgba(i/n))
            gr.setColorAt(i/n, brush_color)
        self.gradient = gr

    def paintEvent(self, event):
        transfer_fct = self.transfer_fct
        if transfer_fct is None or (self.use_histogram and self._hist_values is None):
            return
        w = float(self.width())
        h = float(self.height())
        painter = QtGui.QPainter(self)
        n = float(self.nb_values)-1
        dx = w/n
        painter.setPen(QtCore.Qt.NoPen)
        gr = self.gradient
        if gr is not None:
            painter.setBrush(gr)
            painter.scale(w,h)
            gr.setFinalStop(1, 0)
            if self.use_histogram:
                shape = self.hist_shape
                painter.drawPath(shape)
            else:
                painter.drawRect(QtCore.QRect(0,0,1,1))
            painter.scale(1./w,1./h)

        painter.setBrush(QtGui.QColor(QtCore.Qt.black))
        painter.setPen(QtGui.QColor(QtCore.Qt.black))
        marker_size = self.marker_size-1
        tr = QtGui.QPolygonF(3)
        tr[0] = QtCore.QPointF(-marker_size, 0)
        tr[1] = QtCore.QPointF(0, marker_size)
        tr[2] = QtCore.QPointF(marker_size, 0)
        for pos in transfer_fct:
            pos_tr = QtGui.QPolygonF(tr)
            pos_tr.translate(w*pos, 0)
            painter.drawConvexPolygon(pos_tr)
        painter.setBrush(QtGui.QColor(QtCore.Qt.white))
        for pos in self.stickers:
            pos_tr = QtGui.QPolygonF(tr)
            pos_tr.translate(w*pos, 0)
            painter.drawConvexPolygon(pos_tr)
        if self.current_pos is not None:
            x = self.current_pos * w
            painter.setPen(self.activ_pos_color)
            painter.drawLine(x, marker_size+1, x, h)

    def prepareHistogram(self):
        histogram = self.histogram
        nb_values = len(histogram)
        hist_values = [0]*nb_values
        self.nb_values = nb_values
        min_value = histogram[0]
        max_value = 0
        for v in histogram:
            if 0 < v < min_value:
                min_value = v
            if v > max_value:
                max_value = v
        log_max = log(max_value)
        log_min = log(min_value)-1
        log_delta = log_max - log_min
        for i in xrange(0, nb_values):
            value = float(histogram[i])
            if value > 0:
                value = (log(value) - log_min) / log_delta
            hist_values[i] = value
        self._hist_values = hist_values
        shape = QtGui.QPainterPath(QtCore.QPointF(0,1))
        dx = 1.0/(nb_values-1)
        for i,v in enumerate(hist_values):
            x = i*dx
            y = 1-v
            shape.lineTo(x, y)
        shape.lineTo(1,1)
        shape.lineTo(0,1)
        self.hist_shape = shape
        self.update()
        
    def reverseFunction(self):
        self.transfer_fct.reverse()
        self.setupGradient()
        
    def editMarkers(self):
        dlg = EditMarkersDlg(self.transfer_fct, self)
        if dlg.exec_() == QtGui.QDialog.Accepted:
            self.transfer_fct.point_list = dlg.point_list
            self.setupGradient()

    def mouseDoubleClickEvent(self, event):
        if (self.use_histogram and self._hist_values is None) or event.button() != QtCore.Qt.LeftButton:
            QtGui.QWidget.mouseDoubleClickEvent(self, event)
            return
        w = float(self.width())
        h = self.height()
        marker_size = self.marker_size
        for pos in chain(self.transfer_fct, self.stickers):
            x = pos*w
            if abs(event.x() - x) < marker_size:
                self.current_pos = pos
                event.accept()
                self.update(x-marker_size, 0, x+marker_size, h)
                break
        pos = event.x() / w
        if self.current_pos is not None:
            pos = self.current_pos
        col = self.transfer_fct.rgba(pos)
        qcol = QtGui.QColor.fromRgbF(col[0], col[1], col[2], col[3])
        self.edit_color = True
        qcol = QtGui.QColorDialog.getColor(qcol, self, "Change color", QtGui.QColorDialog.ShowAlphaChannel)
        self.edit_color = False
        self.current_pos = None
        if qcol.isValid():
            self.transfer_fct.add_rgba_point(pos, qcol.redF(), qcol.greenF(),
                    qcol.blueF(), qcol.alphaF())
            self.emit(QtCore.SIGNAL("slowChange"))
            self.setupGradient()

    def mousePressEvent(self, event):
        if (self.use_histogram and self._hist_values is None) or event.button() != QtCore.Qt.LeftButton:
            QtGui.QWidget.mousePressEvent(self, event)
            return
        w = self.width()
        h = self.height()
        marker_size = self.marker_size
        best_dist = w
        best_pos = None
        for pos in self.transfer_fct:
            x = pos*w
            dist = abs(event.x() - x)
            if dist < marker_size and dist < best_dist:
                best_pos = pos
                best_dist = dist
        if best_pos is not None:
                self.current_pos = best_pos
                event.accept()
                x = best_pos*w
                self.update(x-marker_size, 0, x+marker_size, h)
                return
        self.current_pos = None

    def mouseReleaseEvent(self, event):
        self.current_pos = None
        self.saved_color = None
        self.saved_pos = None
        self.setupGradient()
        self.update()
        self.emit(QtCore.SIGNAL("slowChange"))

    def mouseMoveEvent(self, event):
        cpos = self.current_pos
        if event.y() < 0 or event.y() >= self.height():
            if cpos is None:
                return
            self.saved_color = self.transfer_fct.rgba_point(cpos)
            self.saved_pos = cpos
            self.transfer_fct.remove_point(cpos)
            self.current_pos = None
            self.setupGradient()
            return
        if cpos is None:
            if self.saved_pos is None:
                return
            cpos = self.saved_pos
            self.transfer_fct.add_rgba_point( cpos, *self.saved_color )
            self.saved_pos = None
            self.saved_color = None
            self.setupGradient()
        if 0 < cpos < 1:
            transfer_fct = self.transfer_fct
            new_pos = float(event.x())/self.width()
            dp = 1.0/self.width()
            if new_pos < cpos:
                ppos = transfer_fct.prev_pos(cpos)
                if new_pos <= ppos:
                    new_pos = ppos+dp
            elif new_pos > cpos:
                npos = transfer_fct.next_pos(cpos)
                if new_pos >= npos:
                    new_pos = npos-dp
            else:
                self.current_pos = cpos
                return # i.e. no movement
            if self._sticking:
                dm = 20*dp
                if abs(new_pos-cpos) < dm:
                    self.current_pos = cpos
                    return # i.e. no movement
                self._sticking = False
            for s in self.stickers:
                if (cpos-s)*(new_pos-s) < 0 or new_pos == s:
                    self._sticking = True
                    new_pos = s
                    break
            self.current_pos = new_pos
            transfer_fct.move_point(cpos, new_pos)
            self.setupGradient()

