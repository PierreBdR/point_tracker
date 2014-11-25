from __future__ import print_function, division, absolute_import
__author__ = "Pierre Barbier de Reuille <pierre@barbierdereuille.net>"
__docformat__ = "restructuredtext"

from numpy import array, eye, argsort, cross, dot, asarray, asmatrix, diag, matrix, exp, log, cos, sin, pi, arctan2
from numpy.linalg import norm, eig, cond, svd, det, eigh
from math import atan2

def linear2exponential_growth(value, dt):
    """
    Correct a (list of) value(s) for growth estimated using linear-growth
    hypothesis into value(s) corresponding to an exponential growth hypothesis.

    :Note: You should convert growth rate and vorticity but not the direction.
    i.e. Do not convert directly the full tensor as it would not work.
    """
    return log(asarray(value) * dt + 1) / dt

def exponential2linear_growth(value, dt):
    return (exp(asarray(value) * dt) - 1) / dt

def linear2exponential_strain(t, dt):
    t = asarray(t)
    w, v = eigh(t)
    w = linear2exponential_growth(w, dt)
    t = dot(dot(v, diag(w)), v.T)
    return t

def exponential2linear_strain(t, dt):
    t = asarray(t)
    w, v = eigh(t)
    w = exponential2linear_growth(w, dt)
    t = dot(dot(v, diag(w)), v.T)
    return t

def linear2exponential_tensor(t, dt):
    s = (t + t.T) / 2
    v = (t - t.T) / 2
    nt = v + linear2exponential_strain(s, dt)
    return nt

def exponential2linear_tensor(t, dt):
    s = (t + t.T) / 2
    v = (t - t.T) / 2
    nt = v + exponential2linear_strain(s, dt)
    return nt

def fitmat(p, q):
    """
    Compute the best transformation to map p onto q without translation.

    The transformation is best according to the least square residuals criteria and correspond to the matrix M in:

        p-p0 = M(q-q0) + T

    where p0 and q0 are the barycentre of the list of points p and q.

    :Parameters:
        p : array(M,2)
            List of points p, one point per line, first column for x, second for y
        q : array(M,2)
            List of points q, one point per line, first column for x, second for y
    """
    pc = p.sum(0) / p.shape[0]
    qc = q.sum(0) / q.shape[0]
    p = asmatrix(p - pc)
    q = asmatrix(q - qc)
    A = p.T * p
    if cond(A) > 1e15:
        return
    V = p.T * q
    M = (A.I * V).A
    return M.T

# Needs redoing
#def polarDecomposition2D(A,B,C,D):
#    '''
#    Decompose the transformation [[A,B],[C,D]] into a rotation and a symetric transformation.
#    The symetric transformation is to be applied before the rotation.
#    The symetric part is such that the sum of the eigen values is positive.
#    '''
#    ref = abs(A)+abs(B)+abs(C)+abs(D)
#    if ref == 0:
#        return A,B,D,0
#    S = (A+D)**2+(B-C)**2
#    if ((abs(B-C)/ref) < 1e-8 or # if the matrix is already symmetric
#        (abs(S)/(ref*ref)) < 1e-16): # There is no preferential direction. Precision = 1e-8 in double
#        l1 = (A+D-sqrt((A-D)*(A-D)+B*B))/2 # First eigen value
#        l2 = (A+D+sqrt((A-D)*(A-D)+B*B))/2 # Second eigen value
#        if (l1+l2) < 0: # Make sure the sum of the eigenvalues is positive
#            return -A,-B,-D,pi
#        else:
#            return A,B,D,0
#    t = -(A + D - sqrt(S))/(B - C)
#    if abs(t) < 1:
#        # If in the 'bad precision' zone, turn the problem by pi before going on
#        A,B,C,D = -A,-B,-C,-D
#        t = -(A + D - sqrt(S))/(B - C)
#        theta = 2*atan(t)
#        if theta < 0:
#            theta += pi
#        else:
#            theta -= pi
#    else:
#        theta = 2*atan(t)
#    S1 = 2*(A+D)**2+(B-C)**2
#    a = -((A*(A+D)+B*(B-C))*(S1-2*(A+D)*sqrt(S)))/(2*(A+D)*S-S1*sqrt(S))
#    b = -((A*C+B*D)*(S1-2*(A+D)*sqrt(S)))/(2*(A+D)*S-S1*sqrt(S))
#    c = -((D*(A+D)+C*(C-B))*(A+D-sqrt(S)))/(S-(A+D)*sqrt(S))
#    return a,b,c,theta

