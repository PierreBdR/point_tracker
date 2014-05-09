from __future__ import print_function, division, absolute_import
__author__ = "Pierre Barbier de Reuille <pierre@barbierdereuille.net>"
__docformat__ = "restructuredtext"

from PyQt4.QtGui import (QGraphicsScene, QPixmap, QKeySequence, QPainterPath, QDialog,
        QColor, QProgressDialog, QCursor, QGraphicsView, QTransform, QMenu, QBrush)
from PyQt4.QtCore import QPointF, QObject, SIGNAL, QRectF, Qt, pyqtSignature
from .algo import findTemplate
from . import image_cache
from .tracking_undo import (AddPoints, RemovePoints, MovePoints, RemovePointsInAllImages, RemovePointsFromImage,
        RemovePointsToImage, AddCellCommand, RemoveCellsCommand, ChangeCellCommand, DivideCellCommand,
        InsertPointInWallCommand)
from . import parameters
from .tracking_items import PointItem, OldPointItem, ArrowItem, TemplateItem, CellItem
from .geometry import makeStarShaped
from .debug import log_debug
from .sys_utils import createForm
from .tracking_data import EndOfTime

current_id = -1

class TrackingScene(QGraphicsScene):
    """
    Signals:
      - hasSelection(bool)
      - realSceneSizeChanged
    """

    Pan = "Pan"
    Add = "Add"
    Move = "Move"
    ZoomIn = "ZoomIn"
    ZoomOut = "ZoomOut"
    AddCell = "AddCell"
    RemoveCell = "RemoveCell"

    modes = [Pan, Add, Move, AddCell, RemoveCell, ZoomIn, ZoomOut]

    def __init__(self, undo_stack, delete_act, sel_actions, *args):
        """
        Constructor
        """
        params = parameters.instance
        QGraphicsScene.__init__(self, *args)
        self.delete_act = delete_act
        self.undo_stack = undo_stack
        self.data_manager = None
        self._mode = None
        self.link = None
        self.image_path = None
        self.image_name = None
        self.background_image = None
        self.template = TemplateItem()
        self.template.setPos(QPointF(0,0))
        self.template.setVisible(params.show_template)
        self.show_template = False
        self.points = {}
        self.cells = {}
        self._real_scene_rect = QRectF()
        QObject.connect(params, SIGNAL("pointParameterChange"), self.updatePoints)
        QObject.connect(params, SIGNAL("cellParameterChange"), self.updateCells)
        QObject.connect(params, SIGNAL("searchParameterChange"), self.updateTemplate)
        self.had_selection = None
        QObject.connect(self, SIGNAL("selectionChanged()"), self.updateSelectionActions)
        self.current_data = None
        self.back_matrix = QTransform()
        self.invert_back_matrix = QTransform()
        self.clear()
        popup = QMenu("Scene menu")
        validate_cell_act = popup.addAction("Validate cell", self.validateCell)
        validate_cell_act.setVisible(False)
        self._validate_cell_act = validate_cell_act
        lifespan_act = popup.addAction("Change cell lifespan", self.changeLifespan)
        lifespan_act.setVisible(False)
        self.lifespan_act = lifespan_act
        make_starshape_act = popup.addAction("Make cell star shaped", self.makeCellStarshaped)
        make_starshape_act.setVisible(False)
        self.make_starshape_act = make_starshape_act
        sel = popup.addMenu("Selection")
        for act in sel_actions:
            if act == "-":
                sel.addSeparator()
            else:
                sel.addAction(act)
        popup.addAction(delete_act)
        self._popup = popup
        self._sel_rect = None
        self._sel_first_pt = None
        self._current_cell = None
        self._first_point = None
        self.mode = TrackingScene.Pan

    def __del__(self):
        QObject.disconnect(self, SIGNAL("selectionChanged()"), self.updateSelectionActions)

    def hasSelection(self):
        """
        Returns true if any item is selected
        """
        for pt in self.items():
            if isinstance(pt, PointItem) and pt.isSelected():
                return True
        return False

    def updateSelectionActions(self):
        """
        Slot called when the selection changed. May emit the signal `hasSelection(bool)`
        """
        try:
            value = self.hasSelection()
            if value != self.had_selection:
                self.had_selection = value
                self.emit(SIGNAL("hasSelection(bool)"), value)
        except:
            pass

    def _has_current_cell(self):
        return self._current_cell is not None

    has_current_cell = property(_has_current_cell)

    def _get_current_cell(self):
        """
        Get the current edited cell.

        If needed the cell will be created when accessed
        """
        if self._current_cell is None:
            self._current_cell = self.data_manager.createNewCell()
        return self._current_cell

    def _set_current_cell(self, value):
        if value != self._current_cell and self._current_cell in self.cells:
            self.cells[self._current_cell].setCurrent(False)
        if value in self.cells:
            self._current_cell = value
            self.cells[value].setCurrent()

    def _del_current_cell(self):
        if self._current_cell in self.cells:
            self.cells[self._current_cell].setCurrent(False)
        self._current_cell = None

    current_cell = property(_get_current_cell, _set_current_cell, _del_current_cell)

    def _get_selected_cell(self):
        if self._current_cell is not None and self._current_cell not in self.cells:
            self._current_cell = None
        return self._current_cell

    selected_cell = property(_get_selected_cell, _set_current_cell, _del_current_cell)

    def updatePoints(self):
        for p in self.items():
            if isinstance(p, PointItem):
                p.setGeometry()
        self.update()

    def updateCells(self):
        for c in self.cells.values():
            c.setGeometry()
            c.update()
        self.update()

    def selectedPoints(self):
        return [ it for it in self.selectedItems() if isinstance(it, PointItem) ]

    def selectedCells(self):
        return [ it for it in self.selectedItems() if isinstance(it, CellItem) ]

    def mousePressEvent(self, event):
        if event.buttons() == Qt.LeftButton:
            global current_id
            current_id += 1
            if self.mode == TrackingScene.Add:
                event.accept()
                if self.image_name is not None:
                    pos = event.scenePos()*self.min_scale
                    self.planAddPoints(None, [pos])
            elif self.mode == TrackingScene.ZoomOut:
                event.accept()
                self.emit(SIGNAL("ZoomOut"), event.scenePos())
            elif self.mode == TrackingScene.ZoomIn:
                event.accept()
                self.emit(SIGNAL("ZoomIn"), event.scenePos())
            elif self.mode == TrackingScene.AddCell:
                for item in self.items(event.scenePos()):
                    if isinstance(item, CellItem):
                        if item.hover:
                            if self.has_current_cell and item.cell_id == self.current_cell:
                                del self.current_cell
                            else:
                                self.current_cell = item.cell_id
                            event.accept()
                            return
                QGraphicsScene.mousePressEvent(self, event)
            elif self.mode == TrackingScene.RemoveCell:
                remove_cell = None
                for item in self.items(event.scenePos()):
                    if isinstance(item, CellItem):
                        remove_cell = item.cell_id
                        break
                if remove_cell is not None:
                    self.planRemoveCells([remove_cell])
            else:
                QGraphicsScene.mousePressEvent(self, event)
        else:
            QGraphicsScene.mousePressEvent(self, event)

    def contextMenuEvent(self, event):
        cell_under = None
        for it in self.items(event.scenePos()):
            if isinstance(it, CellItem):
                cell_under = it.cell_id
                break
        self._cell_under = cell_under
        if cell_under is not None:
            self.make_starshape_act.setVisible(True)
            self.lifespan_act.setVisible(True)
        else:
            self.make_starshape_act.setVisible(False)
            self.lifespan_act.setVisible(False)
        self._popup.popup(event.screenPos())

    def planAddPoints(self, pt_ids, poss):
        self.undo_stack.push(AddPoints(self.data_manager, self.image_name, pt_ids, poss))

    def planMovePoints(self, pt_ids, new_poss, starts=None):
        self.undo_stack.push(MovePoints(self.data_manager, self.image_name, pt_ids, new_poss, starts = starts))

    def planRemovePoints(self, pt_ids):
        self.undo_stack.push(RemovePoints(self.data_manager, self.image_name, pt_ids))

    def planAddCell(self, cell_id, pt_ids):
        log_debug("Planning adding cell %d" % cell_id)
        self.undo_stack.push(AddCellCommand(self.data_manager, cell_id, pt_ids))

    def planChangeCell(self, cell_id, pt_ids, lifespan = None):
        log_debug("Planning change cell %d" % cell_id)
        self.undo_stack.push(ChangeCellCommand(self.data_manager, cell_id, pt_ids, lifespan))

    def planInsertPointInWall(self, new_pt, wall):
        log_debug("Planning insert point %d in wall (%d,%d)" % ((new_pt,)+wall))
        self.undo_stack.push(InsertPointInWallCommand(self.data_manager, new_pt, wall))

    def planDivideCell(self, cell_id, cid1, cid2, p1, p2):
        log_debug("Planning divide cell %d into %d and %d" % (cell_id, cid1, cid2))
        self.undo_stack.push(DivideCellCommand(self.data_manager, self.image_name, cell_id, cid1, cid2, p1, p2))

    def planRemoveCells(self, cell_ids):
        log_debug("Planning remove cells %s" % ", ".join("%d"%c for c in cell_ids))
        self.undo_stack.push(RemoveCellsCommand(self.data_manager, cell_ids))

    def mouseReleaseEvent(self, event):
        items = self.getSelected()
        if items:
            starts = []
            ends = []
            moved_ids = []
            data = self.current_data
            #pt_scale = (self.scale[0]/self.img_scale[0], self.scale[1]/self.scale[1])
            for item in items:
                pos = item.pos()*self.min_scale
                old_pos = data[item.pt_id]
                if pos != old_pos:
                    moved_ids.append(item.pt_id)
                    starts.append(old_pos)
                    ends.append(pos)
            if moved_ids:
                self.planMovePoints(moved_ids, ends, starts)
        elif self.mode == TrackingScene.AddCell:
            QGraphicsScene.mouseReleaseEvent(self, event)
            if event.isAccepted():
                return
            items = self.items(event.scenePos())
            if items:
                pt = items[0]
                if isinstance(pt, PointItem):
                    pt_id = pt.pt_id
                    cells = self.current_data.cells
                    if self.has_current_cell:
                        cid = self.current_cell
                        cell_shape = list(cells[cid])
                        if pt_id in cell_shape:
                            cell_shape.remove(pt_id)
                            self.planChangeCell(cid, cell_shape)
                        else:
                            cell_shape.append(pt_id)
                            self.planChangeCell(cid, cell_shape)
                    else:
                        cid = self.current_cell
                        cell_shape = [pt_id]
                        self.planAddCell(cid, cell_shape)
            return
        QGraphicsScene.mouseReleaseEvent(self, event)

    def setPointCellSelection(self, region):
        add_pts = []
        remove_pts = []
        items = [ p.pt_id for p in self.items(region) if isinstance(p, PointItem) ]
        if items:
            #print "New cell with: %s" % (items,)
            cells = self.current_data.cells
            cell = self.current_cell
            cell_points = []
            if cell in cells:
                cell_points = list(cells[cell])
            for pt_id in items:
                if pt_id in cell_points:
                    remove_pts.append(pt_id)
                else:
                    add_pts.append(pt_id)
            for pt_id in remove_pts:
                cell_points.remove(pt_id)
            cell_points += add_pts
            cell_points = makeStarShaped(cell_points, self.current_data)
            if cell in cells:
                self.planChangeCell(cell, cell_points)
            else:
                #print "Adding cell %d with %s" % (cell, cell_points)
                self.planAddCell(cell, cell_points)

    def setDivisionLine(self, first_point, second_point):
        dm = self.data_manager
        cid1 = dm.createNewCell()
        cid2 = dm.createNewCell()
        self.planDivideCell(self.current_cell, cid1, cid2, first_point.pt_id, second_point.pt_id)

    def changeLifespan(self):
        cid = self._cell_under
        ls = self.data_manager.lifespan(cid)
        dlg = createForm("lifespan.ui", None)
        self.lifespan_dlg = dlg
        images = QStringList(self.data_manager.images_name)
        images << "End Of Time"
        dlg.images = images
        assert ls.end < len(images) or ls.end == EndOfTime()
        dlg.start_index = ls.start
        if ls.end == EndOfTime():
            dlg.end_index = -1
        else:
            dlg.end_index = ls.end - ls.start
        dlg.startImages.addItems(images[:ls.end])
        dlg.endImages.addItems(images[ls.start:])
        dlg.startImages.setCurrentIndex(ls.start)
        if dlg.end_index != -1:
            dlg.endImages.setCurrentIndex(dlg.end_index)
        else:
            dlg.endImages.setCurrentIndex(dlg.endImages.count()-1)
        dlg.connect(dlg.startImages, SIGNAL("currentIndexChanged(int)"), self.updateLifepsanEndImages)
        dlg.connect(dlg.endImages, SIGNAL("currentIndexChanged(int)"), self.updateLifepsanStartImages)
        if ls.parent is not None:
            dlg.created.setChecked(True)
        if ls.daughters is not None:
            dlg.divides.setChecked(True)
        if dlg.exec_() == QDialog.Accepted:
            new_ls = ls.copy()
            new_ls.start = dlg.start_index
            if dlg.end_index == -1:
                new_ls.end = EndOfTime()
            else:
                new_ls.end = dlg.end_index + dlg.start_index
            log_debug("Change lifespan of cell %d to %s" % (cid, new_ls))
            self.planChangeCell(cid, self.data_manager.cells[cid], new_ls)

    @pyqtSignature("int")
    def updateLifepsanEndImages(self, new_idx):
        dlg = self.lifespan_dlg
        start_idx = dlg.start_index
        if start_idx != new_idx:
            dlg.disconnect(dlg.endImages, SIGNAL("currentIndexChanged(int)"), self.updateLifepsanStartImages)
            dlg.endImages.clear()
            dlg.endImages.addItems(dlg.images[new_idx:])
            if dlg.end_index != -1:
                dlg.end_index += start_idx - new_idx
                dlg.endImages.setCurrentIndex(dlg.end_index)
            else:
                dlg.endImages.setCurrentIndex(dlg.endImages.count()-1)
            dlg.start_index = new_idx
            dlg.connect(dlg.endImages, SIGNAL("currentIndexChanged(int)"), self.updateLifepsanStartImages)

    @pyqtSignature("int")
    def updateLifepsanStartImages(self, new_idx):
        dlg = self.lifespan_dlg
        start_idx = dlg.start_index
        end_idx = dlg.end_index
        if end_idx == -1:
            end_idx = dlg.endImages.count()-1
        if new_idx != end_idx:
            dlg.disconnect(dlg.startImages, SIGNAL("currentIndexChanged(int)"), self.updateLifepsanEndImages)
            dlg.startImages.clear()
            dlg.startImages.addItems(dlg.images[:new_idx+start_idx])
            dlg.startImages.setCurrentIndex(dlg.start_index)
            if new_idx == dlg.endImages.count()-1:
                dlg.end_index = -1
            else:
                dlg.end_index = new_idx
            dlg.connect(dlg.startImages, SIGNAL("currentIndexChanged(int)"), self.updateLifepsanEndImages)

    def makeCellStarshaped(self):
        cid = self._cell_under
        pts = self.current_data.cells[cid]
        #pts = self.makeStarShaped(pts)
        pts = makeStarShaped(pts, self.current_data)
        self.planChangeCell(cid, pts)

    #def makeStarShaped(self, pts):
    #    if len(pts) > 2:
    #        points = self.points
    #        coords = [ points[pt_id].pos() for pt_id in pts ]
    #        center = sum(coords, QPointF())/len(coords)
    #        ref = coords[0] - center
    #        angles = [ angle(ref, p-center) for p in coords ]
    #        to_sort = range(len(angles))
    #        to_sort.sort(key=lambda k:angles[k])
    #        return [ pts[i] for i in to_sort ]
    #    else:
    #        return pts

    def addPointToCell(self, cid, side, pt):
        pts = [ p.pt_id for p in self.items(pt) if isinstance(p, PointItem) ]
        if pts:
            data = self.data_manager
            pt_id = pts[0]
            #print "Add point %d to cell %d in side %d" % (pt_id, cid, side)
            cell_points = list(self.current_data.cells[cid])
            prev_pt = cell_points[side-1]
            next_pt = cell_points[side]
            self.planInsertPointInWall(pt_id, data.wallId(prev_pt, next_pt))

    def clearItems(self):
        for it in self.items():
            if isinstance(it, PointItem) or isinstance(it, OldPointItem):
                it.removePoint()
            elif isinstance(it, ArrowItem):
                it.removeArrow()
            else:
                self.removeItem(it)
        self.points.clear()
        self.cells.clear()
        self.addItem(self.template)

    def clear(self):
        self.clearItems()
        if self.data_manager is not None:
            data_manager = self.data_manager
            QObject.disconnect(data_manager, SIGNAL("pointsAdded"), self.addPoints)
            QObject.disconnect(data_manager, SIGNAL("pointsMoved"), self.movePoints)
            QObject.disconnect(data_manager, SIGNAL("pointsDeleted"), self.delPoints)
            QObject.disconnect(data_manager, SIGNAL("imageMoved"), self.moveImage)
            QObject.disconnect(data_manager, SIGNAL("dataChanged"), self.dataChanged)
            QObject.disconnect(data_manager, SIGNAL("cellsAdded"), self.addCells)
            QObject.disconnect(data_manager, SIGNAL("cellsRemoved"), self.removeCells)
            QObject.disconnect(data_manager, SIGNAL("cellsChanged"), self.changeCells)
        self.current_data = None
        self.data_manager = None
        self.image_path = None

    def changeDataManager(self, data_manager):
        self.clear()
        self.data_manager = data_manager
        self.min_scale = 1.0
        self.scale = (1.0, 1.0)
        QObject.connect(data_manager, SIGNAL("pointsAdded"), self.addPoints)
        QObject.connect(data_manager, SIGNAL("pointsMoved"), self.movePoints)
        QObject.connect(data_manager, SIGNAL("pointsDeleted"), self.delPoints)
        QObject.connect(data_manager, SIGNAL("dataChanged"), self.dataChanged)
        QObject.connect(data_manager, SIGNAL("imageMoved"), self.moveImage)
        QObject.connect(data_manager, SIGNAL("cellsAdded"), self.addCells)
        QObject.connect(data_manager, SIGNAL("cellsRemoved"), self.removeCells)
        QObject.connect(data_manager, SIGNAL("cellsChanged"), self.changeCells)

    def moveImage(self, image_name, scale, pos, angle):
        if image_name == self.image_name:
            self.setImageMove(scale, pos, angle)
            self.updateElements()
            self.invalidate()
            self.update()

    def updateElements(self):
        for pt in self.items():
            pt.scale = self.img_scale
            pt.setGeometry()

    def setImageMove(self, scale, pos, angle):
        log_debug("New scale = %s" % (scale,))
        self.scale = scale
        self.min_scale = self.data_manager.minScale()
        self.img_scale = (scale[0]/self.min_scale, scale[1]/self.min_scale)
        back_matrix = QTransform()
        back_matrix.scale(*self.img_scale)
        back_matrix.translate(pos.x(), pos.y())
        back_matrix.rotate(angle)
        self.back_matrix = back_matrix
        rect = back_matrix.mapRect(QRectF(self.background_image.rect()))
        inv, ok = back_matrix.inverted()
        if not ok:
            raise ValueError("The movement is not invertible !?!")
        self.invert_back_matrix = inv
        self.real_scene_rect = rect

    def _get_real_scene_rect(self):
        '''Real size of the scene'''
        return self._real_scene_rect

    def _set_real_scene_rect(self, value):
        if self._real_scene_rect != value:
            self._real_scene_rect = value
            self.emit(SIGNAL("realSceneSizeChanged"))

    real_scene_rect = property(_get_real_scene_rect, _set_real_scene_rect)

    def changeImage(self, image_path):
        log_debug("Changed image to {0}".format(image_path))
        if image_path is None:
            image_path = self.image_path
        if image_path is None:
            return
        image_name = image_path.basename()
        self.image_name = image_name
        self.current_data = self.data_manager[image_name]
        current_data = self.current_data
        self.clearItems()
        self.image_path = image_path
        img = image_cache.cache.image(image_path)
        self.background_image = img
        pos = current_data.shift[0]
        angle = current_data.shift[1]
        scale = current_data.scale
        log_debug('Scale of image "%s": %s' % (image_name, scale))
        self.setImageMove(scale, pos, angle)
        self.invalidate()
        for pt_id in current_data:
            self.addPoint(pt_id, current_data[pt_id], new=False)
        cells = self.current_data.cells
        log_debug("Found {0} cells".format(len(cells)))
        if cells:
            self.addCells(list(cells.keys()))
        del self.current_cell
        self.setTemplatePos()

    def dataChanged(self, image_name):
        if image_name == self.image_name:
            self.current_data = self.data_manager[image_name]

    def drawBackground(self, painter, rect):
        painter.fillRect(rect, QBrush(QColor(0,0,0)))
        if self.background_image:
            #bm = self.back_matrix
            #log_debug("m = [%g %g ; %g %g ]" % (bm.m11(), bm.m12(), bm.m21(), bm.m22()))
            painter.setWorldTransform(self.back_matrix, True)
            #real_rect = self.invert_back_matrix.mapRect(rect)
            #rect = self.back_matrix.mapRect(real_rect)
            #painter.drawImage(rect,self.background_image, real_rect)
            painter.drawImage(QPointF(0,0), self.background_image)

    def drawForeground(self, painter, rect):
        QGraphicsScene.drawForeground(self, painter, rect)

    def _addPoint(self, pt_id, pos, new):
        point = PointItem(self.img_scale, pt_id, new=new)
        point.setSelected(new)
        self.addItem(point)
        self.points[pt_id] = point
        point.setPos(QPointF(pos.x()/self.min_scale, pos.y()/self.min_scale))
        return point

    def addPoint(self, pt_id, pos, new=True):
        point = self._addPoint(pt_id, pos, new)
        if self.link is not None and pt_id in self.link.points:
            self.link.linkPoint(point, self.link.points[pt_id])
        cell_points = self.data_manager.cell_points
        cells = self.cells
        cs = [ cells[cid] for cid in cell_points[pt_id] if cid in cells ]
        point.setCells(cs)
        return point

    def addPoints(self, image_name, pt_ids):
        #print "TrackingScene - Adding points [%s]" % ','.join('%d' % c for c in pt_ids)
        if image_name == self.image_name:
            #print "... in this image!"
            data = self.current_data
            dm = self.data_manager
            cells = self.cells
            for pt_id in pt_ids:
                pt = self.addPoint(pt_id, data[pt_id], new=True)
                pt.setCells([cells[cid] for cid in dm.cell_points[pt_id] if cid in cells])
            cids = set(cid for pt_id in pt_ids for cid in dm.cell_points[pt_id])
            cells_to_add = []
            for cid in cids:
                if cid in cells:
                    cells[cid].setGeometry()
                else:
                    cells_to_add.append(cid)
            if cells_to_add:
                self.addCells(cells_to_add)

    def delPoint(self, point):
        del self.points[point.pt_id]
        point.removePoint()

    def delPoints(self, image_name, pt_ids):
        if image_name == self.image_name:
            dm = self.data_manager
            cells = self.cells
            for pt_id in pt_ids:
                self.delPoint(self.points[pt_id])
                for cid in dm.cell_points[pt_id]:
                    cell = cells.get(cid, None)
                    if cell is not None:
                        cells[cid].setGeometry()

    def movePoints(self, image_name, pt_ids):
        if image_name == self.image_name:
            data = self.current_data
            dm = self.data_manager
            points = self.points
            cells = self.cells
            for pt_id in pt_ids:
                pos = data[pt_id]
                pos = QPointF(pos.x() / self.min_scale, pos.y() / self.min_scale)
                points[pt_id].setPos(pos)
                for cid in dm.cell_points[pt_id]:
                    cell = cells.get(cid, None)
                    if cell is not None and cell.isVisible():
                        cell.setGeometry()

    def addCells(self, cell_ids, image_list = None):
        log_debug("addCell signal with images: (%s,%s)" % (cell_ids, image_list))
        if image_list is not None:
            used_ids = []
            used_il = []
            for cid, il in zip(cell_ids, image_list):
                if il is None or self.image_name in il:
                    used_ids.append(cid)
                    used_il = il
            if not used_ids:
                log_debug("Current image is: '%s' and is not in any of the lists" % self.image_name)
                return
            cell_ids = used_ids
            image_list = used_il
        log_debug("Adding cells %s to image %s" % (','.join("%d" % c for c in cell_ids), self.image_name))
        data = self.data_manager
        current_data = self.current_data
        cell_ids = [ cid for cid in cell_ids if cid in current_data.cells ]
        log_debug("cell_ids = %s" % (cell_ids,))
        points = self.points
        cells = self.cells
        cell_points = data.cell_points
        for cid in cell_ids:
            if cid in cells or not [pid for pid in current_data.cells[cid] if pid in current_data]:
                continue
            log_debug("-- Add cell %d with points %s" % (cid, current_data.cells[cid]))
            ci = CellItem(self.img_scale, self.min_scale, cid, current_data.cells[cid], points, current_data.walls)
            self.addItem(ci)
            cells[cid] = ci
            ci.setEditable(self.mode == TrackingScene.AddCell)
            if self.has_current_cell and cid == self.current_cell:
                ci.setCurrent()
            pid = data.cells_lifespan[cid].parent
            if pid is not None:
                ls = data.cells_lifespan[pid]
                if data.images_name[ls.end] == self.image_name:
                    div_line = ls.division
                    ci.setDivisionLine(div_line[0], div_line[1])
        for cid in cell_ids:
            for pid in current_data.cells[cid]:
                if pid in points:
                    pt = points[pid]
                    pt.setCells(cells[i] for i in cell_points[pid] if i in cells)

    def removeCells(self, cell_ids, image_list = None):
        log_debug("removeCells signal with images: (%s,%s)" % (cell_ids, image_list))
        if image_list is not None:
            used_ids = []
            used_il = []
            for cid, il in zip(cell_ids, image_list):
                if il is None or self.image_name in il:
                    used_ids.append(cid)
                    used_il = il
            if not used_ids:
                log_debug("Current image is: '%s' and is not in any of the lists" % self.image_name)
                return
            cell_ids = used_ids
            image_list = used_il
        log_debug("Removing cells %s to image %s" % (','.join("%d" % c for c in cell_ids), self.image_name))
        if self.has_current_cell and self.current_cell in cell_ids:
            del self.current_cell
        cells = self.cells
        for cid in cell_ids:
            cell = cells.get(cid, None)
            if cell is not None:
                self.removeItem(cell)
                del self.cells[cid]

    def changeCells(self, cell_ids):
        #print "TrackingScene - Changing cells: [%s]" % ','.join("%d" % c for c in cell_ids)
        log_debug("Change cells %s in image %s" % (','.join("%d" % c for c in cell_ids), self.image_name))
        data = self.data_manager
        current_data = self.current_data
        cell_ids = [ cid for cid in cell_ids if cid in current_data.cells ]
        points = self.points
        cells = self.cells
        for cid in cell_ids:
            ci = cells.get(cid, None)
            if ci is not None:
                ci.changePoints(current_data.cells[cid])
                for pid in current_data.cells[cid]:
                    if pid in points:
                        pt = points[pid]
                        pt.setCells(cells[i] for i in data.cell_points[pid] if i in cells)
                pid = data.cells_lifespan[cid].parent
                if pid is not None:
                    ls = data.cells_lifespan[pid]
                    if data.images_name[ls.end] == self.image_name:
                        div_line = ls.division
                        ci.setDivisionLine(div_line[0], div_line[1])

    def pointMoved(self, pt_id, start_pos, end_pos):
        self.planMovePoints([pt_id], [end_pos], starts = [start_pos])

    def selectNew(self):
        for it in self.points.es():
            it.setSelected(it.new)

    def selectAll(self):
        for it in self.points.values():
            it.setSelected(True)

    def selectNone(self):
        for it in self.points.values():
            it.setSelected(False)

    def selectInvert(self):
        for it in self.points.values():
            it.setSelected(not it.isSelected())

    def selectNonAssociated(self):
        for it in self.points.values():
            if it.arrow is None and it.link is None:
                it.setSelected(True)
            else:
                it.setSelected(False)

    def selectAssociated(self):
        for it in self.points.values():
            if it.arrow is None and it.link is None:
                it.setSelected(False)
            else:
                it.setSelected(True)

    def getSelected(self):
        return [ pt for pt in self.points.values() if pt.isSelected() ]

    def getSelectedIds(self):
        return [ pt.pt_id for pt in self.points.values() if pt.isSelected() ]

    def getAllItems(self):
        return self.points.values()

    def getAllIds(self):
        return self.points.keys()

    def _get_mode(self):
        """
        Mouse interaction mode
        """
        return self._mode

    def _set_pan_view(self, view):
        view.setInteractive(True)
        view.setCursor(Qt.ArrowCursor)
        view.setDragMode(QGraphicsView.ScrollHandDrag)

    def _set_select_view(self, view):
        view.setInteractive(True)
        view.setDragMode(QGraphicsView.RubberBandDrag)
        view.setCursor(Qt.PointingHandCursor)

    def _set_add_view(self, view):
        view.setInteractive(True)
        view.setDragMode(QGraphicsView.NoDrag)
        view.setCursor(Qt.CrossCursor)

    def _set_zoomin_view(self, view):
        view.setInteractive(True)
        view.setDragMode(QGraphicsView.NoDrag)
        view.setCursor(QCursor(QPixmap(":/icons/gtk-zoom-in.png")))

    def _set_zoomout_view(self, view):
        view.setInteractive(True)
        view.setDragMode(QGraphicsView.NoDrag)
        view.setCursor(QCursor(QPixmap(":/icons/gtk-zoom-out.png")))

    def _set_pan(self):
        params = parameters.instance
        del self.current_cell
        self._validate_cell_act.setVisible(False)
        params.is_point_selectable = False
        params.is_point_editable = False
        params.is_cell_editable = False

    def _set_normal(self):
        params = parameters.instance
        del self.current_cell
        self._validate_cell_act.setVisible(False)
        params.is_point_selectable = True
        params.is_point_editable = True
        params.is_cell_editable = False

    def _set_cell_view(self, view):
        view.setInteractive(True)
        view.setCursor(Qt.ArrowCursor)
        view.setDragMode(QGraphicsView.NoDrag)

    def _set_add_cell(self):
        params = parameters.instance
        self._validate_cell_act.setVisible(True)
        params.is_point_selectable = True
        params.is_point_editable = False
        params.is_cell_editable = True

    def _set_remove_cell(self):
        params = parameters.instance
        del self.current_cell
        self._validate_cell_act.setVisible(False)
        params.is_point_selectable = False
        params.is_point_editable = False
        params.is_cell_editable = False

    _init_view = { Pan: (_set_pan_view, _set_pan),
                   Move: (_set_select_view, _set_normal),
                   Add: (_set_add_view, _set_normal),
                   AddCell: (_set_cell_view, _set_add_cell),
                   RemoveCell: (_set_cell_view, _set_remove_cell),
                   ZoomIn: (_set_zoomin_view, _set_normal),
                   ZoomOut: (_set_zoomout_view, _set_normal) }

    def _set_mode(self, new_mode):
        if new_mode in TrackingScene.modes:
            if new_mode != self._mode:
                log_debug("Changed mode to %s" % new_mode)
                self._mode = new_mode
                fct_view, fct = self._init_view[new_mode]
                fct(self)
                for v in self.views():
                    fct_view(self, v)

    mode = property(_get_mode, _set_mode)

    def validateCell(self):
        del self.current_cell

    def keyPressEvent(self, event):
        if event.matches(QKeySequence.Delete):
            if self.mode == TrackingScene.RemoveCell:
                c_ids = []
                for item in self.selectedCells():
                    c_ids = item.cell_id
                if c_ids:
                    self.planRemoveCells(c_ids)
            elif self.mode != TrackingScene.AddCell:
                pt_ids = []
                for item in self.selectedPoints():
                    pt_ids.append(item.pt_id)
                if pt_ids:
                    self.planRemovePoints(pt_ids)
        elif event.key() == Qt.Key_Delete and event.modifiers() | Qt.ShiftModifier:
            self.delete_act.trigger()
        elif event.matches(QKeySequence.ZoomIn):
            self.emit(SIGNAL("ZoomIn"))
        elif event.matches(QKeySequence.ZoomOut):
            self.emit(SIGNAL("ZoomOut"))
        elif event.matches(QKeySequence.SelectAll):
            path = QPainterPath()
            path.addRect(self.sceneRect())
            self.setSelectionArea(path)

    def setSelectedIds(self, ids):
        for it in self.points.values():
            it.setSelected(False)
        for id in ids:
            it = self.points.get(id)
            if it:
                it.setSelected(True)

    def deleteInAllImages(self):
        if self.mode == TrackingScene.RemoveCell:
            c_ids = []
            for item in self.selectedCells():
                c_ids.append(item.cell_id)
            if c_ids:
                self.planRemoveCells(c_ids)
        else:
            pt_ids = []
            for item in self.selectedPoints():
                pt_ids.append(item.pt_id)
            if pt_ids:
                self.undo_stack.push(RemovePointsInAllImages(self.data_manager, self.image_name, pt_ids))

    def deleteFromImage(self):
        if self.mode == TrackingScene.RemoveCell:
            c_ids = []
            for item in self.selectedCells():
                c_ids.append(item.cell_id)
            if c_ids:
                self.planRemoveCells(c_ids)
        else:
            pt_ids = []
            for item in self.selectedPoints():
                pt_ids.append(item.pt_id)
            if pt_ids:
                self.undo_stack.push(RemovePointsFromImage(self.data_manager, self.image_name, pt_ids))

    def deleteToImage(self):
        if self.mode == TrackingScene.RemoveCell:
            c_ids = []
            for item in self.selectedCells():
                c_ids.append(item.cell_id)
            if c_ids:
                self.planRemoveCells(c_ids)
        else:
            pt_ids = []
            for item in self.selectedPoints():
                pt_ids.append(item.pt_id)
            if pt_ids:
                self.undo_stack.push(RemovePointsToImage(self.data_manager, self.image_name, pt_ids))

    def findPoint(self, im1, im2, other, point):
        params = parameters.instance
        ppos = self.current_data[point.pt_id]
        pos = self.invert_back_matrix.map(ppos)
        npos = other.invert_back_matrix.map(ppos)
        pos = (int(pos.x()), int(pos.y()))
        npos = (int(npos.x()), int(npos.y()))
        size = (params.template_size, params.template_size)
        search_size = (params.search_size, params.search_size)
        new_pos, value = findTemplate(im1, pos, size, npos, search_size, im2)
        if value < 0.5:
            return ppos
        p = QPointF(new_pos[0],new_pos[1])*self.min_scale
        return other.back_matrix.map(p)

    def transferPoints(self, other):
        params = parameters.instance
        current_data = self.current_data
        items = self.selectedItems()
        if len(items) == 0:
            items = [ it for it in self.points.values() if it.arrow is None and it.link is None ]
        new_pt_ids = []
        new_pt_pos = []
        move_pt_ids = []
        move_pt_new_pos = []
        if params.estimate:
            progress = QProgressDialog("Estimating position of the points...", "Abort", 0, len(items), self.parent())
            progress.setMinimumDuration(1)
            size = (params.filter_size,params.filter_size)
            im1 = image_cache.cache.numpy_array(self.image_path, size)
            im2 = image_cache.cache.numpy_array(other.image_path, size)
            for i, it in enumerate(items):
                pos = self.findPoint(im1, im2, other, it)
                id = it.pt_id
                if id in other.points:
                    move_pt_ids.append(id)
                    move_pt_new_pos.append(pos)
                else:
                    new_pt_ids.append(id)
                    new_pt_pos.append(pos)
                progress.setValue(i+1)
                if progress.wasCanceled():
                    progress.hide()
                    break
        else:
            for it in items:
                id = it.pt_id
                pos = current_data[id]
                if id in other.points:
                    move_pt_ids.append(id)
                    move_pt_new_pos.append(pos)
                else:
                    new_pt_ids.append(id)
                    new_pt_pos.append(pos)
        if new_pt_ids or move_pt_ids:
            self.undo_stack.beginMacro("Transfer point(s) from %s to %s" % (self.image_name, other.image_name))
            if new_pt_ids:
                other.planAddPoints(new_pt_ids, new_pt_pos)
            if move_pt_ids:
                other.planMovePoints(move_pt_ids, move_pt_new_pos)
            self.undo_stack.endMacro()

    def copyToLinked(self, linked):
        self.transferPoints(linked)

    def setTemplatePos(self, pos = None):
        if pos is None:
            views = self.views()
            if len(views) > 0:
                view = views[0]
                pos = view.mapToScene(view.rect().center())
        if pos is not None:
            self.template.setPos(pos)

    def showTemplates(self, value = True):
        params = parameters.instance
        self.show_template = value
        if not params.show_template:
            if value:
                self.template.setGeometry()
                self.template.setVisible(True)
                self.setTemplatePos()
            else:
                self.template.setVisible(False)

    def updateTemplate(self):
        params = parameters.instance
        if params.show_template or self.show_template:
            self.template.setGeometry()
            if not self.template.isVisible():
                self.template.setVisible(True)
                self.setTemplatePos()
        else:
            self.template.setVisible(False)
        self.update()

    def templatePosChange(self, pos):
        self.emit(SIGNAL("templatePosChange"), pos)

    def resetNewPoints(self):
        for items in self.points.values():
            items.new = False
        self.update()

