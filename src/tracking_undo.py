__author__ = "Pierre Barbier de Reuille <pbdr@uea.ac.uk>"
__docformat__ = "restructuredtext"
from PyQt4.QtGui import QUndoCommand, QMessageBox
from PyQt4.QtCore import QPointF
from itertools import izip
from tracking_data import LifeSpan
from debug import print_debug

class TrackingCommand(QUndoCommand):
    def __init__(self, text, cmd_id, parent):
        QUndoCommand.__init__(self, text, parent)
        self._id = cmd_id

    def id(self):
        return int(self._id)

class PointsCommand(TrackingCommand):
    def __init__(self, text, data_manager, image_name, cmd_id=-1, parent=None):
        TrackingCommand.__init__(self, text, cmd_id, parent)
        self.data_manager = data_manager
        self.image_name = image_name
        self.current_data = data_manager[image_name]

class MovePoints(PointsCommand):
    def __init__(self, data_manager, image_name, pts_id, ends, cmd_id=-1, parent = None, starts = None):
        PointsCommand.__init__(self, "Move point(s) in image %s" % image_name, data_manager, image_name, cmd_id, parent)
        if starts is None:
            data = self.current_data
            self.move = dict((pt_id,(data[pt_id],end)) for pt_id,end in izip(pts_id, ends))
        else:
            self.move = dict((pt_id,(start,end)) for pt_id,start,end in izip(pts_id, starts, ends))

    def undo(self):
        data = self.current_data
        for pt_id, mvt in self.move.iteritems():
            data[pt_id] = mvt[0]

    def redo(self):
        data = self.current_data
        for pt_id, mvt in self.move.iteritems():
            data[pt_id] = mvt[1]

def cellsToWatch(data, pts_id):
    """
    :returns: A dictionnary of the cells to watch with their current state
    :returntype: dict of int*(list of int, `tracking_data.LifeSpan`)
    """
    cells = data.cells
    cells_lifespan = data.cells_lifespan
    watching_cells = {}
    for pt_id in pts_id:
        watching_cells.update((cid,(cells[cid],cells_lifespan[cid])) for cid in data.cell_points[pt_id])
    return watching_cells

def wallsToWatch(data, pts_id):
    """
    :returns: A dictionnary of the walls to watch with their current shape
    :returntype: dict of (int,int)*(list of (float,list of QPointF))
    """
    walls = data.walls
    watching_walls = {}
    wall_sets = {}
    for time,img_data in enumerate(data):
        walls = data.walls[time]
        for i1,i2 in walls:
            wall_sets.setdefault(i1, {}).setdefault(i2, []).append(time)
            wall_sets.setdefault(i2, {}).setdefault(i1, []).append(time)
    for pt_id in pts_id:
        ws = wall_sets.get(pt_id, None)
        if ws is not None:
            for i2 in ws:
                times = ws[i2]
                if pt_id < i2:
                    i1 = pt_id
                else:
                    i1,i2 = i2,pt_id
                for time in times:
                    watching_walls[time,i1,i2] = walls[time,i1,i2]
    return watching_walls

def modifiedCells(data, watching_cells):
    """
    Check if any of the cells watched were modified

    :returns: a tuple containing: the cells modified, their old content, their old life span
    :returntype: (tuple of int, tuple of (list of int), tuple of `tracking_data.LifeSpan`)
    """
    modified_cells = []
    cells = data.cells
    for cid in watching_cells:
        if cid not in cells or watching_cells[cid][0] != cells[cid]:
            modified_cells.append((cid,)+ watching_cells[cid])
    return zip(*modified_cells)

