from numbapro.vectorize import GUVectorize
import numbapro as numba
from numbapro import *

import numpy as np
import numpy.core.umath_tests as ut

f = float_

@autojit(backend='ast')
def array_expr(a, b, c):
    return a + b * c

@autojit(backend='ast')
def func(a):
    return a * 2.0

@autojit(backend='ast')
def array_expr2(a, b, c):
    return a + b + func(c)

@autojit(backend='ast')
def array_expr3(a, b, c):
#    a[1:, 1:] = a[1:, 1:] + b[1:, :-1] * c[1:, :-1]
    a[...] = a + b * c

def test_array_expressions():
    a = np.arange(120).reshape(10, 12).astype(np.float32)
    assert np.all(array_expr(a, a, a) == array_expr.py_func(a, a, a))
    assert np.all(array_expr2(a, a, a) == array_expr2.py_func(a, a, a))

    result, numpy_result = a.copy(), a.copy()
    array_expr3(result, result, result)
    array_expr3.py_func(numpy_result, numpy_result, numpy_result)

    assert np.all(result == numpy_result)

#
### test matrix multiplication w/ array expressions
#
@autojit(backend='ast')
def array_expr_matmul(A, B):
    m, n = A.shape
    n, p = B.shape
    C = np.empty((m, p), dtype=A.dtype)
    for i in range(m):
        for j in range(p):
            C[i, j] = (A[i, :] * B[:, j]).sum()

    return C

def test_matmul():
    a = np.arange(120).reshape(10, 12).astype(np.float32)
    b = a.T
    result = array_expr_matmul(a, b)
    assert np.all(result == np.dot(a, b))

#
### test gufuncs
#
def array_expr_gufunc(A, B, C):
    m, n = A.shape
    n, p = B.shape
    for i in range(m):
        for j in range(p):
            result = (A[i, :] * B[:, j]).sum()
            # print result
            C[i, j] = result

def test_gufunc_array_expressions():
    gufunc = GUVectorize(array_expr_gufunc, '(m,n),(n,p)->(m,p)', backend='ast')
    gufunc.add(argtypes=[f[:,:], f[:,:], f[:,:]])
    gufunc = gufunc.build_ufunc()

    matrix_ct = 10
    A = np.arange(matrix_ct * 2 * 4, dtype=np.float32).reshape(matrix_ct, 2, 4)
    B = np.arange(matrix_ct * 4 * 5, dtype=np.float32).reshape(matrix_ct, 4, 5)

    C = gufunc(A, B)
    Gold = ut.matrix_multiply(A, B)

    if (C != Gold).any():
        print(C)
        print(Gold)
        raise ValueError

@autojit
def vectorized_math(a):
    a[...] = np.cos(a) * np.sin(a)
    return a

def test_vectorized_math():
    a = vectorized_math(np.arange(100, dtype=np.float64))
    b = vectorized_math.py_func(np.arange(100, dtype=np.float64))
    assert np.allclose(a, b)

@autojit
def diffuse_numbapro(iter_num):
    u = np.zeros((Lx, Ly), dtype=np.float64)
    temp_u = np.zeros_like(u)
    temp_u[Lx / 2, Ly / 2] = 1000.0

    for i in range(iter_num):
        u[1:-1, 1:-1] = mu * (temp_u[2:, 1:-1] + temp_u[:-2, 1:-1] +
                              temp_u[1:-1, 2:] + temp_u[1:-1, :-2] -
                              4 * temp_u[1:-1, 1:-1])

        temp = u
        u = temp_u
        temp_u = temp

    return u

mu = 0.1
Lx, Ly = 101, 101

def test_diffusion():
    assert np.allclose(diffuse_numbapro(100), diffuse_numbapro.py_func(100))


if __name__ == '__main__':
#    a = np.arange(120).reshape(10, 12).astype(np.float32)
#    assert np.all(array_expr(a, a, a) == array_expr.py_func(a, a, a))
#    test_array_expressions()
    tests = [name for name in globals().keys() if name.startswith('test_')]
    for t in tests:
        globals()[t]()

