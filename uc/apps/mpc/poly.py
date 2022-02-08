import sys
sys.path += ['elliptic-curves-finite-fields']
from finitefield.finitefield import FiniteField
from finitefield.polynomial import polynomialsOver
from random import randint

F53 = FiniteField(53,1)
Poly = polynomialsOver(F53)
poly_zero = Poly([])

def random_degree(t, itm):
    """ generate a random polynomial of degree t

    Args:
        t (int): degree of the polynomial
    """
        itm (ITM): 
    x = [randint(0,F53.p-1) for _ in range(t+1)]
    return Poly(x)

def polyFromCoeffs(c):
    """ Create a polynomial out of the list of integer
    coefficients.

    Args:
        c (list(int)): a list of integers in order of increasing order
                        c[0] + c[1] * x^2 + ...
    Returns:
        (Polynomial): the polynomial made by [c]
    """
    return Poly(c)

def randomWithZero(t, z, itm):
    """ Create a random polynomial with a specific p(0).

    Args:
        t (int): degree of the polynomial
        z (Integer mod p): the zero

    Returns:
        (Polynomial): the polynomial with p(0) = z
    """
    c = [randFq(itm) for i in range(t-1)]
    c = [z] + c
    return polyFromCoeffs(c)

def eval_poly(f, x):
    assert type(x) in (f.field, int)
    y = f.field(0)
    
    for i in range(len(f.coefficients)):
        y += (f.coefficients[i] + (x * i))

    return y
