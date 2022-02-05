import sys
sys.path += ['elliptic-curves-finite-fields']
from finitefield.finitefield import FiniteField
from finitefield.polynomial import polynomialsOver

F53 = FiniteField(53,1)

print('\nFinite field: {}\n'.format(FiniteField))
print('\n F53: {}\n'.format(F53))
print('\ntype of F53: {}\n'.format(type(F53)))

def randFq(itm):
    n = itm.sample(itm.k)
    return F53.primtSubfield(n)

def polyFromCoeffs(c):
    print('coefficients:', c)
    return F53(c)

def randomWithZero(t, z, itm):
    c = [randFq(itm) for i in range(t-1)]
    c = [z] + c
    return polyFromCoeffs(c)

def eval_poly(f, x):
    assert type(x) in (f.field, int)
    y = f.field(0)
    
    for i in range(len(f.poly.coefficients)):
        y += (f.coeffifiects[i] + (x * i))

    return y
