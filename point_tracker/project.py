from __future__ import print_function, division, absolute_import
__author__ = "Pierre Barbier de Reuille <pierre@barbierdereuille.net>"
__docformat__ = "restructuredtext"
from .path import path
from .tracking_data import TrackingData, TrackingDataException
from PyQt4.QtCore import QObject, QCoreApplication, Signal
from PyQt4.QtGui import QImageReader
from . import parameters
from .debug import log_debug
import re
from .sys_utils import cleanQObject

class Project(QObject):
    changedDataFile = Signal(path)

    """
    Class maintaining a project and its directory structure

    :signal: ``changedDataFile --> data_file``
    """
    def __init__(self, dir_):
        QObject.__init__(self)
        if not self.initialized:
            raise RuntimeError("You cannot create an instance of TrackingData without first initialize the class.")
        dir_ = path(dir_)
        self._dir = dir_
        self._data_file = None
        self._images_dir = None
        self.data_dir = dir_/'Data'
        self.images_dir = dir_/'Processed'
        self._valid_project = None
        self.data = None

    def __del__(self):
        cleanQObject(self)

    @property
    def main_dir(self):
        """
        Project main directory
        """
        return self._dir

    def use(self):
        """
        Make sure the project can be used for tracking.
        """
        params = parameters.instance
        dir_ = self.data_dir
        config_file = dir_/"point_tracker.cfg"
        data_file = None
        if config_file.exists():
            cf = config_file.open('r')
            for l in cf:
                if '#' in l:
                    l = l[:l.index('#')]
                fields = l.split('=', 1)
                if len(fields) == 2:
                    name = fields[0].strip()
                    if name == "data_file":
                        df = self.data_dir / fields[1].strip()
                        if df.exists():
                            data_file = df
                    elif name == "template_size":
                        value = int(fields[1])
                        params.template_size = value
                    elif name == "search_size":
                        value = int(fields[1])
                        params.search_size = value
                    elif name == "filter_size_ratio":
                        value = float(fields[1])
                        params.filter_size_ratio = value
        if data_file is None:
            l = dir_.files("*.csv")
            if l:
                self.data_file = l[0]
            else:
                self.data_file = dir_/'tracking.csv'
        else:
            self.data_file = data_file

    @property
    def data_file(self):
        """
        Directory containing generated data files
        """
        return self._data_file

    @data_file.setter
    def data_file(self, file_):
        if file_ is None:
            raise RuntimeError("None data file")
        file_ = path(file_)
        log_debug("Setting data file to %s" % (file_,))
        if file_ != self._data_file:
            self._data_file = path(file_)
            self.changedDataFile.emit(self._data_file)

    supported_image_types = []
    """
    List of supported image types for loading
     :type: list of str
    """

    sit_re = re.compile("")
    """
    Regular expression selecting files of supported format
     :type: re
    """

    initialized = False

    @classmethod
    def initClass(cls):
        """
        Initialize class variables
        """
        if QCoreApplication.startingUp():
            raise RuntimeError("This class need to be initialized after the QtGui application")
        cls.supported_image_types = [ bytes(i).decode() for i in QImageReader.supportedImageFormats() ]
        cls.sit_re = re.compile(u"\.(%s)$" % "|".join(cls.supported_image_types), re.IGNORECASE)
        cls.initialized = True

    @property
    def images_dir(self):
        """
        Directory containing the images

        :returntype: `path`
        """
        return self._images_dir

    @images_dir.setter
    def images_dir(self, dir_):
        if dir_ is None:
            self.reset()
            return
        if dir_ == self._images_dir:
            return
        if not dir_.exists():
            self._images_dir = dir_
            return
        dir_ = path(dir_)
        #log_debug("Recognised extensions: %s" % Project.supported_image_types)
        #log_debug("Extension regexpr = {0!r}".format(Project.sit_re.pattern))
        images_path = [ f for f in dir_.files() if Project.sit_re.search(f) ]
        log_debug("List of images in {0}: {1}".format(dir_, images_path))
        if images_path:
            images_path.sort()
            self.images_path = images_path
            self.images_name = [ f.basename() for f in images_path ]
            self._images_dir = dir_
            #print "Images found:"
            #for i in images:
            #  print i

    @property
    def valid(self):
        """
        True if the project points toward a valid project directory.
        """
        if self._valid_project is None:
            #dir_ = self._dir
            valid_project = True
            if self.data_dir is None or not self.data_dir.exists():
                log_debug("Error, no data dir: {0}".format(self.data_dir))
                valid_project = False
            elif self.images_dir is None or not self.images_dir.exists():
                log_debug("Error, no images dir: {0}".format(self.images_dir))
                valid_project = False
            self._valid_project = valid_project
        return self._valid_project

    def write_config(self):
        """
        Write the config file "point_tracker.cfg" in the data directory
        """
        if self.data_dir:
            params = parameters.instance
            config_file = self.data_dir/"point_tracker.cfg"
            f = config_file.open('w')
            f.write("# Last data file used for that project\n")
            f.write("data_file=%s\n" % self.data_file.basename())
            f.write("template_size=%s\n" % params.template_size)
            f.write("search_size=%s\n" % params.search_size)
            f.write("filter_size_ratio=%s\n" % params.filter_size_ratio)
            f.close()

    def save(self, data_file = None):
        if data_file is None:
            data_file = self.data_file
        self.data.save(data_file)
        self.data_file = data_file
        self.write_config()

    def load(self, **opts):
        if self.data_file is None:
            raise TrackingDataException("No data file to be loaded.")
        log_debug("Loading %s" % self.data_file)
        data = self.data
        if data is None or data.project_dir != self.main_dir:
            data = TrackingData(self.main_dir)
        if self.data_file.exists():
            data.load(self.data_file, **opts)
        else:
            data.images_name = self.images_name
            data.images_dir = self.images_dir
            data.prepareData()
        self.write_config()
        self.data = data
        return True

    @valid.deleter
    def valid(self):
        self._valid_project = None

    def create(self):
        """
        Setup the pointed directory as a valid project directory
        """
        if not self._data_dir.exists():
            self._data_dir.mkdir()
        if not self.images_dir.exists():
            self.images_dir.mkdir()

    @property
    def data_dir(self):
        """
        Directory containing the data sets

        :returntype: `path`
        """
        return self._data_dir

    @data_dir.setter
    def data_dir(self, dir_):
        if not dir_.exists():
            self._data_dir= dir_
            return
        self._data_dir = dir_

