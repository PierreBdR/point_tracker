from __future__ import print_function, division, absolute_import
__docformat__ = "restructuredtext"
import scipy
from scipy import nonzero, array, concatenate
from scipy import misc
import sys
from .path import path
from .project import Project
import csv
import os.path

grey_threshold = 40
color_distance = 80

class Data(object):
    def __init__(self, proj):
        self.project = proj
        self.colors = None
        self.pts_colors = {} # Associate to each color a pt id
        self.pts = {} # Associate to point an array of pos per time
        self.list_imgs = [ f.basename() for f in proj.images_dir.files() ]
# Then, find the files with the most common extensions
        exts = [ os.path.splitext(f)[1] for f in self.list_imgs ]
        ext_count = {}
        for e in exts:
            ext_count.setdefault(e, 0)
            ext_count[e] += 1
        maj_ext = max(ext_count.keys(), key=ext_count.__getitem__)
        self.list_imgs = [ f for f in self.list_imgs if f.endswith(maj_ext) ]
        self.list_imgs.sort()

    def get_pts(self, color):
        color = tuple(color)
        if color not in self.pts_colors:
# First, look for a color close to it
            idx = None
            if self.colors is not None:
                d = abs(self.colors - array([color]))
                d = d.sum(1)
                if d.min() < color_distance:
                    color_idx = d.argmin()
                    idx = self.pts_colors[tuple(self.colors[color_idx,:])]
            if idx is None:
                idx = len(self.pts)
                self.pts[idx] = [ () for i in self.list_imgs ]
            self.pts_colors[color] = idx
            if self.colors is None:
                self.colors = array([color], dtype='int16')
            else:
                self.colors = concatenate((self.colors, [color]))
        else:
            idx = self.pts_colors[color]
        return self.pts[idx]

    def process(self, i):
        img_file = self.list_imgs[i]
        print("Processing image: %s" % img_file)
        img = misc.imread(self.project.images_dir / img_file)
# First, find the list of color points
        img_diff = img.astype('int16')
        if len(img_diff.shape) != 3 or img_diff.shape[2] != 3:
            print("  Image has shape %s. Skipping." % (img_diff.shape,))
            return
        img_diff -= img_diff[...,[1,2,0]]
        Y,X = nonzero(img_diff.max(2) > 40)
        print "  Found %d points" % len(X)
# Second, store their points
        for x,y in zip(X,Y):
            c = img[y,x]
            pt = self.get_pts(c)
            pt[i] = (x,y)
        print("  Total nb of points: %d" % len(self.pts))

    def save(self, filename):
        f = (self.project.data_dir / filename).open("wb")
        w = csv.writer(f, delimiter=",")
        w.writerow(["TRK_VERSION", "0.1"])
        imgs = sum([ [img,''] for img in self.list_imgs ], [])
        w.writerow(["Images"] + imgs)
        shifts = ["XY Shift"] + (["0","0"]*len(self.list_imgs))
        w.writerow(shifts)
        an_shift = ["Angle Shift"] + (["0.0", ""] * len(self.list_imgs))
        w.writerow(an_shift)
        for i in range(len(self.pts)):
            pt = [ "Point %d" % i ]
            for pos in self.pts[i]:
                if pos:
                    pt += [ repr(pos[0]), repr(pos[1]) ]
                else:
                    pt += [ "", "" ]
            w.writerow(pt)

def main():
    p = ""
    savefile = ""
    if len(sys.argv) > 1:
         p = path(sys.argv[1])
         if not p.exists():
             p = ""
    if len(sys.argv) > 2:
        savefile = path(sys.argv[2]).expand()
    while not p:
        p = raw_input("Enter the path to the project: ")
        if p[0] == '"' and p[-1] == '"':
            p = p[1:-1]
        p = path(p).expand()
        if not p.exists():
            p = ""
    proj = Project(p)
    if not proj.valid:
        print("Warning, the project directory doesn't have the valid structure.")
        a = raw_input("Do you want to convert it?").lower()
        if a == "y" or a == "yes":
            proj.create()
        else:
            print("Ok, aborting.")
            return
    proj.use()
    d = Data(proj)
    for i in range(len(d.list_imgs)):
        d.process(i)
    if not savefile:
        savefile = raw_input("Please enter the name of the file to save: [default:tracking.csv]")
        if not savefile:
            savefile = path("tracking.csv")
        savefile = path(savefile).expand()
    d.save(savefile)

if __name__ == "__main__":
    main()
