from __future__ import print_function, division, absolute_import
# vim: set fileencoding=utf-8 :
"""
This module defines the computation and selection methods for the growth computation.
"""
__author__ = "Pierre Barbier de Reuille <pierre@barbierdereuille.net>"
__docformat__ = "restructuredtext"

from .growth_algo import growthParams
from .geometry import polygonArea, dist
from math import log, ceil, pi
import csv
from .tracking_data import TrackingData, RetryTrackingDataException
import re
from .path import path
import sys
if sys.version_info.major < 3:
    from cStringIO import StringIO
else:
    from io import StringIO
from numpy import isnan, isinf, sqrt, array
from .debug import log_debug
from .project import Project

class GrowthResultException(Exception):
    """
    Exception launched by the `Result` object when an error linked to the
    data arise.
    """
    def __init__(self, text, **others):
        Exception.__init__(self, text)
        self.others = others

class Result(object):
    """
    :Ivariables:
        images_used : list of str
            name of the images used in the growth calculation
        images : list of str
            name of the images contained in the result
        cells : list of ( dict of int * (float,float,float,float) )
            Growth parameters for the cells for each image stored.
            The parameters are: kmaj, kmin, theta and psi, respectively the
            growth along the major and minor axis, the orientation of the major
            axis (i.e. angle from the x axis) and the rotation speed.
        method_params : list of str
            Parameters defining how growth was computed
        walls : list of ( dict of (int,int) * float )
            Relative growth rate for the walls. A wall is identified by a pair
            of points identifiers with the first number lower than the second.
        data : `TrackingData`
            Data used to calculate growth
    """
    def __init__(self, data, images_used = []):
        self.clear()
        self.data = data
        self.images_used = images_used

    def clear(self):
        self.images_used = []
        self.images = []
        self.cells = []
        self.walls = []
        self.cells_shapes = []
        self.cells_area = []
        self.method_params = []
        self.cells_selection_params = []
        self.data = None

    CURRENT_VERSION = "0.4"
    """
    Current version number for the results.
    """

    def addImage(self, image_name):
        self.images.append(image_name)
        self.cells.append({})
        self.walls.append({})
        self.cells_area.append({})
        self.cells_shapes.append({})
        return len(self.images)-1

    def __len__(self):
        return len(self.images)

    def set_data(self, row):
        if hasattr(self, "current_filename"):
            filename = path(self.current_filename).abspath()
        else:
            filename = path('.').abspath()
        if filename.isdir():
            p = filename
        else:
            p = filename.dirname()
        # Now, find the first directory that's a valid project
        proj = Project(p)
        while not proj.valid:
            if p == p.parent:
                raise GrowthResultException("Cannot find a valid project directory.")
            p = p.parent
            proj = Project(p)
        data = TrackingData(p)
        if len(row) > 1:
            data.data_file = p
            try:
                data.load()
            except Exception as ex:
                raise GrowthResultException("Error while loading data file: %s" % str(ex), previous=ex)
        self.data = data

    def get_data(self):
        return [] # Put the data at the end of the file
        data_file = self.data.data_file
        main_dir = self.data.project.main_dir
        if data_file.startswith(main_dir):
            data_file = path(data_file[len(main_dir):])
            data_file = data_file.splitall()[1:]
        else:
            data_file = data_file.splitall()
        return data_file

    def set_estimation(self, row):
        self.method_params = row[1:]

    def get_estimation(self):
        return self.method_params

    def set_cell_selection(self, row):
        self.cells_selection_params = row[1:]

    def get_cell_selection(self):
        return self.cells_selection_params

    def set_images_used(self, row):
        self.images_used = row[1:]

    def get_images_used(self):
        return self.images_used

    header_fields = {"Data file": (get_data, set_data),
            "List of the images used": (get_images_used, set_images_used),
            "Estimation method": (get_estimation, set_estimation),
            "Cell selection": (get_cell_selection, set_cell_selection) }

    header_order = ["Data file", "List of the images used", "Estimation method", "Cell selection"]

    fields = ["Image", "Cell", "karea (1/h)", "kmaj (1/h)", "kmin (1/h)",
              "Orientation of the major axis (° to the x axis)", "phi (1/h)", "", "Wall", "k (1/h)"]

    fields_num = {"image": 0,
                  "cell" : 1,
                  "karea": 2,
                  "kmaj" : 3,
                  "kmin" : 4,
                  "theta": 5,
                  "phi"  : 6,
                  "wall" : 8,
                  "kwall": 9 }

    growth_num = { "kmax" : 0,
                   "kmin" : 1,
                   "theta": 2,
                   "phi"  : 3 }

    def save(self, filename):
        growth_num = Result.growth_num
        fdata = StringIO()
        invert_pts, invert_cells = self.data.save(f=fdata)
        f = open(filename, 'w')
        w = csv.writer(f, delimiter=',')
        w.writerow(["TRKR_VERSION", Result.CURRENT_VERSION])
        w.writerow(["Growth computation parameters"])
        hf = self.header_fields
        for h in self.header_order:
            w.writerow([h] + hf[h][0](self))
        w.writerow([])
        w.writerow(["Growth per image"])
        w.writerow(Result.fields)
        for img_id in range(len(self.images)):
            img = self.images[img_id]
            w.writerow([img])
            cells = self.cells[img_id]
            cells_area = self.cells_area[img_id]
            walls = self.walls[img_id]
            rows = []
            for c in sorted(cells.keys()):
                row = ["","Cell %d" % invert_cells[c], cells_area[c], cells[c][growth_num["kmax"]],
                        cells[c][growth_num["kmin"]], cells[c][growth_num["theta"]]*180/pi, cells[c][growth_num["phi"]]]
                rows.append(row)
            lr = len(rows)
            for i,ws in enumerate(sorted(walls.keys())):
                wll = [ "", "Wall %d-%d"%(invert_pts[ws[0]], invert_pts[ws[1]]), walls[ws] ]
                if i >= lr:
                    rows.append([""]*7)
                rows[i] += wll
            w.writerows(rows)
        w.writerow(["Actual cell shapes"])
        w.writerow(["Image", "Cell", "Begin/End", "Shape [x y]"])
        for img_id in range(len(self.images)):
            img = self.images[img_id]
            w.writerow([img])
            cells_shapes = self.cells_shapes[img_id]
            rows = []
            for c in sorted(cells_shapes.keys()):
                sh = cells_shapes[c]
                row1 = ["", "Cell %d" % invert_cells[c], "Begin"] + list(sh[0].flatten())
                row2 = ["", "Cell %d" % invert_cells[c], "End"]+ list(sh[1].flatten())
                rows.append(row1)
                rows.append(row2)
            w.writerows(rows)
        w.writerow([])
        w.writerow(["Data"])
        f.write(fdata.getvalue())
        f.close()
        fdata.close()

    def load_version01(self, filename, **opts):
        fields_num = Result.fields_num
        f = open(filename, "r")
        r = csv.reader(f, delimiter=',')
        l = next(r)
        assert l[0] == "TRKR_VERSION" and l[1] == "0.1", "Wrong reader for version %s:%s" % (l[0], l[1])
        l = next(r)
