from __future__ import print_function, division, absolute_import
__author__ = "Pierre Barbier de Reuille <pierre@barbierdereuille.net>"
__docformat__ = "restructuredtext"
from PyQt4.QtGui import QImage
import numpy
from .algo import filterImage
from .utils import bigendian

def nbytes(obj):
    """
    :returns: the number of bytes used by the object Obj
    :returntype: int
    """
    if obj is None:
        return 0
    if isinstance(obj, QImage):
        return obj.numBytes()
    if hasattr(obj, "nbytes"):
        return obj.nbytes
    raise TypeError("Don't know how to compute the size of this object")

def load_image(img, filter_size = None):
    """
    Load an image from a QImage

    :Parameters:
        img : `QImage`
            Image to build to array from
        filter_size : (int,int)
            Size of the smoothing filter to apply on the image

    :returns: an numpy array built from the image `img`
    :returntype: `numpy.ndarray`
    """
    format = img.format()
    type = numpy.uint8
    if (format == QImage.Format_ARGB32 or
        format == QImage.Format_ARGB32_Premultiplied):
        data_size = 4
    elif format == QImage.Format_RGB32:
        data_size = 3
    elif format == QImage.Format_Indexed8:
        data_size = 1
    else:
        raise ValueError("Error, format unsupported or not recognised: %d" % format)
    dsize = img.width()*img.height()*data_size
    data = img.bits().asstring(dsize)
    arr = numpy.fromstring(data, type)
    shape = (img.height(), img.width())
    if data_size>1:
        shape = shape + (data_size,)
    arr.shape = shape
    if data_size>1:
        if bigendian(): # alpha is on the first component
            arr = arr[...,1:].max(-1)
        else: # or on the last
            arr = arr[...,:3].max(-1)
    arr = numpy.array(arr, dtype=float)
    if filter_size:
        return filterImage(arr, filter_size)
    return arr

class ImageCache(object):
    """
    This object implement a memory-limited image cache. It takes into account image transformation.

    :Ivariables:
        images : dict of (str * (`QImage`, `numpy.ndarray`))
            List of images present in the cache
        order : list of str
            Order of image access. The first image will be the first discarded if memory is consumed.
        current_size : int
            Current memory used by the cache
    """
    def __init__(self):
        self.images = {}
        self.order = []
        self.current_size = 0
        self._real_max_size = 0
        self.max_size = 0

    @property
    def max_size(self):
        """
        Maximum size of the cache in MB.
        """
        return self._real_max_size/(1024*1024)

    @max_size.setter
    def max_size(self, value):
        self._max_size = value
        value *= 1024*1024
        if value < self._real_max_size:
            self._real_max_size = value
            self.clean()
        else:
            self._real_max_size = value

    def __get(self, image_name, want_numpy, filter_size = None):
        #print "Asking for image: %s" % (image_name,)
        img = None
        numpy_img = None
        if image_name in self.images:
            self.order.remove(image_name)
            self.order.append(image_name)
            img, numpy_img, cached_size = self.images[image_name]
            if cached_size != filter_size:
                prev_size = nbytes(numpy_img)
                if want_numpy:
                    numpy_img = load_image(img, filter_size)
                else:
                    numpy_img = None
                self.images[image_name] = (img, numpy_img, filter_size)
                self.current_size += nbytes(numpy_img) - prev_size
        else:
            img = QImage(image_name)
            if want_numpy:
                numpy_img = load_image(img, filter_size)
            else:
                numpy_img = None
            self.current_size += nbytes(img) + nbytes(numpy_img)
            self.images[image_name] = (img, numpy_img, filter_size)
            self.order.append(image_name)
        self.clean()
        return (img, numpy_img)

    def image(self, image_name):
        """
        :returns: the QImage corresponding to image_name

        :returntype: `QImage`
        """
        return self.__get(image_name, False)[0]

    def numpy_image(self, image_name, filter = None):
        """
        :returns: the tuple (image,nimage) where image is a QImage and nimage a numpy array corresponding to the filtered image.

        :returntype: (`QImage`, `numpy.ndarray`)
        """
        return self.__get(image_name, True, filter)

    def numpy_array(self, image_name, filter = None):
        """
        :returns: the numpy array only

        :returntype: `numpy.ndarray`
        """
        return self.__get(image_name,  True,  filter)[1]

    def  clean(self):
        """
        Ensure the cache is no bigger than its maximum size
        """
        while self.current_size > self._real_max_size:
            to_del_img = self.order.pop(0)
            img_, npy_img, _ = self.images[to_del_img]
            self.current_size -= nbytes(img_) + nbytes(npy_img)
            del self.images[to_del_img]


def createCache():
    """
    Create the cache object as a singleton.
    """
    global cache
    if cache is None:
        cache = ImageCache()

cache = None
"""
Singleton representing the cache object
"""
