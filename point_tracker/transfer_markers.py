from __future__ import print_function, division, absolute_import
'''
Module defining the model behind the markers of the transfer function
'''

from PyQt4.QtCore import QAbstractTableModel, Qt, QModelIndex
from PyQt4.QtGui import QLineEdit, QDoubleValidator, QItemDelegate, QPalette, QBrush, QColor

class MarkerColorDelegate(QItemDelegate):
    def __init__(self, parent = None):
        QItemDelegate.__init__(self, parent)

    def createEditor(self, parent, option, index):
        editor = QLineEdit(parent)
        if index.column() == 0:
            editor.setValidator(QDoubleValidator(0, 1, 6, editor))
        else:
            editor.setInputMask(r"\#HHHHHHHH")
        return editor

    def setEditorData(self, editor, index):
        if index.column() == 0:
            try:
                value = float(index.model().data(index, Qt.EditRole))
            except (ValueError, TypeError):
                return
            editor.setText("%.6f" % (value,))
        else:
            txt = index.model().data(index, Qt.EditRole)
            editor.setText(txt)

    def setModelData(self, editor, model, index):
        if index.column() == 0:
            value = float(editor.text())
        else:
            value = str(editor.text())
        model.setData(index, value, Qt.EditRole)

    def updateEditorGeometry(self, editor, option, index):
        editor.setGeometry(option.rect)

