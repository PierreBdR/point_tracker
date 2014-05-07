from __future__ import print_function, division, absolute_import
"""
:newfield signal: Signal, Signals
"""
__author__ = "Pierre Barbier de Reuille <pierre@barbierdereuille.net>"
__docformat__ = "restructuredtext"

from PyQt4.QtCore import QPointF, QObject, SIGNAL
from PyQt4.QtGui import QTransform
from path import path
import csv
import numpy
from .utils import compare_versions
from .debug import print_debug
from .geometry import cross

class TrackingDataException(Exception):
    """
    Exception launched by the `TrackingData` object when an error linked to the 
    data arise.
    """
    def __init__(self, text):
        Exception.__init__(self, text)

class RetryTrackingDataException(Exception):
    """
    Exception launched by the `TrackingData` object when an error occurs, 
    but the user should be prompted for a retry (i.e. a yes/no question only).
    """
    def __init__(self, question, option):
        Exception.__init__(self, question)
        self.question = question
        self.method_args = {option: True}

class EndOfTime(object):
    """
    Represent the end of time, and as such bigger than any other object.

    Implemented as a singleton.
    """
    def __new__(cls):
        if cls.instance is None:
            cls.instance = object.__new__(cls)
        return cls.instance

    instance = None
    """ Singleton instance """

    def __cmp__(self, other):
        if self is other:
            return 0
        return 1

    def __ne__(self, other):
        return self is not other

    def __eq__(self, other):
        return self is other

    def __str__(self):
        return "EndOfTime"

    def __repr__(self):
        return "EndOfTime()"

    def __index__(self):
        return -1

class LifeSpan(object):
    """
    :Ivariables:
      start : int
        Start of the life span of the cell
      parent : int|None
        id of the parent cell
    """
    def __init__(self, start=0, end=EndOfTime(), parent = None, daughters=None, division=None):
        self.start = start
        self._end = end
        self.parent = parent
        if daughters is None:
            self._daughters = None
        else:
            d1, d2 = daughters
            self._daughters = (d1, d2)
        if division is None:
            self._division = None
        else:
            p1, p2 = division
            self._division = (p1, p2)

    def __repr__(self):
        return "LifeSpan(start=%d,end=%s,parent=%s,daughters=%s,division=%s)" % (self.start, self.end, self.parent, self.daughters, self.division)

    def copy(self):
        return LifeSpan(self.start, self.end, self.parent, self.daughters, self.division)

    def _get_end(self):
        """
        Time at which the cell cease to exist.

        At that time, the cell has already divided.

        :returntype: int|`EndOfTime`
        """
        return self._end

    def _set_end(self, value):
        if value < 0:
            value = EndOfTime()
        self._end = value

    def _del_end(self):
        self._end = EndOfTime()

    end = property(_get_end, _set_end, _del_end)

    def _get_daughters(self):
        """
        Daughters of the cell if any, or None.

        :returntype: (int,int)|None
        """
        return self._daughters

    def _set_daughters(self, ds):
        (d1, d2) = ds
        self._daughters = (d1, d2)

    def _del_daughters(self):
        self._daughters = None

    daughters = property(_get_daughters, _set_daughters, _del_daughters)

    def _get_division(self):
        """
        Points used to divide the cell if any, or None.

        :returntype: (int,int)|None
        """
        return self._division

    def _set_division(self, ps):
        (p1, p2) = ps
        self._division = (p1, p2)

    def _del_division(self):
        self._division = None

    division = property(_get_division, _set_division, _del_division)

    def slice(self):
        """
        :returns: a slice object to extract the elements of the list in which the object is alive.
        :returntype: slice
        """
        if self.end == EndOfTime():
            return slice(self.start, None)
        return slice(self.start, self.end)

    def __len__(self):
        """
        Number of used elements of the object: 3 if no division occured, 7 otherwise.

        :returns: 3 or 7
        :returntype: int
        """
        if self.daughters is None:
            return 3
        return 7

    def __getitem__(self, idx):
        """
        Get each element in an indexed way. The index correspond to:
          0. start
          1. end or -1 if `EndOfTime`
          2. parent cell or -1
          3. first daughter cell
          4. second daughter cell
          5. first division point
          6. second division point

        :returntype: int
        """
        if idx == 0:
            return self.start
        elif idx == 1:
            return self.end.__index__()
        elif idx == 2:
            return self.parent if self.parent is not None else -1
        elif self.daughters is None:
            raise IndexError(idx)
        elif idx == 3:
            return self.daughters[0]
        elif idx == 4:
            return self.daughters[1]
        elif idx == 5:
            return self.division[0]
        elif idx == 6:
            return self.division[1]
        else:
            raise IndexError(idx)

    def __setitem__(self, idx, value):
        """
        Set the elements with the same semantic as in `__getitem__`.
        """
        if idx == 0:
            self.start = value
        elif idx == 1:
            self.end = value if value >= 0 else EndOfTime()
        elif idx == 2:
            self.parent = value if value >= 0 else None
        elif idx == 3:
            if isinstance(self.daughters, tuple):
                self.daughters = (value, self.daughters[1])
            else:
                self.daughters = (value, None)
        elif idx == 4:
            if isinstance(self.daughters, tuple):
                self.daughters = (self.daughters[0], value)
            else:
                self.daughters = (None, value)
        elif idx == 5:
            if isinstance(self.division, tuple):
                self.division = (value, self.division[1])
            else:
                self.division = (value, None)
        elif idx == 6:
            if isinstance(self.division, tuple):
                self.division = (self.division[0], value)
            else:
                self.division = (value, None)
        else:
            raise IndexError(idx)

class TimedWallShapes(object):
    """
    Represent the wall shapes at a given time
    """
    def __init__(self, ws, time):
        self._data = ws[time]

    def __contains__(self, ps):
        (p1, p2) = ps
        return (p1,p2) in self._data

    def __getitem__(self, ps):
        (p1, p2) = ps
        try:
            if p1 < p2:
                return self._data[p1,p2][:]
            else:
                return self._data[p2,p1][::-1]
        except KeyError:
            return []

    def __setitem__(self, ps, values):
        (p1, p2) = ps
        if p1 < p2:
            self._data[p1,p2] = values[:]
        else:
            self._data[p2,p1] = values[::-1]

    def __delitem__(self, ps):
        (t, p1, p2) = ps
        if (p1,p2) in self._data:
            del self._data[p1,p2]

    def __iter__(self):
        return iter(self._data)

    def __len__(self):
        return len(self._data)

class WallShapes(object):
    """
    Store wall shapes without duplication. The real data structure is a dictionnary associating, for each time, a dictionnary.

    The inner dictionnary stores, for each couple of points, the list of intermediate points.

    Note that the __getitem__ returns a *copy* of the points.
    """
    def __init__(self, content = None):
        self._walls = {}
        if content is not None:
            for t,p1,p2 in content:
                self[t,p1,p2] = content[t,p1,p2]

    def __repr__(self):
        return "WallShapes({%s})" % ", ".join([ "%s: %s" % (val, self[val]) for val in self ])

    def __str__(self):
        s = "WallShapes:"
        for t in self._walls:
            s += "\n\tTime %s:" % t
            s += "".join("\n\t\t%s - %s: %s" % (p1, p2, self._walls[t][p1,p2]) for p1,p2 in self._walls[t])
        if not self._walls:
            s += "\n\tempty"
        return s

    def add_time(self, t):
        if t not in self._walls:
            self._walls[t] = {}

    def __delitem__(self, ps):
        (t,p1,p2) = ps
        if t in self._walls:
            if (p1,p2) in self._walls[t]:
                del self._walls[t][p1,p2]

    def __contains__(self, ps):
        (t,p1,p2) = ps
        return t in self._walls and (p1,p2) in self._walls[t]

    def __getitem__(self, i):
        try:
            time,p1,p2 = i
            revert = False
            if p1 > p2:
                p1,p2 = p2,p1
                revert = True
            if revert:
                return self._walls[time][p1,p2][::-1]
            else:
                return self._walls[time][p1,p2][:] # Force copy of the points
        except KeyError:
            return []
        except:
            if not i in self._walls:
                self._walls[i] = {}
            return self._walls[i]

    def __setitem__(self, ps, pts):
        (time, p1, p2) = ps
        if p1 > p2:
            p1,p2 = p2,p1
            pts = pts[::-1]
        if not time in self._walls:
            self._walls[time] = {(p1,p2): pts}
        else:
            self._walls[time][p1,p2] = pts

    def __iter__(self):
        for t in self._walls:
            for (p1,p2) in self._walls[t]:
                yield (t, p1, p2)

    def empty(self):
        for t in self._walls:
            w = self._walls[t]
            for (p1,p2) in w:
                if w[p1,p2]:
                    return False
        return True