# First, the header
        header_fields = self.header_fields
        for l in r:
            if not l:
                break
            if l[0] in header_fields:
                header_fields[l[0]][1](self, l)
        next(r) # "Growth per image"
        next(r) # header ...
        split_wall_re = re.compile('[ -]')
        for l in r:
            if len(l) == 0:
                break
            elif len(l) == 1:
                img = self.addImage(l[fields_num["image"]])
                cells = self.cells[img]
                cells_area = self.cells_area[img]
                walls = self.walls[img]
            else:
                if l[1]: # There is a cell
                    cid = int(l[fields_num["cell"]].split(' ')[1])
                    cells_area[cid] = float(l[fields_num["karea"]])
                    cells[cid] = (float(l[fields_num["kmaj"]]), float(l[fields_num["kmin"]]),
                                  float(l[fields_num["theta"]])*pi/180, float(l[fields_num["phi"]]))
                if len(l) > 7: # The is a wall
                    p1,p2 = (int(i) for i in split_wall_re.split(l[fields_num["wall"]])[1:3])
                    k = float(l[fields_num["kwall"]])
                    walls[p1,p2] = k
        l = next(r)
        if len(l) == 1 and l[0] == "Data":
            self.data.load(f = f, **opts)

    def load_version02(self, filename, **opts):
        if "force_load" in opts and opts["force_load"]:
            return self.load_version03(filename, **opts)
        else:
            raise RetryTrackingDataException("Warning, this file was generated with a version of the point tracker that doesn't growth orientation and vorticity correctly. You should recompute the growth for this data set. Do you still want to load that file?", "force_load")

    def load_version03(self, filename, **opts):
        fields_num = Result.fields_num
        f = open(filename, "r")
        l1 = f.readline()
        if '\t' in l1:
            delim = '\t'
        elif ',' in l1:
            delim = ','
        else:
            raise GrowthResultException("Invalid file format, delimiter needs to be '\\t' or ','")
        f.close()
        f = open(filename, "r")
        r = csv.reader(f, delimiter=delim)
        l = next(r)
        if "force_load" not in opts or not opts['force_load']:
            assert l[0] == "TRKR_VERSION" and l[1] == "0.3", "Wrong reader for version %s:%s" % (l[0], l[1])
        l = next(r)
