from __future__ import print_function, division, absolute_import
'''
Created on Jun 21, 2010

@author: pbdr
'''

import src.growth_computation_methods as gcm
import pylab as pl

def plot_dense_cell(ps):
    pps = pl.array([[p.x(), p.y()] for p in ps])
    pl.plot(pps[:,0], pps[:,1], '.')

def image_axis():
    pl.axis('equal')
    pl.ylim(pl.ylim()[::-1])

def plot_aligned_cell(aligned, data):
    colors = ['blue', 'red', 'green']
    l = len(aligned)
    for i,seg in enumerate(aligned):
        next = (i+1) % l
        pps = pl.array([[p.x(), p.y()] for p in (seg[0]+aligned[next][0][0:1])])
        if i == 0:
            color = colors[2]
        else:
            color = colors[i%2]
        pl.plot(pps[:,0], pps[:,1], color = color)
    pts = pl.array([[p[0][0].x(), p[0][0].y()] for p in aligned])
    pl.plot(pts[:,0], pts[:,1], '*')
    for seg in aligned:
        if seg[1] is not None:
            pos = seg[0][0]
            pl.text(pos.x(), pos.y(), str(seg[1]))
    pass

def compute_cell(data, c, t):
    img1 = data.images_name[t]
    img2 = data.images_name[t+1]
    data1 = data[img1]
    data2 = data[img2]
    pts = data.cellAtTime(c, t)
    try:
        new_pts = data.cellAtTime(c, t+1)
    except ValueError:
        print "Skipping cell %d" % c
        return
    result = gcm.alignCells(c, pts, new_pts, data1, data2, 100)
    if result is None:
        print "Error while aligning cell %d" % c
        return
    return result

def test_time(data, t):
    img1 = data.images_name[t]
    img2 = data.images_name[t+1]
    data1 = data[img1]
    data2 = data[img2]
    pl.figure(1)
    pl.clf()
    pl.figure(2)
    pl.clf()
    for c in data1.cells:
        result = compute_cell(data, c, t)
        if result is None:
            continue
        aligned1, aligned2, ps, qs = result
        pl.figure(1)
        pl.subplot(1,2,1)
        plot_dense_cell(ps)
        pl.subplot(1,2,2)
        plot_dense_cell(qs)
        pl.figure(2)
        pl.subplot(1,2,1)
        plot_aligned_cell(aligned1, data1)
        pl.subplot(1,2,2)
        plot_aligned_cell(aligned2, data2)
    pl.figure(1)
    pl.gcf().canvas.set_window_title('Figure 1 - Resampled cells')
    pl.suptitle('Resampled cells')
    pl.subplot(1,2,1)
    image_axis()
    pl.title('Time %d' % t)
    pl.subplot(1,2,2)
    image_axis()
    pl.title('Time %d' % (t+1))
    pl.figure(2)
    pl.gcf().canvas.set_window_title('Figure 2 - Alignment of segments')
    pl.suptitle('Alignment of segments')
    pl.subplot(1,2,1)
    image_axis()
    pl.title('Time %d' % t)
    pl.subplot(1,2,2)
    image_axis()
    pl.title('Time %d' % (t+1))
