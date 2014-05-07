"""
:newfield signal: Signal, Signals
"""
__author__ = "Pierre Barbier de Reuille <pbdr@uea.ac.uk>"
__docformat__ = "restructuredtext"

from PyQt4.QtGui import QDialog, QPixmap, QIcon, QMessageBox
from PyQt4.QtCore import QSize, Qt, QVariant, pyqtSignature
from ui_timeeditdlg import Ui_TimeEditDlg
from itertools import izip
import image_cache
from timemodel import time2hours, TimeDelegate, TimedImageModel

class TimeEditDlg(QDialog):
    def __init__(self, images, times, images_path, *args):
        QDialog.__init__(self, *args)
        cache = image_cache.cache
        self.ui = Ui_TimeEditDlg()
        self.ui.setupUi(self)
        icons = []
        for pth in images_path:
            ico = QIcon(QPixmap.fromImage(cache.image(pth).scaled(QSize(64,64), Qt.KeepAspectRatio)))
            icons.append(ico)
        self.model = TimedImageModel(icons, images, times)
        self.ui.imagesTiming.setModel(self.model)
        #self.ui.imagesTiming.resizeRowsToContents()
        self.ui.imagesTiming.resizeColumnToContents(0)
        self.ui.imagesTiming.resizeColumnToContents(1)
        self.delegate = TimeDelegate()
        self.ui.imagesTiming.setItemDelegate(self.delegate)

    def accept(self):
        if not self.model.isValid():
            if QMessageBox.critical(self, "Invalid time data", "The time data you entered are not valid.\n If you continue, your changes will be ignored.\nDo you want to continue?", QMessageBox.Yes|QMessageBox.No) == QMessageBox.Yes:
                return self.reject()
            return
        return QDialog.accept(self)

    @pyqtSignature("")
    def on_resetTiming_clicked(self):
        selected = self.ui.imagesTiming.selectionModel().selectedIndexes()
        rows = []
        for s in selected:
            if s.column() == 1:
                rows.append((s.row(), s))

        if len(rows) < 2:
            model = self.model
            rows = [ (r, model.index(r,1)) for r in xrange(model.rowCount(model.root)) ]
        rows.sort()

        start = self.model.times[rows[0][0]]
        dt = time2hours(self.ui.deltaTime.text())
        for (r,idx),t in izip(rows, (start+n*dt for n in xrange(len(rows)))):
            self.model.setData(idx, QVariant(t), Qt.EditRole)
        self.ui.imagesTiming.viewport().update()