# First, the header
        header_fields = self.header_fields
        for l in r:
            if not l:
                break
            if l[0] in header_fields:
                header_fields[l[0]][1](self, l)
        next(r) # "Growth per image"
        next(r) # header ...
        split_wall_re = re.compile('[ -]')
        for l in r:
            if len(l) == 0:
                break
            elif len(l) == 1:
                img = self.addImage(l[fields_num["image"]])
                cells = self.cells[img]
                cells_area = self.cells_area[img]
                walls = self.walls[img]
            else:
                if l[1]: # There is a cell
                    cid = int(l[fields_num["cell"]].split(' ')[1])
                    cells_area[cid] = float(l[fields_num["karea"]])
                    cells[cid] = (float(l[fields_num["kmaj"]]), float(l[fields_num["kmin"]]),
                                  float(l[fields_num["theta"]])*pi/180, float(l[fields_num["phi"]]))
                if len(l) > 7: # The is a wall
                    p1,p2 = (int(i) for i in split_wall_re.split(l[fields_num["wall"]])[1:3])
                    k = float(l[fields_num["kwall"]])
                    walls[p1,p2] = k
        l = next(r)
        if len(l) == 1 and l[0] == "Data":
            if "no_data" not in opts or not opts["no_data"]:
                self.data.load(f = f, **opts)

    def load_version04(self, filename, **opts):
        fields_num = Result.fields_num
        f = open(filename, "r")
        l1 = f.readline()
        if '\t' in l1:
            delim = '\t'
        elif ',' in l1:
            delim = ','
        else:
            raise GrowthResultException("Invalid file format, delimiter needs to be '\\t' or ','")
        f.close()
        f = open(filename, "r")
        r = csv.reader(f, delimiter=delim)
        l = next(r)
        if "force_load" not in opts or not opts['force_load']:
            assert l[0] == "TRKR_VERSION" and l[1] == "0.4", "Wrong reader for version %s:%s" % (l[0], l[1])
        l = next(r)
# First, the header
        header_fields = self.header_fields
        for l in r:
            if not l:
                break
            if l[0] in header_fields:
                header_fields[l[0]][1](self, l)
        next(r) # "Growth per image"
        next(r) # header ...
        split_wall_re = re.compile('[ -]')
        found_cell_shapes = False
        for l in r:
            if len(l) == 0:
                break
            elif len(l) == 1:
                if l[0] == "Actual cell shapes":
                    found_cell_shapes = True
                    break
                img = self.addImage(l[fields_num["image"]])
                cells = self.cells[img]
                cells_area = self.cells_area[img]
                walls = self.walls[img]
            else:
                if l[1]: # There is a cell
                    cid = int(l[fields_num["cell"]].split(' ')[1])
                    cells_area[cid] = float(l[fields_num["karea"]])
                    cells[cid] = (float(l[fields_num["kmaj"]]), float(l[fields_num["kmin"]]),
                                  float(l[fields_num["theta"]])*pi/180, float(l[fields_num["phi"]]))
                if len(l) > 7: # The is a wall
                    p1,p2 = (int(i) for i in split_wall_re.split(l[fields_num["wall"]])[1:3])
                    k = float(l[fields_num["kwall"]])
                    walls[p1,p2] = k
        if found_cell_shapes:
            next(r) # Skip header description
            for l in r:
                if len(l) == 0:
                    break
                elif len(l) == 1:
                    img = self.addImage(l[fields_num["image"]])
                    cells_shapes = self.cells_shapes[img]
                else:
                    if l[1][:5] == "Cell ":
                        cell_id = int(l[1][5:])
                        begin = l[2] == "Begin"
                        shape = array([float(fl) for fl in l[3:]])
                        assert shape.shape[0] % 2 == 0, "A cell shape needs an even number of values (x,y)"
                        shape.shape = (shape.shape[0]/2, 2)
                        if cell_id in cells_shapes:
                            if begin:
                                cells_shapes[cell_id] = (shape, cells_shapes[cell_id][1])
                            else:
                                cells_shapes[cell_id] = (cells_shapes[cell_id][0], shape)
                        else:
                            if begin:
                                cells_shapes[cell_id] = (shape, [])
                            else:
                                cells_shapes[cell_id] = ([], shape)
        l = next(r)
        if len(l) == 1 and l[0] == "Data":
            if "no_data" not in opts or not opts["no_data"]:
                self.data.load(f = f, **opts)

    versions_loader = {
            "0.1": load_version01,
            "0.2": load_version02,
            "0.3": load_version03,
            "0.4": load_version04
            }
    """
    Which function load which version of the result
    """

    def load(self, filename, **opts):
        self.current_filename = filename
        version = None
        f = open(filename, 'r')
        first_line = f.readline()
        f.close()
        if "," in first_line:
            first_line = first_line.split(",")
        else:
            first_line = first_line.split("\t")
        if first_line and first_line[0].strip() == "TRKR_VERSION":
            try:
                version = first_line[1].strip()
            except IndexError:
                raise GrowthResultException("Incorrect file format: the version line does not contain a version number")
        else:
            raise GrowthResultException("Invalid file format")
        self.clear()
        if version not in Result.versions_loader:
            raise GrowthResultException("Unknown version number: %s" % version)
        Result.versions_loader[version](self, filename, **opts)

