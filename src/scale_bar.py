# coding=utf-8
__docformat__ = "restructuredtext"
__author__ = "Pierre Barbier de Reuille <pbdr@uea.ac.uk>"
from PyQt4.QtGui import QFont, QLinearGradient, QColor, QFontMetricsF, QPen
from PyQt4.QtCore import QRectF, Qt, QPointF, QString
from numpy import log10, floor, arange, ceil, round, abs
from itertools import izip
from debug import print_debug

def limit_rect(rect, size, lim_width, lim_height):
    if rect.left() < lim_width:
        rect.moveLeft(lim_width)
        if size.width()-rect.right() < lim_width:
            rect.setRight(size.width() - lim_width)
    elif size.width()-rect.right() < lim_width:
        rect.moveRight(size.width() - lim_width)
        if rect.left() < lim_width:
            rect.setLeft(lim_width)
    if rect.top() < lim_height:
        rect.moveTop(lim_height)
        if size.height()-rect.bottom() < lim_height:
            rect.setBottom(size.height()-lim_height)
    elif size.height()-rect.bottom() < lim_height:
        rect.moveBottom(size.height()-lim_height)
        if rect.top() < lim_height:
            rect.setTop(lim_height)

class ScaleBar(object):
    """
    Draw a scale bar on the painter.

    :Ivariables:
        position : str
            One of "Top", "Right", "Left" or "Bottom"
        transfer_function : `TransferFunction`
            Transfer function used on the graph
        font : `QFont`
            Font used to render the text
        text_color : `QColor`
            Color used to render the text
        line_color : `QColor`
            Color used to draw the line around the color scale and the ticks
        line_thickness : int
            Thickness used to draw the line around the color scale and the ticks
        value_range : (float,float)
            Range of values on which the scale span
        """
