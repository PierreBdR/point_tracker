__docformat__ = "restructuredtext"
import scipy
from scipy import log
from scipy.signal.signaltools import correlate2d, fftconvolve
from scipy.signal import fft, fft2
from itertools import izip
import time

def domain_time(shape_t, shape_i):
    return domain_time_compute()*shape_t[0]*shape_t[1]*shape_i[0]*shape_i[1]

def domain_time_compute():
    """
    time a spatial domain convolution for 10-by-10 x 20-by-20 matrices
    """
    if domain_time_compute.K is None:
        AS = 10
        BS = 40
        a = scipy.ones((AS,AS))
        b = scipy.ones((BS,BS))
        mintime = 0.5

        k = 0
        t1 = time.clock()
        for i in xrange(100):
            c = correlate2d(a,b,mode='same')
        t2 = time.clock()
        t_total = (t2-t1)/100
# convolution time = K*prod(size(a))*prod(size(b))
# t_total = K*AS*AS*BS*BS = 40000*K
        domain_time_compute.K = t_total/(AS*AS*BS*BS)
    return domain_time_compute.K

domain_time_compute.K = None

def fourrier_time(shape):
    """
    Returns the estimated time to compute fourrier transform a matrix of size 
    shape
    """
    R = shape[0]
    S = shape[1]

    K_fft = fourrier_time_compute()
    Tr = K_fft*R*log(R)

    if S == R:
        Ts = Tr
    else:
        Ts = K_fft*S*log(S)
    return S*Tr+R*Ts

def fourrier_time_compute():
    """
    time a fourrier convolution that is 100 elements long
    """
    if fourrier_time_compute.K is None:
        R = 10000
        vec = scipy.array([1+1j]*R)
        t1 = time.clock()
        for i in xrange(100):
            c = fft(vec)
        t2 = time.clock()
        t_total = (t2-t1)/100
        fourrier_time_compute.K = t_total/(R*log(R))
    return fourrier_time_compute.K

fourrier_time_compute.K = None