class TrackingData(QObject):
    """
    Handled the data generated by tracking.

    :signal: ``saved``
    :signal: ``pointsAdded --> image_name, ids``
    :signal: ``pointsMoved --> image_name, ids``
    :signal: ``pointsDeleted --> image_name, ids``
    :signal: ``imageMoved --> image_name, pos, angle``
    :signal: ``dataChanged --> image_name``
    :signal: ``cellsRemoved --> cell_ids[, image_list]``
    :signal: ``cellsChanged --> cell_ids``
    :signal: ``cellsAdded --> cells_ids[, image_list]``

    Signal pointsDeleted is sent before the modification is actually made. 
    Thus, one can get the previous value on the signal handler. The other signals 
    are sent after the action has been done.

    The image list is sent only if part of the images is affected

    :Ivariables:
        _last_pt_id : int
            last point id used
        _last_cell_id : int
            last cell id used
        _images_dir : `path`
            directory containing the images
        _data_file : `path`
            path of the data file in use
        images_shift : dict of str * (`QPointF`, float)
            shift (translation,rotation) of the images
        images_scale: dict of str * (float, float)
            size of a pixel in each image
        images_name : list of str
            name of the images, sorted by time
        _images_time : list of float
            time at which the images where taken
        data : dict of str*(dict of int * `QPointF`)
            position of the points for each image name
        cells : dict of int*(tuple of int)
            description of the cells
        cells_lifespan : dict of int * `LifeSpan`
            describe the lifespan of the cell whose id is the key. LifeSpan 
            describe the start and end of the existence of the cell, as well as 
            the parent and daughter cells (it any) and the division points if 
            the cell divide.
        cell_points : dict of int*(set of int)
            cells in which the points are
        walls : `WallShapes`
            List of walls. The two points are such that the first id is always smaller than the second
    """
    def __init__(self, project_dir = path("")):
        """
        :Parameters:
            project : `Project`
                Project containing the data.
            data_file : str | unicode
                If project is None, this parameter can point to the data file. The project will be guessed from it.
        """
        QObject.__init__(self)
        self.reset()
        self.project_dir = project_dir

    def copy(self):
        """
        :returns: a deep copy of the TrackingData object.
        :returntype: `TrackingData`
        """
        copy = TrackingData()
        copy._last_pt_id = self._last_pt_id
        copy._last_cell_id = self._last_cell_id
        copy.project_dir = self.project_dir
        copy._data_file = self._data_file
        copy.images_shift = dict((name, [QPointF(pos), a]) for name, (pos, a) in self.images_shift.iteritems())
        copy.images_scale = dict((name, (x,y)) for name, (x,y) in self.images_scale.iteritems())
        copy.images_name = list(self.images_name)
        copy._images_time = list(self._images_time)
        copy.data = dict((name, dict((i,QPointF(pos)) for i,pos in d.iteritems())) for name,d in self.data.iteritems())
        copy.walls = WallShapes(self.walls)
        return copy

    def _valid(self):
        """
        True if the object contains a valid set of data.

        :returntype: bool
        """
        return (self.data is not None) and (self.images_name is not None)

    valid = property(_valid)

    def _get_images_time(self):
        """
        Get the immutable list of times for the images.

        To modify, you have to use the syntax:

            >>> data[image_name].time = value
        """
        return tuple(self._images_time)

    images_time = property(_get_images_time)

    def reset_data(self):
        """
        Reset the data in the object, but not the images
        """
        self._last_pt_id = -1
        self._last_cell_id = -1
        self.data = {}
        self.cells = {}
        self.cells_lifespan = {}
        self.cell_points = {}
        self.walls = WallShapes()
        for t in range(len(self.images_name)):
            self.walls.add_time(t)

    def reset(self):
        """
        Reset the whole object, data and images.
        """
        self.project_dir = path("")
        self._data_file = None
        self.images_name = []
        self._images_time = []
        self.images_shift = {}
        self.images_scale = {}
        self.reset_data()

    def image_path(self, name):
        """
        Utility converting the name of an image onto its path
        :returntype: `path`
        """
        return self.project_dir / "Processed" / str(name)
        #return self.images_path[self.images_name.index(name)]

    def load_version0(self, f, has_version = None, **opts):
        """
        Load files for version 0
        """
        r = csv.reader(f, delimiter="\t")
        title = r.next()
        num_columns = len(title)
        if num_columns % 2 == 1:
            raise TrackingDataException("Incorrect number of columns in title line. Even number expected.")
        #num_img = num_columns/2
        images = title[::2]
        data = {}
        shifts = {}
        scales = {}
        for img in images:
            data[img] = {}
            shifts[img] = [QPointF(0,0), 0]
            scales[img] = (1,1)
        for i,l in enumerate(r):
            if len(l) != num_columns:
                raise TrackingDataException("Incorrect number of columns in line %d: %d instead of %d expected" % (i+1, len(l), num_columns))
            pos = [ (img,QPointF(float(x),float(y))) for img,x,y in zip(images,l[::2],l[1::2]) if x != '' or y != '' ]
            for img,p in pos:
                data[img][i] = p
            self._last_pt_id = i
        return self._set_data(data, shifts, scales)

    def _set_data(self, data, shifts, scales, cells={}, cells_lifespan=None, times=None, wall_shapes = None):
        """
        Private method finalizing the data after the file has been loaded
        
        :returns: wether the data was unchanged or not
        :returntype: bool
        """
        self.data = data
        self.cells = cells
        self.cells_lifespan = cells_lifespan
        if wall_shapes:
            self.walls = wall_shapes
        else:
            self.walls = WallShapes()
        cell_points = {}
        self.cell_points = cell_points
        self.images_shift = shifts
        for img in scales:
            sc = scales[img]
            scales[img] = ( sc[0] if sc[0] > 0 else 1, sc[1] if sc[1] > 0 else 1 )
        self._min_scale = min(min(sc) for sc in scales.itervalues())
        self.images_scale = scales
# Check the image list
        images_name = data.keys()
        images_name.sort()
        self.images_name = images_name
        if times is None:
            self._images_time = range(len(images_name))
        else:
            self._images_time = list(times)
        for img, (pos, angle) in shifts.iteritems():
            self._imageMoved(img, scales[img], pos, angle)
        for img, d in data.iteritems():
            self._dataChanged(img)
            for p in d.keys():
                cell_points.setdefault(p, set())
            self._pointsAdded(img, d.keys())
        if cells_lifespan is None:
            cells_lifespan = {}
            for c in cells:
                cells_lifespan[c] = LifeSpan()
            self.cells_lifespan = cells_lifespan
        if wall_shapes is None:
            print("Init empty walls")
            wall_shapes = WallShapes()
            for image_data in self:
                t = image_data.index
                for c in image_data.cells:
                    # first, filter points not visible at time t
                    pts = [ p for p in image_data.cells[c] if p in image_data ]
                    if pts:
                        prev = pts[-1]
                        for i in pts:
                            if prev < i:
                                wall_shapes[t,prev,i] = []
                            prev = i
            self.walls = wall_shapes
        if cells:
            for cid in cells:
                for p in cells[cid]:
                    cell_points[p].add(cid)
            self._cellsAdded(cells.keys())
        print_debug("TrackingData loaded with %d images, %d points and %d cells." % (len(self.data), len(cell_points), len(cells)))
        cells_changed, _ = self.cleanCells()
        self.checkCells()
        if cells_changed:
            print_debug("Correction of the data:\n%s" % ("\n".join("Cell %d was invalid" % cid for cid in cells_changed),))
            return True
        return False

    def load_version0_1(self, f, has_version = True, **opts):
        """
        Load files for version 0.1
        """
        r = csv.reader(f, delimiter=",")
        if has_version:
            version = r.next()
            assert compare_versions(version[1], "0.1") >= 0
        title = r.next()
        num_columns = len(title)
        if num_columns % 2 == 0:
            raise TrackingDataException("Incorrect number of columns in title line. Odd number expected.")
        num_columns -= 1
        #num_img = num_columns/2
        images = title[1::2]
        data = {}
        shifts = {}
        scales = {}
        for img in images:
            data[img] = {}
            shifts[img] = [QPointF(0,0), 0]
            scales[img] = (1,1)
# First, read the shifts for each image
        for i in range(2):
            shift = r.next()
            if shift[0] == "XY Shift":
                if len(shift) != num_columns+1:
                    raise TrackingDataException("Incorrect number of XY shifting values. There should be two shifting value per image")
                xshift = shift[1::2]
                yshift = shift[2::2]
                for img,x,y in zip(images, xshift, yshift):
                    shifts[img][0] = QPointF(float(x), float(y))
            elif shift[0] == "Angle Shift":
                if len(shift) != num_columns+1:
                    raise TrackingDataException("Incorrect number of angle shifting values. There should be one shifting value per image")
                ashift = shift[1::2]
                for img,a in zip(images, ashift):
                    shifts[img][1] = float(a)
        for i,l in enumerate(r):
            if len(l) != num_columns+1:
                raise TrackingDataException("Incorrect number of columns in line %d: %d instead of %d expected" % (i+1, len(l), num_columns+1))
            pos = [ (img,QPointF(float(x),float(y))) for img,x,y in zip(images,l[1::2],l[2::2]) if x != '' or y != '' ]
            for img,p in pos:
                data[img][i] = p
            self._last_pt_id = i
        return self._set_data(data, shifts, scales)

    def load_version0_2(self, f, has_version = True, **opts):
        """
        Load files for version 0.2
        """
        r = csv.reader(f, delimiter=",")
        if has_version:
            version = r.next()
            assert compare_versions(version[1], "0.2") >= 0
        title = r.next()
        num_columns = len(title)
        if num_columns % 2 == 0:
            raise TrackingDataException("Incorrect number of columns in title line. Odd number expected.")
        num_columns -= 1
        #num_img = num_columns/2
        images = title[1::2]
        data = {}
        shifts = {}
        scales = {}
        for img in images:
            data[img] = {}
            shifts[img] = [QPointF(0,0), 0]
            scales[img] = (1,1)
# First, read the shifts for each image
        for i in range(2):
            shift = r.next()
            if shift[0] == "XY Shift":
                if len(shift) != num_columns+1:
                    raise TrackingDataException("Incorrect number of XY shifting values. There should be two shifting value per image")
                xshift = shift[1::2]
                yshift = shift[2::2]
                for img,x,y in zip(images, xshift, yshift):
                    shifts[img][0] = QPointF(float(x), float(y))
            elif shift[0] == "Angle Shift":
                if len(shift) != num_columns+1:
                    raise TrackingDataException("Incorrect number of angle shifting values. There should be one shifting value per image")
                ashift = shift[1::2]
                for img,a in zip(images, ashift):
                    shifts[img][1] = float(a)
        cell_list = False
        cells = {}
        for i,l in enumerate(r):
            if len(l) == 1 and l[0].lower() == "cells":
                cell_list = True
                break
            if len(l) != num_columns+1:
                raise TrackingDataException("Incorrect number of columns in line %d: %d instead of %d expected" % (i+1, len(l), num_columns+1))
            pos = [ (img,QPointF(float(x),float(y))) for img,x,y in zip(images,l[1::2],l[2::2]) if x != '' or y != '' ]
            for img,p in pos:
                data[img][i] = p
            self._last_pt_id = i
        if cell_list:
            for cell,l in enumerate(r):
                pts_ids = [ int(i) for i in l[1:] ]
                cells[cell] = tuple(pts_ids)
                self._last_cell_id = cell
        return self._set_data(data, shifts, scales, cells)

    def load_version0_3(self, f, has_version = True, **opts):
        """
        Load files for version 0.3
        """
        r = csv.reader(f, delimiter=",")
        if has_version:
            version = r.next()
            assert compare_versions(version[1], "0.3") >= 0
        title = r.next()
        num_columns = len(title)
        if num_columns % 2 == 0:
            raise TrackingDataException("Incorrect number of columns in title line. Odd number expected.")
        num_columns -= 1
        #num_img = num_columns/2
        images = title[1::2]
        data = {}
        shifts = {}
        scales = {}
        for img in images:
            data[img] = {}
            shifts[img] = [QPointF(0,0), 0]
            scales[img] = (1,1)
