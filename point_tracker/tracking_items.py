from __future__ import print_function, division, absolute_import
__author__ = "Pierre Barbier de Reuille <pierre@barbierdereuille.net>"
__docformat__ = "restructuredtext"
from . import parameters
from PyQt4.QtGui import (QPainterPath, QColor, QGraphicsItem, QPen, QPolygonF, QCursor,
        QTransform, QPainterPathStroker)
from PyQt4.QtCore import QPointF, QRectF, Qt, QLineF
from math import cos, pi
from math import hypot as norm
from .geometry import dist, distToPolyLine,  inf
from .debug import log_debug

class OldPointItem(QGraphicsItem):
    def __init__(self, scale, pt_id, parent = None):
        QGraphicsItem.__init__(self, parent)
        self.pt_id = pt_id
        self.scale = scale
        self.setZValue(1)
        #self.setFlag(QGraphicsItem.ItemIgnoresTransformations, True)
        self.setSelectable()
        self.link = None
        self.back_link = None
        self.arrow = None
        self._show_template = False # Are we showing the template *now* ?
        self.hover_template = False
        self.hover = False
        self.setGeometry()

    def setGeometry(self):
        """
        Read the parameters that define the geometry of the point
        """
        params = parameters.instance
        self.prepareGeometryChange()
        size = params.old_point_size
        scale = self.scale
        self.rect = QRectF(-size*scale[0], -size*scale[1], 2*size*scale[0], 2*size*scale[1])

    def removePoint(self):
        scene = self.scene()
        if scene:
            scene.removeItem(self)

    def itemChange(self, change, value):
        if change == QGraphicsItem.ItemSceneChange:
# if the item is removed from the scene ...
            if self.scene():
                if self.arrow:
# I can only remove the target of the arrow ... so I have to remove the source
                    src = self.arrow.source
                    self.arrow.removeArrow()
                    src.removePoint()
                if self.link:
                    self.link.removePoint()
                if self.back_link:
                    self.back_link.link = None
                self.link = self.arrow = self.back_link = None
        elif change == QGraphicsItem.ItemPositionHasChanged:
            pos = self.pos()
            if self.link:
                self.link.setPos(pos)
            if self.arrow:
                self.arrow.updateShape(self, value.toPointF())
        return QGraphicsItem.itemChange(self, change, value)

    def boundingRect(self):
        return self.rect

    def shape(self):
        params = parameters.instance
        path = QPainterPath()
        scale = self.scale
        half_size = params.old_point_size/2.
        path.moveTo(0, -half_size*scale[1])
        path.lineTo(0,  half_size*scale[1])
        path.moveTo(-half_size*scale[0], 0)
        path.lineTo( half_size*scale[0], 0)
        return path

    def paint(self, painter, option, widget):
        params = parameters.instance
        tr = painter.worldMatrix()
        saved = False
        scale = self.scale
        ms = min(scale)
        if tr.m11() < 1/scale[0] or tr.m12() < 1/scale[1]:
            painter.save()
            saved = True
            dx = tr.dx()
            dy = tr.dy()
            painter.setWorldTransform(QTransform(1/scale[0],0,0,1/scale[1],dx,dy))
        if self.hover:
            pen_color = params.old_point_matching_color
        else:
            pen_color = params.old_point_color
        half_size = params.old_point_size/2.
        pen = QPen(pen_color)
        pen.setWidth(params.old_point_thickness*ms)
        painter.setPen(pen)
        painter.drawLine(0, -half_size*scale[1], 0, half_size*scale[1])
        painter.drawLine(-half_size*scale[0], 0, half_size*scale[0], 0)
        if saved:
            painter.restore()

    def setSelectable(self, value=True):
        self.setFlag(QGraphicsItem.ItemIsSelectable, False)
        self.setFlag(QGraphicsItem.ItemIsMovable, False)