class RemovePoints(PointsCommand):
    def __init__(self, data_manager, image_name, pts_id, cmd_id=-1, parent = None):
        PointsCommand.__init__(self, "Remove point(s) from image %s" % image_name, data_manager, image_name, cmd_id, parent)
        data = self.current_data
        self.points = dict((pt_id, data[pt_id]) for pt_id in pts_id)
        self.watching_cells = cellsToWatch(data_manager, pts_id)
        self.first_run = True

    def undo(self):
        data = self.current_data
        points = self.points
        for pt in points:
            data[pt] = points[pt]
        if self.modified_cells:
            self.data_manager.setCells(*self.modified_cells)

    def redo(self):
        data = self.current_data
        points = self.points
        for pt in points:
            del data[pt]
        if self.first_run:
            self.first_run = False
            self.modified_cells = modifiedCells(self.data_manager, self.watching_cells)

class RemovePointsInImages(PointsCommand):
    def __init__(self, title, data_manager, image_name, pts_id, image_list, cmd_id=-1, parent = None):
        PointsCommand.__init__(self, title, data_manager, image_name, cmd_id, parent)
        self.pts_id = pts_id
        self.images = [ [im for im in image_list if pt in data_manager[im]] for pt in pts_id ]
        self.pos = [ [ data_manager[im][pt] for im in img] for img,pt in izip(self.images, pts_id) ]
        self.watching_cells = cellsToWatch(data_manager, pts_id)
        #self.watching_walls = wallsToWatch(data_manager, pts_id)
        self.first_run = True

    def undo(self):
        data = self.data_manager
        for img,pt,poss in izip(self.images,self.pts_id,self.pos):
            for image,pos in izip(img,poss):
                data[image][pt] = pos
        if self.modified_cells:
            data.setCells(*self.modified_cells)

    def redo(self):
        data = self.data_manager
        self.presence = {}
        for imgs,pt in izip(self.images,self.pts_id):
            for image in imgs:
                del data[image][pt]
        if self.first_run:
            self.first_run = False
            self.modified_cells = modifiedCells(data, self.watching_cells)

class RemovePointsInAllImages(RemovePointsInImages):
    def __init__(self, data_manager, image_name, pts_id, cmd_id=-1, parent = None):
        images = data_manager.images_name
        RemovePointsInImages.__init__(self, "Remove point(s) in all images", data_manager, image_name, pts_id, images, cmd_id, parent)

class RemovePointsFromImage(RemovePointsInImages):
    def __init__(self, data_manager, image_name, pts_id, cmd_id=-1, parent = None):
        idx = data_manager.images_name.index(image_name)
        images = data_manager.images_name[idx:]
        RemovePointsInImages.__init__(self, "Remove point(s) starting at image %s" % image_name, data_manager, image_name, pts_id, images, cmd_id, parent)

class RemovePointsToImage(RemovePointsInImages):
    def __init__(self, data_manager, image_name, pts_id, cmd_id=-1, parent = None):
        idx = data_manager.images_name.index(image_name)
        images = data_manager.images_name[:idx+1]
        RemovePointsInImages.__init__(self, "Remove point(s) up to image %s" % image_name, data_manager, image_name, pts_id, images, cmd_id, parent)

class AddPoints(PointsCommand):
    def __init__(self, data_manager, image_name, ids, pos, cmd_id=-1, parent = None):
        PointsCommand.__init__(self, "Add point(s) to image %s" % image_name, data_manager, image_name, cmd_id, parent)
        data = self.data_manager
        if ids is None:
            dpos = {}
            for p in pos:
                dpos[data.createNewPoint()] = p
            self.pos = dpos
        else:
            self.pos = dict(izip(ids,pos))

    def undo(self):
        data = self.current_data
        pos = self.pos
        for pt in pos:
            del data[pt]

    def redo(self):
        data = self.current_data
        pos = self.pos
        for pt in pos:
            data[pt] = pos[pt]