# First, read the shifts for each image
        for i in range(2):
            shift = r.next()
            if shift[0] == "XY Shift":
                if len(shift) != num_columns+1:
                    raise TrackingDataException("Incorrect number of XY shifting values. There should be two shifting value per image")
                xshift = shift[1::2]
                yshift = shift[2::2]
                for img,x,y in zip(images, xshift, yshift):
                    shifts[img][0] = QPointF(float(x), float(y))
            elif shift[0] == "Angle Shift":
                if len(shift) != num_columns+1:
                    raise TrackingDataException("Incorrect number of angle shifting values. There should be one shifting value per image")
                ashift = shift[1::2]
                for img,a in zip(images, ashift):
                    shifts[img][1] = float(a)
        cell_list = False
        cells = {}
        cells_lifespan = {}
        for i,l in enumerate(r):
            if len(l) == 1 and l[0].lower() == "cells":
                cell_list = True
                break
            if len(l) != num_columns+1:
                raise TrackingDataException("Incorrect number of columns in line %d: %d instead of %d expected" % (i+1, len(l), num_columns+1))
            pos = [ (img,QPointF(float(x),float(y))) for img,x,y in zip(images,l[1::2],l[2::2]) if x != '' or y != '' ]
            for img,p in pos:
                data[img][i] = p
            self._last_pt_id = i
        cell_division = False
        if cell_list:
            for cell,l in enumerate(r):
                if len(l) == 1 and l[0].lower() == "divisions":
                    cell_division = True
                    break
                pts_ids = [ int(i) for i in l[1:] ]
                cells[cell] = tuple(pts_ids)
                self._last_cell_id = cell
                cells_lifespan[cell] = LifeSpan()
        if cell_division:
            for l in r:
                cell = int(l[0].split()[1])
                div_time = int(l[1])
                daughters = (int(l[2]),int(l[3]))
                division = (int(l[4]),int(l[5]))
                ls = cells_lifespan[cell]
                ls.end = div_time
                ls.daughters = daughters
                ls.division = division
                ls1 = cells_lifespan[daughters[0]]
                ls1.start = div_time
                ls1.parent = cell
                ls2 = cells_lifespan[daughters[1]]
                ls2.start = div_time
                ls2.parent = cell
#                print("Cell %s divided at time %s" % (repr(cell), repr(div_time)))
#            for i in range(len(cells)):
#                print("%d: %s" % (i, cells_lifespan[i]))
            for cid,ls in cells_lifespan.iteritems():
                if ls.daughters:
                    cells_lifespan[ls.daughters[0]].parent = cid
                    cells_lifespan[ls.daughters[1]].parent = cid
        return self._set_data(data, shifts, scales, cells, cells_lifespan)

    def load_version0_4(self, f, has_version = True, **opts):
        """
        Load files for version 0.4
        """
        r = csv.reader(f, delimiter=",")
        if has_version:
            version = r.next()
            assert compare_versions(version[1], "0.4") >= 0
        title = r.next()
        num_columns = len(title)
        if num_columns % 2 == 0:
            raise TrackingDataException("Incorrect number of columns in title line. Odd number expected.")
        num_columns -= 1
        #num_img = num_columns/2
        images = title[1::2]
        data = {}
        shifts = {}
        scales = {}
        for img in images:
            data[img] = {}
            shifts[img] = [QPointF(0,0), 0]
            scales[img] = (1,1)
# First, read the shifts for each image
        times = range(len(images))
        for i in range(2):
            shift = r.next()
            if shift[0] == "XY Shift":
                if len(shift) != num_columns+1:
                    raise TrackingDataException("Incorrect number of XY shifting values. There should be two shifting value per image")
                xshift = shift[1::2]
                yshift = shift[2::2]
                for img,x,y in zip(images, xshift, yshift):
                    shifts[img][0] = QPointF(float(x), float(y))
            elif shift[0] == "Angle Shift-Time":
                if len(shift) != num_columns+1:
                    raise TrackingDataException("Incorrect number of angle shifting values. There should be one shifting value per image")
                ashift = shift[1::2]
                for img,a in zip(images, ashift):
                    shifts[img][1] = float(a)
                times = [float(t) for t in shift[2::2]]
        cell_list = False
        cells = {}
        cells_lifespan = {}
        for i,l in enumerate(r):
            if len(l) == 1 and l[0].lower() == "cells":
                cell_list = True
                break
            if len(l) != num_columns+1:
                raise TrackingDataException("Incorrect number of columns in line %d: %d instead of %d expected" % (i+1, len(l), num_columns+1))
            pos = [ (img,QPointF(float(x),float(y))) for img,x,y in zip(images,l[1::2],l[2::2]) if x != '' or y != '' ]
            for img,p in pos:
                data[img][i] = p
            self._last_pt_id = i
        cell_division = False
        if cell_list:
            for cell,l in enumerate(r):
                if l and l[0].lower() == "divisions":
                    cell_division = True
                    break
                pts_ids = [ int(i) for i in l[1:] ]
                cells[cell] = tuple(pts_ids)
                self._last_cell_id = cell
                cells_lifespan[cell] = LifeSpan()
        if cell_division:
            for l in r:
                cell = int(l[0].split()[1])
                div_time = int(l[1])
                daughters = (int(l[2]),int(l[3]))
                division = (int(l[4]),int(l[5]))
                ls = cells_lifespan[cell]
                ls.end = div_time
                ls.daughters = daughters
                ls.division = division
                ls1 = cells_lifespan[daughters[0]]
                ls1.start = div_time
                ls1.parent = cell
                ls2 = cells_lifespan[daughters[1]]
                ls2.start = div_time
                ls2.parent = cell
#                print("Cell %s divided at time %s" % (repr(cell), repr(div_time)))
#            for i in range(len(cells)):
#                print("%d: %s" % (i, cells_lifespan[i]))
            for cid,ls in cells_lifespan.iteritems():
                if ls.daughters:
                    cells_lifespan[ls.daughters[0]].parent = cid
                    cells_lifespan[ls.daughters[1]].parent = cid
        return self._set_data(data, shifts, scales, cells, cells_lifespan, times)

    def load_version0_5(self, f, has_version = True, **opts):
        """
        Load files for version 0.5
        """
        r = csv.reader(f, delimiter=",")
        if has_version:
            version = r.next()
            assert compare_versions(version[1], "0.5") >= 0
        title = r.next()
        num_columns = len(title)
        if num_columns % 2 == 0:
            raise TrackingDataException("Incorrect number of columns in title line. Odd number expected.")
        num_columns -= 1
        #num_img = num_columns/2
        images = title[1::2]
        data = {}
        shifts = {}
        scales = {}
        for img in images:
            data[img] = {}
            shifts[img] = [QPointF(0,0), 0]
            scales[img] = (1,1)
# First, read the shifts for each image
        times = range(len(images))
        for i in range(3):
            shift = r.next()
            if shift[0] == "XY Shift":
                if len(shift) != num_columns+1:
                    raise TrackingDataException("Incorrect number of XY shifting values. There should be two shifting value per image")
                xshift = shift[1::2]
                yshift = shift[2::2]
                for img,x,y in zip(images, xshift, yshift):
                    shifts[img][0] = QPointF(float(x), float(y))
            elif shift[0] == "Angle Shift-Time":
                if len(shift) != num_columns+1:
                    raise TrackingDataException("Incorrect number of angle shifting values. There should be one shifting value per image")
                ashift = shift[1::2]
                for img,a in zip(images, ashift):
                    shifts[img][1] = float(a)
                times = [float(t) for t in shift[2::2]]
            elif shift[0] == "Scaling" and not opts.get('IgnoreScaling', False):
                if len(shift) != num_columns+1:
                    raise TrackingDataException("Incorrect number of scaling values. There should be two scaling values per image (x and y)")
                xscale = shift[1::2]
                yscale = shift[2::2]
                for img,x,y in zip(images, xscale, yscale):
                    print_debug('scale[%s] = (%s,%s)' % (repr(img), repr(x), repr(y)))
                    x = float(x)
                    y = float(y)
                    if x == 0 or y == 0:
                        raise RetryTrackingDataException("The file contains invalid scaling specification. Do you want to load it ignoring the scaling?", "IgnoreScaling")
                    scales[img] = (x,y)
        cell_list = False
        cells = {}
        cells_lifespan = {}
        for i,l in enumerate(r):
            if len(l) == 1 and l[0].lower() == "cells":
                cell_list = True
                break
            if len(l) != num_columns+1:
                raise TrackingDataException("Incorrect number of columns in line %d: %d instead of %d expected" % (i+1, len(l), num_columns+1))
            pos = [ (img,QPointF(float(x),float(y))) for img,x,y in zip(images,l[1::2],l[2::2]) if x != '' or y != '' ]
            for img,p in pos:
                data[img][i] = p
            self._last_pt_id = i
        cell_division = False
        if cell_list:
            for cell,l in enumerate(r):
                if l and l[0].lower() == "divisions":
                    cell_division = True
                    break
                pts_ids = [ int(i) for i in l[1:] ]
                cells[cell] = tuple(pts_ids)
                self._last_cell_id = cell
                cells_lifespan[cell] = LifeSpan()
        if cell_division:
            for l in r:
                if not l[0].startswith("Cell"):
                    break
                cell = int(l[0].split()[1])
                div_time = int(l[1])
                daughters = (int(l[2]),int(l[3]))
                division = (int(l[4]),int(l[5]))
                ls = cells_lifespan[cell]
                ls.end = div_time
                ls.daughters = daughters
                ls.division = division
                ls1 = cells_lifespan[daughters[0]]
                ls1.start = div_time
                ls1.parent = cell
                ls2 = cells_lifespan[daughters[1]]
                ls2.start = div_time
                ls2.parent = cell
