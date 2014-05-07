from __future__ import print_function, division, absolute_import
__author__ = "Pierre Barbier de Reuille <pierre@barbierdereuille.net>"
__docformat__ = "restructuredtext"
import traceback
import sys
import __main__
import os.path

log = sys.stderr
pth = None

def init():
    """
    Open the log files and redirect outputs if necessary.
    """
    global log
#if not "IPython" in type(__main__).__module__: # i.e. if ipython is not launched
    if hasattr(__main__, "__file__") and not "IPython" in type(__main__).__module__ and "epydoc" not in __main__.__file__: # if not interactive session and not doc
        global stored_out, stored_err, restore_io
        pth = os.path.dirname(__main__.__file__)
        output = open(os.path.join(pth, "point_tracking_output.txt"), "wt")

        stored_out = os.dup(1)
        stored_err = os.dup(2)
        os.dup2(output.fileno(), 1)
        os.dup2(output.fileno(), 2)

        def restore_io():
            os.dup2(stored_out, 1)
            os.dup2(stored_err, 2)
    else:
        pth = os.path.dirname(os.path.dirname(__file__))
        def restore_io():
            pass

    log = open(os.path.join(pth, "point_tracking.log"), "wt")

#log = sys.stderr

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

def print_debug_simple(msg):
    """
    Simply print the message in the log file.
    """
    global log
    print(msg, file=log)

def print_debug_calling_class(msg):
    """
    Print the message in the log file, preceded by the module and name of the caller class.
    """
    global log
    cls = calling_class()
    if cls:
        print("[%s.%s] %s" % (cls.__module__, cls.__name__, msg), file=log)
    else:
        print("[GLOBAL] %s" % (msg,), file=log)
    log.flush()

print_debug = print_debug_calling_class

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
            print_debug( "Deleted object %s of class '%s'" % (id(self), type(self).__name__))
        def debug_init(self):
            print_debug( "Creating object %s of class '%s'" % (id(self), type(self).__name__))

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