class PointItem(QGraphicsItem):
    def __init__(self, scale, pt_id, new = False, cells = (), parent = None):
        QGraphicsItem.__init__(self, parent)
        self.remove_in_all = False
        self.new = new
        self.pt_id = pt_id
        self.scale = scale
        self.setZValue(3)
        self.setAcceptsHoverEvents(True)
        self.setSelectable()
        self.link = None
        self.back_link = None
        self.arrow = None
        self._show_template = False # Are we showing the template *now* ?
        self.hover_template = False
        self.hover = False
        self.setToolTip(unicode(pt_id))
        self.cells = tuple(cells)
        self.setGeometry()
        self.setFlag(QGraphicsItem.ItemSendsGeometryChanges, True)

    def setEditable(self, value=True):
        self.setFlag(QGraphicsItem.ItemIsMovable, value)

    def mousePressEvent(self, event):
        if self.flags() & QGraphicsItem.ItemIsMovable:
            return QGraphicsItem.mousePressEvent(self, event)
        event.ignore()

    def setCells(self, cells):
        self.cells = tuple(cells)

    def setSelectable(self, value=True):
        if value:
            self.setFlag(QGraphicsItem.ItemIsSelectable)
            self.setFlag(QGraphicsItem.ItemIsMovable)
        else:
            self.setFlag(QGraphicsItem.ItemIsSelectable, False)
            self.setFlag(QGraphicsItem.ItemIsMovable, False)

    def setGeometry(self):
        """
        Read the parameters that define the geometry of the point
        """
        params = parameters.instance
        self.setSelectable(params.is_point_selectable)
        self.setEditable(params.is_point_editable)
        self.prepareGeometryChange()
        size = params.point_size
        scale = self.scale
        self.rect = QRectF(-size*scale[0], -size*scale[1], 2*size*scale[0], 2*size*scale[1])
        ts = size/(params.font_zoom)
        self.text_rect = QRectF(-ts*scale[0], -ts*scale[1], 2*ts*scale[0], 2*ts*scale[1])

    def removePoint(self):
        scene = self.scene()
        if scene:
            scene.removeItem(self)

    def itemChange(self, change, value):
        if change == QGraphicsItem.ItemSceneChange:
# if the item is removed from the scene ...
            if self.scene():
                if self.arrow:
# I can only remove the target of the arrow ... so I have to remove the source
                    src = self.arrow.source
                    self.arrow.removeArrow()
                    src.removePoint()
                if self.link:
                    self.link.removePoint()
                if self.back_link:
                    self.back_link.link = None
                self.link = self.arrow = self.back_link = None
        elif change == QGraphicsItem.ItemPositionHasChanged:
            pos = self.pos()
            if self.link:
                self.link.setPos(pos)
            if self.arrow:
                self.arrow.updateShape(self, pos)
            for c in self.cells:
                c.setGeometry()
        return QGraphicsItem.itemChange(self, change, value)

    def hoverEnterEvent(self, event):
        self.hover = True
        if self.link:
            self.link.hover = True
            self.link.update()
        self.update()

    def hoverLeaveEvent(self, event):
        self.hover = False
        if self.link:
            self.link.hover = False
            self.link.update()
        self.update()

    def boundingRect(self):
        return self.rect

    def shape(self):
        path = QPainterPath()
        path.addEllipse(self.rect)
        return path

    def paint(self, painter, option, widget):
        params = parameters.instance
        tr = painter.worldMatrix()
        scale = self.scale
        #ms = min(scale)
        saved = False
        if tr.m11() < 1/scale[0] or tr.m22() < 1/scale[1]:
            saved = True
            painter.save()
            dx = tr.dx()
            dy = tr.dy()
            painter.setWorldTransform(QTransform(1/scale[0],0,0,1/scale[1],dx,dy))
        pen = QPen(QColor(Qt.black))
        pen.setWidth(params.point_thickness)
        painter.setPen(pen)
        if self.isSelected():
            painter.setBrush(params.selected_point_color)
        elif self.new:
            if self.hover:
                painter.setBrush(params.new_point_hover_color)
            else:
                painter.setBrush(params.new_point_color)
        else:
            if self.hover:
                painter.setBrush(params.point_hover_color)
            else:
                painter.setBrush(params.point_color)
        painter.drawEllipse(self.rect)
        if params.show_id:
            painter.setFont(params.font)
            painter.save()
            fz = params.font_zoom
            painter.scale(fz, fz)
            painter.drawText(self.text_rect, Qt.AlignCenter, unicode(self.pt_id))
            painter.restore()
        if saved:
            painter.restore()