#                print "Cell %s divided at time %s" % (repr(cell), repr(div_time))
#            for i in range(len(cells)):
#                print "%d: %s" % (i, cells_lifespan[i])
            for cid,ls in cells_lifespan.iteritems():
                if ls.daughters:
                    cells_lifespan[ls.daughters[0]].parent = cid
                    cells_lifespan[ls.daughters[1]].parent = cid
        return self._set_data(data, shifts, scales, cells, cells_lifespan, times)

    def load_version0_6(self, f, has_version = True, **opts):
        """
        Load files for version 0.6
        """
        r = csv.reader(f, delimiter=",")
        if has_version:
            version = r.next()
            assert compare_versions(version[1], "0.6") >= 0
        title = r.next()
        num_columns = len(title)
        if num_columns % 2 == 0:
            raise TrackingDataException("Incorrect number of columns in title line. Odd number expected.")
        num_columns -= 1
        #num_img = num_columns/2
        images = title[1::2]
        data = {}
        shifts = {}
        scales = {}
        for img in images:
            data[img] = {}
            shifts[img] = [QPointF(0,0), 0]
            scales[img] = (1,1)
# First, read the shifts for each image
        times = range(len(images))
        for i in range(3):
            shift = r.next()
            if shift[0] == "XY Shift":
                if len(shift) != num_columns+1:
                    raise TrackingDataException("Incorrect number of XY shifting values. There should be two shifting value per image")
                xshift = shift[1::2]
                yshift = shift[2::2]
                for img,x,y in zip(images, xshift, yshift):
                    shifts[img][0] = QPointF(float(x), float(y))
            elif shift[0] == "Angle Shift-Time":
                if len(shift) != num_columns+1:
                    raise TrackingDataException("Incorrect number of angle shifting values. There should be one shifting value per image")
                ashift = shift[1::2]
                for img,a in zip(images, ashift):
                    shifts[img][1] = float(a)
                times = [float(t) for t in shift[2::2]]
            elif shift[0] == "Scaling" and not opts.get('IgnoreScaling', False):
                if len(shift) != num_columns+1:
                    raise TrackingDataException("Incorrect number of scaling values. There should be two scaling values per image (x and y)")
                xscale = shift[1::2]
                yscale = shift[2::2]
                for img,x,y in zip(images, xscale, yscale):
                    print_debug('scale[%s] = (%s,%s)' % (repr(img), repr(x), repr(y)))
                    x = float(x)
                    y = float(y)
                    if x == 0 or y == 0:
                        raise RetryTrackingDataException("The file contains invalid scaling specification. Do you want to load it ignoring the scaling?", "IgnoreScaling")
                    scales[img] = (x,y)
        cell_list = False
        cells = {}
        cells_lifespan = {}
        delta = 0
        for i,l in enumerate(r):
            if not l:
                delta += 1
                continue
            if len(l) == 1 and l[0].lower() == "cells":
                print_debug("Found list of cells")
                cell_list = True
                break
            elif not l[0].lower().startswith("point"):
                print_debug("No more points: " + l[0])
                break
            elif len(l) != num_columns+1:
                raise TrackingDataException("Incorrect number of columns in line %d: %d instead of %d expected" % (i+1, len(l), num_columns+1))
            pid = i - delta
            pos = [ (img,QPointF(float(x),float(y))) for img,x,y in zip(images,l[1::2],l[2::2]) if x != '' or y != '' ]
            for img,p in pos:
                data[img][pid] = p
            self._last_pt_id = pid
        cell_division = False
        if cell_list:
            delta = 0
            for line_cell,l in enumerate(r):
                if not l:
                    delta += 1
                    continue
                if l[0].lower() == "divisions":
                    print_debug("Found division")
                    cell_division = True
                    break
                elif not l[0].lower().startswith("cell"):
                    print_debug("No more cell: " + l[0])
                    break
                cell = line_cell - delta
                pts_ids = [ int(i) for i in l[1:] ]
                cells[cell] = tuple(pts_ids)
                self._last_cell_id = cell
                cells_lifespan[cell] = LifeSpan()
        lifespan_of_cells = False
        if cell_division:
            for l in r:
                if not l:
                    continue
                if l[0].lower() == "lifespan of cells":
                    print_debug("Found life span of cells")
                    lifespan_of_cells = True
                    break
                elif not l[0].lower().startswith("cell"):
                    print_debug("No more cell: " + l[0])
                    break
                cell = int(l[0].split()[1])
                div_time = int(l[1])
                daughters = (int(l[2]),int(l[3]))
                division = (int(l[4]),int(l[5]))
                ls = cells_lifespan[cell]
                ls.end = div_time
                ls.daughters = daughters
                ls.division = division
                ls1 = cells_lifespan[daughters[0]]
                ls1.start = div_time
                ls1.parent = cell
                ls2 = cells_lifespan[daughters[1]]
                ls2.start = div_time
                ls2.parent = cell
#                print "Cell %s divided at time %s" % (repr(cell), repr(div_time))
#            for i in range(len(cells)):
#                print "%d: %s" % (i, cells_lifespan[i])
            for cid,ls in cells_lifespan.iteritems():
                if ls.daughters:
                    cells_lifespan[ls.daughters[0]].parent = cid
                    cells_lifespan[ls.daughters[1]].parent = cid
        has_wall_shapes = False
        if lifespan_of_cells:
            for l in r:
                if not l:
                    continue
                if l[0].lower() == "wall shapes":
                    print_debug("Found wall shapes")
                    has_wall_shapes = True
                    break
                elif not l[0].lower().startswith("cell"):
                    print_debug("No more cell: " + l[0])
                    break
                cell = int(l[0].split()[1])
                start = int(l[1])
                end = int(l[2])
                ls = cells_lifespan[cell]
                ls.end = end
                ls.start = start
        wall_shapes = None
        if has_wall_shapes:
            wall_shapes = WallShapes()
            for l in r:
                if not l:
                    continue
                if not l[0].lower().startswith("wall"):
                    break
                time = int(l[1])
                p1 = int(l[2])
                p2 = int(l[3])
                pos = [ float(f) for f in l[4:] if f]
                assert len(pos) % 2 == 0
                pos = [ QPointF(pos[i],pos[i+1]) for i in range(0,len(pos),2) ]
                wall_shapes[time, p1, p2] = pos
                print_debug("wall shape from %d to %d at time %d =\n%s" % (p1, p2, time, ", ".join("%f,%f" % (p.x(), p.y()) for p in pos)))
        else:
            print_debug("No wall shape!")
        return self._set_data(data, shifts, scales, cells, cells_lifespan, times, wall_shapes)

    versions_loader = {
            "0.0": load_version0,
            "0.1": load_version0_1,
            "0.2": load_version0_2,
            "0.3": load_version0_3,
            "0.4": load_version0_4,
            "0.5": load_version0_5,
            "0.6": load_version0_6
            }

    """
    Loader methods for each version of the files

    :type: dict of str*methods
    """

    CURRENT_VERSION = 0.5
    """
    Current version of the file format

    :type: str
    """

    def load(self, data_file = None, f = None, **opts):
        """
        Read the data from the data file

        :raise TrackingDataException:
        :returns: True if the data were changed while loading (typically if invalid data were corrected
        :returntype: bool
        """
        if f is None:
            if data_file is None:
                raise TrackingDataException("You need to provide either a data file path or an opened file object")
            f = open(data_file, "rb")
            # if there is no project specified, try to find it
            if not self.project_dir:
                p = path(data_file).dirname()
                self.project_dir = p.parent
        r = csv.reader(f)
        first_line = r.next()
        if first_line and first_line[0] == "TRK_VERSION":
            try:
                version = first_line[1].strip()
            except IndexError:
                raise TrackingDataException("Incorrect file format: the version line does not contain a version number")
            self.clear()
            return self.load_version(version, f, False, **opts)
        else:
            version = "0"
            self.clear()
            return self.load_version(version, open(data_file, "rb"), True, **opts)

    def load_version(self, version, f, has_version=True, **opts):
        if version in TrackingData.versions_loader:
            return TrackingData.versions_loader[version](self, f, has_version=has_version, **opts)
        else:
            return TrackingData.versions_loader[TrackingData.CURRENT_VERSION](self, f, has_version=has_version, **opts)

    def save(self, data_file=None, f = None):
        if self.walls.empty():
            result = self.save_0_5(data_file, f)
        else:
            result = self.save_0_6(data_file, f)
        self.emit(SIGNAL("saved"))
        return result

    def save_0_6(self, data_file, f = None):
        num_img = len(self.images_name)
        pts = set()
        data = self.data
        for i in data:
            pts.update(data[i].keys())
        pts = list(pts)
        pts.sort()
        invert_pts = dict( (p,i) for i,p in enumerate(pts) )
        invert_images = dict( (img,i) for i,img in enumerate(self.images_name) )
        num_pts = len(pts)
        num_columns = num_img*2+1
        array = numpy.zeros((num_pts,num_columns), dtype='S20')
        for img in data:
            d = data[img]
            img_num = 2*invert_images[img]
            col = img_num+1
            column = array[:,col:col+2] # Just a view on the column
            for p in d:
                i = invert_pts[p]
                pos = d[p]
                column[i] = [str(pos.x()), str(pos.y())]
        cells = self.cells
        ordered_cells = cells.keys()
        ordered_cells.sort()
        cells_lifespan = self.cells_lifespan
        new_cells = []
        divisions = []
        life_spans = []
        cells_ids = []
        invert_cells = dict( (c,i) for i,c in enumerate(ordered_cells) )
        for i,c in enumerate(ordered_cells):
            ls = cells_lifespan[c]
            cell_name = "Cell %d" % i
            new_cells.append([cell_name] + [ invert_pts[pt] for pt in cells[c] ])
            cells_ids.append(c)
            if ls.daughters is not None:
                divisions.append([cell_name, ls[1], invert_cells[ls[3]],
                    invert_cells[ls[4]], invert_pts[ls[5]], invert_pts[ls[6]] ])
            life_spans.append([cell_name, ls[0], ls[1] ])
        invert_cells = dict( (c,i) for i,c in enumerate(cells_ids) )
        array[:,0] = ["Point %d" % i for i in range(num_pts)]
        # Now, prepare walls
        walls = self.walls
        wall_list = []
        wid = 0
        cells = self.cells
        for (t,p1,p2) in walls:
            wall_name = "Wall %d" % wid
            wid += 1
            wall_list.append([wall_name,t,invert_pts[p1], invert_pts[p2]]+ sum([[p.x(), p.y()] for p in walls[t,p1,p2]], []))
