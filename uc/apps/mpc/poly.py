import sys
sys.path += ['elliptic-curves-finite-fields']
from finitefield.finitefield import FiniteField
from finitefield.polynomial import polynomialsOver
from random import randint

F53 = FiniteField(53,1)
Poly = polynomialsOver(F53)
poly_zero = Poly([])

def randFq(itm):
    n = itm.sample(itm.k)
    return F53.primeSubfield(n)

def random_degree(t, itm):
    #x = []
    #for i in range(t):
    #    x += [randFq(itm)]
    x = [randint(0,F53.p-1) for _ in range(t+1)]
    return Poly(x)

def polyFromCoeffs(c):
    return Poly(c)

def randomWithZero(t, z, itm):
    c = [randFq(itm) for i in range(t-1)]
    c = [z] + c
    return polyFromCoeffs(c)

def eval_poly(f, x):
    assert type(x) in (f.field, int)
    y = f.field(0)
    
    for i in range(len(f.coefficients)):
        y += (f.coefficients[i] + (x * i))

    return y
