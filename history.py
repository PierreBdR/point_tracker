data= main_win._data
data.cells[2]
data.images_name 
data1 = data[data.images_name[0]]
data2 = data[data.images_name[1]]
38 in data1
52 in data1
c1 = [ pid for pid in data.cells[2] if pid in data1 ]
c2 = [ pid for pid in data.cells[2] if pid in data2 ]
c1
c2
import src.growth_computation_methods
import src.growth_computation_methods as scm
import src.growth_computation_methods as gcm
gcm.align_segments([38, 51], [38, 52, 51], data1, data2)
import pdb
pdb.pm()
reload(src.growth_computation_methods)
gcm.align_segments([38, 51], [38, 52, 51], data1, data2)
import pdb
pdb.pm()
reload(src.growth_computation_methods)
resutl = gcm.align_segments([38, 51], [38, 52, 51], data1, data2)
import pdb
pdb.pm()
data2.walls[51,52]
_ip.magic("p all")

reload(src.growth_computation_methods)
result = gcm.align_segments(s1,s2,data1,data2)
result = gcm.align_segments(s1,s2,data1,data2)
resutl = gcm.align_segments([38, 51], [38, 52, 51], data1, data2)
reload(src.growth_computation_methods)
resutl = gcm.align_segments([38, 51], [38, 52, 51], data1, data2)
reload(src.growth_computation_methods)
resutl = gcm.align_segments([38, 51], [38, 52, 51], data1, data2)
resutl 
data2.walls[52,51]
help(pdb)
result = pdb.runcall(gcm.align_segments, [38, 51], [38, 52, 51], data1, data2)
reload(src.growth_computation_methods)
gcm.align_segments([38, 51], [38, 52, 51], data1, data2)
result = pdb.runcall(gcm.align_segments, [38, 51], [38, 52, 51], data1, data2)
reload(src.growth_computation_methods)
result = pdb.runcall(gcm.align_segments, [38, 51], [38, 52, 51], data1, data2)
result = gcm.align_segments([38, 51], [38, 52, 51], data1, data2)
import pdb
pdb.pm()
reload(src.growth_computation_methods)
result = gcm.align_segments([38, 51], [38, 52, 51], data1, data2)
result
result[0]
result[1]
result = pdb.runcall(gcm.align_segments, [38, 51], [38, 52, 51], data1, data2)
reload(src.growth_computation_methods)
result = gcm.align_segments([38, 51], [38, 52, 51], data1, data2)
result
l = [PyQt4.QtCore.QPointF(913.79642723539303, 2214.5778902924535),
    PyQt4.QtCore.QPointF(893.39400000000001, 2207.0500000000002),
    PyQt4.QtCore.QPointF(895.79700000000003, 2217.0799999999999), PyQt4.QtCore.QPointF(896.2045041633786, 2217.7449649527935)]
import PyQt4.QtCore
l = [PyQt4.QtCore.QPointF(913.79642723539303, 2214.5778902924535),
    PyQt4.QtCore.QPointF(893.39400000000001, 2207.0500000000002),
    PyQt4.QtCore.QPointF(895.79700000000003, 2217.0799999999999), PyQt4.QtCore.QPointF(896.2045041633786, 2217.7449649527935)]
diff = l[1:] - l[:-1]
diff = [ p-q for p,q in zip(l[1:],l[:-1])]
from itertool import zip
from itertools import zip
diff = [ p-q for p,q in zip(l[1:],l[:-1])]
print(sum(sqrt(p.x()*p.x() + p.y()*p.y()) for p in diff))
from math import sqrt
print(sum(sqrt(p.x()*p.x() + p.y()*p.y()) for p in diff))
reload(src.growth_computation_methods)
result = pdb.runcall(gcm.align_segments, [38, 51], [38, 52, 51], data1, data2)
reload(src.growth_computation_methods)
result = pdb.runcall(gcm.align_segments, [38, 51], [38, 52, 51], data1, data2)
reload(src.growth_computation_methods)
result = pdb.runcall(gcm.align_segments, [38, 51], [38, 52, 51], data1, data2)
result = pdb.runcall(gcm.align_segments, [38, 51], [38, 52, 51], data1, data2)
for i in []:
    pass
else:
    print "bo break"
for i in []:
    break
else:
print("bo break")
for i in []:
    break
else:
print("bo break")
for i in []:
    pass