#        for img in self.images_name:
#            data = self[img]
#            t = data.index
#            for cid in cells:
#                cell = [ pid for pid in cells[cid] if pid in data ]
#                if len(cell)>1:
#                    p1 = cell[-1]
#                    for p2 in cell:
#                        w = walls[t,p1,p2]
#                        wall_name = "Wall %d" % wid
#                        wid += 1
#                        wall_list.append([wall_name,t,invert_pts[p1],invert_pts[p2]] + sum([[p.x(), p.y()] for p in w ], []))
#                        p1 = p2

        if f is None:
            f = open(data_file, "wb")
        w = csv.writer(f, delimiter=",")
        w.writerow(["TRK_VERSION", "0.6"])
        title = ['']*num_columns
        title[0] = "Images"
        title[1::2] = self.images_name
        w.writerow(title)
        xyshift = ['']*num_columns
        xyshift[0] = "XY Shift"
        shifts = self.images_shift
        xyshift[1::2] = [shifts[img][0].x() for img in self.images_name]
        xyshift[2::2] = [shifts[img][0].y() for img in self.images_name]
        w.writerow(xyshift)
        ashift = ['']*num_columns
        ashift[0] = "Angle Shift-Time"
        ashift[1::2] = [shifts[img][1] for img in self.images_name]
        ashift[2::2] = [ repr(t) for t in self._images_time ]
        w.writerow(ashift)
        scales = self.images_scale
        sc_row = ("Scaling",) + sum([ scales[img] for img in self.images_name ], ())
        w.writerow(sc_row)
        w.writerows(array)
        w.writerow(["Cells"])
        for c in new_cells:
            w.writerow(c)
        w.writerow(["Divisions", "Time", "Daughter cell 1", "Daughter cell 2", "Division point 1", "Division point 2"])
        for c in divisions:
            w.writerow(c)
        w.writerow(["LifeSpan of cells","Birth","Death"])
        for c in life_spans:
            w.writerow(c)
        w.writerow(["Wall shapes","Time","Point 1","Point 2","Positions (x,y)"])
        for c in wall_list:
            w.writerow(c)
        return invert_pts, invert_cells


    def save_0_5(self, data_file = None, f = None):
        """
        Save all the data into the file format 0.6

        :raise TrackingDataException:
        """