class LinkedTrackingScene(TrackingScene):
    def __init__(self, link, *args):
        TrackingScene.__init__(self, *args)
        self._show_vector = True
        self.link = link
        self.link.link = self
        params = parameters.instance
        QObject.connect(params, SIGNAL("oldPointParameterChange"), self.updateOldPoints)
        QObject.connect(params, SIGNAL("arrowParameterChange"), self.updateArrows)

    def linkPoint(self, link, point):
        if point.arrow is None:
            old_point = OldPointItem(self.img_scale, link.pt_id)
            old_point.setPos(link.pos())
            self.addItem(old_point)
            link.link = old_point
            old_point.back_link = link
            arrow = ArrowItem(self.img_scale, old_point, point)
            arrow.setVisible(self._show_vector)
            old_point.arrow = arrow
            point.arrow = arrow
            self.addItem(arrow)
        else:
            point.arrow.updateShape()

    def addPoint(self, pt_id, pos, new=True):
        point = self._addPoint(pt_id, pos, new)
        if pt_id in self.link.points:
            self.linkPoint(self.link.points[pt_id], point)
        return point

    def copyFromLinked(self, previous):
        self.transferPoints(previous)

    def showVector(self, value):
        self._show_vector = value
        for i in self.items():
            if isinstance(i, ArrowItem):
                i.setVisible(value)

    def updateOldPoints(self):
        for p in self.items():
            if isinstance(p, OldPointItem):
                p.setGeometry()
        self.update()

    def updateArrows(self):
        for a in self.items():
            if isinstance(a, ArrowItem):
                a.updateShape()
        self.update()