class TransferMarkerModel(QAbstractTableModel):
    def __init__(self, markers, colors, mode, show_rgba):
        QAbstractTableModel.__init__(self, None)
        assert len(markers) == len(colors)
        self.markers = markers
        self.colors = colors
        root = QModelIndex()
        for idx in range(len(markers)):
            self.createIndex(idx, 0, root)
            self.createIndex(idx, 1, root)
        self.root = root
        self.mode = mode
        self.show_rgba = show_rgba
        
    def colorText(self, idx):
        col = self.colors[idx]
        if self.show_rgba:
            return "#%02x%02x%02x%02x" % (col.red(), col.green(), col.blue(), col.alpha())
        else:
            return "#%02x%02x%02x%02x" % (col.hue(), col.value(), col.saturation(), col.alpha())
        
    def setColorText(self, idx, txt):
        if len(txt) != 9 or txt[0] != '#':
            return False
        if self.show_rgba:
            r = int(txt[1:3], 16)
            g = int(txt[3:5], 16)
            b = int(txt[5:7], 16)
            a = int(txt[7:9], 16)
            col = QColor.fromRgb(r,g,b,a)
        else:
            h = int(txt[1:3], 16)
            v = int(txt[3:5], 16)
            s = int(txt[5:7], 16)
            a = int(txt[7:9], 16)
            col = QColor.fromHsv(h, s, v, a)
        self.colors[idx] = col
        return True

    def rowCount(self, parent):
        if parent == self.root:
            return len(self.markers)
        return 0
    
    def columnCount(self, parent):
        return 2
    
    def flags(self, index):
        if not index.isValid():
            return Qt.NoItemFlags
        row = index.row()
        column = index.column()
        if column == 0 and (row == 0 or row == len(self.markers)-1):
            return Qt.ItemIsSelectable | Qt.ItemIsEnabled
        else:
            return Qt.ItemIsSelectable | Qt.ItemIsEditable | Qt.ItemIsEnabled
    
    def data(self, index, role):
        if not index.isValid():
            return None

        row = index.row()
        column = index.column()

        if row >= len(self.markers) or column > 1:
            return None

        if column >= 2:
            return None

        if column == 0:
            if role == Qt.DisplayRole or role == Qt.EditRole:
                return float(self.markers[row])
        else:
            if role == Qt.DisplayRole or role == Qt.EditRole:
                return self.colorText(row)
            elif role == Qt.DecorationRole:
                return self.colors[row]
        return None
    
    def setData(self, index, value, role):
        if not index.isValid():
            return False
        row = index.row()
        column = index.column()
        
        if row >= len(self.markers) or column > 1:
            return False

        if column == 0:
            if row == 0 or row == len(self.markers)-1:
                return False
            try:
                val = float(value)
            except (TypeError, ValueError):
                return False
            if val <= self.markers[row-1] or val >= self.markers[row+1]:
                return False
            self.markers[row] = val
            self.dataChanged.emit(index, index)
            return True
        else:
            if self.setColorText(row, str(value)):
                self.dataChanged.emit(index, index)
                return True
        return False
    
    def headerData(self, section, orientation, role = Qt.DisplayRole):
        if role != Qt.DisplayRole:
            return None

        if orientation == Qt.Horizontal:
            if section == 0:
                return "Position"
            elif section == 1:
                return "Color"
        return None
    
    def addMarker(self, selection):
        rows = [m.row() for m in selection.indexes()]
        if not rows:
            return
        max_row = max(rows)
        if max_row < len(self.markers)-1:
            self.beginInsertRows(self.root, max_row+1, max_row+1)
            new_pt = (self.markers[max_row] + self.markers[max_row+1])/2
            col1 = self.colors[max_row]
            col2 = self.colors[max_row+1]
            col = QColor()
            if self.mode == "rgb":
                r = (col1.redF()+col2.redF())/2
                g = (col1.greenF()+col2.greenF())/2
                b = (col1.blueF()+col2.blueF())/2
                a = (col1.alphaF()+col2.alphaF())/2
                col.setRgbF(r,g,b,a)
            elif self.mode == "hsv":
                h = (col1.hueF()+col2.hueF())/2
                s = (col1.saturationF()+col2.saturationF())/2
                v = (col1.valueF()+col2.valueF())/2
                a = (col1.alphaF()+col2.alphaF())/2
                col.setHsvF(h,s,v,a)
            else: # cyclic_hsv
                h1 = col1.hueF()
                h2 = col2.hueF()
                if h2 < h1:
                    h1,h2 = h2,h1
                if h2-h1 < 0.5:
                    h = (h2+h1)/2
                else:
                    h = (h1+h2+1)/2
                    if h > 1:
                        h -= 1
                s = (col1.saturationF()+col2.saturationF())/2
                v = (col1.valueF()+col2.valueF())/2
                a = (col1.alphaF()+col2.alphaF())/2
                col.setHsvF(h,s,v,a)
            self.markers.insert(max_row+1, new_pt)
            self.colors.insert(max_row+1, col)
            self.endInsertRows()
    
    def removeMarker(self, selection):
        rows = [m.row() for m in selection.indexes()]
        if not rows:
            return
        min_row = min(rows)
        max_row = max(rows)
        if min_row == 0:
            min_row = 1
        if max_row == len(self.markers)-1:
            max_row -= 1
        if min_row > max_row:
            return
        self.beginRemoveRows(self.root, min_row, max_row)
        del self.markers[min_row:max_row+1]
        del self.colors[min_row:max_row+1]
        self.endRemoveRows()

    def spreadMarkers(self, selection):
        rows = [m.row() for m in selection.indexes()]
        if not rows:
            return
        min_row = min(rows)
        max_row = max(rows)
        if max_row <= min_row:
            return
        markers = self.markers
        min_marker = markers[min_row]
        max_marker = markers[max_row]
        delta = (max_marker - min_marker) / (max_row - min_row)
        value = min_marker
        for i in range(min_row+1, max_row):
            value += delta
            markers[i] = value
        self.dataChanged.emit(self.index(min_row+1, 0), self.index(max_row-1, 1))
        
    def rgbaMode(self):
        if not self.show_rgba:
            self.show_rgba = True
            self.dataChanged.emit(self.index(0,1), self.index(len(self.markers)-1, 1))

    def hsvaMode(self):
        if self.show_rgba:
            self.show_rgba = False
            self.dataChanged.emit(self.index(0,1), self.index(len(self.markers)-1, 1))
