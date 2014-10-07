from __future__ import print_function, division, absolute_import
__author__ = "Pierre Barbier de Reuille <pierre@barbierdereuille.net>"
__docformat__ = "restructuredtext"
import scipy
from scipy import signal, cos, sin, c_, newaxis
from .normcross import normcross2d
from PyQt4.QtCore import QThread, QEvent, QCoreApplication, QPointF, QRectF
from .tracking_undo import AddPoints, MovePoints
import math
from .sys_utils import cleanQObject


class NextImage(QEvent):
    """
    Event notifying the GUI a new image has been processed
    """
    def __init__(self, cur_img, nb_pts):
        QEvent.__init__(self, QEvent.User)
        self.currentImage = cur_img
        self.nbPoints = nb_pts


class NextPoint(QEvent):
    """
    Event notifying the GUI a new point has been processed in the current image
    """
    def __init__(self, cur_pt):
        QEvent.__init__(self, QEvent.User)
        self.currentPoint = cur_pt


class FoundAll(QEvent):
    """
    Event notifying the GUI the processed is finished.
    """
    def __init__(self):
        QEvent.__init__(self, QEvent.User)


class Aborted(QEvent):
    """
    Event notifying the GUI the processed has been aborter.
    """
    def __init__(self):
        QEvent.__init__(self, QEvent.User)


class FindInAll(QThread):
    """
    Thread finding a set of points in a set of images.

    The thread send the event NextImage, NextPoint, FoundAll and Aborted to the main GUI thread.

    All instance variable are private and should NOT be changed without calling methods

    Instance variables:
      - undo_stack, QUndoStack: place there all what is done as a compound undo event.
      - stop, bool: if true, the algorithm will stop at the next point
      - data_manager, TrackingData: object handling the current data
      - list_images, list of str: list of images where the points will be searched
      - template_size, int: size of the search template
      - search_size, int: size of the search area
      - filter_size, int: size of the bluring filter
      - num_images, int: total number of images to look into (just used to setup a correct percentage)
      - pts, list of int: list of points id to look for in images
    """
    def __init__(self, data_manager, start, pts, template_size, search_size, filter_size, parent):
        QThread.__init__(self, parent)
        self.undo_stack = parent.undo_stack
        self.stop = False
        self.data_manager = data_manager
        self.list_images = [data_manager.image_path[img] for img in data_manager.images_name[start:]]
        self.template_size = (template_size, template_size)
        self.search_size = (search_size, search_size)
        self.filter_size = (filter_size, filter_size)
        self.num_images = len(self.list_images)-2
        self.pts = pts

    def __del__(self):
        cleanQObject(self)

    def run(self):
        import image_cache
        undo_stack = self.undo_stack
        data_manager = self.data_manager
        undo_stack.beginMacro("Copy from %s to followings" % self.list_images[0])
        try:
            app = QCoreApplication.instance()
            parent = self.parent()
            source = data_manager[self.list_images[0].basename()]
            if self.pts is None:
                pts = list(source)
            else:
                pts = self.pts
            cache = image_cache.cache
            filter_size = self.filter_size
            im_source = cache.numpy_array(self.list_images[0], filter_size)
            template_size = self.template_size
            search_size = self.search_size
            source_matrix = source.matrix()
            inv_src_matrix, ok = source_matrix.inverted()
            for currentImage, image_name in enumerate(self.list_images[1:]):
                target = data_manager[image_name.basename()]
                target_matrix = target.matrix()
                inv_tgt_matrix, ok = target_matrix.inverted()
                im_target = cache.numpy_array(image_name, filter_size)
                app.postEvent(parent, NextImage(currentImage, len(pts)-1))
                new_pts_id = []
                new_pts_pos = []
                move_pts_id = []
                move_pts_pos = []

                new_pts = []
                for currentPoint, id in enumerate(pts):
                    if self.stop:
                        app.postEvent(parent, Aborted())
                        break
                    pos = source[id]
                    npos = inv_tgt_matrix.map(pos)
                    pos = inv_src_matrix.map(pos)
                    new_pos, value = findTemplate(im_source, (pos.x(), pos.y()), template_size,
                                                  (npos.x(), npos.y()), search_size, im_target)
                    if value >= 0.5:
                        new_pts.append(id)
                        new_pos = target_matrix.map(QPointF(new_pos[0], new_pos[1]))
                        if id in target:
                            move_pts_id.append(id)
                            move_pts_pos.append(new_pos)
                        else:
                            new_pts_id.append(id)
                            new_pts_pos.append(new_pos)
                    app.postEvent(parent, NextPoint(currentPoint))
                if new_pts_id:
                    undo_stack.push(AddPoints(data_manager, image_name.basename(), new_pts_id, new_pts_pos))
                if move_pts_id:
                    undo_stack.push(MovePoints(data_manager, image_name.basename(), move_pts_id, move_pts_pos))
                pts = new_pts
                source = target
                source_matrix = target_matrix
                inv_src_matrix = inv_tgt_matrix
                im_source = im_target
                if self.stop or not pts:
                    break
        finally:
            app.postEvent(parent, FoundAll())
            undo_stack.endMacro()


