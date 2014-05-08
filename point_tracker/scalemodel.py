from __future__ import print_function, division, absolute_import
# -*- coding: utf8 -*-
"""
:newfield signal: Signal, Signals
"""
__author__ = "Pierre Barbier de Reuille <pierre@barbierdereuille.net>"
__docformat__ = "restructuredtext"

from PyQt4.QtGui import QItemDelegate, QLineEdit, QBrush, QColor, QPalette
from PyQt4.QtCore import Qt, QAbstractTableModel, QModelIndex, SIGNAL
from math import floor

class ScaleModel(QAbstractTableModel):
    def __init__(self, icons, names, scales):
        QAbstractTableModel.__init__(self, None)
        self.factor = self.old_factor = 1
        self.unit = 'm'
        self.icons = icons
        self.names = names
        self.scales = [ [float(scales[img][0]), float(scales[img][1])] for img in names ]
        root = QModelIndex()
        for idx in range(len(names)):
            self.createIndex(idx, 0, root)
            self.createIndex(idx, 1, root)
        self.root = root

    def findUnit(self, size):
        if size > 90:
            idx = 0
            unit = 'km'
        elif size > .09:
            idx = 1
            unit = 'm'
        elif size > 9e-5:
            idx = 2
            unit = 'mm'
        elif size > 9e-8:
            idx = 3
            unit = u'µm'
        else:
            idx = 4
            unit= 'nm'
        self.setUnit(unit)
        return idx

    def setUnit(self, unit):
        self.old_factor = self.factor
        self.unit = unit
        if unit == 'km':
            self.factor = 1e3
        elif unit == 'm':
            self.factor = 1
        elif unit == 'mm':
            self.factor = 1e-3
        elif unit == 'nm':
            self.factor = 1e-9
        else: # µm
            self.factor = 1e-6
        self.updateValues()

    def updateValues(self):
        for i,sc in enumerate(self.scales):
            sc = (float(sc[0])*self.old_factor, float(sc[1])*self.old_factor)
            self.scales[i] = [sc[0]/self.factor, sc[1]/self.factor]
        self.old_factor = self.factor
        self.allModified()

    def rowCount(self, parent):
        if parent == self.root:
            return len(self.names)
        return 0

    def columnCount(self, parent = None):
        return 3

    def data(self, index, role):
        if not index.isValid():
            return None

        row = index.row()
        column = index.column()

        if row >= len(self.names):
            return None

        if column >= 3:
            return None

        if column == 0:
            if role == Qt.DisplayRole:
                return self.names[row]
            elif role == Qt.DecorationRole:
                return self.icons[row]
        elif column == 1:
            if role == Qt.DisplayRole:
                return "%g %s" % (self.scales[row][0], self.unit)
            elif role == Qt.EditRole:
                return self.scales[row][0]
        else:
            if role == Qt.DisplayRole:
                return "%g %s" % (self.scales[row][1], self.unit)
            elif role == Qt.EditRole:
                return self.scales[row][1]

        if role == Qt.BackgroundRole:
            return QBrush(Qt.white)

        return None

    def headerData(self, section, orientation, role = Qt.DisplayRole):
        if role != Qt.DisplayRole:
            return None

        if orientation == Qt.Horizontal:
            if section == 0:
                return "Image"
            elif section == 1:
                return "Pixel width"
            elif section == 2:
                return "Pixel height"
        return None

    def flags(self, index):
        if not index.isValid():
            return Qt.ItemIsEnabled

        base = QAbstractTableModel.flags(self, index)
        if index.column() > 0:
            return base | Qt.ItemIsEditable
        return base

    def setData(self, index, value, role):
        column = index.column()
        if index.isValid() and column > 0 and role == Qt.EditRole:
            row = index.row()
            try:
                value = float(value)
            except (ValueError, TypeError):
                return False
            next_row_changed = False
            self.scales[row][column-1] = value
            self.emit(SIGNAL("dataChanged(const QModelIndex&,const QModelIndex&)"), index, index)
            return True
        return False

    def __iter__(self):
        for n,s in zip(self.names, self.scales):
            yield n,(s[0]*self.factor, s[1]*self.factor)

    def __getitem__(self, idx):
        s = self.scales[idx.row()]
        return self.names[idx], (s[0]*self.factor, s[1]*self.factor)

    def __len__(self):
        return len(self.names)

    def name(self, idx):
        return self.names[idx.row()]

    def icon(self, idx):
        return self.icons[idx.row()]

    def scale(self, idx):
        s = self.scales[idx.row()]
        return (s[0]*self.factor, s[1]*self.factor)

    def position(self, idx):
        return idx.row()

    def allModified(self):
        self.emit(SIGNAL("dataChanged(const QModelIndex&,const QModelIndex&)"), self.index(0,1), self.index(len(self.names)-1, 2))

    def subsetModified(self, sel):
        rows = [ r.row() for r in sel.selectedRows(1) ]
        self.emit(SIGNAL("dataChanged(const QModelIndex&,const QModelIndex&)"), self.index(min(rows),1), self.index(max(rows), 2))

    def setAll(self, w, h):
        w = float(w)
        h = float(h)
        for i,sc in enumerate(self.scales):
            self.scales[i] = [w,h]
        self.allModified()

    def setSubset(self, w, h, sel):
        rows = [ r.row() for r in sel.selectedRows(1) ]
        for r in rows:
            self.scales[r] = [w,h]
        self.subsetModified(sel)
