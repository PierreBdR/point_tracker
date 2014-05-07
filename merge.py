#! /usr/bin/env python
from __future__ import print_function, division, absolute_import
from PyQt4.QtCore import *
from PyQt4.QtGui import *
from src.path import path

QCoreApplication.setOrganizationName("PBdR")
QCoreApplication.setApplicationName("PointTracker")
QCoreApplication.setOrganizationDomain("barbierdereuille.net")
#QSettings.setDefaultFormat(QSettings.IniFormat)

import sys
app = QApplication(sys.argv)

from src import tracking_data, project, debug

debug.restore_io()

files = QFileDialog.getOpenFileNames(None, "Select files to merge", "", "CSV files (*.csv);;All files (*.*)")
if len(files) < 2:
  print "You need to select at least 2 files"
  sys.exit(2)

first_file = path(files[0])
data_dir = first_file.dirname()

data = [ tracking_data.TrackingData(None, False, path(f)) for f in files ]

whole = data[0]

def nb_points(d):
  return max([max(d.data[img].keys()) for img in d.data if d.data[img]])+1

print "Nb of point in first image: %d" % nb_points(whole)
print "Nb of cells in first image: %d" % len(whole.cells)

for d in data[1:]:
  print "Nb of point in next image: %d" % nb_points(d)
  print "Nb of cells in next image: %d" % len(d.cells)
# Update cells and points shift
  shift_pts = nb_points(whole)
  shift_cell = len(whole.cells)
# First, align the images and add the points
  for img in d.data:
    w_data = whole[img]
    d_data = d[img]
    d_data.move(*w_data.shift)
    for p in d_data:
      w_data[p+shift_pts] = d_data[p]
# Then, the cells
  for c in d.cells:
    whole.cells[c+shift_cell] = tuple(p+shift_pts for p in d.cells[c])
# Last, the lifespan
  for c in d.cells_lifespan:
    ls = d.cells_lifespan[c]
    new_ls = tracking_data.LifeSpan(ls.start, ls.end)
    if ls.daughters:
      new_ls.daughters = (ls.daughters[0]+shift_cell, ls.daughters[1]+shift_cell)
      new_ls.division = (ls.division[0]+shift_pts, ls.division[1]+shift_pts)
    whole.cells_lifespan[c+shift_cell] = new_ls

print "Nb of point in next image: %d" % nb_points(whole)
print "Nb of cells in merged image: %d" % len(whole.cells)

newfile = QFileDialog.getSaveFileName(None, "File to save with merged data", data_dir, "CSV Files (*.csv);; All files (*.*)")
if not newfile.isEmpty():
  newfile = path(newfile)
  whole.save(newfile)