class SplitCells(PointsCommand):
    def __init__(self, data_manager, image_name, cell_id, cmd_id = -1, parent = None):
        PointsCommand.__init__(self, "Split cell %s at image %s" % (cell_id, image_name), data_manager, image_name, cmd_id, parent)
        self.cell_id = cell_id
        self.split_time = data_manager.images_name.index(image_name)+1
        self.ls = data_manager.lifespan(cell_id).copy()
        self.new_cell_id = data_manager.createNewCell()
        self.cell = data_manager.cells[self.cell_id]

    def undo(self):
        if self.ls.daughters:
            ls0 = self.data_manager.lifespan(self.ls.daughters[0])
            ls1 = self.data_manager.lifespan(self.ls.daughters[1])
            ls0.parent = self.cell_id
            ls1.parent = self.cell_id
        self.data_manager.removeCells(self.new_cell_id)
        self.data_manager.setCells(self.cell_id, self.cell, self.ls)

    def redo(self):
        first_ls = LifeSpan(start=self.ls.start, end=self.split_time, parent=self.ls.parent)
        second_ls = LifeSpan(start=self.split_time, end=self.ls.end, daughters=self.ls.daughters)
        if self.ls.daughters:
            ls0 = self.data_manager.lifespan(self.ls.daughters[0])
            ls1 = self.data_manager.lifespan(self.ls.daughters[1])
            ls0.parent = self.new_cell_id
            ls1.parent = self.new_cell_id
        first_cell = []
        second_cell = []
        first_images = set(self.data_manager.imagesWithLifespan(first_ls))
        second_images = set(self.data_manager.imagesWithLifespan(second_ls))
        for vid in self.cell:
            for img in self.data_manager.imagesWithPoint(vid):
                if img in first_images:
                    first_cell.append(vid)
                    break
            for img in self.data_manager.imagesWithPoint(vid):
                if img in second_images:
                    second_cell.append(vid)
                    break
        self.data_manager.setCells([self.cell_id, self.new_cell_id],
                                   [first_cell, second_cell],
                                   [first_ls, second_ls])

class MergeCells(PointsCommand):
    def __init__(self, data_manager, image_name, cell_id, new_cell_id, cmd_id=-1, parent=None):
        PointsCommand.__init__(self, "Merge cell %s with cell %s" % (cell_id, new_cell_id), data_manager, image_name, cmd_id, parent)
        ls_cid = data_manager.lifespan(cell_id).copy()
        ls_new_cid = data_manager.lifespan(new_cell_id).copy()
        self.cell_id = cell_id
        self.new_cell_id = new_cell_id
        self.ls_cid = ls_cid
        self.ls_new_cid = ls_new_cid
        self.cell = list(data_manager.cells[cell_id])
        self.new_cell = list(data_manager.cells[new_cell_id])
        assert ls_cid.daughters is None or ls_new_cid.daughters is None, "Both cells are dividing. It is not possible to merge them."
        assert ls_cid.parent is None or ls_new_cid.parent is None, "Both cells results from division of a mother cell. It is not possible to merge them."

    def undo(self):
        if self.ls_cid.parent:
            lsp = self.data_manager.lifespan(self.ls_cid.parent)
            dgtrs = list(lsp.daughters)
            if dgtrs[0] == self.new_cell_id:
                dgtrs[0] = self.cell_id
            else:
                dgtrs[1] = self.cell_id
            lsp.daughters = dgtrs
        if self.ls_cid.daughters:
            ls0 = self.data_manager.lifespan(self.ls_cid.daughters[0])
            ls1 = self.data_manager.lifespan(self.ls_cid.daughters[1])
            ls0.parent = self.cell_id
            ls1.parent = self.cell_id
        print_debug("Restoring cells %d and %d" % (self.cell_id, self.new_cell_id))
        self.data_manager.setCells([self.cell_id, self.new_cell_id],
                                   [self.cell   , self.new_cell],
                                   [self.ls_cid , self.ls_new_cid])
    
    def redo(self):
        new_daughters =self.ls_cid.daughters or self.ls_new_cid.daughters 
        new_division = self.ls_cid.division or self.ls_new_cid.division
        new_parent = self.ls_cid.parent or self.ls_new_cid.parent
        new_ls = LifeSpan(parent = new_parent, daughters = new_daughters, division=new_division)
        if new_ls.parent:
            new_ls.start = self.data_manager.lifespan(new_ls.parent).end
        else:
            new_ls.start = min(self.ls_cid.start, self.ls_new_cid.start)
        if new_ls.daughters:
            new_ls.end = self.data_manager.lifespan(new_ls.daughters[0]).start
        else:
            new_ls.end = max(self.ls_cid.end, self.ls_new_cid.end)
        new_cell = list(self.new_cell)
        cell = list(self.cell)
        # First, find a common point
        for i,c in enumerate(cell):
            if c in new_cell:
                cell = cell[i:] + cell[:i]
                idx = new_cell.index(c)
                new_cell = new_cell[idx:] + new_cell[:idx]
                break
        i = 0
        for v in cell:
            if v in new_cell:
                i = new_cell.index(v)
            else:
                new_cell.insert(i+1, v)
                i=i+1
        if self.ls_cid.parent:
            ls_parent = self.data_manager.lifespan(self.ls_cid.parent)
            dgtrs = list(ls_parent.daughters)
            if dgtrs[0] == self.cell_id:
                dgtrs[0] = self.new_cell_id
            else:
                dgtrs[1] = self.new_cell_id
            ls_parent.daughters = dgtrs
            self.data_manager.lifespan(self.cell_id).parent = None
        if self.ls_cid.daughters:
            lf0 = self.data_manager.lifespan(self.ls_cid.daughters[0])
            lf1 = self.data_manager.lifespan(self.ls_cid.daughters[1])
            lf0.parent = self.new_cell_id
            lf1.parent = self.new_cell_id
        print_debug("Merging cell %d with cell %d" % (self.cell_id, self.new_cell_id))
        self.data_manager.removeCells(self.cell_id)
        self.data_manager.setCells(self.new_cell_id, new_cell, new_ls)