def wall(p1, p2):
    if p1 < p2:
        return (p1,p2)
    return (p2,p1)

def polygonToCoordinates(poly, img_data):
    return array([ [img_data[p].x(), img_data[p].y()] for p in poly if p in img_data])

def polygonToPointList(poly, img_data):
    return [ img_data[p] for p in poly if p in img_data]

def cellToPointList(cid, img_data):
    return polygonToPointList(img_data.cells[cid], img_data)

class GrowthMethod(object):
    def __init__(self):
        self._thread = None

    @property
    def thread(self):
        """
        Thread running the method.

        The thread is supposed to expose:
            1. a ``stop`` attribute, telling if the method is suppose to stop computing.
            2. a ``nextImage`` method, called everytime a new image has been processed
        """
        return self._thread

    @thread.setter
    def thread(self, thread):
        if not hasattr(thread, "stop"):
            raise ValueError("The thread must have a stop property")
        self._thread = thread


class ForwardMethod(GrowthMethod):
    def __init__(self):
        GrowthMethod.__init__(self)

    def parameters(self):
        return ["Forward"]

    def nbOutputImages(self, inputImages, data):
        return len(inputImages)-1

    def computeFromImages(self, list_img, i):
        return list_img[i:i+2]

    def usedImages(self, list_img):
        return list_img[:-1]

    def growthParams(self, ps, qs, dt):
        return growthParams(ps, qs, dt, at_start=True)

    def __call__(self, list_img, data, cells_selection):
        result = Result(data, list_img)
        thread = self.thread
        used_images = self.usedImages(list_img)
        for i in range(len(used_images)):
            img_name = used_images[i]
            used_imgs = self.computeFromImages(list_img, i)
            cells_pts = cells_selection(used_imgs, data)
            #print "%d cells for images %s" % (len(cells_pts), used_imgs)
            if cells_pts:
                img_data = data[used_imgs[0]]
                next_img_data = data[used_imgs[1]]
                n = result.addImage(img_name)
                cell_result = result.cells[n]
                wall_result = result.walls[n]
                cell_shapes = result.cells_shapes[n]
                cell_area_result = result.cells_area[n]
                walls = set()
                for c in sorted(cells_pts.keys()):
                    #print "Processing cell %d" % c
                    pts = [ pid for pid in cells_pts[c] if pid in img_data and pid in next_img_data ]
                    if not pts:
                        continue
                    lp = len(pts)
                    if lp < 3: # Cannot have growth of less than three points
                        continue
                    for i in range(lp):
                        walls.add(wall(pts[i], pts[(i+1)%lp]))
                    ps = polygonToCoordinates(pts, img_data)
                    qs = polygonToCoordinates(pts, next_img_data)
                    dt = next_img_data.time - img_data.time
                    gp = self.growthParams(ps, qs, dt)
                    if gp is not None:
                        a1 = polygonArea(cellToPointList(c, img_data))
                        if c in next_img_data.cells:
                            a2 = polygonArea(cellToPointList(c, next_img_data))
                        else:
                            ds = [ c2 for c2 in data.daughterCells(c) if c2 in next_img_data.cells ]
                            a2 = 0
                            for c2 in ds:
                                a2 += polygonArea(cellToPointList(c2, next_img_data))
                        if a2/(a2+a1) < 1e-15:
                            continue
                        r = log(a2/a1)/dt
                        if isnan(r) or isinf(r) or isnan(gp).any():
                            #print "  Invalid growth:\n %s" % (gp,)
                            continue
                        cell_area_result[c] = r
                        cell_result[c] = gp
                        cell_shapes[c] = (ps, qs)
                        #print "  Growth area: %g" % r
                    #else:
                        #print "  No growth parameter"
                for p1, p2 in walls:
                    if p1 in next_img_data and p2 in next_img_data:
                        pos11 = img_data[p1]
                        pos12 = img_data[p2]
                        pos21 = next_img_data[p1]
                        pos22 = next_img_data[p2]
                        d1 = dist(pos11, pos12)
                        d2 = dist(pos21, pos22)
                        k = (d2-d1)/(d1*dt)
                        wall_result[p1,p2] = k
            if thread.stopped():
                return
            thread.nextImage()
        return result

