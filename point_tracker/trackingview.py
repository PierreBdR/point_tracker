from __future__ import print_function, division, absolute_import
__author__ = "Pierre Barbier de Reuille <pierre@barbierdereuille.net>"
__docformat__ = "restructuredtext"
from PyQt4.QtGui import (QGraphicsView, QApplication, QStyleOptionRubberBand, QRubberBand,
        QStyleHintReturnMask, QStyle, QRegion, QPen)
from PyQt4.QtCore import Qt, QRect, QPoint, QLine
from .tracking_scene import TrackingScene
from .tracking_items import PointItem
from . import parameters

class TrackingView(QGraphicsView):
    def __init__(self, *args):
        QGraphicsView.__init__(self, *args)
        self._sel_rect = QRect()
        self._start_selection = None
        self._start_sel = False
        self._sel_accepted = False
        self._first_point = None
        self._second_point = None
        self._div_accepted = False
        self._div_line = QLine()

    def rubberBandRegion(self, rect):
        viewport = self.viewport()
        mask = QStyleHintReturnMask()
        option = QStyleOptionRubberBand()
        option.initFrom(viewport)
        option.rect = rect
        option.opaque = False
        option.shape = QRubberBand.Rectangle
        tmp = QRegion()
        tmp += rect
        if viewport.style().styleHint(QStyle.SH_RubberBand_Mask, option, viewport, mask):
            tmp &= mask.region
        return tmp

    def lineSelectionRect(self, line):
        rect = QRect(line.p1(), line.p2()).normalized()
        if rect.isValid():
            rect.adjust(-2, -2, 2, 2)
        return rect

    def mousePressEvent(self, event):
        scene = self.scene()
        if not isinstance(scene, TrackingScene):
            return QGraphicsView.mousePressEvent(self, event)
        QGraphicsView.mousePressEvent(self, event)
        if not event.isAccepted():
            if scene.mode == TrackingScene.AddCell and event.buttons() == Qt.LeftButton:
                event.accept()
                self._start_selection = QPoint(event.pos())
                if scene.has_current_cell:
                    items = scene.items(self.mapToScene(event.pos()))
                    try:
                        first_point = items[0]
                        if isinstance(first_point, PointItem) and first_point.pt_id in scene.data_manager.cells[scene.current_cell]:
                            self._first_point = first_point
                            params = parameters.instance
                            params.is_cell_editable = False
                            return
                    except IndexError:
                        pass
                self._start_sel = True

    def mouseMoveEvent(self, event):
        if self._start_sel:
            if self._sel_accepted or (event.pos() - self._start_selection).manhattanLength() >= QApplication.startDragDistance():
                scene = self.scene()
                self._sel_accepted = True
                event.accept()
                viewport = self.viewport()
                viewport.update(self.rubberBandRegion(self._sel_rect))
                new_rect = QRect(self._start_selection, event.pos()).normalized()
                viewport.update(self.rubberBandRegion(new_rect))
                self._sel_rect = new_rect
                scene_poly = self.mapToScene(new_rect)
                for it in scene.items():
                    it.setSelected(False)
                for it in scene.items(scene_poly):
                    it.setSelected(True)
                return
        elif self._first_point is not None:
            if self._div_accepted or (event.pos() - self._start_selection).manhattanLength() >= QApplication.startDragDistance():
                scene = self.scene()
                self._div_accepted = True
                event.accept()
                viewport = self.viewport()
                if not self._div_line.isNull():
                    viewport.update(self.lineSelectionRect(self._div_line))
                first_point = self._first_point
                first_pos = self.mapFromScene(first_point.pos())
                new_line = QLine(first_pos, event.pos())
                viewport.update(self.lineSelectionRect(new_line))
                self._div_line = new_line
                scene_pos = self.mapToScene(event.pos())
                if self._second_point is not None:
                    self._second_point.setSelected(False)
                    self._second_point = None
                for it in scene.items(scene_pos):
                    if isinstance(it, PointItem) and it.pt_id in scene.data_manager.cells[scene.current_cell]:
                        it.setSelected(True)
                        self._second_point = it
                return
        QGraphicsView.mouseMoveEvent(self, event)

    def mouseReleaseEvent(self, event):
        if self._start_sel:
            self._start_sel = False
            if self._sel_accepted:
                self.viewport().update(self.rubberBandRegion(self._sel_rect))
                sceneRegion = self.mapToScene(self._sel_rect)
                self._sel_accepted = False
                self._sel_rect = QRect()
                event.accept()
                if self.scene():
                    self.scene().setPointCellSelection(sceneRegion)
                return
        elif self._first_point is not None:
            scene = self.scene()
            div_accepted = self._div_accepted
            if div_accepted:
                event.accept()
                self.viewport().update(self.lineSelectionRect(self._div_line))
                if self._second_point is not None:
                    scene.setDivisionLine(self._first_point, self._second_point)
                    self._second_point.setSelected(False)
            self._first_point = None
            self._second_point = None
            self._div_line = QLine()
            self._div_accepted = False
            params = parameters.instance
            params.is_cell_editable = True
            if div_accepted:
                return
        QGraphicsView.mouseReleaseEvent(self, event)

    def drawForeground(self, painter, rect):
        QGraphicsView.drawForeground(self, painter, rect)
        if self._sel_accepted:
            painter.save()
            painter.resetTransform()
            rect = self._sel_rect
            viewport = self.viewport()
            option = QStyleOptionRubberBand()
            option.initFrom(viewport)
            option.rect = self._sel_rect
            option.shape = QRubberBand.Rectangle
            mask = QStyleHintReturnMask()
            self.style().drawControl(QStyle.CE_RubberBand, option, painter, viewport);
            painter.restore()
        elif self._div_accepted:
            painter.save()
            painter.resetTransform()
            line = self._div_line
            viewport = self.viewport()
            palette = viewport.palette()
            pen = QPen(Qt.DashDotLine)
            pen.setWidth(2)
            pen.setColor(Qt.red)
            painter.setPen(pen)
            painter.drawLine(self._div_line)
            painter.restore()