class SplitPointsId(PointsCommand):
    def __init__(self, data_manager, image_name, pts_id, cmd_id = -1, parent = None):
        assert len(pts_id) == 1, "Cannot split more than one point at a time"
        PointsCommand.__init__(self, "Split point %s at image %s" % (pts_id[0], image_name), data_manager, image_name, cmd_id, parent)
        pt_id = pts_id[0]
        self.pt_id = pt_id
        self.new_pt_id = data_manager.createNewPoint()
        self.cells = list(data_manager.cell_points[pt_id])
        self.cell_shape = [list(data_manager.cells[cid]) for cid in self.cells]
        self.images = data_manager.imagesWithPoint(pt_id)
        idx = self.images.index(image_name)
        tid = data_manager[image_name].index
        # Store divisions
        dividing = {}
        for cid in self.cells:
            ls = data_manager.lifespan(cid)
            if ls.division and ls.end > tid:
                if pt_id == ls.division[0]:
                    dividing[cid] = 0
                elif pt_id == ls.division[1]:
                    dividing[cid] = 1
        self.dividing = dividing
        self.images = self.images[idx+1:]
        # Adding walls
        walls = set()
        for (t,p1,p2) in data_manager.walls:
            if t > tid and (p1 == pt_id or p2 == pt_id):
                walls.add((t,p1,p2))
        self.walls = walls
        self.tid = tid
        print "Split point of id %d.\nCreating point %d on images %s" % (pt_id, self.new_pt_id, str(self.images))

    def undo(self):
        dm = self.data_manager
        images = self.images
        pt_id = self.pt_id
        new_pt_id = self.new_pt_id
        lifespans = []
        # First, change cells
        for cid in self.cells:
            lifespans.append(dm.lifespan(cid))
            # Next, change division points if needed
            if cid in self.dividing:
                pos = self.dividing[cid]
                ls = lifespans[-1]
                div = list(ls.division)
                div[pos] = new_pt_id
                ls.division = div
        dm.setCells(self.cells, self.cell_shape, lifespans)
        # Then, walls
        for (t,p1,p2) in self.walls:
            if pt_id == p1:
                dm.walls[t,p1,p2] = dm.walls[t,new_pt_id,p2]
                del dm.walls[t,new_pt_id,p2]
            else:
                dm.walls[t,p1,p2] = dm.walls[t,p1,new_pt_id]
                del dm.walls[t,p1,new_pt_id]
        # At last, points
        for image in images:
            data = dm[image]
            data[pt_id] = data[new_pt_id]
            del data[new_pt_id]

    def redo(self):
        dm = self.data_manager
        images = self.images
        pt_id = self.pt_id
        new_pt_id = self.new_pt_id
        tid = self.tid
        cell_shapes = []
        lifespans = []
        # First, change cells
        for cid in self.cells:
            print "Inserting point %d in cell %d" % (new_pt_id, cid)
            ls = dm.lifespan(cid)
            lifespans.append(ls)
            cell_shape = list(dm.cells[cid])
            idx = cell_shape.index(pt_id)
            if ls.start <= tid and ls.end > tid:
                cell_shape.insert(idx, new_pt_id)
            elif ls.start > tid:
                cell_shape[idx] = new_pt_id
            cell_shapes.append(cell_shape)
            # Next, change division points if needed
            if cid in self.dividing:
                pos = self.dividing[cid]
                ls = lifespans[-1]
                div = list(ls.division)
                div[pos] = new_pt_id
                ls.division = div
        dm.setCells(self.cells, cell_shapes, lifespans)
        # Then, walls
        for (t,p1,p2) in self.walls:
            if pt_id == p1:
                dm.walls[t,new_pt_id,p2] = dm.walls[t,p1,p2]
            else:
                dm.walls[t,p1,new_pt_id] = dm.walls[t,p1,p2]
            del dm.walls[t,p1,p2]
        # At last, points
        for image in images:
            data = dm[image]
            data[new_pt_id] = data[pt_id]
            del data[pt_id]