class TemplateItem(QGraphicsItem):
    def __init__(self, parent = None):
        QGraphicsItem.__init__(self, parent)
        self.setZValue(5)
        self.setFlags(QGraphicsItem.ItemIsMovable)
        self.setAcceptsHoverEvents(True)
        self.on_search = False
        self.on_template = None
        self.last_pos = None
        self.changing = False
        self.setGeometry()
        #self.setFlag(QGraphicsItem.ItemIgnoresTransformations, True)

    def setGeometry(self):
        params = parameters.instance
        self.prepareGeometryChange()
        ss = params.search_size
        ts = params.template_size
        self.search_size = ss
        self.template_size = ts
        self.search_rect = QRectF(-ss, -ss, 2*ss, 2*ss)
        self.template_rect = QRectF(-ts, -ts, 2*ts, 2*ts)
        ssi = min(0.1*ss, 5)
        if 2*ssi > ss-ts:
            ssi = (ss-ts)/2.
        self.sensitive_size = ssi
        self.sensitive_rect = self.search_rect.adjusted(-ssi,-ssi,ssi,ssi)

    def itemChange(self, change, value):
        if change == QGraphicsItem.ItemPositionChange:
            pos = value.toPointF()
            scene = self.scene()
            if not self.changing and scene is not None:
                self.changing = True
                scene.templatePosChange(pos)
                self.changing = False
        return QGraphicsItem.itemChange(self, change, value)

    def resetCursor(self):
        self.unsetCursor()

    def updateCursor(self, x, y, all_dir):
        if y != 0:
            r = x/y
        else:
            r = 10
        if all_dir:
            if abs(r) > 2:
                self.setCursor(QCursor(Qt.SizeHorCursor))
            elif abs(r) < 0.5:
                self.setCursor(QCursor(Qt.SizeVerCursor))
            elif r < 0:
                self.setCursor(QCursor(Qt.SizeBDiagCursor))
            else:
                self.setCursor(QCursor(Qt.SizeFDiagCursor))
        else:
            if abs(r) > 1:
                self.setCursor(QCursor(Qt.SizeHorCursor))
            else:
                self.setCursor(QCursor(Qt.SizeVerCursor))

    def hoverMoveEvent(self, event):
        pos = event.pos()
        x = pos.x()
        y = pos.y()
        event.accept()
        ss = self.search_size
        ts = self.template_size
        ssi = self.sensitive_size
        #diff = abs(dist_from_center-ss)
        diff = min(abs(abs(x)-ss), abs(abs(y)-ss))
        self.on_template = False
        self.on_search = False
        if diff < ssi:
            self.on_search = True
            self.updateCursor(x,y,True)
            return
        diff = min(abs(abs(x)-ts), abs(abs(y)-ts))
        if diff < ssi:
            self.on_template = True
            self.updateCursor(x,y,False)
            return
        self.resetCursor()

    def mousePressEvent(self, event):
        pos = event.pos()
        x = pos.x()
        y = pos.y()
        if self.on_search:
            self.updateCursor(x,y,True)
            event.accept()
            return
        elif self.on_template:
            self.updateCursor(x,y,False)
            event.accept()
            return
        QGraphicsItem.mousePressEvent(self, event)

    def mouseMoveEvent(self, event):
        params = parameters.instance
        pos = event.pos()
        x = pos.x()
        y = pos.y()
        if self.on_search:
            ns = norm(x,y)
            params.search_size = ns
            self.updateCursor(x,y,True)
            event.accept()
            return
        elif self.on_template:
            ns = max(abs(x), abs(y))
            params.template_size = ns
            self.updateCursor(x,y,False)
            event.accept()
            return
        QGraphicsItem.mouseMoveEvent(self, event)

    def mouseReleaseEvent(self, event):
        pos = event.pos()
        x = pos.x()
        y = pos.y()
        if self.on_search:
            self.updateCursor(x,y,True)
            event.accept()
            return
        elif self.on_template:
            self.updateCursor(x,y,False)
            event.accept()
            return
        QGraphicsItem.mouseReleaseEvent(self, event)

    def boundingRect(self):
        return self.sensitive_rect

    def shape(self):
        shape = QPainterPath()
        shape.addEllipse(self.sensitive_rect)
        return shape

    def paint(self, painter, option, widget):
        params = parameters.instance
        #tr = painter.worldMatrix()
        painter.setPen(QColor(Qt.black))
        painter.setBrush(params.search_color)
        painter.drawRect(params.search_rect)
        #painter.drawEllipse(params.search_rect)
        painter.setBrush(params.template_color)
        painter.drawRect(params.template_rect)