#        inverse_scale : bool
#            If true, the scale will represent 1/x and not x. (i.e. 0 will be
#            ∞, 2 will be 0.5, ...)
    def __init__(self, position = "Top", transfer_function = None,
                 font = QFont(), text_color = QColor(0,0,0),
                 line_color = QColor(0,0,0), line_thickness = 0, value_range = (0,1),
                 unit = ""):
        """
        Initialize the instance variables either with default values or
        provided once.
        """
        values = dict(locals())
        del values['self']
        self.__dict__.update(values)

    scale_length = 0.8
    scale_width = 0.05
    scale_shift_width = 0.02
    text_to_bar = 5
    tick_size = 0.2
    exp_size = 0.7
    epsilon = 1e-9

    def _getValues(self, start, end, delta):
        epsilon = self.epsilon
        new_start = (start // delta) * delta
        if ((start < epsilon and abs(new_start - start) > self.epsilon) or
            (start >= epsilon and abs((new_start-start)/start) > self.epsilon)):
            new_start += delta
        return arange(new_start, end+delta/100, delta)

    def _tick2str(self, ticks):
        epsilon = self.epsilon
        m = max(abs(ticks))
        if m <= 0.01:
            exp = -1000
            for t in ticks:
                exp = max(log10(t), exp)
            exp -= 1
            exp = floor(exp)
            factor = 10**exp
            new_ticks = ticks/factor
            t = abs(round(new_ticks) - new_ticks)
            t[new_ticks != 0] /= new_ticks[new_ticks != 0]
            if (t>epsilon).any():
                exp = floor(log10(m))
                factor = 10**exp
                new_ticks = ticks/factor
        elif m >= 20000:
            exp = 1000
            for t in ticks:
                exp = min(log10(t), exp)
            factor = 10**exp
            new_ticks = ticks/factor
            t = abs(round(new_ticks) - new_ticks)
            t[new_ticks != 0] /= new_ticks[new_ticks != 0]
            if (t>epsilon).any():
                exp = floor(log10(m))
                factor = 10**exp
                new_ticks = ticks/factor
        else:
            new_ticks = ticks
            exp = None
        new_ticks[abs(new_ticks/abs(ticks).max()) < epsilon] = 0
        ticks_str = ["% g" % t for t in new_ticks]
        if exp is None:
            extra = None
        else:
            extra = "%d" % int(round(exp))
        return ticks_str, extra

    def _canRenderTicks(self, ticks, length, min_dist, is_vertical, font_metric):
        b,e = self.value_range
        dl = length/(e-b)
        pos = dl*(ticks - b)
        cur_pos = -length
        ticks_str, _ = self._tick2str(ticks)
        for t,p in izip(ticks_str, pos):
            r = font_metric.boundingRect(t)
            if is_vertical:
                w = r.height()/2
            else:
                w = r.width()/2
            left = p-w
            if left < cur_pos:
                return False
            cur_pos = p+w+min_dist
        return True

    def selectValues(self, length, is_vertical, painter = None):
        if painter is not None:
            metric = QFontMetricsF(self.font, painter.device())
        else:
            metric = QFontMetricsF(self.font)
        min_dist = 1
        if not is_vertical: # Find the maximum size of 2 figures
            test = [ str(i)*2 for i in range(10) ]
            for t in test:
                min_dist = max(min_dist, metric.boundingRect(t).width())
        return self._selectValues_direct(length, is_vertical, metric, min_dist)

    def _significant_digits(self, start, end):
        delta = (end-start)/10
        first_num = floor(log10(delta))
        exp = 10**first_num
        real_delta = ceil(delta/exp)
        if real_delta > 6:
            real_delta = 10
        elif real_delta > 2:
            real_delta = 5
        return real_delta, exp

    def _selectValues_direct(self, length, is_vertical, metric, min_dist):
        """
        Determine which numbers to represent within the value range
        """
        start, end = self.value_range
        start = float(start)
        end = float(end)
        real_delta, exp = self._significant_digits(start, end)
        ticks = self._getValues(start, end, real_delta*exp)
        while not self._canRenderTicks(ticks, length, min_dist, is_vertical, metric):
            if real_delta == 1:
                real_delta = 2
            elif real_delta == 2:
                real_delta = 5
            elif real_delta == 5:
                exp *= 10
                real_delta = 1
            else:
                exp *= 10
                real_delta = 2
            ticks = self._getValues(start, end, real_delta*exp)
            if len(ticks) == 1:
                return []
        return ticks

    def draw(self, painter, size = None):
        """
        :Arguments:
            painter : QPainter
                Opened painter on which to draw
        """
        bounding_rect = QRectF()
        position = self.position
        transfer_function = self.transfer_function
        font = QFont(self.font)
        text_color = self.text_color
        line_color = self.line_color
        line_thickness = self.line_thickness
        value_range = self.value_range
        if size is None:
            viewport = painter.viewport() # viewport rectangle
            mat, ok = painter.worldMatrix().inverted()
            if not ok:
                raise ValueError("Transformation matrix of painter is singular.")
            viewport = mat.mapRect(viewport)
        else:
            viewport = size
# First, prepare the gradient
        w = viewport.width()
        h = viewport.height()
        gr = QLinearGradient()
        nb_values = ceil(w/5.0)
        brush_color = QColor()
        for i in xrange(int(nb_values)):
            brush_color.setRgbF(*transfer_function.rgba(i/nb_values))
            gr.setColorAt(i/nb_values, brush_color)
# Second, find its position
        metric = QFontMetricsF(font, painter.device())
        font_test = [ str(i)*5 for i in range(10) ]
        lim_width = 0
        lim_height = 0
        for t in font_test:
            rect = metric.boundingRect(t)
            lim_width  = max(lim_width,  rect.width())
            lim_height = max(lim_height, rect.height())
        lim_height *= 3
        length = self.scale_length
        shift_length = (1-length)/2
        width = self.scale_width
        shift_width = self.scale_shift_width
        delta_value = value_range[1]-value_range[0]
        if position == "Top":
            scale_rect = QRectF(shift_length*w, shift_width*h, length*w, width*h)
            limit_rect(scale_rect, viewport, lim_width, lim_height)
            gr.setStart(scale_rect.left(), scale_rect.center().y())
            gr.setFinalStop(scale_rect.right(), scale_rect.center().y())
            start_pos = scale_rect.bottomLeft()
            end_pos = scale_rect.bottomRight()
        elif position == "Right":
            scale_rect = QRectF((1-shift_width-width)*w, shift_length*h, width*w, length*h)
            limit_rect(scale_rect, viewport, lim_width, lim_height)
            gr.setStart(scale_rect.center().x(), scale_rect.bottom())
            gr.setFinalStop(scale_rect.center().x(), scale_rect.top())
            start_pos = scale_rect.bottomLeft()
            end_pos = scale_rect.topLeft()
        elif position == "Bottom":
            scale_rect = QRectF(shift_length*w, (1-shift_width-width)*h, length*w, width*h)
            limit_rect(scale_rect, viewport, lim_width, lim_height)
            gr.setStart(scale_rect.left(), scale_rect.center().y())
            gr.setFinalStop(scale_rect.right(), scale_rect.center().y())
            start_pos = scale_rect.topLeft()
            end_pos = scale_rect.topRight()
        elif position == "Left":
            scale_rect = QRectF(shift_width*w, shift_length*h, width*w, length*h)
            limit_rect(scale_rect, viewport, lim_width, lim_height)
            gr.setStart(scale_rect.center().x(), scale_rect.bottom())
            gr.setFinalStop(scale_rect.center().x(), scale_rect.top())
            start_pos = scale_rect.bottomRight()
            end_pos = scale_rect.topRight()
        else:
            raise ValueError("Invalid scale position: %s" % position)
        shift_pos = (end_pos-start_pos)/delta_value
        if position in ["Left", "Right"]:
            is_vertical = True
            length = scale_rect.height()
        else:
            is_vertical = False
            length = scale_rect.width()
# Get the ticks
        ticks = self.selectValues(length, is_vertical, painter)
        if len(ticks) == 0:
            return
        ticks_str, ticks_extra = self._tick2str(ticks)
# Figure the shifts
        dist_to_bar = self.text_to_bar
        max_width = 0
        max_height = 0
        for t in ticks_str:
            rect = metric.boundingRect(t)
            max_width = max(rect.width(), max_width)
            max_height = max(rect.height(), max_height)
        if position == "Left":
            shift_left = dist_to_bar
            shift_top = None
        elif position == "Right":
            shift_left = -dist_to_bar-max_width
            shift_top = None
        elif position == "Top":
            shift_left = None
            shift_top = dist_to_bar
        else:
            shift_left = None
            shift_top = -dist_to_bar-max_height
        painter.save()
        painter.translate(viewport.topLeft())
        painter.setBrush(gr)
        line_pen = QPen(line_color)
        line_pen.setWidth(line_thickness)
        painter.setPen(line_pen)
        painter.drawRect(scale_rect)
        bounding_rect |= scale_rect
        painter.setFont(font)
        painter.setPen(text_color)
        for ts,t in izip(ticks_str, ticks):
            r = metric.boundingRect(ts)
            pos = start_pos+shift_pos*(t-value_range[0])
            if shift_left is None:
                pos.setX( pos.x() - r.width()/2 )
            else:
                pos.setX( pos.x() + shift_left )
            if shift_top is None:
                pos.setY( pos.y() - r.height()/2)
            else:
                pos.setY( pos.y() + shift_top )
            r.moveTo(pos)
            real_rect = painter.drawText(r, Qt.TextDontClip | Qt.AlignVCenter | Qt.AlignHCenter, ts)
            bounding_rect |= real_rect
        if ticks_extra is not None or self.unit:
            unit = self.unit
            exp_width = width = space_width = 0
            exp_txt = ""
            r = exp_r = unit_r = QRectF()
            exp_font = None
            if ticks_extra is not None:
                exp_txt = QString.fromUtf8("×10")
                r = metric.boundingRect(exp_txt)
                exp_font = QFont(font)
                exp_size = self.exp_size
                if exp_font.pixelSize() != -1:
                    exp_font.setPixelSize(exp_size*exp_font.pixelSize())
                else:
                    exp_font.setPointSizeF(exp_size*exp_font.pointSizeF())
                exp_metric = QFontMetricsF(exp_font, painter.device())
                exp_r = exp_metric.boundingRect(ticks_extra)
            if unit:
                unit_r = metric.boundingRect(unit)
            total_width = r.width()+exp_r.width()+unit_r.width()
            total_height = max(r.height(),unit_r.height())+exp_r.height()/2
            pos = scale_rect.topRight()
            print_debug("top right of scale bar = (%g,%g)" % (pos.x(), pos.y()))
            print_debug("Size of image = (%d,%d)" % (w,h))
            print_debug("Size of text = (%g,%g)" % (total_width, total_height))
            if position == "Bottom":
                pos.setY(pos.y() + scale_rect.height() + dist_to_bar)
                pos.setX(pos.x() - total_width)
            elif position == "Top":
                pos.setY(pos.y() - dist_to_bar - total_height)
                pos.setX(pos.x() - total_width)
            else: # position == "left" or "right"
                pos.setX(pos.x() - (scale_rect.width() + total_width)/2)
                if pos.x() < 0:
                    pos.setX(dist_to_bar)
                elif pos.x()+total_width+dist_to_bar > w:
                    pos.setX(w - total_width - dist_to_bar)
                pos.setY(pos.y() - dist_to_bar - total_height)
            print_debug("Display unit at position: (%g,%g)" % (pos.x(), pos.y()))

            if ticks_extra is not None:
                r.moveTo(pos)
                real_rect = painter.drawText(r, Qt.TextDontClip | Qt.AlignVCenter | Qt.AlignHCenter, exp_txt)
                bounding_rect |= real_rect
                pos.setX( pos.x() + r.width() )
                pos.setY( pos.y() - metric.ascent()/2 )
                exp_r.moveTo(pos)
                painter.setFont(exp_font)
                real_rect = painter.drawText(exp_r, Qt.TextDontClip | Qt.AlignVCenter | Qt.AlignHCenter, ticks_extra)
                bounding_rect |= real_rect
                pos.setY(pos.y() + metric.ascent()/2)
            if unit:
                pos.setX(pos.x() + space_width + exp_r.width())
                unit_r.moveTo(pos)
                painter.setFont(font)
                real_rect = painter.drawText(unit_r, Qt.TextDontClip | Qt.AlignVCenter | Qt.AlignHCenter, unit)
                bounding_rect |= real_rect
        # Draw the ticks now
        painter.setPen(line_pen)
        tick_size = self.tick_size
        if is_vertical:
            width = scale_rect.width()*tick_size
        else:
            width = scale_rect.height()*tick_size
        pen_width = painter.pen().widthF()
        if pen_width == 0:
            pen_width = 1.0
        for t in ticks:
            pos1 = start_pos + shift_pos*(t-value_range[0])
            pos2 = QPointF(pos1)
            if is_vertical:
                pos1.setX(scale_rect.left() + pen_width)
                pos2.setX(pos1.x() + width - pen_width)
                painter.drawLine(pos1, pos2)
                pos1.setX(scale_rect.right() - pen_width)
                pos2.setX(pos1.x() - width + pen_width)
                painter.drawLine(pos1, pos2)
            else:
                pos1.setY(scale_rect.top() + pen_width)
                pos2.setY(pos1.y() + width - pen_width)
                painter.drawLine(pos1, pos2)
                pos1.setY(scale_rect.bottom() - pen_width)
                pos2.setY(pos1.y() - width + pen_width)
                painter.drawLine(pos1, pos2)
        painter.restore()
        bounding_rect = bounding_rect.adjusted(-pen_width, -pen_width, pen_width, pen_width)
        return bounding_rect