class ChangePointsId(PointsCommand):
    def __init__(self, data_manager, image_name, pts_id, new_pts_id, cmd_id=-1, parent=None):
        assert len(pts_id) == len(new_pts_id), "The number of new and old points must be the same."
        assert len(pts_id) == 1, "Cannot merge more than one point at a time"
        PointsCommand.__init__(self, "Merge point %s with point %s" % (pts_id[0], new_pts_id[0]), data_manager, image_name, cmd_id, parent)
        pt_id = pts_id[0]
        new_pt_id = new_pts_id[0]
        self.pt_id = pt_id
        self.new_pt_id = new_pt_id
        self.images = data_manager.imagesWithPoint(pt_id)
        errors = []
        # Store the cells
        for img in data_manager.imagesWithPoint(new_pt_id):
            if img in self.images:
                errors.append(img)
        self.cells = list(data_manager.cell_points[pt_id])
        self.cell_shape = [ list(data_manager.cells[cid]) for cid in self.cells ]
        walls = set()
        # Store the walls
        for (t,p1,p2) in data_manager.walls:
            if p1 == pt_id or p2 == pt_id:
                walls.add((t,p1,p2))
        self.walls = walls
        # Store the cell divisions
        divisions = []
        for cid in self.cells:
            life = data_manager.lifespan(cid)
            if life.division is not None:
                if life.division[0] == pt_id:
                    divisions.append((cid, 0))
                elif life.division[1] == pt_id:
                    divisions.append((cid, 1))
        self.divisions = divisions
        assert not errors, self.error_to_string(pt_id, new_pt_id, errors)

    def error_to_string(self, pt_id, new_pt_id, errors):
        error_pattern = "The points of id %d and %d coexist the images %s."
        error_str = ""
        error_str += error_pattern % (pt_id, new_pt_id, ", ".join(errors))
        return error_str

    def undo(self):
        dm = self.data_manager
        images = self.images
        pt_id = self.pt_id
        new_pt_id = self.new_pt_id
        # First, the walls
        for (t,p1,p2) in self.walls:
            if p1 == pt_id:
                dm.walls[t,p1,p2] = dm.walls[t,new_pt_id,p2]
                del dm.walls[t,new_pt_id,p2]
            else:
                dm.walls[t,p1,p2] = dm.walls[t,p1,new_pt_id]
                del dm.walls[t,p1,new_pt_id]
        # And then, the cell divisions
        for cid, pos in self.divisions:
            lf = dm.lifespan(cid)
            div = list(lf.division)
            div[pos] = pt_id
            lf.division = div
        # Then, the cells
        dm.setCells(self.cells, self.cell_shape)
        # At last, replace the points
        for image in images:
            data = dm[image]
            data[pt_id] = data[new_pt_id]
            del data[new_pt_id]

    def redo(self):
        dm = self.data_manager
        images = self.images
        pt_id = self.pt_id
        new_pt_id = self.new_pt_id
        # First, the walls
        for (t,p1,p2) in self.walls:
            if p1 == pt_id:
                dm.walls[t,new_pt_id,p2] = dm.walls[t,p1,p2]
            else:
                dm.walls[t,p1,new_pt_id] = dm.walls[t,p1,p2]
            del dm.walls[t,p1,p2]
        # Then, the cells
        cell_shapes = []
        for cid in self.cells:
            cell = list(dm.cells[cid])
            if new_pt_id in cell:
                cell.remove(pt_id)
            else:
                idx = cell.index(pt_id)
                cell[idx] = new_pt_id
            cell_shapes.append(cell)
        # And then, the cell divisions
        for cid, pos in self.divisions:
            lf = dm.lifespan(cid)
            div = list(lf.division)
            div[pos] = new_pt_id
            lf.division = div
        dm.setCells(self.cells, cell_shapes)
        # At last, replace points
        for image in images:
            data = dm[image]
            data[new_pt_id] = data[pt_id]
            del data[pt_id]