class BackwardMethod(ForwardMethod):
    def usedImages(self, list_img):
        return list_img[1:]

    def computeFromImages(self, list_img, i):
        return list_img[i:i+2]

    def growthParams(self, ps, qs, dt):
        return growthParams(ps, qs, dt, at_start=False)

    def parameters(self):
        return ["Backward"]

# Functions needes for the ForwardDenseMethod

def length_polyline(w):
    vects = [w[i+1] - w[i] for i in range(len(w)-1)]
    return sum(sqrt(pos.x()*pos.x() + pos.y()*pos.y()) for pos in vects)

def length_segment(s, data):
    total_length = 0
    lengths = [0]
    for p1,p2 in zip(s[:-1],s[1:]):
        w = data.walls[p1,p2]
        w.insert(0,data[p1])
        w.append(data[p2])
        l = length_polyline(w)
        total_length += l
        lengths.append(total_length)
    return lengths

def align_segments(s1, s2, data1, data2):
    """
    Compute the alignment of segments s1 and s2,
    such that the first and last elements of s1 and s2 are the same, but nothing else.

    :return_type: list of (list of QPointF, int)
    :returns: List of wall parts such that the first point is the vertex.
              The integer is the id of the point (if it corresponds to one).
    """
    # First, compute ratios
    lengths_s1 = length_segment(s1, data1)
    lengths_s2 = length_segment(s2, data2)
    ratios_s1 = [l/lengths_s1[-1] for l in lengths_s1]
    ratios_s2 = [l/lengths_s2[-1] for l in lengths_s2]
    len_s1 = lengths_s1[-1]
    len_s2 = lengths_s2[-1]
    all_pos = list(set(ratios_s1+ratios_s2))
    all_pos.sort()
    def _align(length,s, ratios, data):
        align = [None] * (len(all_pos)-1)
        ratios = set(ratios)
        p1,p2 = 0,1 # Position in s1
        pos = data[s[p1]]
        cur = s[p1]
        next = None
        w = data.walls[s[p1],s[p2]]
        for j,(r1,r2) in enumerate(zip(all_pos[:-1],all_pos[1:])):
            w1 = [pos]
            if r2 in ratios: # If the next point is in the current wall
                w1.extend(w)
                pos = data[s[p2]]
                p1,p2 = p1+1,p2+1
                if p2 < len(s):
                    w = data.walls[s[p1],s[p2]]
                    next = s[p1]
            else: # Otherwise, find where it stops
                l = (r2-r1)*length
                acc = 0
                while w:
                    p = w[0]
                    vec = p - w1[-1]
                    dl = sqrt(vec.x()*vec.x() + vec.y()*vec.y())
                    if acc+dl > l: # If we go past the next stop
                        pos = w1[-1] + vec*((l-acc)/dl)
                        break
                    acc += dl
                    w1.append(p)
                    w.pop(0)
                else: # If the end of the wall has been reached
                    p = data[s[p2]]
                    vec = p - w1[-1]
                    dl = sqrt(vec.x()*vec.x() + vec.y()*vec.y())
                    pos = w1[-1] + vec*((l-acc)/dl)
            align[j] = (w1, cur)
            l = (r2-r1)*len_s2
            cur, next = next, None
        return align
    align_s1 = _align(len_s1, s1, ratios_s1, data1)
    align_s2 = _align(len_s2, s2, ratios_s2, data2)
    return align_s1, align_s2