class ArrowItem(QGraphicsItem):
    def __init__(self, scale, source, target, parent = None):
        QGraphicsItem.__init__(self, parent)
        self.source = source
        self.target = target
        self.scale = scale
        self.updateShape()
        self.setZValue(2)
        #self.setFlag(QGraphicsItem.ItemIgnoresTransformations, True)

    def setGeometry(self):
        self.prepareGeometryChange()
        self.updateShape()

    def updateShape(self, point = None, pos = None):
# Main arrow direction
        params = parameters.instance
        scale = self.scale
        ms = min(scale)
        head_size = params.arrow_head_size*ms
        width = params.arrow_line_size*ms
        self.prepareGeometryChange()
        if point == self.source:
            p1 = pos
        else:
            p1 = self.source.pos()
        self.setPos(p1)
        if point == self.target:
            p2 = pos
        else:
            p2 = self.target.pos()
        tip = p2-p1
        if abs(tip.x()) > 0.001 or abs(tip.y()) > 0.001:
# Normalised
            #ntip = tip/stip
            ntip = tip
# Arrow head base
            orth = QPointF(ntip.y(), -ntip.x())*(head_size*0.5)
            base_center = tip*(1-2*head_size)
            base1 = base_center + orth
            base2 = base_center - orth
            base_center = tip*(1-head_size*1.50)
        else:
            ntip = tip
            base_center = tip
            base1 = tip
            base2 = tip

        self.tip = tip
        self.base_center = base_center
        self.base1 = base1
        self.base2 = base2

        path = QPainterPath()
        path.lineTo(base_center)
        path.addPolygon(QPolygonF([base_center, base1, tip, base2]))
        path.closeSubpath()
        self.rect = path.controlPointRect().adjusted(-width, -width, 2*width, 2*width)
        self.path = path
        self.update()

    def boundingRect(self):
        return self.rect

    def shape(self):
        return self.path

    def removeArrow(self):
        scene = self.scene()
        self.source.arrow = None
        self.target.arrow = None
        if scene:
            scene.removeItem(self)

    def paint(self, painter, option, widget):
        params = parameters.instance
        col = QColor(params.arrow_color)
        pen = QPen(col)
        pen.setWidth(params.arrow_line_size)
        painter.setPen(pen)
        painter.setBrush(col)
        painter.drawPath(self.path)

class CellItem(QGraphicsItem):
    """
    Class representing a cell on the screen.
    
    :IVariables:
        cell_id : int
            Identifier of the cell
        hover : bool
            True if the cell is being hovered over
        hover_contour : bool
            True if the contour of the cell is being hovered over
        hover_side : int|None
            Number of the side being hovered over
        sides : list of `QPainterPath`
            shape of each side
        polygon_id : list of int
            list of point ids for the polygon
        walls : `TimedWallShapes`
            Ref to the structure defining the shape of the walls at the current time
        points : dict of int * QPointF
            Ref to the structure holding the position of all the points at the current time
        current : bool
            True if the cell is the currently selected one
        drag_line : bool
            True if one of the side is being dragged
        p1 : int
            Start of a division line
        p2 : int
            End of a division line
    """

    def __init__(self, scale, glob_scale, cell_id, polygon, points, walls, parent = None):
        QGraphicsItem.__init__(self, parent)
        self.cell_id = cell_id
        self.setZValue(2.5)
        self.setAcceptsHoverEvents(True)
        self.setSelectable(False)
        self.setFlag(QGraphicsItem.ItemSendsGeometryChanges, True)
        self.hover = False
        self.hover_contour = False
        self.hover_side = None
        self.scale = scale
        self.glob_scale = glob_scale
        self.setToolTip(unicode(cell_id))
        self.polygon_id = polygon
        self.walls = walls
        self.sides = []
        self.points = points
        self.current = False
        self.drag_line = False
        self.dragging_line = False
        self.editable = False
        self.p1 = None
        self.p2 = None
        self.setGeometry()

    def setCurrent(self, value = True):
        """
        Set this cell as the current one (i.e. on top and different color)
        """
        if value:
            self.setZValue(2.8)
        else:
            self.setZValue(2.5)
        self.current = value
        self.update()

    def setDivisionLine(self, p1, p2):
        """
        Set the line from p1 to p2 to be a division line (i.e. different representation)
        """
        self.p1 = p1
        self.p2 = p2
        self.setGeometry()

    def setGeometry(self):
        """
        Read the parameters that define the geometry of the point
        """
        params = parameters.instance
        self.setEditable(params.is_cell_editable)
        points = self.points
        polygon_id = self.polygon_id
        polygon = [points[pt].pos() if pt in points else None for pt in polygon_id ]
        non_none_cnt = len([p for p in polygon if p is not None])
        if non_none_cnt == 0:
            self.rect = QRectF()
            self.bounding_rect = QRectF()
            self.setVisible(False)
            return
        self.setVisible(True)