class AddCellCommand(TrackingCommand):
    def __init__(self, data_manager, cell_id, pts_ids, cmd_id=-1, parent=None):
        assert cell_id not in data_manager.cells, "The cell %d cannot be added, it already exists" % cell_id
        TrackingCommand.__init__(self, "Add cell %s" % cell_id, cmd_id, parent)
        self.cell_id = cell_id
        self.pts_ids = pts_ids
        self.data_manager = data_manager

    def undo(self):
        self.data_manager.removeCells([self.cell_id])
        self.data_manager.checkCells()

    def redo(self):
        print "Actually adding the cell %s" % (self.cell_id,)
        self.data_manager.setCells([self.cell_id], [self.pts_ids])
        self.data_manager.checkCells()

class ChangeCellCommand(TrackingCommand):
    def __init__(self, data_manager, cell_id, pts_ids, lifespan, cmd_id=-1, parent=None):
        assert cell_id in data_manager.cells, "The cell %d cannot be changed, it does not exist" % cell_id
        TrackingCommand.__init__(self, "Change cell %s" % cell_id, cmd_id, parent)
        self.cell_id = cell_id
        self.pts_ids = pts_ids
        if lifespan is not None:
            self.ls = [lifespan]
            self.old_ls = [data_manager.lifespan(cell_id).copy()]
        else:
            self.ls = None
            self.old_ls = None
        self.old_pts_ids = tuple(data_manager.cells[cell_id])
        self.data_manager = data_manager

    def undo(self):
        self.data_manager.checkCells()
        self.data_manager.setCells([self.cell_id], [self.old_pts_ids], self.old_ls)
        self.data_manager.checkCells()

    def redo(self):
        self.data_manager.checkCells()
        self.data_manager.setCells([self.cell_id], [self.pts_ids], self.ls)
        self.data_manager.checkCells()

class InsertPointInWallCommand(TrackingCommand):
    def __init__(self, data_manager, new_pt, wid, cmd_id=-1, parent = None):
        TrackingCommand.__init__(self, "Insert point %d in wall (%d,%d)" % ((new_pt,)+wid), cmd_id, parent)
        cells = data_manager.cells
        wall_cells = data_manager.wallCells(wid)
        assert wall_cells, "The point %d and %d do not form a wall in any cell." % wid
        remove_cell = []
        for cid in wall_cells:
            if new_pt in cells[cid]:
                remove_cell.append(cid)
        for cid in remove_cell:
            wall_cells.remove(cid)
        self.wall_cells = wall_cells
        self.saved_cells = [ tuple(cells[cid]) for cid in wall_cells ]
        self.data_manager = data_manager
        self.new_pt = new_pt
        self.wid = wid

    def undo(self):
        self.data_manager.setCells( self.wall_cells, self.saved_cells )
        self.data_manager.checkCells()

    def redo(self):
        self.data_manager.insertPointInWall( self.new_pt, self.wid )
        self.data_manager.checkCells()