def polarDecomposition(M, at_start=True):
    '''
    Decompose the 2D/3D transformation matrix M (i.e. 2x2 or 3x3 matrix) into a rotation and a symetric matrix.

    The symetric matrix is such that only the smallest eigenvalue may be negative.

    :returns: (S,R), with S the scaling and R the rotation.
    :returntype: (matrix of float,matrix of float)

    If at_start is True, then the scaling is performed first (i.e. M = R*S).
    '''
    w, s, vh = svd(M)
    W = matrix(w)
    V = matrix(vh).H
    U = W * V.H
    if det(U) < 0:  # Is the unit matrix not a rotation (i.e. direct)
        s[-1] *= -1
        V[:, -1] *= -1
        U = W * V.H
    S = matrix(diag(s))
    if at_start:
        P = V * S * V.H
    else:
        P = W * S * W.H
    return P, U

def rotation2Vorticity(r, dt):
    if r.shape == (1, 1):
        return [0]  # there is no rotation ...
    elif r.shape == (2, 2):
        a = arctan2(r[1, 0], r[0, 0])
        r = matrix([[0, -a], [a, 0]])
        return a, r / dt
    elif r.shape == (3, 3):
        r = asarray(r)
        ev, ec = eig(r)
        axis = (ec[:, abs(ev - 1) < 1e-10].real).squeeze()
        if abs(axis[2]) / norm(axis) > 1e-8:
            naxis = cross(axis, [1., 0, 0])
        else:
            naxis = cross(axis, [0, 0, 1.])
        tn = dot(r, naxis)  # i.e. matrix multiplication
        ca = dot(tn, naxis)
        sa = dot(cross(tn, naxis), axis)
        a = arctan2(sa, ca)
        saxis = axis * a
        vm = matrix([[0, saxis[2], -saxis[1]],
                     [-saxis[2], 0, saxis[0]],
                     [saxis[1], -saxis[0], 0]], dtype=float)
        return saxis, vm / dt
    raise ValueError("Cannot extract vorticity from a rotation in dimension greater than 3")

def transformation2Tensor(t, dt, at_start=True, exp_correction=True):
    if t.shape[0] != t.shape[1]:
        raise ValueError("Error, the transformation is not an endomorphism")
    if t.shape[0] > 3:
        raise ValueError("Error, this function doesn't work in more than 3 dimensions")
    tr, R = polarDecomposition(t, at_start)
    _, r = rotation2Vorticity(R, dt)
    tr -= eye(tr.shape[0])
    tr /= dt
    if exp_correction:
        tr = linear2exponential_strain(tr, dt)
    T = tr + r
    return T

def growthTensor(p, q, dt, at_start=True, exp_correction=True, want_transform=False):
    """
    Growth tensor transforming points p into points q with dt.

    The growth tensor will be the best one using least square criteria.
    """
    p = asarray(p)
    q = asarray(q)
    t = fitmat(p, q)
    if t is None:
        return
    T = transformation2Tensor(t, dt, at_start, exp_correction)
    if want_transform:
        return T, t
    return T

def growthParams(p, q, dt, exp_correction=True, at_start=True):
    """
    Return the growth parameters corresponding to the transformation of points
    p into points q with dt.

    :Parameters:
        p : ndarray(N*2)
            List of points at time t
        q : ndarray(N*2)
            List of points at time t+dt
        dt : float
            Time between points p and q
        exp_correction : bool
            If True, the result is corrected for exponential growth instead of linear

    :returns: The growth parameters as (kmaj, kmin, theta, phi) if 2D and
        (kmaj, kmed, kmin, theta_maj_xy, theta_maj_z, theta_med, psi_x, psi_y, psi_z) if 3D
    :returntype: (float,)*4|(float,)*9
    """