# First, check if this is a "simple" cell
        walls = self.walls
        real_polygon = [ pid for pid in polygon_id if pid in points ]
        #sides = [ walls[real_polygon[i], real_polygon[(i+1)%len(real_polygon)]] for i in range(len(real_polygon)) ]
        sides = [None] * len(polygon)
        self.sides = sides
        real_scale_x = self.scale[0]/self.glob_scale
        real_scale_y = self.scale[1]/self.glob_scale
        for i in range(len(polygon)):
            if polygon[i] is not None: # Find the next
                j = (i+1) % len(polygon)
                while polygon[j] is None:
                    j = (j+1) % len(polygon)
                w = [ QPointF(p.x()*real_scale_x, p.y()*real_scale_y) for p in walls[polygon_id[i], polygon_id[j]] ]
                sides[i] = [ polygon[i] ] + w + [ polygon[j] ]
        prev = real_polygon[-1]
        polygon_shape = []
        for i in range(len(polygon)):
            if polygon[i]:
                polygon_shape.append(polygon[i])
                polygon_shape.extend(sides[i])
# Now add the dummy points .. starts at the first non-None point
        if non_none_cnt > 2:
            #print "List of points: [%s]" % ','.join("(%f,%f)"%(p.x(),p.y()) if p is not None else "None" for p in polygon)
            start = None
            for i in range(len(polygon)):
                if polygon[i] is not None:
                    start = i
                    break
            prev = start
            cur = start+1 if start+1 < len(polygon) else 0
            log_debug("Polygon before: [%s]" % ",".join("(%f,%f)" % (p.x(), p.y()) if p is not None else "None" for p in polygon))
            while cur != start:
                if polygon[cur] is None:
                    cnt = 1
                    next = cur+1 if cur+1 < len(polygon) else 0
                    while True:
                        if polygon[next] is None:
                            cnt += 1
                        else:
                            break
                        next += 1
                        if next == len(polygon):
                            next = 0
                    #print "%d points missing" % cnt
                    # First, find total length of wall
                    length = 0.0
                    side = sides[prev]
                    for i in range(len(side)-1):
                        length += dist(side[i], side[i+1])
                    diff = length/(cnt+1) # Distance between two points
                    i = cur
                    p = side[0]
                    for j in range(cnt):
                        l = 0.0
                        found = False
                        for k in range(len(side)-1):
                            dl = dist(side[k], side[k+1])
                            l += dl
                            if l > diff*(1+1e-5): # Account for accumulation of small errors
                                c = (i+j)%len(polygon)
                                delta = diff-l+dl
                                p = side[k] + (side[k+1]-side[k])*delta/dl
                                s1 = side[:k+1] + [p]
                                s2 = [p] + side[k+1:]
                                sides[c-1] = s1
                                sides[c] = s2
                                side = s2
                                polygon[c] = p
                                found = True
                                break
                        assert found, "Could not find point in polygon for position %d" % (j+i,)
                        #p = p + diff
                        #c = (i+j)%len(polygon)
                        #polygon[c] = QPointF(p)
                    cur = next
                else:
                    prev = cur
                    cur += 1
                if cur >= len(polygon):
                    cur = 0
            assert None not in polygon, "Error, some dummy points were not added"
            #print "New list of points: [%s]" % ','.join("(%f,%f)"%(p.x(),p.y()) if p is not None else "None" for p in polygon)
        else:
            polygon = [ p for p in polygon if p is not None ]
        center = sum(polygon, QPointF(0,0)) / float(len(polygon))
        self.center = center
        if len(polygon) > 2:
            polygon = QPolygonF(polygon+[polygon[0]])
            polygon.translate(-center)
            polygon_shape = QPolygonF(polygon_shape + [polygon_shape[0]])
            self.polygon_shape = polygon_shape
            polygon_shape.translate(-center)
            # Translate the sides too
            sides = [ [p-center for p in s] for s in sides ]
            self.sides = sides
            assert len(sides) == len(polygon)-1
        elif len(polygon) == 2:
            polygon = QLineF(polygon[0], polygon[1])
            polygon.translate(-center)
        else:
            polygon = None
        self.polygon = polygon
        self.setPos(center)
        params = parameters.instance
        self.prepareGeometryChange()
        size = params.cell_size
        scale = self.scale
        height = size*cos(pi/6)*scale[1]
        width = size*scale[0]
        pos_x = size*cos(pi/3)*scale[0]
        self.sel_rect = QRectF(-width, -height, 2*width, 2*height)
        if isinstance(polygon, QPolygonF):
            self.rect = self.polygon_shape.boundingRect() | self.sel_rect
        elif isinstance(polygon, QLineF):
            self.rect = QRectF(polygon.p1(), polygon.p2()).normalized() | self.sel_rect
        else:
            self.rect = self.sel_rect
        self.bounding_rect = QRectF(self.rect)
        if self.p1 in points and self.p2 in points:
            self.division_line = QLineF(points[self.p1].pos()-center, points[self.p2].pos()-center)
        else:
            self.division_line = None
        self.hexagon = QPolygonF([QPointF(-width, 0), QPointF(-pos_x, height), QPointF(pos_x, height),
            QPointF(width, 0), QPointF(pos_x, -height), QPointF(-pos_x, -height)])
        self.hexagon_path = QPainterPath()
        self.hexagon_path.addPolygon(self.hexagon)
        s1 = QPainterPath()
        if isinstance(self.polygon, QPolygonF):
            s1.addPolygon(polygon_shape)
        elif isinstance(self.polygon, QLineF):
            s1.moveTo(self.polygon.p1())
            s1.lineTo(self.polygon.p2())
        stroke = QPainterPathStroker()
        sel_thick = 3*params.cell_thickness
        if sel_thick == 0:
            sel_thick = 3
        stroke.setWidth(sel_thick)
        self.stroke = stroke.createStroke(s1)

    def changePoints(self, polygon):
        self.polygon_id = polygon
        self.setGeometry()

    def paint(self, painter, option, widget):
        params = parameters.instance
        pen = QPen(QColor(Qt.black))
        scale = self.scale
        ms = min(scale)
        pen.setWidth(params.cell_thickness)
        sel_thick = 2*params.cell_thickness
        if sel_thick == 0:
            sel_thick = 2*ms
        col = None
        if self.current:
            col = QColor(params.selected_cell_color)
        elif self.hover:
            col = QColor(params.cell_hover_color)
        else:
            col = QColor(params.cell_color)
        painter.setBrush(col)
        if self.hover_contour:
            pen1 = QPen(QColor(Qt.white))
            pen1.setWidth(sel_thick)
            painter.setPen(pen1)
        else:
            painter.setPen(pen)
        if isinstance(self.polygon, QPolygonF):
            painter.drawPolygon(self.polygon_shape)
        elif isinstance(self.polygon, QLineF):
            painter.drawLine(self.polygon)
        pen.setWidth(0)
        painter.setPen(pen)
        painter.drawPolygon(self.hexagon)
        if self.hover_side is not None:
            pen = QPen(QColor(Qt.red))
            pen.setWidth(sel_thick)
            side = self.sides[self.hover_side]
            painter.setPen(pen)
            pp = QPainterPath()
            pp.moveTo(side[0])
            for p in side[1:]:
                pp.lineTo(p)
            painter.drawPath(pp)
        elif self.division_line is not None:
            pen = QPen(params.division_wall_color)
            pen.setWidth(sel_thick)
            painter.setPen(pen)
            painter.drawLine(self.division_line)
        elif self.dragging_line:
            pen = QPen(QColor(Qt.red))
            pen.setWidth(sel_thick)
            painter.setPen(pen)
            polygon = self.polygon
            dg = self.drag_side
            p1 = polygon[dg]
            p2 = polygon[dg+1]
            painter.drawLine(p1, self.moving_point)
            painter.drawLine(self.moving_point, p2)

    def setEditable(self, value):
        self.editable = value

    def boundingRect(self):
        return self.bounding_rect

    def shape(self):
        """
        Returns the shape used for selection
        """
        s = QPainterPath()
        s.addPath(self.hexagon_path)
        if self.editable:
            s.addPath(self.stroke)
        return s

    def setSelectable(self, value=True):
        self.setFlag(QGraphicsItem.ItemIsSelectable, value)
        self.setFlag(QGraphicsItem.ItemIsMovable, True)

    def findClosestSide(self, pos):
        """
        Find the side of the polygon closest to pos
        """
        polygon = self.polygon
        min_dist = inf
        min_side = None
        if isinstance(polygon, QLineF):
            min_side = 0
            min_dist = 0
        else:
            #pos = pos + self.center
            sides = self.sides
            assert len(sides) == len(polygon)-1
            for i in range(len(polygon)-1):
                side = sides[i]
                d = distToPolyLine(pos,  side)
                if d <min_dist:
                    min_dist = d
                    min_side = i
        #print "Closest side found = %d, with distance = %f"%(min_side,  min_dist)
        return min_side, min_dist

    def findHover(self, pos):
        """
        Find which side is being hovered over
        """
        if self.editable:
            if self.drag_line:
                self.hover = False
                self.hover_side = None
                self.hover_contour = False
            elif self.hexagon_path.contains(pos):
                self.hover = True
                self.hover_side = None
                self.hover_contour = False
            else:
                params = parameters.instance
                sel_thick = 3*params.cell_thickness
                if sel_thick == 0:
                    sel_thick = 3
                self.hover_contour = True
                self.hover = False
                polygon = self.polygon
                if isinstance(polygon, QPolygonF):
                    min_side, min_dist = self.findClosestSide(pos)
                    #print "Closest side = %d"%min_side
                    if min_dist < sel_thick and min_side is not None:
                        self.hover_side = min_side
                    else:
                        self.hover_side = None
                        self.hover_contour = False
                        self.hover = True
        else:
            self.hover = True
            self.hover_side = None
            self.hover_contour = False

    def hoverEnterEvent(self, event):
        self.findHover(event.pos())
        self.update()

    def hoverMoveEvent(self, event):
        self.findHover(event.pos())
        self.update()

    def hoverLeaveEvent(self, event):
        self.hover = False
        self.hover_contour = False
        self.hover_side = None
        self.update()

    def mousePressEvent(self, event):
        if self.hover_side is not None:
            moving_point = QPointF(event.pos())
            self.drag_side = self.hover_side
            #self.polygon.insert(self.hover_side+1, moving_point)
            #self.sides[self.hover_side] = [self.polygon[self.hover_side], self.polygon[self.hover_side+1]]
            #self.sides.insert(self.hover_side+1, [self.polygon[self.hover_side+1], self.polygon[self.hover_side+2]])
            self.moving_point = moving_point
            self.start_drag = event.screenPos()
            self.hover_contour = False
            self.hover_side = None
            self.drag_line = True
            self.dragging_line = False
            self.update()
            event.accept()
        else:
            event.ignore()
            QGraphicsItem.mousePressEvent(self, event)

    def mouseMoveEvent(self, event):
        if not self.dragging_line and self.drag_line and (self.start_drag - event.screenPos()).manhattanLength() > 5:
            self.dragging_line = True
        if self.dragging_line:
            params = parameters.instance
            ms = min(self.scale)
            sel_thick = 2*params.cell_thickness
            if sel_thick == 0:
                sel_thick = 2*ms
            self.prepareGeometryChange()
            mp = self.moving_point
            mp.setX(event.pos().x())
            mp.setY(event.pos().y())
            self.bounding_rect = self.rect | QRectF(mp.x()-sel_thick,
                                                    mp.y()-sel_thick,
                                                    2*sel_thick,
                                                    2*sel_thick)
            self.update()

    def mouseReleaseEvent(self, event):
        if self.dragging_line:
            print("Adding point to cell")
            self.setGeometry()
            drag_side = (self.drag_side+1) % (len(self.polygon)-1)
            self.scene().addPointToCell(self.cell_id, drag_side, self.mapToScene(event.pos()))
        else:
            event.ignore()
            QGraphicsItem.mouseReleaseEvent(self, event)
        self.drag_line = False
        self.dragging_line = False