else:
print("bo break")
_ip.magic("edit _i84")
reload(src.growth_computation_methods)
result = gcm.align_segments([38, 51], [38, 52, 51], data1, data2)
result
result = pdb.runcall(gcm.align_segments, [38, 51], [38, 52, 51], data1, data2)
reload(src.growth_computation_methods)
result = gcm.align_segments([38, 51], [38, 52, 51], data1, data2)
result
data2.walls[52,51]
result[0]
result
aligned_pts,aligned_new_pts = result
sum(seg for (seg,_) in aligned_pts)
sum(seg for (seg,_) in aligned_pts, [])
sum((seg for (seg,_) in aligned_pts), [])
sum((seg for (seg,_) in aligned_new_pts), [])
reload(src.growth_computation_methods)
reload(src.growth_computation_methods)
aligned_pts
aligned_pts[1]
aligned_pts[1][0]
aligned_pts[1][0]+aligned_pts[0][0:1]
aligned_pts[1][0]+aligned_pts[0][0][0:1]
aligned_pts[1][0]
gcm.discretize_segment(aligned_pts[1][0], 10, gcm.length_polyline(aligned_pts[1][0]))
reload(src.growth_computation_methods)
gcm.discretize_segment(aligned_pts[1][0], 10, gcm.length_polyline(aligned_pts[1][0]))
res = gcm.discretize_segment(aligned_pts[1][0], 10, gcm.length_polyline(aligned_pts[1][0]))
len(res)
diffs = res[1:] - res[:-1]
diffs = [ p - q for p,q in zip(res[1:],res[:-1])]
[sqrt(p.x()*p.x() + p.y()*p.y()) for p in diffs]
reload(src.growth_computation_methods)
res = gcm.discretize_segment(aligned_pts[1][0], 10, gcm.length_polyline(aligned_pts[1][0]))
diffs = [ p - q for p,q in zip(res[1:],res[:-1])]
[sqrt(p.x()*p.x() + p.y()*p.y()) for p in diffs]
res = pdb.runcall(gcm.discretize_segment,aligned_pts[1][0], 10, gcm.length_polyline(aligned_pts[1][0]))
reload(src.growth_computation_methods)
res = gcm.discretize_segment(aligned_pts[1][0], 10, gcm.length_polyline(aligned_pts[1][0]))
diffs = [ p - q for p,q in zip(res[1:],res[:-1])]
[sqrt(p.x()*p.x() + p.y()*p.y()) for p in diffs]
sum([sqrt(p.x()*p.x() + p.y()*p.y()) for p in diffs])
3.3511328858834157*9
reload(src.growth_computation_methods)
pts
c2 = [ pid for pid in data.cells[2] if pid in data2 ]
c1
c2
result = gcm.alignCells(c1, c2, data1, data2)
import pdb
pdb.pm()
reload(src.growth_computation_methods)
result = gcm.alignCells(c1, c2, data1, data2)
reload(src.growth_computation_methods)
result = gcm.alignCells(c1, c2, data1, data2)
result = gcm.alignCells(c1, c2, data1, data2, True)
reload(src.growth_computation_methods)
result = gcm.alignCells(c1, c2, data1, data2, True)
result = gcm.alignCells(c1, c2, data1, data2, 50, True)
pdb.pm()
reload(src.growth_computation_methods)
result = gcm.alignCells(c1, c2, data1, data2, 50, True)
result
c1
c2
pts1 = [data1[pid] for pid in c1]
pts2 = [data2[pid] for pid in c2]
from pylab import *
ion()
ppts1 = array([[p.x(), p.y()] for p in pts1])
ppts2 = array([[p.x(), p.y()] for p in pts2])
plot(ppts1, '+-')
clf()
ppts.shape
ppts1.shape
plot(ppts1[:,0], ppts1[:,1])
help(axis)
axis('equal')
axis('ij')
help(axis)
axis('image')
help(axis)
axis()
a = axis()
axis((a[0], a[1], a[3], a[2]))
help(axis)
axis('equal')
ppts1 = array([[p.x(), p.y()] for p in pts1+pts1[0:1]])
ppts2 = array([[p.x(), p.y()] for p in pts2+pts2[0:1]])
clf()
plot(ppts1[:,0], ppts1[:,1])
axis('equal')
ylim(ylim()[::-1])
main_win._previousScene.cells[2]
main_win._previousScene.cells[2]
ci1 = main_win._previousScene.cells[2]
ci1.polygon_shape 
list(ci1.polygon_shape )
shape1 = list(ci1.polygon_shape )
list(ws)
ci2 = main_win._currentScene.cells[2]
shape2 = list(ci2.polygon_shape)
ppts1 = array([[p.x(), p.y()] for p in shape1+shape1[0:1]])
ppts2 = array([[p.x(), p.y()] for p in shape2+shape2[0:1]])
clf()
plot(ppts1[:,0], ppts1[:,1])
axis('equal')
ylim(ylim()[::-1])
figure(2)
plot(ppts2[:,0], ppts1[:,2])
plot(ppts2[:,0], ppts2[:,2])
plot(ppts2[:,0], ppts2[:,1])
axis('equal')
ylim(ylim()[::-1])
len(result)
figure(1)
sa1 = array([[p.x(), p.y()] for p in result[2] + result[2][0:1]])
sa2 = array([[p.x(), p.y()] for p in result[3] + result[3][0:1]])
plot(sa1[:,0], sa1[:,1])
sa1
ppts1
clf()
ci1.center 
ppts1 += array([ci1.center.x(), ci1.center.y()])
plot(ppts1[:,0], ppts1[:,1])
plot(sa1[:,0], sa1[:,1])
axis('equal')
ylim(ylim()[::-1])
figure(2)
ppts2 += array([ci2.center.x(), ci2.center.y()])
clf()
plot(ppts2[:,0], ppts2[:,1])
plot(sa2[:,0], sa2[:,1])
axis('equal')
ylim(ylim()[::-1])
figure(1)
clf()
plot(ppts1[:,0], ppts1[:,1])
aligned1 = result[0]
aligned2 = result[1]
segs1 = sum((seg[0] for seg in aligned1), [])
aligned1[0][0]
list(seg[0] for seg in aligned1)
concatenate(seg[0] for seg in aligned1)
concatenate([seg[0] for seg in aligned1])
concatenate([seg[0] for seg in aligned1]).shape
#?flatten
flatten(seg[0] for seg in aligned1)
len(list(flatten(seg[0] for seg in aligned1)))
segs1 = list(flatten(seg[0] for seg in aligned1))
segs2 = list(flatten(seg[0] for seg in aligned2))
ss1 = array([p.x(), p.y()] for p in segs1+segs1[0:1]])
ss1 = array([[p.x(), p.y()] for p in segs1+segs1[0:1]])
ss2 = array([[p.x(), p.y()] for p in segs2+segs2[0:1]])
figure(1)
plot(ss1[:,0], ss2[:,1])
plot(ss1[:,0], ss1[:,1])
s1
segs1
aligned1
help(enumerate)
reload(src.growth_computation_methods)
result = gcm.alignCells(c1, c2, data1, data2, 50, True)
aligned1, aligned2, ps, qs = result
clf()
segs1 = list(flatten(seg[0] for seg in aligned1))
plot(ppts1[:,0], ppts1[:,1])
ss1 = array([[p.x(), p.y()] for p in segs1+segs1[0:1]])
plot(ss1[:,0], ss2[:,1])
plot(ss1[:,0], ss1[:,1])
clf()
plot(ppts1[:,0], ppts1[:,1])
plot(ss1[:,0], ss1[:,1])
reload(src.growth_computation_methods)
result = gcm.alignCells(c1, c2, data1, data2, 50, True)
reload(src.growth_computation_methods)
result = gcm.alignCells(c1, c2, data1, data2, 50, True)
pdb.pm()
reload(src.growth_computation_methods)
result = gcm.alignCells(c1, c2, data1, data2, 50, True)
aligned1, aligned2, ps, qs = result
segs1 = list(flatten(seg[0] for seg in aligned1))
ss1 = array([[p.x(), p.y()] for p in segs1+segs1[0:1]])
clf()
plot(ppts1[:,0], ppts1[:,1])
plot(ss1[:,0], ss1[:,1])
reload(src.growth_computation_methods)
result = gcm.alignCells(c1, c2, data1, data2, 50, True)
aligned1, aligned2, ps, qs = result
segs1 = list(flatten(seg[0] for seg in aligned1))
ss1 = array([[p.x(), p.y()] for p in segs1+segs1[0:1]])
clf()
plot(ppts1[:,0], ppts1[:,1])
plot(ss1[:,0], ss1[:,1])
result = pdb.runcall(gcm.alignCells,c1, c2, data1, data2, 50, True)
reload(src.growth_computation_methods)
result = pdb.runcall(gcm.alignCells,c1, c2, data1, data2, 50, True)
result is None
aligned1, aligned2, ps, qs = result
axis('equal')
ylim(ylim()[::-1])
#?save
%%help
