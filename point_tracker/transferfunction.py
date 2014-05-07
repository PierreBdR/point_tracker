from __future__ import print_function, division, absolute_import
__author__ = "Pierre Barbier de Reuille <pierre@barbierdereuille.net>"
__docformat__ = "restructuredtext"
from PyQt4 import QtCore
from colorsys import rgb_to_hsv, hsv_to_rgb
import sys
if sys.version_info.major < 3:
    from StringIO import StringIO
else:
    from io import StringIO

def rgba_to_hsva(r, g, b, a):
    return rgb_to_hsv(r, g, b) + (a,)

def hsva_to_rgba(h, s, v, a):
    return hsv_to_rgb(h, s, v) + (a,)

class TransferFunction(QtCore.QObject):
    def __init__(self, copy = None):
        QtCore.QObject.__init__(self)
        if copy is None:
            self._values = []
            self._keys = {}
            self._interpolation = "rgb"
            self._cyclic = False
            self._clamp = True
            self._exterior_color = (0,0,0,0)
        else:
            self._values = list(copy._values)
            self._keys = dict(copy._keys)
            self._interpolation = copy._interpolation
            self._cyclic = copy._cyclic
            self._clamp = copy._clamp
            self._exterior_color = tuple(copy._exterior_color)

    @staticmethod
    def loads(string):
        """
        Create a TransferFunction object from the string generated with the `TransferFunction.dumps` method.
        """
        input = StringIO(unicode(string))
        nb_values = -1
        nb_colored_pos = 0
        fct = TransferFunction()
        for line in input:
            header, value = line.split(":")
            header = header.strip()
            value = value.strip()
            if header == "Interpolation":
                fct.interpolation = value
            elif header == "Clamp":
                fct.clamp = bool(value)
            elif header == "ExteriorColor":
                fct.exterior_color = tuple(int(s) for s in value.split(","))
            elif header == "NbValues":
                nb_values = int(value)
            elif header == "ColoredPos":
                pos, color_s = value.split("-")
                pos = float(pos)
                color = tuple(float(c) for c in color_s.split(","))
                fct.point_list.append((pos, color))
                nb_colored_pos += 1
        assert nb_colored_pos == nb_values, "Wrong number of colored position"
        fct.update_keys()
        return fct

    def dumps(self):
        output = StringIO()
        print("Interpolation: %s" % self.interpolation, file=output)
        print("Clamp: %s" % self.clamp, file=output)
        col = self.exterior_color
        print("ExteriorColor: %g,%g,%g,%g" % col, file=output)
        print("NbValues: %d" % len(self.point_list), file=output)
        for pos,color in self.point_list:
            print("ColoredPos: %g - %g, %g, %g, %g" % ((pos,)+color), file=output)
        return output.getvalue()

    def __eq__(self, other):
        return ((type(self) == type(other)) and
                (self._values == other._values) and
                (self._keys == other._keys) and
                (self._interpolation == other._interpolation) and
                (self._cyclic == other._cyclic) and
                (self._exterior_color == other._exterior_color))

    def __reduce__(self):
        dct = {'point_list': self.point_list,
                'interpolation': self.interpolation,
                'clamp': self.clamp,
                'exterior_color': self.exterior_color }
        return (TransferFunction, (), dct)

    def __setstate__(self, dct):
        self.point_list = dct['point_list']
        self.interpolation = dct['interpolation']
        self.clamp = dct['clamp']
        self.exterior_color = dct['exterior_color']

    def copy(self):
        cpy = TransferFunction()
        cpy.point_list = list(self.point_list)
        cpy.interpolation = self.interpolation
        cpy.clamp = self.clamp
        return cpy

    def _SetInterpolation(self, value):
        if self._GetInterpolation() == value:
            return
        if value not in ["rgb", "hsv", "cyclic_hsv"]:
            raise ValueError("Interpolation must be either 'rgb', 'hsv' or 'cyclic_hsv'")
        self._interpolation = value[-3:]
        self._cyclic = value.startswith("cyclic")
        self.emit(QtCore.SIGNAL("changed()"))

    def _GetInterpolation(self):
        cyclic = ""
        if self._cyclic:
            cyclic = "cyclic_"
        return "%s%s" % (cyclic, self._interpolation)

    interpolation = property(_GetInterpolation, _SetInterpolation)

    def _SetClamp(self, value):
        if self._clamp == value:
            return
        self._clamp = bool(value)
        self.emit(QtCore.SIGNAL("changed()"))

    def _GetClamp(self ):
        return self._clamp

    clamp = property(_GetClamp, _SetClamp)

    def _SetExteriorColor(self, color):
        if color == self._exterior_color:
            return
        try:
            color = tuple(color)
            if len(color) != 4:
                raise ValueError()
        except ValueError:
            raise ValueError("Exterior color must be an iterable of 4 elements")
        except TypeError:
            raise TypeError("Exterior color must be an iterable of 4 elements")
        self._exterior_color = color
        self.emit(QtCore.SIGNAL("changed()"))

    def _GetExteriorColor(self):
        return self._exterior_color

    exterior_color = property(_GetExteriorColor, _SetExteriorColor)

    def __len__(self):
        return len(self._values)

    def __iter__(self):
        return iter(sorted(self._keys.keys()))

    def interpolate(self, position, p1, col1, p2, col2):
        delta = float(p2-p1)
        dp1 = abs((position - p2)/delta)
        dp2 = abs((position - p1)/delta)
        if self._interpolation == "hsv":
            col1 = rgba_to_hsva(*col1)
            col2 = rgba_to_hsva(*col2)
            if self._cyclic:
                if col2[0] - col1[0] > 0.5:
                    col1 = (col1[0]+1,) + col1[1:]
                elif col1[0] - col2[0] > 0.5:
                    col2 = (col2[0]+1,) + col2[1:]
        col = tuple(i1*dp1 + i2*dp2 for i1,i2 in zip(col1, col2))
        if self._cyclic and (col[0] > 1 or col[0] < 0):
            col = (col[0]%1,) + col[1:]
        col = tuple(min(1.0, i) for i in col)
        if self._interpolation == "hsv":
            col = hsva_to_rgba(*col)
        return col

    def rgba(self, pos):
        prev_col = None
        prev_pos = None
        for p, col in self._values:
            if pos < p:
                if prev_col is None:
                    if self.clamp:
                        return col
                    else:
                        return self.exterior_color
                else:
                    return self.interpolate(pos, prev_pos, prev_col, p, col)
            elif pos == p:
                return col
            prev_col = col
            prev_pos = p
        if self.clamp:
            return prev_col
        else:
            return self.exterior_color

    def hsva(self, pos):
        return rgba_to_hsva(*self.rgba(pos))

    def update_keys(self):
        self._values.sort()
        keys = {}
        for i, v in enumerate(self._values):
            keys[v[0]] = i
        self._keys = keys
        
    def reverse(self):
        values = [ (1-pos, col) for pos,col in self._values ]
        values.sort()
        self._values = values
        self.update_keys()
        self.emit(QtCore.SIGNAL("changed()"))

    def add_rgba_point(self, pos, r, g, b, a):
        if pos in self._keys:
            id = self._keys[pos]
            if self._values[id][1] == (r,g,b,a):
                return
            self._values[id] = (pos, (r, g, b, a))
        else:
            self._values.append((pos, (r, g, b, a)))
            self._values.sort()
            self.update_keys()
        self.emit(QtCore.SIGNAL("changed()"))

    def add_hsva_point(self, pos, h, s, v, a):
        rgba = hsva_to_rgba(h, s, v, a)
        self.add_rgba_point(pos, *rgba)

    def remove_point(self, pos):
        if pos not in self._keys:
            raise ValueError("No point at pos %s" % pos)
        del self._values[self._keys[pos]]
        self.update_keys()
        self.emit(QtCore.SIGNAL("changed()"))

    def rgba_point(self, pos):
        return self._values[self._keys[pos]][1]

    def hsva_point(self, pos):
        return rgba_to_hsva(*self. rgba_point(pos))

    def _GetPointList(self):
        return self._values

    def _SetPointList(self, values):
        if values == self._values:
            return
        self._values = values
        self.update_keys()

    point_list = property(_GetPointList, _SetPointList)

    def clear(self):
        self._values = []
        self._keys = {}
        self.emit(QtCore.SIGNAL("changed()"))

    def move_point(self, old_pos, new_pos):
        if old_pos not in self._keys:
            raise ValueError("No point at pos %s" % old_pos)
        id = self._keys[old_pos]
        col = self._values[id][1]
        self._values[id] = (new_pos, col)
        self.update_keys()
        self.emit(QtCore.SIGNAL("changed()"))

    def next_pos(self, pos):
        if pos not in self._keys:
            raise ValueError("No point at pos %s" % pos)
        id = self._keys[pos]
        if id+1 < len(self._values):
            return self._values[id+1][0]
        return None

    def prev_pos(self, pos):
        if pos not in self._keys:
            raise ValueError("No point at pos %s" % pos)
        id = self._keys[pos]
        if id > 0:
            return self._values[id-1][0]
        return None

    @staticmethod
    def hue_scale():
        fct = TransferFunction()
        fct.add_hsva_point(0, 0, 1, 1, 0)
        fct.add_hsva_point(0.3, 0.3, 1, 1, 0.3)
        fct.add_hsva_point(0.7, 0.7, 1, 1, 0.7)
        fct.add_hsva_point(1, 1, 1, 1, 1)
        fct.interpolation = "hsv"
        return fct

    @staticmethod
    def gray_scale():
        fct = TransferFunction()
        fct.add_rgba_point(0, 0, 0, 0, 0)
        fct.add_rgba_point(1, 1, 1, 1, 1)
        fct.interpolation = "rgb"
        return fct