def copyFromImage(data_manager, start, items, undo_stack):
    """
    Copy a set of points from one image to the next images. The new position of the points are NOT estimated.

    Arguments:
      - data_manager, TrackingData: current data manager
      - start, int: time where the points are defined
      - items, list of int: list of points id to look for
      - undo_stack, QUndoStack: undo stack where a macro will be put for undo
    """
    undo_stack.beginMacro("Copy from %s to followings" % data_manager.images_name[start])
    img_name = data_manager.images_name[start]
    data = data_manager[img_name]
    poss = [data[pt_id] for pt_id in items]
    for img in data_manager.images_name[start+1:]:
        data = data_manager[img]
        new_items = []
        new_items_pos = []
        moved_items = []
        moved_items_pos = []
        for pt_id, pos in zip(items, poss):
            if pt_id in data:
                moved_items.append(pt_id)
                moved_items_pos.append(pos)
            else:
                new_items.append(pt_id)
                new_items_pos.append(pos)
        if new_items:
            undo_stack.push(AddPoints(data_manager, img, new_items, new_items_pos))
        if moved_items:
            undo_stack.push(MovePoints(data_manager, img, moved_items, moved_items_pos))
    undo_stack.endMacro()


def filterImage(image, filter_size):
    """
    Filter the image with a rectangular filter

    filter_size, (int,int) : size of the filter to apply
    """
    hrow = [1./filter_size[1]]*filter_size[1]
    hcol = [1./filter_size[0]]*filter_size[0]
    image = image - signal.sepfir2d(image, hrow, hcol)
    return image


def findTemplate(origin, template_pos, template_size, search_pos, search_size, target):
    """
    Find a template image into another image by normalized cross-correlation.

    Arguments:
      - origin, ndarray: image where the template is extracted (the image is accessed as a matrix, i.e. the points (x,y)
      is found at origin[y,x])
      - template_pos, (int,int): position (x,y) of the template
      - template_size, (int,int): size (width,height) of the template
      - search_pos, (int,int): central position (x,y) of the search zone
      - search_size, (int,int): size (width,height) of the search zone
      - target, ndarray: image where the template is searched (the image is accessed as a matrix, i.e. the points (x,y)
      is found at target[y,x])
    """
    t_left = max(0, template_pos[0] - template_size[0])
    t_right = min(origin.shape[1]-1,
                  template_pos[0]
                  + template_size[0])
    t_bottom = max(0, template_pos[1] - template_size[1])
    t_top = min(origin.shape[0]-1, template_pos[1] + template_size[1])
    template = origin[t_bottom:t_top, t_left:t_right]
    if t_left == 0:
        template_size = (template_pos[0]-1, template_size[1])
    if t_bottom == 0:
        template_size = (template_size[0], template_pos[1]-1)