# First, prepare the data to be written fast
        num_img = len(self.images_name)
        pts = set()
        data = self.data
        for i in data:
            pts.update(data[i].keys())
        pts = list(pts)
        pts.sort()
        invert_pts = dict( (p,i) for i,p in enumerate(pts) )
        invert_images = dict( (img,i) for i,img in enumerate(self.images_name) )
        num_pts = len(pts)
        num_columns = num_img*2+1
        array = numpy.zeros((num_pts,num_columns), dtype='S20')
        for img in data:
            d = data[img]
            img_num = 2*invert_images[img]
            col = img_num+1
            column = array[:,col:col+2] # Just a view on the column
            for p in d:
                i = invert_pts[p]
                pos = d[p]
                column[i] = [str(pos.x()), str(pos.y())]
        cells = self.cells
        ordered_cells = cells.keys()
        ordered_cells.sort()
        cells_lifespan = self.cells_lifespan
        new_cells = []
        divisions = []
        life_spans = []
        cells_ids = []
        invert_cells = dict( (c,i) for i,c in enumerate(ordered_cells) )
        for i,c in enumerate(ordered_cells):
            ls = cells_lifespan[c]
            cell_name = "Cell %d" % i
            new_cells.append([cell_name] + [ invert_pts[pt] for pt in cells[c] ])
            cells_ids.append(c)
            if ls.daughters is not None:
                divisions.append([ cell_name, ls[1], invert_cells[ls[3]],
                    invert_cells[ls[4]], invert_pts[ls[5]], invert_pts[ls[6]] ])
                life_spans.append([ cell_name, ls[0], ls[1] ])
        invert_cells = dict( (c,i) for i,c in enumerate(cells_ids) )

        array[:,0] = ["Point %d" % i for i in range(num_pts)]
        if f is None:
            f = open(data_file, "wb")
        w = csv.writer(f, delimiter=",")
        w.writerow(["TRK_VERSION", "0.5"])
        title = ['']*num_columns
        title[0] = "Images"
        title[1::2] = self.images_name
        w.writerow(title)
        xyshift = ['']*num_columns
        xyshift[0] = "XY Shift"
        shifts = self.images_shift
        xyshift[1::2] = [shifts[img][0].x() for img in self.images_name]
        xyshift[2::2] = [shifts[img][0].y() for img in self.images_name]
        w.writerow(xyshift)
        ashift = ['']*num_columns
        ashift[0] = "Angle Shift-Time"
        ashift[1::2] = [shifts[img][1] for img in self.images_name]
        ashift[2::2] = [ repr(t) for t in self._images_time ]
        w.writerow(ashift)
        scales = self.images_scale
        sc_row = ("Scaling",) + sum([ scales[img] for img in self.images_name ], ())
        w.writerow(sc_row)
        w.writerows(array)
        w.writerow(["Cells"])
        for c in new_cells:
            w.writerow(c)
        w.writerow(["Divisions", "Time", "Daughter cell 1", "Daughter cell 2", "Division point 1", "Division point 2"])
        for c in divisions:
            w.writerow(c)
        return invert_pts, invert_cells

    def prepareData(self):
        """
        Make sure the data structure is ready. This means that each image has
        a dictionnary ready to store data in and there are no useless dictionnaries.
        """
        data = self.data
        names = set(self.images_name)
        for img in data.keys():
            if img not in names:
                del data[img]
        for img in names:
            if img not in data:
                data[img] = {}
        shifts = dict((img, [QPointF(), 0]) for img in names)
        scales = dict((img, (1,1)) for img in names)
        self._set_data(data, shifts, scales)

    def clear(self):
        """
        Remove all the points from the data and reset the position of the images
        """
        data = self.data
        shifts = self.images_shift
        scales = self.images_scale
        cells = self.cells
        self.walls = WallShapes()
        for t in range(len(self.images_name)):
            self.walls.add_time(t)
        for img, pts in data.iteritems():
            self.emit(SIGNAL("pointsDeleted"), img, pts.keys())
            pts.clear()
            self.emit(SIGNAL("imageMoved"), img, (1,1), QPointF(0,0), 0)
            shifts[img] = [QPointF(0,0), 0]
            scales[img] = (1,1)
        if cells:
            self.emit(SIGNAL("cellsRemoved"), cells.keys())
        cells.clear()
        self.cells_lifespan.clear()
        self.cell_points.clear()
        self._min_scale = 1.0
        for data in self:
            self._imageMoved(data.image_name, data.scale, *data.shift)

    def createNewPoint(self):
        """
        Reserve a new point id and returns it.
        """
        self._last_pt_id += 1
        return self._last_pt_id

    def createNewCell(self):
        """
        Reserve a new cell id and returns it.
        """
        self._last_cell_id += 1
        return self._last_cell_id

    def __getitem__(self, image_name):
        """
        Return the data associated with an image

        :Arguments:
            image_name : str|int
                If the argument is an integer, return the nth image, otherwise, returns the image whose name is image_name
        """
        try:
            return ImageData(self, self.images_name[image_name])
        except TypeError:
            return ImageData(self, image_name)

    def __contains__(self, image_name):
        return image_name in self.data

    def __len__(self):
        """
        Number of images in the data set
        """
        return len(self.images_name)

    def __iter__(self):
        """
        Iterate over the images
        """
        for img in self.images_name:
            yield ImageData(self, img)

    def deletePointInAll(self, pt_id):
        """
        Delete a point in all the images
        """
        for img in self.data.itervalues():
            if pt_id in img:
                del img[pt_id]

    def imagesWithPoint(self, pt_id):
        """
        Return the list of images containing a points.

        Returns: list of str
        """
        return [img for img in self.images_name if pt_id in self.data[img] ]

    def _pointsAdded(self, image_name, ids):
        self.emit(SIGNAL("pointsAdded"), image_name, ids)

    def _pointsMoved(self, image_name, ids):
        self.emit(SIGNAL("pointsMoved"), image_name, ids)

    def _pointsDeleted(self, image_name, ids):
        self.emit(SIGNAL("pointsDeleted"), image_name, ids)

    def _imageMoved(self, image_name, scale, pos, angle):
        self.emit(SIGNAL("imageMoved"), image_name, scale, pos, angle)

    def _dataChanged(self, image_name):
        self.emit(SIGNAL("dataChanged"), image_name)

    def _cellsAdded(self, cells, image_list = None):
        if image_list is not None:
            self.emit(SIGNAL("cellsAdded"), cells, image_list)
        else:
            #print "Emitting signal cellsAdded with arg %s" % (cells,)
            self.emit(SIGNAL("cellsAdded"), cells)

    def _cellsRemoved(self, cells, image_list = None):
        if image_list is not None:
            self.emit(SIGNAL("cellsRemoved"), cells, image_list)
        else:
            self.emit(SIGNAL("cellsRemoved"), cells)

    def _cellsChanged(self, cells):
        self.emit(SIGNAL("cellsChanged"), cells)

    def oldestAncestor(self, cid):
        """
        Return the oldest ancestor of the cell
        """
        cells_lifespan = self.cells_lifespan
        ls = cells_lifespan[cid]
        while ls.parent is not None:
            cid = ls.parent
        return cid
    
    def cellAtImage(self, cid, img):
        '''
        Return the shape of the cell cid in image img. That is, considering it might have divided.
        '''
        return self.cellAtTime(cid, self.images_name.index(img))
    
    def cellAtTime(self, cid, img):
        """
        Return the shape of the cell cid at time t. That is, considering it might have divided.
        """
        cells_lifespan = self.cells_lifespan
        ls = cells_lifespan[cid]
        img_data = self[img]
        t = img_data.index
        cells = self.cells
        if ls.start <= t and ls.end > t:
            return [ pid for pid in cells[cid] if pid in img_data ]
        if ls.start > t or ls.daughters is None:
            raise ValueError("The cell %d doesn't exit at time %d" % (cid, t))
        daughters = list(ls.daughters)
        final = []
        for did in daughters:
            lsd = cells_lifespan[did]
            if lsd.end > t:
                final.append(did)
            elif lsd.daughters is not None:
                daughters.extend(lsd.daughters)
        if not final:
            raise ValueError("The cell %d doesn't exist at time %d" % (cid, t))
        # Now, find the contour. But first, find the walls that form the exterior of the set of cells
        walls = set()
        for did in final:
            pts = [pid for pid in cells[did] if pid in img_data ]
            if not pts:
                raise ValueError("The cell %d doesn't exist at time %d" % (cid, t))
            prev = pts[-1]
            for pid in pts:
                if (pid, prev) in walls:
                    walls.remove((pid,prev))
                else:
                    walls.add((prev, pid))
                prev = pid
        # Next, find a point common between cid and the walls we have
        wallsd = dict(walls)
        if len(wallsd) != len(walls):
            raise ValueError("The contour of the childs of the cell is not unique.")
        walls = wallsd
        pts = cells[cid]
        for start in wallsd:
            if start in pts:
                break
        else:
            start = walls.keys()[0]
        pts = [start, walls[start]]
        while pts[-1] != start:
            try:
                pts.append(walls[pts[-1]])
            except KeyError:
                raise ValueError("The contour of the cell %d at time %d is not closed" % (cid, t))
        del pts[-1]
        return pts

    def parentCells(self, cid):
        """
        Returns all the parents of a cell (i.e. grand-parent, ...)

        Returns: list of int
        """
        parents = []
        cells_lifespan = self.cells_lifespan
        ls = cells_lifespan[cid]
        while ls.parent is not None:
            cid = ls.parent
            parents.append(cid)
            ls = cells_lifespan[cid]
        return parents

    def daughterCells(self, cid):
        """
        Returns all the daughters of a cell (i.e. grand-daughters, ...)

        Returns: list of int
        """
        daughters = []
        cells_lifespan = self.cells_lifespan
        cids = [cid]
        while cids:
            cid = cids.pop(0)
            ls = cells_lifespan[cid]
            ds = ls.daughters
            if ds is not None:
                daughters += ds
                cids += ds
        return daughters

    def sisterCell(self, cid):
        """
        Returns the sister of a cell if any

        Returns: int|None
        """
        cells_lifespan = self.cells_lifespan
        ls = cells_lifespan[cid]
        if ls.parent is None:
            return None
        ls1 = cells_lifespan[ls.parent]
        ans = list(ls1.daughters)
        ans.remove(cid)
        return ans[0]

    def commonAncestorCell(self, cid1, cid2):
        """
        Returns the closest common ancestor if any

        Returns: int|None
        """
        ps = set(self.parentCells(cid1))
        cells_lifespan = self.cells_lifespan
        ls = cells_lifespan[cid2]
        parent = ls.parent
        while parent is not None and parent not in ps:
            ls = cells_lifespan[parent]
            parent = ls.parent
        return parent

    def lifespan(self, cid):
        """
        Return the life span of the cell cid

        Returns: LifeSpan
        """
        return self.cells_lifespan[cid]
    
    def imagesWithCell(self, cid):
        return self.images_name[self.cells_lifespan[cid].slice()]
    
    def imagesWithLifespan(self, ls):
        return self.images_name[ls.slice()]

    def wallId(self, p1, p2):
        """
        :Parameters:
            p1 : int
                Id of a point
            p2 : int
                Id of a point

        Note that the wall does not have to exist for this function to work. The only condition is p1 != p2.

        :returns: the unique id of the wall from point p1 to p2.
        :returntype: (int,int)
        """
        assert p1!=p2, "A wall cannot start and end on the same point %d." % p1
        if p1 < p2:
            return (p1,p2)
        return (p2,p1)

    def wallCells(self, wid):
        """
        :Parameters:
            wid : (int,int)
                tuple of point if defining (or not) a wall
        :returns: the list of cells containing the wall as argument
        :returntype: list of int
        """
        cell_points = self.cell_points
        cells = self.cells
        wcells = cell_points[wid[0]] & cell_points[wid[1]]
        wall_cells = []
        for cid in wcells:
            pts = list(cells[cid])
            lpts = len(pts)-1
            i = pts.index(wid[0])
            j = pts.index(wid[1])
            if (abs(i-j) == 1) or (i==0 and j==lpts) or (j==0 and i==lpts):
                wall_cells.append(cid)
        return wall_cells

    def insertPointInWall(self,pt,wid):
        cells = self.cells
        point_cells = self.cell_points
        wcells = self.wallCells(wid)
        assert cells, "Wall (%d,%d) does not exist" % wid
        for c in wcells:
            if pt in cells[c]:
                continue
            pts = list(cells[c])
            i = pts.index(wid[1])
            if pts[i-1] == wid[0]:
                pts.insert(i, pt)
            else:
                pts.insert(i+1, pt)
            cells[c] = tuple(pts)
            point_cells[pt].add(c)
        self._cellsChanged(wcells)
        self.checkCells()


    def setCells(self, cell_ids, pt_ids_list, lifespans = None):
        """
        Create or change cells

        This function will call _cellsAdded and _cellsChanged methods to notify any listener.

        Arguments:
            `cell_ids` : (iter of int|int)
                list of cells to add/change
            `pt_ids_list` : (iter of (iter of int)|iter of int)
                list of list of points corresponding to each cell. cell_ids and 
                pt_ids_list must have the same number of elements.
            `lifespans` : None|`LifeSpan`
                New lifespan of the cells. If None, the lifespan is untouched.
        """
        cells = self.cells
        cell_points = self.cell_points
        cells_lifespan = self.cells_lifespan
        try:
            iter(cell_ids)
        except TypeError:
            if lifespans is not None:
                return self.setCells([cell_ids], [pt_ids_list], [lifespans])
            return self.setCells([cell_ids], [pt_ids_list])
        print_debug("Settings cells: %s" % ", ".join("%d" % c for c in cell_ids))
        cells_added = {}
        cells_changed = []
        cells_deleted = {}
        if lifespans is None:
            lifespans = [ cells_lifespan.get(cid, LifeSpan()) for cid in cell_ids ]
        for cell, pt_ids, ls in zip(cell_ids, pt_ids_list, lifespans):
            if cell in cells:
                for p in cells[cell]:
                    cell_points[p].remove(cell)
                for p in pt_ids:
                    cell_points.setdefault(p, set()).add(cell)
                cells_changed.append(cell)
                imgs_before = self.imagesWithCell(cell)
                imgs_after = self.imagesWithLifespan(ls)
                diff = [ img for img in imgs_after if img not in imgs_before ]
                if diff:
                    cells_added[cell] = diff
                diff = [ img for img in imgs_before if img not in imgs_after]
                if diff:
                    cells_deleted[cell] = diff
            else:
                for p in pt_ids:
                    cell_points.setdefault(p, set()).add(cell)
                cells_added[cell] = self.imagesWithLifespan(ls)
            cells[cell] = tuple(pt_ids)
            cells_lifespan[cell] = ls
        if cells_added:
            #print "Cells added: %s" % (cells_added,)
            self._cellsAdded(cells_added.keys(), cells_added.values())
        if cells_deleted:
            self._cellsRemoved(cells_deleted.keys(), cells_deleted.values())
        if cells_changed:
            self._cellsChanged(cells_changed)
        self.checkCells()
        
    def checkCells(self):
        cells = self.cells
        cell_points = self.cell_points
        for cid in cells:
            for p in cells[cid]:
                assert cid in cell_points[p]
        for p in cell_points:
            for cid in cell_points[p]:
                assert p in cells[cid]

    def changeCellsLifespan(self, cells, lifespans):
        """
        Change the lifespan of the cells and signal the listeners.

        Arguments:
          - cells, iter of int: list of cell ids to be changed
          - lifespans, iter of LifeSpan: list of new lifespans
        """
        cells_lifespan = self.cells_lifespan
        for cid, ls in zip(cells, lifespans):
            cur_ls = cells_lifespan[cid]
            cur_lst = set(self.images_name[cur_ls.slice()])
            new_lst = set(self.images_name[ls.slice()])
            add_cells = new_lst - cur_lst
            del_cells = cur_lst - new_lst
            cells_lifespan[cid] = ls
            if add_cells:
                self._cellsAdded([cid], [add_cells])
            if del_cells:
                self._cellsRemoved([cid], [del_cells])

    def removeCells(self, cell_ids):
        """
        Remove the cells specified.

        If the cell has parents, then the daughter cell will also be removed 
        and the parent life will be extended to the whole of the time.

        Arguments:
          - cell_ids, (iter of int|int): list of cell ids to be removed
        """
        try:
            iter(cell_ids)
        except TypeError:
            return self.removeCells([cell_ids])
        print_debug("Removing cells: %s" % ", ".join("%d" % c for c in cell_ids))
        cells = self.cells
        cells_lifespan = self.cells_lifespan
        cell_points = self.cell_points
        daughters = set()
        parents = set()
        for cid in cell_ids:
            daughters.update(self.daughterCells(cid))
            sisid = self.sisterCell(cid)
            if sisid:
                daughters.add(sisid)
                daughters.update(self.daughterCells(sisid))
                parents.add(cells_lifespan[cid].parent)
        cell_ids = list(set(cell_ids) | daughters)
        self._cellsRemoved(cell_ids)
        for cell in cell_ids:
            for p in cells[cell]:
                cell_points[p].remove(cell)
            del cells[cell]
            del cells_lifespan[cell]
        parents = list(parents)
        parents_newls = []
        for cid in parents:
            ls = cells_lifespan[cid].copy()
            ls.end = EndOfTime()
            del ls.daughters
            del ls.division
            parents_newls.append(ls)
        self.changeCellsLifespan(parents, parents_newls)
        self.checkCells()

    def setTimes(self, times):
        assert len(times) == len(self.images_time), "You can only use this function to reset the times of all images"
        self._images_time = [float(t) for t in times]

    def setScales(self, scales):
        self._min_scale = min(min(sc) for sc in scales)
        for data in self:
            size = tuple(scales[data.index])
            ratio_x = size[0] / data.scale[0]
            ratio_y = size[1] / data.scale[1]
            pids = list(data)
            self.images_scale[data.image_name] = size
            self._imageMoved(data.image_name, size, *data.shift)
            new_pos = [ QPointF(data[pid].x()*ratio_x, data[pid].y()*ratio_y) for pid in pids ]
            self._pointsMoved(data.image_name, pids)
            data[pids] = new_pos
            for (p1,p2) in data.walls:
                w = data.walls[p1,p2]
                new_w = [ QPointF(p.x()*ratio_x, p.y()*ratio_y) for p in w ]
                data.walls[p1,p2] = new_w
                
    def copyAlignementAndScale(self, other):
        for img_data in self:
            inv_old_mat, ok = img_data.matrix().inverted()
            if not ok:
                raise ValueError("Position matrix cannot be inverted")
            other_data = other[img_data.image_name]
            pos, angle = other_data.shift
            scale = other_data.scale
            self._imageMoved(img_data._current_image, scale, pos, angle)
            shift = [ pos, angle ]
            # Change position of the points
            self.images_shift[img_data.image_name] = shift
            self.images_scale[img_data.image_name] = scale
            mat = inv_old_mat*img_data.matrix()
            for pos in img_data.iterpositions():
                npos = mat.map(pos)
                pos.setX(npos.x())
                pos.setY(npos.y())
            # Change position of the walls
            for w in img_data.walls:
                wall = img_data.walls[w]
                new_wall = [ mat.map(pt) for pt in wall ]
                img_data.walls[w] = new_wall
            self._pointsMoved(img_data.image_name, img_data.points())

    def minScale(self):
        return self._min_scale

    def cleanCells(self):
        """
        Clean the cells from duplicated or invalid points and return what has been done.
        Also checks if the cells are oriented counter-clockwise or not.
        In case they are, reorient them correctly.

        :returns: The list of cells changed, and the shape of the cells before the change.
        :returntype: (list of int, list of (list of int))
        """
        saved_cells = []
        changed_cells = []
        cells = self.cells
        cell_points = self.cell_points
        for cid in cells:
            pt_ids = list(cells[cid])
            # First, find duplicate points
            to_remove = set(pt_id for pt_id in pt_ids if pt_ids.count(pt_id) > 1)
            if to_remove:
                saved_cells.append(cells[cid])
                changed_cells.append(cid)
                pos_to_remove = set()
                for pt_id in to_remove:
                    pos = -1
                    nb_pt_id = pt_ids.count(pt_id)
                    nb_removed = 0
                    while nb_pt_id > nb_removed+1:
                        try:
                            pos = pt_ids.index(pt_id, pos+1)
                            # Always remove successive points
                            if pt_ids[pos-1] == pt_id:
                                pos_to_remove.add(pos)
                                nb_removed += 1
                            else: # Try to figure out if the edge exist somewhere else
                                other_cids = list(cell_points[pt_id])
                                other_cids.remove(cid)
                                for pcids in self.parentCells(cid):
                                    if pcids in other_cids:
                                        other_cids.remove(pcids)
                                prev_pt_id = pt_ids[pos-1]
                                next_pt_id = pt_ids[(pos+1) % len(pt_ids)]
                                for ocid in other_cids:
                                    o_ptids = list(cells[ocid])
                                    oi = o_ptids.index(pt_id)
                                    prev_opt_id = o_ptids[oi-1]
                                    next_opt_id = o_ptids[(oi+1) % len(o_ptids)]
                                    if next_pt_id == prev_opt_id or prev_pt_id == next_opt_id:
                                        break
                                else:
                                    pos_to_remove.add(pos)
                                    nb_removed += 1
                        except ValueError:
                            pos = pt_ids.index(pt_id)
                            while pos in pos_to_remove:
                                pos = pt_ids.index(pt_id, pos+1)
                            pos_to_remove.add(pos)
                            nb_removed += 1
                pos_to_remove = list(pos_to_remove)
                pos_to_remove.sort(reverse=True)
                for pos in pos_to_remove:
                    del pt_ids[pos]
                cells[cid] = tuple(pt_ids)
            # Then, check the cell is oriented counter-clockwise
            # Remember, the reference system is inverted
            for img in self.imagesWithCell(cid):
                imgdata = self[img]
                walls = imgdata.walls
                pts = self.cellAtTime(cid, img)
                if len(pts) < 3:
                    continue
                geometry = sum([walls[pts[i-1], pts[i]] + [imgdata[pts[i]]] for i in range(len(pts))],[])
                area = 0
                for i in range(len(geometry)):
                    p1 = geometry[i-1]
                    p2 = geometry[i]
                    area += cross(p1, p2)
                if area < 0:
                    saved_cells.append(cells[cid])
                    changed_cells.append(cid)
                    cells[cid] = cells[cid][::-1]
                    break
                elif area > 0:
                    break
        if changed_cells:
            self._cellsChanged(changed_cells)
        self.checkCells()
        return changed_cells, saved_cells

    def divisionPoints(self):
        """
        :returns: All the points ids involved in cell division.
        :returntype: set of int
        """
        result = set()
        for ls in self.cells_lifespan.values():
            if ls.division:
                result.update(ls.division)
        return result

