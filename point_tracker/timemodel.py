from __future__ import print_function, division, absolute_import
"""
:newfield signal: Signal, Signals
"""
__author__ = "Pierre Barbier de Reuille <pierre@barbierdereuille.net>"
__docformat__ = "restructuredtext"

from PyQt4.QtGui import QItemDelegate, QLineEdit, QBrush, QColor, QPalette
from PyQt4.QtCore import Qt, QAbstractTableModel, QModelIndex
from math import floor
from .sys_utils import cleanQObject

def time2hours(time_str):
    time_str = str(time_str)
    assert time_str[-3:] == "min"
    time_str = time_str[:-3]
    time_comp = time_str.split('h')
    assert len(time_comp) == 2
    h = float(time_comp[0])
    m = float(time_comp[1])
    return h+m/60

def hours2time(hours):
    h = int(floor(hours))
    m = int(round((hours-h)*60))
    return "%dh%02dmin" % (h,m)

class TimeDelegate(QItemDelegate):
    def __init__(self, parent = None):
        QItemDelegate.__init__(self, parent)

    def __del__(self):
        cleanQObject(self)

    def createEditor(self, parent, option, index):
        editor = QLineEdit(parent)
        editor.setInputMask(r"000009\h09mi\n; ")
        return editor

    def setEditorData(self, editor, index):
        try:
            value = float(index.model().data(index, Qt.EditRole))
            editor.setText(hours2time(value).rjust(editor.maxLength()))
        finally:
            pass

    def setModelData(self, editor, model, index):
        value = time2hours(editor.text())
        model.setData(index, value, Qt.EditRole)

    def updateEditorGeometry(self, editor, option, index):
        editor.setGeometry(option.rect)

    def paint(self, painter, option, index):
        palette = option.palette
        color_select = palette.brush(QPalette.Highlight)
        if not index.model().isValid(index):
            palette.setBrush(QPalette.Highlight, QBrush(QColor(170,0,255)))
        return QItemDelegate.paint(self, painter, option, index)

class TimedImageModel(QAbstractTableModel):
    def __init__(self, icons, names, times):
        QAbstractTableModel.__init__(self, None)
        self.icons = icons
        self.names = names
        self.times = [ float(t) for t in times ]
        self._valid = [ times[i] > times[i-1] if i > 0 else True for i in range(len(times)) ]
        root = QModelIndex()
        for idx in range(len(names)):
            self.createIndex(idx, 0, root)
            self.createIndex(idx, 1, root)
        self.root = root

    def __del__(self):
        cleanQObject(self)

    def rowCount(self, parent):
        if parent == self.root:
            return len(self.names)
        return 0

    def columnCount(self, parent = None):
        return 2

    def data(self, index, role):
        if not index.isValid():
            return

        row = index.row()
        column = index.column()

        if row >= len(self.names):
            return

        if column >= 2:
            return

        if column == 0:
            if role == Qt.DisplayRole:
                return self.names[row]
            elif role == Qt.DecorationRole:
                return self.icons[row]
        else:
            if role == Qt.DisplayRole:
                return hours2time(self.times[row])
            elif role == Qt.EditRole:
                return self.times[row]

        if role == Qt.BackgroundRole:
                if self._valid[row]:
                    return QBrush(Qt.white)
                else:
                    return QBrush(QColor(Qt.red).lighter())

        return None

    def headerData(self, section, orientation, role = Qt.DisplayRole):
        if role != Qt.DisplayRole:
            return None

        if orientation == Qt.Horizontal:
            if section == 0:
                return "Image"
            elif section == 1:
                return "Time"
        return None

    def flags(self, index):
        if not index.isValid():
            return Qt.ItemIsEnabled

        base = QAbstractTableModel.flags(self, index)
        if index.column() == 1:
            return base | Qt.ItemIsEditable
        return base

    def setData(self, index, value, role):
        if index.isValid() and index.column() == 1 and role == Qt.EditRole:
            row = index.row()
            try:
                time = float(value)
            except (ValueError, TypeError):
                return False
            next_row_changed = False
            self.times[row] = time
            self._updateValids()
            self.dataChanged['const QModelIndex&','const QModelIndex&'].emit(index, index)
            return True
        return False

    def __iter__(self):
        for n,t in zip(self.names, self.times):
            yield (n,t)

    def __getitem__(self, idx):
        return self.names[idx], self.times[idx]

    def __len__(self):
        return len(self.names)

    def isValid(self, idx = None):
        if idx is None:
            return all(self._valid)
        else:
            return self._valid[idx.row()]

    def addImage(self, icon, name, time):
        root = self.root
        if self.times:
            for idx,t in enumerate(self.times):
                if t == time:
                    return False
                if t > time:
                    break
            if time > self.times[idx]:
                idx += 1
        else:
            idx = 0
        self.beginInsertRows(root, idx, idx)
        self.icons.insert(idx, icon)
        self.names.insert(idx, name)
        self.times.insert(idx, time)
        self.createIndex(idx, 0, root)
        self.createIndex(idx, 1, root)
        self._updateValids()
        self.endInsertRows()
        return True

    def removeImage(self, position):
        root = self.root
        self.beginRemoveRows(root, position, position)
        del self.icons[position]
        del self.times[position]
        del self.names[position]
        self._updateValids()
        self.endRemoveRows()
        
    def clear(self):
        root = self.root
        self.beginRemoveRows(root, 0, len(self.names)-1)
        del self.icons[:]
        del self.times[:]
        del self.names[:]
        self.endRemoveRows()

    def _updateValids(self):
        times = self.times
        self._valid = [ times[i] > max(times[:i]) if i > 0 else times[i] >= 0 for i in range(len(times)) ]

    def name(self, idx):
        return self.names[idx.row()]

    def icon(self, idx):
        return self.icons[idx.row()]

    def time(self, idx):
        return self.times[idx.row()]

    def position(self, idx):
        return idx.row()