#  template = template / sqrt((template*template).sum().sum())

    s_left = max(0, search_pos[0] - search_size[0])
    s_right = min(target.shape[1]-1, search_pos[0] + search_size[0])
    s_bottom = max(0, search_pos[1] - search_size[1])
    s_top = min(target.shape[0]-1, search_pos[1] + search_size[1])
    target = target[s_bottom:s_top, s_left:s_right]

#  target = target / sqrt((target*target).sum().sum())

    cross = abs(normcross2d(template, target))
    pos = scipy.unravel_index(cross.argmax(), cross.shape)
    value = cross[pos]
    center = (pos[1]+s_left-template_size[1]+1,
              pos[0]+s_bottom-template_size[0]+1)
    return center, value


class AlgoException(Exception):
    """
    Exception denoting an error in the arguments of an algorithm
    """
    def __init__(self, s):
        Exception.__init__(self, s)


def alignImages(data, alignment_data, translation, rotation):
    """
    Align the images in data using the points found in alignment_data.

    Arguments:
      - data, TrackingData: data set to align
      - alignment_data, TrackingData: data set used for the alignment
      - translation, (str|int): type of translation. Valid values are:
         * "Bounding-box centre"
         * "Barycentre"
         * Any point if in alignment_data
      - rotation, (str,int,int): type of rotation. The first value is the rotation type. For now, it has to be
      "TwoPoint". The two other values are the points id used for the rotation. """
    # First, check the alignment data is valid
    #pts = alignment_data[alignment_data.images_name[0]].points()
    a = scipy.zeros(len(data), dtype=float)
    if rotation is not None:
        assert len(rotation) == 3
        assert rotation[0] == "TwoPoint"
        r1 = rotation[1]
        r2 = rotation[2]
        for d in alignment_data:
            if not r1 in d:
                raise AlgoException("Image %s doesn't contain point %d." % (d._current_image, r1))
            if not r2 in d:
                raise AlgoException("Image %s doesn't contain point %d." % (d._current_image, r2))
        # Then, compute the rotation
        vecs = scipy.zeros((len(data), 2), dtype=float)
        for i, d in enumerate(alignment_data):
            v = d[r2] - d[r1]
            vecs[i, :] = (v.x(), v.y())
        a = scipy.arctan2(vecs[:, 1], vecs[:, 0])
        a = a[0] - a
    # At last, compute the translation using the reference
    refs = scipy.zeros((len(data), 2), dtype=float)
    if translation == "Bounding-box centre":
        for i, d in enumerate(alignment_data):
            mat, _ = d.matrix().inverted()
            p1 = None
            rect = QRectF()
            for p in d.positions():
                p = mat.map(p)
                if p1 is None:
                    p1 = p
                else:
                    rect |= QRectF(p1, p).normalized()
            mid_pos = rect.center()
            refs[i, :] = (mid_pos.x(), mid_pos.y())
    elif translation == "Barycentre":
        for i, d in enumerate(alignment_data):
            mat, _ = d.matrix().inverted()
            mid_pos = mat.map(sum(d.positions(), QPointF())/len(d))
            refs[i, :] = (mid_pos.x(), mid_pos.y())
    else:
        for i, d in enumerate(alignment_data):
            mat, _ = d.matrix().inverted()
            if not translation in d:
                s = "Error, point %d is not in image %s. Cannot use it to align images."
                raise AlgoException(s % (translation, d.image_name))
            pos = mat.map(d[translation])
            refs[i, :] = (pos.x(), pos.y())
    moved_refs = refs*cos(a)[:, newaxis] + c_[-refs[:, 1], refs[:, 0]]*sin(a)[:, newaxis]
    moved_refs = moved_refs[0, :] - moved_refs
    a *= 180/math.pi
    return moved_refs, a