def discretize_segment(seg, n, l):
    dl = l/n
    result = []
    idx = 0
    pos = seg[idx]
    vec = seg[idx+1]-pos
    vec_size = sqrt(vec.x()*vec.x() + vec.y()*vec.y())
    vec /= vec_size
    shift = 0
    for j in range(n):
        result.append(pos)
        if j == n-1: break
        needed_dl = dl
        while shift+needed_dl > vec_size:
            idx += 1
            needed_dl -= vec_size - shift
            pos = seg[idx]
            vec = seg[idx+1]-seg[idx]
            vec_size = sqrt(vec.x()*vec.x() + vec.y()*vec.y())
            vec /= vec_size
            shift = 0
        pos = pos + vec*needed_dl
        shift += needed_dl
    return result

def alignCells(c, pts, new_pts, img_data, next_img_data, nb_points):
    # First, find a common vertex between the cells
    for common in pts:
        if common in new_pts:
            idx = pts.index(common)
            idx1 = new_pts.index(common)
            pts = pts[idx:] + pts[:idx]
            new_pts = new_pts[idx1:] + new_pts[:idx1]
            break
    else:
        log_debug("Error, cell %d have no common points between times %s and %s" % (c, img_data.image_name, next_img_data.image_name))
        return
    # Then, align the cells. i.e. add missing points
    aligned_pts = []
    aligned_new_pts = []
    i1,j1 = 0,0
    for i2,pid in enumerate(pts[1:]):
        i2 = i2+1
        if pid in new_pts:
            j2 = new_pts.index(pid)
            if j2 < j1:
                log_debug("Error, cell %d is inconsistent between times %s and %s" % (c, img_data.image_name, next_img_data.image_name))
                aligned_pts = []
                aligned_new_pts = []
                i1 = 0
                j1 = 0
                break
            seg, new_seg = align_segments(pts[i1:i2+1], new_pts[j1:j2+1], img_data, next_img_data)
            aligned_pts += seg
            aligned_new_pts += new_seg
            i1 = i2
            j1 = j2
    # Add the missing segment
    if i1 != 0:
        seg, new_seg = align_segments(pts[i1:]+pts[0:1], new_pts[j1:]+new_pts[0:1], img_data, next_img_data)
        aligned_pts += seg
        aligned_new_pts += new_seg
    if not aligned_pts:
        return
    # Next, for the cell, start by resampling them
    # Compute total perimeter of first cell
    l1 = sum((seg for (seg,_) in aligned_pts), [])
    l1.append(l1[0])
    len_c1 = length_polyline(l1)
    # Approximate the dl
    dl = len_c1 / nb_points
    ps = [] # Resampled first cell
    qs = [] # Resampled second cell
    nb_seg = len(aligned_pts)
    for i,((seg1,_),(seg2,_)) in enumerate(zip(aligned_pts, aligned_new_pts)):
        seg1 = seg1 + aligned_pts[(i+1) % nb_seg][0][0:1]
        seg2 = seg2 + aligned_new_pts[(i+1) % nb_seg][0][0:1]
        l1 = length_polyline(seg1)
        l2 = length_polyline(seg2)
        # Number of point on the current segment
        n = int(ceil(l1/dl))
        # Real dl for first and second cells
        ps += discretize_segment(seg1, n, l1)
        qs += discretize_segment(seg2, n, l2)
    return aligned_pts, aligned_new_pts, ps, qs

