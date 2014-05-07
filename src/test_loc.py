__docformat__ = "restructuredtext"
import sys
from PyQt4.QtCore import QCoreApplication, QLibraryInfo

print sys.argv
app = QCoreApplication(sys.argv)
print QCoreApplication.applicationDirPath()
loc = str(QLibraryInfo.location(QLibraryInfo.ExamplesPath))
print loc
loc = str(QLibraryInfo.location(QLibraryInfo.DemosPath))
print loc
loc = str(QLibraryInfo.location(QLibraryInfo.DocumentationPath))
print loc

