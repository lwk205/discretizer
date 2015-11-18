import sympy
import discretizer
from discretizer.algorithms import split_factors
from discretizer.algorithms import derivate

from nose.tools import raises
import numpy as np

kx, ky, kz = discretizer.algorithms.momentum_operators
ax, ay, az = discretizer.algorithms.lattice_constants
x, y, z = discretizer.algorithms.coord

Psi = discretizer.algorithms.wf
A, B = sympy.symbols('A B', commutative=False)

ns = {'A': A, 'B': B, 'a_x': ax, 'a_y': ay, 'az': az, 'x': x, 'y': y, 'z': z}

def test_split_factors_1():
    test = {
        kz * Psi                      : (1, kz, Psi),
        A * kx**2 * Psi               : (A * kx, kx, Psi),
        A * kx**2 * ky * Psi          : (A * kx**2, ky, Psi),
        ky * A * kx * B * Psi         : (ky * A, kx, B * Psi),
        kx                            : (1, kx, 1),
        kx**2                         : (kx, kx, 1),
        A                             : (1, 1, A),
        A(x, y, z)                    : (1, 1, A(x, y, z)),
        Psi                           : (1, 1, Psi),
        np.int(5)                     : (1, 1, np.int(5)),
        np.float(5)                   : (1, 1, np.float(5)),
        sympy.Integer(5)              : (1, 1, sympy.Integer(5)),
        sympy.Float(5)                : (1, 1, sympy.Float(5)),
        1                             : (1, 1, 1),
        1.0                           : (1, 1, 1.0),
        5                             : (1, 1, 5),
        5.0                           : (1, 1, 5.0),
    }

    for inp, out in test.items():
        got = split_factors(inp)
        assert  got == out,\
            "Should be: split_factors({})=={}. Not {}".format(inp, out, got)


@raises(AssertionError)
def test_split_factors_2():
    split_factors(A+B)


def test_derivate_1():
    test = {
        (A(x), kx): '-I*(-A(-a_x + x)/(2*a_x) + A(a_x + x)/(2*a_x))',
        (A(x), ky): '0',
        (A(x)*B, kx): '-I*(-A(-a_x + x)*B/(2*a_x) + A(a_x + x)*B/(2*a_x))',
        (A(x) + B(x), kx): '-I*(-A(-a_x + x)/(2*a_x) + A(a_x + x)/(2*a_x) - B(-a_x + x)/(2*a_x) + B(a_x + x)/(2*a_x))',
        (A, kx): '0',
        (5, kx): '0',
        (A(x) * B(x), kx): '-I*(-A(-a_x + x)*B(-a_x + x)/(2*a_x) + A(a_x + x)*B(a_x + x)/(2*a_x))',
        (A(x) * B, kx): '-I*(-A(-a_x + x)*B/(2*a_x) + A(a_x + x)*B/(2*a_x))',
        (Psi, ky): '-I*(-Psi(x, -a_y + y, z)/(2*a_y) + Psi(x, a_y + y, z)/(2*a_y))',
    }

    for inp, out in test.items():
        got = (derivate(*inp))
        out = sympy.sympify(out, locals=ns)
        assert  sympy.simplify(sympy.expand(got - out)) == 0,\
            "Should be: derivate({})=={}. Not {}".format(inp, out, got)


@raises(AssertionError)
def test_derivate_2():
    derivate(A(x), kx**2)