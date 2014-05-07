__author__ = "Pierre Barbier de Reuille <pbdr@uea.ac.uk>"
__docformat__ = "restructuredtext"
import scipy
from scipy import rot90, zeros, cumsum, sqrt, maximum, std, absolute, array, real
from scipy.signal.signaltools import correlate2d, fftconvolve
try:
    from scipy.signal import fft2, ifft2
except ImportError:
    from numpy.fft import fft2, ifft2
from utils import centered, eps, padding
# Turns out fourrier is almost always faster ... no need to test!
#import convolution_timing

def normcross2d(template, A, mode="full"):
    """
    Compute the normalized cross-correlation of A and the template.

    The normalized cross-correlation is decribed in Lewis, J. P., "Fast 
    Normalized Cross-Correlation," Industrial Light & Magic. 
    (http://www.idiom.com/~zilla/Papers/nvisionInterface/nip.html)

    :Parameters:
        template
            template to use for the cross-correlation
        A
            Array containing the 2D data
        mode
            'full' to get the full correlation matrix, 'same' to get the 
            matrix with the same dimensions as `A`, 'valid' to get only the parts 
            strictly valid.
    """
    cmplx = False
    if (template.dtype.char in ['D','F']) or (A.dtype.char in ['D', 'F']):
        cmplx = True

    corr_TA = fftcorrelate2d(template, A)
    m,n = template.shape
    mn = m*n

    local_sum_A = local_sum(A, m, n)
    local_sum_A2 = local_sum(A*A,m,n)
    diff_local_sums = (local_sum_A2 - (local_sum_A*local_sum_A)/mn)
    denom_A = sqrt(maximum(diff_local_sums,0))

    denom_T = sqrt(mn-1)*unbiased_std(template.flat)
    denom = denom_T*denom_A
    numerator = corr_TA - local_sum_A*sum(template.flat)/mn

    C = zeros(numerator.shape, dtype=numerator.dtype)
    tol = 1000*eps(max(absolute(denom.flat)))
    i_nonzero = denom > tol
    C[i_nonzero] = numerator[i_nonzero] / denom[i_nonzero]

    if not cmplx:
        C = real(C)

    if mode == 'full':
        return C
    elif mode == 'same':
        return centered(C,A.shape)
    elif mode == 'valid':
        return centered(C, array(A.shape)-array(template.shape)+1)

def unbiased_std(vector):
    l = len(vector)
    s = std(vector)
    return sqrt((s*s*l)/(l-1))

def local_sum(A, m, n):
    B = padding(A, (m, n))
    s = cumsum(B, 0)
    c = s[m:-1]-s[:-m-1]
    s = cumsum(c,1)
    return s[:,n:-1]-s[:,:-n-1]

def fftconvolve2d(in1, in2):
    """
    Convolve two 2-dimensional arrays using FFT.

    I took the code of fftconvolve and specialized it for fft2d ...
    """
    s1 = array(in1.shape)
    s2 = array(in2.shape)
    if (s1.dtype.char in ['D','F']) or (s2.dtype.char in ['D', 'F']):
            cmplx=1
    else: cmplx=0
    size = s1+s2-1
    IN1 = fft2(in1,size)
    IN1 *= fft2(in2,size)
    ret = ifft2(IN1)
    del IN1
    if not cmplx:
            ret = real(ret)
    return ret

def fftcorrelate2d(template, A):
    """
    Perform a 2D fft correlation using fftconvolve2d.
    """
    return fftconvolve2d(rot90(template,2), A)

def fftcorrelatend(template, A):
    """
    Perform a 2D fft correlation using fftconvolve.
    """
    return fftconvolve(rot90(template,2), A)

correlation_functions = {
        'fft2': fftcorrelate2d,
        'fftn': fftcorrelatend,
        'domain': correlate2d }