class ForwardDenseMethod(GrowthMethod):
    def __init__(self, nb_points = 100):
        GrowthMethod.__init__(self)
        self._nb_points = nb_points

    def parameters(self):
        return ["ForwardDense", self._nb_points]

    @property
    def nb_points(self):
        """Number of points used to discretize the cell"""
        return self._nb_points

    @nb_points.setter
    def nb_points(self, value):
        value = int(value)
        if value < 3:
            raise ValueError("The cell needs at least 3 points for the algorithm to work.")
        self._nb_points = value

    def nbOutputImages(self, inputImages, data):
        return len(inputImages)-1

    def computeFromImages(self, list_img, i):
        return list_img[i:i+2]

    def baseImage(self, list_img, i):
        return list_img[i]

    def usedImages(self, list_img):
        return list_img[:-1]

    def growthParams(self, ps, qs, dt):
        return growthParams(ps, qs, dt, at_start=True)

    def processCell(self, c, img_data, next_img_data, ref_is_img):
        log_debug("Processing cell %d" % c)
        cell_shapes = self.cell_shapes
        cell_result = self.cell_result
        wall_result = self.wall_result
        cell_area_result = self.cell_area_result
        walls = self.walls
        data = img_data.parent
        try:
            pts = data.cellAtTime(c, img_data.index)
            new_pts = data.cellAtTime(c, next_img_data.index)
        except ValueError:
            return
        if ref_is_img:
            ref_pts = pts
        else:
            ref_pts = new_pts
        dt = next_img_data.time - img_data.time
        result = alignCells(c, pts, new_pts, img_data, next_img_data, self.nb_points)
        if result is None:
            return
        aligned_pts, aligned_new_pts, ps, qs = result
        # Now, we know enough to compute growth of walls
        w1,prev = aligned_pts[0]
        w2,_ = aligned_new_pts[0]
        shifted1 = aligned_pts[1:] + aligned_pts[0:1]
        shifted2 = aligned_new_pts[1:] + aligned_new_pts[0:1]
        for (seg1,p1),(seg2,p2) in zip(shifted1, shifted2):
            if p1 in ref_pts or p2 in ref_pts:
                cur = p2 if p1 is None else p1
                assert prev is not None and cur is not None
                id = data.wallId(prev,cur)
                if id not in walls:
                    walls.add(id)
                    w1.append(seg1[0])
                    w2.append(seg2[0])
                    l1 = length_polyline(w1)
                    l2 = length_polyline(w2)
                    k = log(l2/l1)/dt
                    wall_result[id] = k
                prev = cur
                w1 = seg1
                w2 = seg2
            else:
                w1 += seg1
                w2 += seg2
        ps = array([[p.x(), p.y()] for p in ps])
        qs = array([[p.x(), p.y()] for p in qs])
        gp = self.growthParams(ps, qs, dt)
        if gp is not None:
            poly1 = sum([ s[0] for s in aligned_pts ], [])
            poly2 = sum([ s[0] for s in aligned_new_pts ], [])
            a1 = polygonArea(poly1)
            a2 = polygonArea(poly2)
            if a2/(a2+a1) < 1e-15: # Too small, there is a pb
                return
            r = log(a2/a1)/dt
            if isnan(r) or isinf(r) or isnan(gp).any():
                log_debug("Invalid growth for cell %d on image %s:\n %s" % (c, img_data.image_name, gp,))
                return
            cell_area_result[c] = r
            cell_result[c] = gp
            cell_shapes[c] = (ps, qs)

    def __call__(self, list_img, data, cells_selection):
        result = Result(data, list_img)
        thread = self.thread
        used_images = self.usedImages(list_img)
        for i in range(len(used_images)):
            img_name = used_images[i]
            used_imgs = self.computeFromImages(list_img, i)
            ref_img = self.baseImage(list_img, i)
            cells_pts = cells_selection(used_imgs, data)
            log_debug("%d cells for images %s" % (len(cells_pts), used_imgs))
            if cells_pts:
                img_data = data[used_imgs[0]]
                next_img_data = data[used_imgs[1]]
                n = result.addImage(img_name)
                self.cell_shapes = result.cells_shapes[n]
                self.cell_result = result.cells[n]
                self.wall_result = result.walls[n]
                self.cell_area_result = result.cells_area[n]
                self.walls = set()
                for c in sorted(cells_pts.keys()):
                    self.processCell(c, img_data, next_img_data, ref_is_img = (ref_img == used_imgs[0]))
            if thread.stopped():
                return
            thread.nextImage()
        return result

class BackwardDenseMethod(ForwardDenseMethod):
    def __init__(self, nb_points):
        ForwardDenseMethod.__init__(self, nb_points)

    def usedImages(self, list_img):
        return list_img[1:]

    def computeFromImages(self, list_img, i):
        return list_img[i:i+2]

    def baseImage(self, list_img, i):
        return list_img[i+1]

    def growthParams(self, ps, qs, dt):
        return growthParams(ps, qs, dt, at_start=False)

    def parameters(self):
        return ["BackwardDense", self._nb_points]