class ImageData(QObject):
    """
    Class representing the data specific of one image in a data set.

    :IVariables:
        parent : `TrackingData`
            data set the image is part of
        _current_image : str
            name of the image this object represent
        _current_data : dict of int*QPointF
            positions of the points existing in this image
        shift : (QPointF, float)
            shift of the current image (translation, rotation)
        scale : (float, float)
            Size of a pixel in the current image
        _current_index : int
            position of the image in the image list
        cells : `TimedCells`
            cells existing in the image
        walls : `TimedWallShapes`
            walls existing in the image
    """
    def __init__(self, parent, image_name):
        QObject.__init__(self)
        self.parent = parent
        if image_name not in parent:
            try:
                image_name = parent.images_name[image_name]
            except Exception:
                raise ValueError("Invalid image name '%s'" % image_name)
        self._current_image = image_name
        self._current_data = parent.data[image_name]
        self._current_index = parent.images_name.index(image_name)
        self.cells = TimedCells(self)
        self.walls = TimedWallShapes(parent.walls, self._current_index)

    def _get_index(self):
        return self._current_index

    index = property(_get_index)

    def _get_image_name(self):
        """
        Name of the current image
        """
        return self._current_image

    image_name = property(_get_image_name)

    def __iter__(self):
        """
        Return an iterator on the list of point ids
        """
        return iter(self._current_data)

    def points(self):
        """
        List of points in the current image

        Returns: list of int
        """
        return self._current_data.keys()

    def iterpoints(self):
        """
        Iterator over the points

        Returns: iter on int
        """
        return self._current_data.iterkeys()

    def positions(self):
        """
        List of positions for the points in the current image

        Returns: list of QPointF
        """
        return self._current_data.values()

    def iterpositions(self):
        """
        Iterator on the positions for the points in the current image

        Returns: iter of QPointF
        """
        return self._current_data.itervalues()

    def items(self):
        """
        List of tuples (id,position) for all points in the current image

        Returns: list of (int,QPointF)
        """
        return self._current_data.items()

    def iteritems(self):
        """
        Iterator on the tuples (id,position) for all points in the current image

        Returns: iter of (int,QPointF)
        """
        return self._current_data.iteritems()

    def __getitem__(self, pt_id):
        """
        Get the position of a points

        Arguments:
          - pt_id, (int|iter of int): (list of) points to get the position of

        Returns: (QPointF|list of QPointF)
        """
        cd = self._current_data
        try:
            return [ cd[i] for i in pt_id ]
        except TypeError:
            return cd[pt_id]

    def __setitem__(self, pt_id, value):
        """
        Set the position of a point or a list of points

        Arguments:
          - pt_id, (int|iter of int): (list of) points
          - value, (QPointF|iter of QPointF): (list of) positions
        """
        try:
            iter(pt_id)
        except TypeError:
            return self.__setitem__([pt_id], [value])
        data = self._current_data
        moved = []
        added = []
        for i, val in zip(pt_id, value):
            if i in data:
                moved.append(i)
            else:
                added.append(i)
            data[i] = val
            self.parent.cell_points.setdefault(i, set())
        if moved:
            self.parent._pointsMoved(self._current_image, moved)
        if added:
            self.parent._pointsAdded(self._current_image, added)
        self.parent.checkCells()

    def __delitem__(self, pt_id):
        """
        Delete a (lists of) points from the current image

        Arguments:
          - pt_id, (int|iter of int): (List of) point(s) to be deleted
        """
        try:
            iter(pt_id)
        except TypeError:
            return self.__delitem__([pt_id])
        parent = self.parent
        parent._pointsDeleted(self._current_image, pt_id)
        data = self._current_data
        for pt in pt_id:
            del data[pt]
