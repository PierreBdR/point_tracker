__author__ = "Pierre Barbier de Reuille <pbdr@uea.ac.uk>"
__docformat__ = "restructuredtext"
from PyQt4.QtGui import QDialog
from PyQt4.QtCore import QString
from ui_alignmentdlg import Ui_AlignmentDlg

class AlignmentDlg(QDialog):
    def __init__(self, nb_pts, *args):
        QDialog.__init__(self, *args)
        ui = Ui_AlignmentDlg()
        ui.setupUi(self)
        self.ui = ui
        for i in xrange(nb_pts):
            s = QString.number(i)
            ui.referencePoint.addItem(s)
            ui.rotationPt1.addItem(s)
            ui.rotationPt2.addItem(s)
        ui.rotationPt1.setCurrentIndex(0)
        ui.rotationPt2.setCurrentIndex(1)

