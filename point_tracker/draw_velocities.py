from __future__ import print_function, division, absolute_import
"""
:newfield signal: Signal, Signals
"""
__author__ = "Pierre Barbier de Reuille <pierre@barbierdereuille.net>"
__docformat__ = "restructuredtext"

from PyQt4.QtCore import QObject, Qt, QPointF
from PyQt4.QtGui import QPen, QBrush, QColor, QPolygonF
from math import sqrt
from geometry import length
import parameters
from plottingdlg import PlottingDlg
import tracking as src_tracking
from .debug import log_error
from .sys_utils import cleanQObject

class DrawVelocities(QObject):
    def __init__(self, result, result_type, forward = True):
        QObject.__init__(self)
        self.result = result
        self.result_type = result_type
        if result_type == "Data":
            self.data = result
            self.image_list = result.images_name
            if forward:
                self.images = result.images_name[:-1]
            else:
                self.images = result.images_name[1:]
            self.forward = forward
        else:
            self.data = result.data
            self.image_list = result.images_used
            self.images = result.images
            self.forward = (self.image_list[0] == self.images[0])
# Find maximum velocity
        image_list = self.image_list
        data = self.data
        max_v = 0
        for i,image_id in enumerate(image_list[:-1]):
            next_image_id = image_list[i+1]
            d1 = data[image_id]
            d2 = data[next_image_id]
            dt = d2.time - d1.time
            for pt_id in d1:
                if pt_id in d2:
                    v = (d2[pt_id] - d1[pt_id]) / dt
                    vl = length(v)
                    if vl > max_v:
                        max_v = vl
        self.max_velocity = max_v
        self.factor = 0.5
        params = parameters.instance
        self.color = params.arrow_color
        self.head_size = params.arrow_head_size
        self.line_width = self.data.minScale()*params.arrow_line_size

    def __del__(self):
        cleanQObject(self)

    def startImage(self, painter, imageid):
        pass

    def finalizeImage(self, painter, imageid, tr, crop):
        pass

    def __call__(self, painter, imageid):
        if imageid == len(self.images):
            return
        head_size = self.head_size
        color = self.color
        line_width = self.line_width
        max_velocity = self.max_velocity
        forward = self.forward
        img1 = self.image_list[imageid]
        img2 = self.image_list[imageid+1]
        d1 = self.data[img1]
        d2 = self.data[img2]
        dt = d2.time - d1.time
        pen = QPen(color)
        pen.setWidthF(line_width)
        brush = QBrush(color)
        painter.setPen(pen)
        painter.setBrush(brush)
        for pt_id in d1:
            if pt_id in d2:
                p = d1[pt_id] if self.forward else d2[pt_id]
                v = (d2[pt_id] - d1[pt_id]) / dt * self.factor
                vl = length(v)
                if abs(vl / max_velocity) > 1e-3:
                    self.drawArrow(painter, p, v, head_size)

    def drawArrow(self, painter, p, v, head_size):
        base = p-v
        tip = p+v
        painter.drawLine(base, tip)

        vl = length(v)
        nv = v / vl
        head_size = head_size * vl

        orth = QPointF(nv.y(), -nv.x())*head_size
        base_center = tip-nv*head_size*2.0
        base1 = base_center + orth
        base2 = base_center - orth
        base_center = tip-nv*head_size*1.0

        painter.drawPolygon(QPolygonF([base_center, base1, tip, base2]))

def draw_velocities(color = None, head_size = None, factor = None):
    main_window = src_tracking.main_window
    dlg = main_window.current_dlg
    if not isinstance(dlg, PlottingDlg):
        log_error("The current opened dialog box is not the tissue drawing one")
    result = dlg.thread.result
    if result is None:
        log_error("You haven't loaded any data")
    result_type = dlg.thread.result_type
    dv = DrawVelocities(result, result_type)
    if color is not None:
        dv.color = QColor(color)
    if head_size is not None:
        dv.head_size = float(head_size)
    if factor is not None:
        dv.factor = factor
    extraDrawing = dlg.thread.extraDrawing
    for i,ed in enumerate(extraDrawing):
        if isinstance(ed, DrawVelocities):
            extraDrawing[i] = dv
            break
    else:
        extraDrawing.append(dv)