# Figure out if the point still exists at all, and if not, if any cell has to 
# be deleted
        cell_points = parent.cell_points
        cells = parent.cells
        delete_cells = set()
        change_cells = set()
        saved_cells = {}
        for pt in pt_id:
            imgs = parent.imagesWithPoint(pt)
            if not imgs:
                for cid in cell_points[pt]:
                    for cid in saved_cells:
                        saved_cells[cid] = cells[cid]
                    cells[cid] = tuple(p for p in cells[cid] if p != pt)
                    change_cells.add(cid)
                    if not cells[cid]:
                        delete_cells.add(cid)
                del cell_points[pt]
        if change_cells:
            cc = list(change_cells)
            parent._cellsChanged(cc)
        if delete_cells:
            dc = list(delete_cells)
            parent._cellsRemoved(dc)
            for cid in delete_cells:
                del cells[cid]
        parent.checkCells()

    def simulate_delete(self, pt_id):
        """
        Simulate the deletion of a (list of) points and returns first the list of 
        deleted cells and second the list of changed cells.

        Returns: (list of int, list of int)
        """
        try:
            iter(pt_id)
        except TypeError:
            return self.simulate_delete([pt_id])
        parent = self.parent
        #data = self._current_data
        cell_points = parent.cell_points
        cells = parent.cells
        deleted_points = set()
        for pt in pt_id:
            imgs = parent.imagesWithPoint(pt)
            if list(imgs) == [self._current_image]:
                deleted_points.add(pt)
        deleted_cells = set()
        changed_cells = set()
        for pt in deleted_points:
            for cid in cell_points[pt]:
                if cid in deleted_cells or cid in changed_cells:
                    continue
                cell = list(cells[cid])
                for p in deleted_points:
                    try:
                        cell.remove(p)
                    except ValueError:
                        pass
                if not cell:
                    deleted_cells.add(cid)
                else:
                    changed_cells.add(cid)
        return list(deleted_cells), list(changed_cells)

    def __contains__(self, pt_id):
        """
        Check if a point exists in the current image

        Returns: bool
        """
        return pt_id in self._current_data

    def __len__(self):
        """
        Number of points in the image
        """
        return len(self._current_data)

    def createNewPoint(self):
        """
        Reserve an identifier for a new points

        Returns: int
        """
        return self.parent.createNewPoint()

    def move(self, pos, angle):
        """
        Move the current image.

        Also change the position of all the points to reflect the movement of the image

        Arguments:
          - pos, QPointF: new position for the top-left corner of the image
          - angle, float: new orientation for the image
        """
        if pos != self.shift[0] or angle != self.shift[1]:
            inv_old_mat, ok = self.matrix().inverted()
            if not ok:
                raise ValueError("Position matrix cannot be inverted")
            self.parent._imageMoved(self._current_image, self.scale, pos, angle)
            shift = [ pos, angle ]
            # Change position of the points
            self.parent.images_shift[self._current_image] = shift
            mat = inv_old_mat*self.matrix()
            for pos in self.iterpositions():
                npos = mat.map(pos)
                pos.setX(npos.x())
                pos.setY(npos.y())
            # Change position of the walls
            for w in self.walls:
                wall = self.walls[w]
                new_wall = [ mat.map(pt) for pt in wall ]
                self.walls[w] = new_wall
            self.parent._pointsMoved(self._current_image, self.points())

    def _get_shift(self):
        return self.parent.images_shift[self.image_name]

    shift = property(_get_shift)
    
    def _get_scale(self):
        """
        Set the scale of the current image
        """
        return self.parent.images_scale[self.image_name]

    scale = property(_get_scale)

    def matrix(self):
        """
        Returns the transformation matrix of the image.

        Returns: QTransform
        """
        mat = QTransform()
        mat.scale(*self.scale)
        mat.translate(self.shift[0].x(), self.shift[0].y())
        mat.rotate(self.shift[1])
        return mat

    def _get_time(self):
        """
        Time at which the image was taken
        """
        return self.parent._images_time[self._current_index]

    def _set_time(self, time):
        time = float(time)
        images_time = self.parent._images_time
        idx = self._current_index
        if idx > 0:
            t = images_time[idx-1]
            if t >= time:
                raise TrackingDataException("The time values have to be strictly increasing")
        if idx < len(images_time)-1:
            t = images_time[idx+1]
            if t <= time:
                raise TrackingDataException("The time values have to be strictly increasing")
        images_time[idx] = time

    time = property(_get_time, _set_time)

class TimedCells(object):
    """
    Represent the set of cells at a given time

    Instance variables:
      - _image_data, ImageData: Current image data
    """
    def __init__(self, image_data):
        self._image_data = image_data

    def __getitem__(self, cid):
        """
        Get the points id describing
        """
        image_data = self._image_data
        ls = image_data.parent.cells_lifespan[cid]
        if ls.start > image_data._current_index or ls.end <= image_data._current_index:
            raise KeyError(cid)
        return image_data.parent.cells[cid]

    def get(self, cid, value = None):
        image_data = self._image_data
        ls = image_data.parent.cells_lifespan.get(cid, None)
        if ls is None or ls.start > image_data._current_index or ls.end <= image_data._current_index:
            return value
        return image_data.parent.cells[cid]

    def __len__(self):
        idx = self._image_data._current_index
        return len([c for c,ls in self._image_data.parent.cells_lifespan.iteritems() if ls.start <= idx and ls.end > idx])

    def __iter__(self):
        idx = self._image_data._current_index
        for c,ls in self._image_data.parent.cells_lifespan.iteritems():
            if ls.start <= idx and ls.end > idx:
                yield c

    iterkeys = __iter__

    def keys(self):
        idx = self._image_data._current_index
        #cells = self._image_data.parent.cells
        return [ c for c,ls in self._image_data.parent.cells_lifespan.iteritems() if ls.start <= idx and ls.end > idx ]

    def values(self):
        idx = self._image_data._current_index
        cells = self._image_data.parent.cells
        return [ cells[c] for c,ls in self._image_data.parent.cells_lifespan.iteritems() if ls.start <= idx and ls.end > idx ]

    def items(self):
        idx = self._image_data._current_index
        cells = self._image_data.parent.cells
        return [ (c,cells[c]) for c,ls in self._image_data.parent.cells_lifespan.iteritems() if ls.start <= idx and ls.end > idx ]

    def itervalues(self):
        idx = self._image_data._current_index
        cells = self._image_data.parent.cells
        for c,ls in self._image_data.parent.cells_lifespan.iteritems():
            if ls.start <= idx and ls.end > idx:
                yield cells[c]

    def iteritems(self):
        idx = self._image_data._current_index
        cells = self._image_data.parent.cells
        for c,ls in self._image_data.parent.cells_lifespan.iteritems():
            if ls.start <= idx and ls.end > idx:
                yield c, cells[c]

    def __contains__(self, cid):
        ls = self._image_data.parent.cells_lifespan.get(cid, None)
        if ls is None:
            return False
        idx = self._image_data._current_index
        return ls.start <= idx and ls.end > idx

    has_key = __contains__

    def __str__(self):
        return "TimedCells{%s}" % ','.join("%s: %s" % (k,v) for k,v in self.iteritems())

    __repr__ = __str__

    def undivide(self, cid):
        """
        Undo the division of the cell cid at the current time.
        """
        image_data = self._image_data
        parent = image_data.parent
        idx = image_data._current_index
        cells = parent.cells
        cells_lifespan = parent.cells_lifespan
        cell_points = parent.cell_points
        ls = cells_lifespan[cid]
        if ls.end != idx:
            raise ValueError("%d was not divided on image %s. Cannot undo it." % (cid, image_data._current_image))
        childs = ls.daughters
        for c in childs:
            assert not parent.daughterCells(c), "Error, cannot undivide many levels at once and daughter cell %d is divided." % c
        parent._cellsRemoved(childs)
        for c in childs:
            for pt in cells[c]:
                cell_points[pt].remove(c)
            del cells[c]
            del cells_lifespan[c]
        ls.end = EndOfTime()
        del ls.daughters
        del ls.division
        parent._cellsAdded([cid], parent.images_name[idx:])
        parent.checkCells()

    def divide(self, cid, cid1, cid2, p1, p2):
        """
        Divide cid into cid1 and cid2 using [p1,p2] as a division line.
        """
        image_data = self._image_data
        parent = image_data.parent
        idx = image_data._current_index
        assert cid in self, "Cell %d cannot be divided at time %d as it does not exists" % (cid, idx)
        cells = parent.cells
        cells_lifespan = parent.cells_lifespan
        ls = cells_lifespan[cid]
        if ls.end != EndOfTime():
            raise ValueError("%d cannot be divided as it is already divided at time %d" % (cid, ls.end))
        if ls.start > idx:
            raise ValueError("%d cannot be divided at time %d, it does not exist yet" % (cid, idx))
        poly = list(cells[cid])
        try:
            i1 = poly.index(p1)
            i2 = poly.index(p2)
        except ValueError:
            raise ValueError("The division must be done by points contained by the polygon. Points %d and %d are not part of the cell %d." % (p1, p2, cid))
        ls = cells_lifespan[cid]
        ls.end = idx
        ls.division = (p1,p2)
        ls.daughters = (cid1,cid2)
        cells_lifespan[cid1] = LifeSpan(start=idx, parent=cid)
        cells_lifespan[cid2] = LifeSpan(start=idx, parent=cid)
        cell_points = parent.cell_points
        if i1 < i2:
            poly1 = poly[i1:i2+1]
            poly2 = poly[i2:]+poly[:i1+1]
        else:
            poly1 = poly[i1:]+poly[:i2+1]
            poly2 = poly[i2:i1+1]
        for pt in poly1:
            cell_points[pt].add(cid1)
        for pt in poly2:
            cell_points[pt].add(cid2)
        cells[cid1] = poly1
        cells[cid2] = poly2
        #print "Removing cell %d in images %s" % (cid, parent.images_name[idx:])
        #print "Added cells %d and %d in images %s" % (cid1, cid2, parent.images_name[idx:])
        parent._cellsRemoved([cid], parent.images_name[idx:])
        parent._cellsAdded([cid1,cid2])
        parent.checkCells()