class FullCellsOnlySelection(object):
    def __init__(self, daughterCells):
        self.daughterCells = daughterCells

    def parameters(self):
        params = ["AddDivisionOnly"]
        if self.daughterCells:
            params +=  ["with cell division"]
        else:
            params += ["without cell division"]
        return params

    def __call__(self, list_img, data):
        img_data = data[list_img[0]]
        cells = list(img_data.cells)
        division_points = data.divisionPoints()
        if not self.daughterCells:
            cells = list(set(data.oldestAncestor(c) for c in cells))
        cells_pts = dict([ (c,[ p for p in data.cells[c] if p in img_data ]) for c in cells ])
        for c in cells_pts.keys():
            if len(cells_pts[c]) < 3:
                del cells_pts[c]
        log_debug("Initial list of cells: %s" % (sorted(cells_pts.keys()),))
        for img in list_img:
            new_img_data = data[img]
            for c,_ in cells_pts.items():
                missing_pts = set(p for p in data.cells[c] if p not in new_img_data)
                for p in missing_pts:
                    if p not in division_points:
                        del cells_pts[c]
                        break
                else:
                    new_cell = [p for p in cells_pts[c] if p in new_img_data]
                    if len(new_cell) < 3:
                        del cells_pts[c]
                    else:
                        cells_pts[c] = new_cell
        return cells_pts

class AddPointsSelection(object):
    def __init__(self, daughterCells, max_variation):
        self.daughterCells = daughterCells
        self.max_variation = max_variation

    def parameters(self):
        params = ["AddPoints", "%f%% variation" % (self.max_variation*100,)]
        if self.daughterCells:
            params +=  ["with cell division"]
        else:
            params += ["without cell division"]
        return params

    def __call__(self, list_img, data):
        log_debug("Starting AddPointsSelection")
        img_data = data[list_img[0]]
        cells = list(img_data.cells)
        if not self.daughterCells:
            cells = list(set(data.oldestAncestor(c) for c in cells))
        cells_pts = dict([ (c,[ p for p in data.cells[c] if p in img_data ]) for c in cells ])
        for c in cells_pts.keys():
            if len(cells_pts[c]) < 3:
                log_debug("Deleting cell %s because it has less than three vertices" % c)
                del cells_pts[c]
        print("Initial list of cells: %s" % (sorted(cells_pts.keys()),))
        for img in list_img[1:]:
            new_img_data = data[img]
            for c,pts in cells_pts.items():
                for p in pts:
                    if p not in new_img_data:
                        log_debug("Deleting cell %d because it is not in the other image" % c)
                        del cells_pts[c]
                        break
                else:
                    p1 = [ new_img_data[p] for p in data.cells[c] if p in img_data ]
                    p2 = [ new_img_data[p] for p in data.cells[c] if p in new_img_data ]
                    a1 = polygonArea(p1)
                    a2 = polygonArea(p2)
                    if abs((a2-a1)/a1) > self.max_variation:
                        log_debug("Deleting cell %d because of big size variation" % c)
                        del cells_pts[c]
        return cells_pts

class AllCellsSelection(object):
    def __init__(self, daughterCells, max_variation):
        self.daughterCells = daughterCells
        self.max_variation = max_variation

    def parameters(self):
        params = ["AllCells"]
        if self.max_variation is not None:
            params.append("%f%% variation" % (self.max_variation*100,))
        if self.daughterCells:
            params.append("with cell division")
        else:
            params.append("without cell division")
        return params

    def __call__(self, list_img, data):
        img_data = data[list_img[0]]
        cells = list(img_data.cells)
        if not self.daughterCells:
            cells = list(set(data.oldestAncestor(c) for c in cells))
        cells_pts = dict([ (c,[ p for p in data.cells[c] if p in img_data ]) for c in cells ])
        log_debug("Initial list of cells: %s" % (sorted(cells_pts.keys()),))
        for c in cells_pts.keys():
            if len(cells_pts[c]) < 3:
                del cells_pts[c]
        if self.max_variation is not None:
            for img in list_img[1:]:
                new_img_data = data[img]
                for c,_ in cells_pts.items():
                    p1 = [ img_data[p] for p in data.cells[c] if p in img_data ]
                    p2 = [ new_img_data[p] for p in data.cells[c] if p in new_img_data ]
                    a1 = polygonArea(p1)
                    a2 = polygonArea(p2)
                    if abs((a2-a1)/a1) > self.max_variation:
                        del cells_pts[c]
        return cells_pts