def cellsToStr(cells):
    if len(cells) > 1:
        return ','.join("%d" % c for c in cells[:-1]) + " and %d" % cells[-1]
    else:
        return "%d" % cells[0]

class RemoveCellsCommand(TrackingCommand):
    def __init__(self, data_manager, cell_ids, cmd_id=-1, parent=None):
        for cid in cell_ids:
            assert cid in data_manager.cells, "The cell %d cannot be removed, it does not exist" % cid
        TrackingCommand.__init__(self, "Delete cells %s" % (",".join("%d" % cid for cid in cell_ids)), cmd_id, parent)
        cells_deleted = []
        divided_cells = []
        parents = []
        for cid in cell_ids:
            ls = data_manager.cells_lifespan[cid]
            if ls.parent is not None:
                parents.append((ls.parent, cid))
                sis = data_manager.sisterCell(cid)
                cells_deleted.append(sis)
                cells_deleted.extend(data_manager.daughterCells(sis))
            daughters = data_manager.daughterCells(cid)
            cells_deleted.extend(daughters)
            if daughters:
                divided_cells.append(cid)
        cells_deleted += list(cell_ids)
        self.cell_ids = cell_ids
        self.cells_deleted = cells_deleted
        self.old_pts_ids = [ tuple(data_manager.cells[cell_id]) for cell_id in cells_deleted ]
        self.old_lifespans = [ data_manager.lifespan(cid).copy() for cid in cells_deleted ]
        self.data_manager = data_manager
        self.parents = [p[0] for p in parents]
        self.old_parents_lifespans = [ data_manager.lifespan(cid).copy() for cid in self.parents ]

    def undo(self):
        self.data_manager.setCells(self.cells_deleted, self.old_pts_ids, self.old_lifespans)
        self.data_manager.changeCellsLifespan(self.parents, self.old_parents_lifespans)
        self.data_manager.checkCells()

    def redo(self):
        self.data_manager.removeCells(self.cell_ids)
        self.data_manager.checkCells()

RemoveCellsCommand.confirm_delete = True

class DivideCellCommand(TrackingCommand):
    def __init__(self, data_manager, image_name, cell_id, cid1, cid2, p1, p2, cmd_id = -1, parent = None):
        image_data = data_manager[image_name]
        cells = image_data.cells
        all_cells = data_manager.cells
        assert cell_id in cells, "The cell %d cannot be divided in image %s as it does not exist" % (cell_id, image_name)
        assert cid1 not in all_cells, "The cell %d cannot be created, it already exists" % cid1
        assert cid2 not in all_cells, "The cell %d cannot be created, it already exists" % cid2
        cell_shape = cells[cell_id]
        assert p1 in cell_shape, "Cell division error. The point %d is not part of cell %d." % (p1, cell_id)
        assert p2 in cell_shape, "Cell division error. The point %d is not part of cell %d." % (p2, cell_id)
        TrackingCommand.__init__(self, "Divide cell %d on image %s" % (cell_id, image_name), cmd_id, parent)
        self.data_manager = data_manager
        self.image_data = image_data
        self.image_name = image_name
        self.cell_id = cell_id
        self.cid1 = cid1
        self.cid2 = cid2
        self.p1 = p1
        self.p2 = p2

    def undo(self):
        self.image_data.cells.undivide(self.cell_id)
        self.data_manager.checkCells()

    def redo(self):
        self.image_data.cells.divide(self.cell_id, self.cid1, self.cid2, self.p1, self.p2)
        self.data_manager.checkCells()

