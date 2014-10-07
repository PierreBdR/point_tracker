from __future__ import print_function, division, absolute_import
__author__ = "Pierre Barbier de Reuille <pierre@barbierdereuille.net>"
__docformat__ = "restructuredtext"
import traceback
import sys
import logging
from PyQt4 import QtGui
from .path import path
from functools import partial

log = None


def init():
    """
    Open the log files and redirect outputs if necessary.
    """
    global log
    file_location = path(QtGui.QDesktopServices.storageLocation(QtGui.QDesktopServices.DataLocation))
    file_location = file_location / 'point-tracker.log'

    logging.basicConfig(level=logging.INFO, filename=file_location, filemode='w')
    print("Location of log file: '{0}'".format(file_location), file=sys.stderr)
    log = logging.getLogger("point-tracker")

    directReport = logging.StreamHandler(sys.stderr)
    directReport.setLevel(logging.INFO)
    log.addHandler(directReport)

    global restore_io

    def restore_io():
        logging.shutdown()


def calling_class():
    """
    Return the class of the caller.

    This means, the class of the object that called the function calling this one.

    Example::

        >>> import debug
        >>> def fct(a,b,c):
        ...   cls = debug.calling_class()
        ...   return cls
        ...
        >>> class C(object):
        ...   def f(self):
        ...     return fct(1,2,3)
        ...
        >>> C().f()
        <class '__main__.C'>

    """
    try:
        raise ZeroDivisionError
    except ZeroDivisionError:
        tb = sys.exc_info()[2]
        caller_frame = tb.tb_frame.f_back.f_back
        caller_code = caller_frame.f_code
        if caller_code.co_argcount > 0:
            caller_locals = caller_frame.f_locals
            caller_first_arg = caller_code.co_varnames[0]
            first_arg = caller_locals[caller_first_arg]
            cls = type(first_arg)
            if hasattr(cls, caller_code.co_name):
                return cls
        return None


def caller():
    """
    Return the element of the stack corresponding to the calling function.
    """
    stack = traceback.extract_stack()
    return stack[-3][:]


def print_simple(msg, level):
    """
    Simply print the message in the log file.
    """
    log.log(level, msg)
    #print(msg) #, file=log)


def print_calling_class(msg, level):
    """
    Print the message in the log file, preceded by the module and name of the caller class.
    """
    cls = calling_class()
    if cls:
        msg = "[%s.%s] %s" % (cls.__module__, cls.__name__, msg)
    else:
        msg = "[GLOBAL] %s" % (msg,)
    log.log(level, msg)
    #print(msg)
    #log.flush()

log_debug = partial(print_calling_class, level=logging.DEBUG)
log_info = partial(print_calling_class, level=logging.INFO)
log_warning = partial(print_calling_class, level=logging.WARNING)
log_error = partial(print_calling_class, level=logging.ERROR)
log_critical = partial(print_calling_class, level=logging.CRITICAL)


class debug_type(type):
    """
    Metaclass used to debug usage of a class.

    If a class has this metaclass, every creation and deletion of objects will be recorded in the log file.
    """
    def __init__(cls, name, bases, dct):
        '''
        Redefine the initialization of the class
        '''
        type.__init__(cls, name, bases, dct)

        def debug_del(self):
            log_debug("Deleted object %s of class '%s'" % (id(self), type(self).__name__))

        def debug_init(self):
            log_debug("Creating object %s of class '%s'" % (id(self), type(self).__name__))

        if not hasattr(cls, "__debug_class__") or not cls.__debug_class__:
            if hasattr(cls, '__del__'):
                old_del = cls.__del__

                def chained_del(self):
                    old_del(self)
                    debug_del(self)

                chained_del.__doc__ = old_del.__doc__
                cls.__del__ = chained_del
            else:
                cls.__del__ = debug_del

        if hasattr(cls, '__init__'):
            old_init = cls.__init__

            def chained_init(self, *args):
                old_init(self, *args)
                debug_init(self)

            chained_init.__doc__ = old_init.__doc__
            cls.__init__ = chained_init
        else:
            cls.__init__ = debug_init

        cls.__debug_class__ = True


class debug_object(object):
    """
    Base class for an object having debug_type as metaclass.
    """
    __metaclass__ = debug_type