#    import pdb
#    pdb.set_trace()
    T = growthTensor(p, q, dt, at_start, exp_correction)
    if T is None:
        return None
    if T.shape[0] == 1:
        k = T[0]
        if exp_correction:
            return linear2exponential_growth(k, dt)
        return k
    elif T.shape[0] == 2:
        (kmaj, kmin, theta, phi) = tensor2Params(T)
        return (kmaj, kmin, theta, phi)
    elif T.shape[0] == 3:
        (kmaj, kmed, kmin, theta_maj_xy, theta_maj_z, theta_med, psi_x, psi_y, psi_z) = tensor2Params(T)
        return (kmaj, kmed, kmin, theta_maj_xy, theta_maj_z, theta_med, psi_x, psi_y, psi_z)
    else:
        raise ValueError("Cannot handle growth in more than 3D.")

def tensor2Params(tensor):
    """
    :returns: The growth parameters as (kmaj, kmin, theta, phi) if 2D and
    (kmaj, kmed, kmin, theta_maj_xy, theta_maj_z, theta_med, psi_x, psi_y, psi_z) if 3D
    :returntype: (float,)*4|(float,)*9
    """
    # First, extract the symetric and antisymetric parts
    tensor = asarray(tensor)
    assert len(tensor.shape) == 2, "tensor must be a 2d array"
    assert tensor.shape[0] == tensor.shape[1], "tensor must be square"
    assert tensor.shape[0] in [2, 3], "this function can only compute parameters for 2D and 3D tensors"
    ts = (tensor + tensor.T) / 2
    ta = (tensor - tensor.T) / 2
    values, vectors = eigh(ts)
    abs_values = abs(values)
    order = argsort(abs_values)
    values = values[order]
    vectors = vectors[:, order]
    if tensor.shape[0] == 2:
        kmaj = values[1]
        kmin = values[0]
        theta = atan2(vectors[1, 1], vectors[0, 1])
        # Wrap over pi
        if theta < pi / 2:
            theta += pi
        elif theta > pi / 2:
            theta -= pi
        #theta = asin(vectors[1,1]/sum(vectors[:,1]*vectors[:,1]))
        #if theta < 0:
        #    theta += pi
        #theta *= 180/pi
        psi = ta[0, 1]
        return (kmaj, kmin, theta, psi)
    else:
        kmaj = values[2]
        kmed = values[1]
        kmin = values[0]
        theta_maj_xy = atan2(vectors[1, 2], vectors[0, 2])
        theta_maj_xyz = atan2(vectors[2, 2], norm(vectors[:2, 2]))
        theta_med = atan2(norm(cross(vectors[:, 1], vectors[:, 2])), dot(vectors[:, 1], vectors[:, 2]))
        # ta[i,j] = vorticity over vector i x j
        psi = (ta[1, 2], -ta[0, 2], ta[0, 1])
        return (kmaj, kmed, kmin, theta_maj_xy, theta_maj_xyz, theta_med) + psi

def params2Tensor(*params):
    """
    Convert growth parameters into growth tensor for 2D or 3D growth.
    """
    if len(params) == 4:
        kmaj, kmin, theta, psi = params
        #theta *= pi/180
        vx = cos(theta)
        vy = sin(theta)
        V = matrix([[vx, vy], [-vy, vx]])
        D = matrix(diag([kmaj, kmin]))
        return (V.I * D * V).A + array([[0, psi], [-psi, 0]])
    elif len(params) == 9:
        raise NotImplementedError("The params2Tensor is not yet implemented for 3D tensors")
    else:
        raise TypeError("params2Tensor() takes 4 or 9 arguments (%d given)" % len(params))