class ChangeTiming(TrackingCommand):
    def __init__(self, data_manager, times, cmd_id=-1, parent=None):
        TrackingCommand.__init__(self, "Updating images timing", cmd_id, parent)
        self.data_manager = data_manager
        self.timed_images = list(times)
        self.old_timed_images = [ data.time for data in self.data_manager]

    def undo(self):
        self.data_manager.setTimes(self.old_timed_images)
        self.data_manager.checkCells()

    def redo(self):
        self.data_manager.setTimes(self.timed_images)
        self.data_manager.checkCells()

class ChangeScales(TrackingCommand):
    def __init__(self, data_manager, scales, cmd_id = -1, parent = None):
        TrackingCommand.__init__(self, "Changing images scales", cmd_id, parent)
        self.data_manager = data_manager
        self.scales = list(scales)
        self.old_scales = [ data.scale for data in data_manager ]
        
    def undo(self):
        self.data_manager.setScales(self.old_scales)
        self.data_manager.checkCells()
        
    def redo(self):
        self.data_manager.setScales(self.scales)
        self.data_manager.checkCells()

class AlignImages(QUndoCommand):
    def __init__(self, data_manager, shifts, angles, parent=None):
        QUndoCommand.__init__(self, "Align images", parent)
        self.data_manager = data_manager
        self.shifts = shifts
        self.angles = angles
        self.saved_move = None

    def redo(self):
        saved_move = [0]*len(self.data_manager)
        shifts = self.shifts
        angles = self.angles
        for i,d in enumerate(self.data_manager):
            saved_move[i] = d.shift
            d.move(QPointF(shifts[i,0], shifts[i,1]), angles[i])
        self.saved_move = saved_move
        self.data_manager.checkCells()

    def undo(self):
        saved_move = self.saved_move
        for i,d in enumerate(self.data_manager):
            d.move(*saved_move[i])
        self.data_manager.checkCells()

class ResetAlignment(QUndoCommand):
    def __init__(self, data_manager, parent=None):
        QUndoCommand.__init__(self, "Reset images alignment", parent)
        self.data_manager = data_manager
        self.saved_move = None

    def redo(self):
        saved_move = [0]*len(self.data_manager)
        for i,d in enumerate(self.data_manager):
            saved_move[i] = d.shift
            d.move(QPointF(0,0), 0)
        self.saved_move = saved_move
        self.data_manager.checkCells()

    def undo(self):
        saved_move = self.saved_move
        for i,d in enumerate(self.data_manager):
            d.move(*saved_move[i])
        self.data_manager.checkCells()

class CleanCells(QUndoCommand):
    def __init__(self, data_manager, parent=None):
        QUndoCommand.__init__(self, "Cleaning cells", parent)
        self.data_manager = data_manager
        self.first_run = True

    def redo(self):
        changed_cells, saved_cells = self.data_manager.cleanCells()
        self.changed_cells = changed_cells
        self.saved_cells = saved_cells
        if self.first_run:
            self.first_run = False
            msg = "Nothing to do. Cells are clean."
            if saved_cells:
                actions = []
                for cid, old_pt_ids in izip(changed_cells, saved_cells):
                    left_pts = list(old_pt_ids)
                    saved_pts = []
                    new_pts = self.data_manager.cells[cid]
                    for pt_id in new_pts:
                        left_pts.remove(pt_id)
                    actions.append((cid,left_pts))
                    if left_pts:
                        actions.append("On cell %d, removed duplicated points: %s" % (cid, ",".join(str(ptid) for ptid in left_pts)))
                    if old_pt_ids.index(new_pts[0]) > old_pt_ids(new_pts[1]):
                        actions.append("Reversed orientation of cell %d" % cid)
                msg = "\n".join(actions)
                msg = "Cleaning actions:\n%s" % msg
            QMessageBox.information(None, "Cell cleaning result", msg)
        self.data_manager.checkCells()

    def undo(self):
        self.data_manager.setCells(self.changed_cells, self.saved_cells)
        self.data_manager.checkCells()

