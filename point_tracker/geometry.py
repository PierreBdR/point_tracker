from __future__ import print_function, division, absolute_import
__author__ = "Pierre Barbier de Reuille <pierre@barbierdereuille.net>"
__docformat__ = "restructuredtext"
from PyQt4.QtCore import QPointF, QRectF
from math import atan2, sqrt
from numpy import inf


def angle(ref, pt):
    x = ref.x()*pt.x() + ref.y()*pt.y()
    y = ref.x()*pt.y() - ref.y()*pt.x()
    return atan2(y, x)


def cross(p1, p2):
    return p1.x()*p2.y()-p1.y()*p2.x()


def makeStarShaped(pts, pts2coords):
    if len(pts) > 2:
        coords = [pts2coords[pt_id] for pt_id in pts]
        center = sum(coords, QPointF())/len(coords)
        ref = coords[0] - center
        angles = [angle(ref, p-center) for p in coords]
        to_sort = list(range(len(angles)))
        to_sort.sort(key=lambda k: angles[k])
        return [pts[i] for i in to_sort]
    else:
        return pts


def boundingBox(pts, pts2coords):
    coords = [pts2coords[pt_id] for pt_id in pts if pt_id in pts2coords]
    if coords:
        xmin = min(p.x() for p in coords)
        ymin = min(p.y() for p in coords)
        xmax = max(p.x() for p in coords)
        ymax = max(p.y() for p in coords)
        return QRectF(QPointF(xmin, ymin), QPointF(xmax, ymax))
    else:
        return QRectF()


def gravityCenter(polygon):
    """
    The polygon should be a list of QPointF or equivalent
    """
    if not polygon:
        return QPointF()
    elif len(polygon) == 1:
        return polygon[0]
    elif len(polygon) == 2:
        return (polygon[0]+polygon[1])/2
    else:
        a = 0
        cx = cy = 0
        for i in range(len(polygon)):
            prev = polygon[i-1]
            cur = polygon[i]
            cross = prev.x()*cur.y()-prev.y()*cur.x()
            cx += (prev.x()+cur.x())*cross
            cy += (prev.y()+cur.y())*cross
            a += cross
        a /= 2
        cx /= 6*a
        cy /= 6*a
        return QPointF(cx, cy)


def pointListToStr(lst):
    return "[%s]" % (",".join("(%f,%f)" % (p.x(), p.y()) for p in lst))


def polygonArea(polygon):
    a = 0
    L = len(polygon)
    if L < 3:
        return 0
    for i in range(L):
        a += cross(polygon[i-1], polygon[i])
    return abs(a/2)


def length(v):
    return sqrt(v.x()*v.x() + v.y()*v.y())


def dist(p1, p2):
    dx = p2.x() - p1.x()
    dy = p2.y() - p1.y()
    return sqrt(dx*dx+dy*dy)


def dist_sq(p1, p2):
    dx = p2.x() - p1.x()
    dy = p2.y() - p1.y()
    return dx*dx+dy*dy


def distToLine(pt,  p1,  p2):
    """
    Compute the distance from the point `pt` to the line segment [p1,p2]
    """
    u = p2-p1
    lu = u.x()*u.x() + u.y()*u.y()
    pmax = QPointF(max(abs(p1.x()), abs(p2.x())), max(abs(p1.y()), abs(p2.y())))
    if lu / (pmax.x()*pmax.x() + pmax.y()*pmax.y()) < 1e-10:
        diff = u - p1
        return sqrt(diff.x()*diff.x() + diff.y()*diff.y())
    dp = pt-p1
    proj = (u.x()*dp.x() + u.y()*dp.y())
    if proj >= 0 and proj <= lu:
        return abs(dp.x()*u.y() - u.x()*dp.y())/sqrt(lu)
    elif proj < 0:
        return dp.x()*dp.x() + dp.y()*dp.y()
    else:
        return dist(pt,  p2)


def distToPolyLine(pt,  line):
    """
    Compute the distance from the point pt to the polygin line.

    Line is a list of positions.
    """
    if not line:
        raise ValueError("The line doesn't containany points")
    if len(line) == 1:
        return dist(pt,  line[0])
    d = inf
    for i in range(len(line)-1):
        p1 = line[i]
        p2 = line[i+1]
        d1 = distToLine(pt,  p1,  p2)
        if d1 < d:
            d = d1
    return d
