#| ## Handout 0: Groups in Python (based on Jeremy Kun's post)
#|
#|This file is an implementation of a particular Ellitpic Curve group
#|used in cryptography, called secp256k1. This happens to be the curve used
#|by Bitcoin and most related cryptocurrencies. We'll also use this as our
#|go-to general purpose discrete-log group in our class.
#|
#|We call an element of this group (i.e., a point on the curve), simply a Point.
#|
#|The order of this group, `p`, is a 256-bit prime number. Furthermore, `p`
#|happens to be extremely close to 2^256. Because of this, we can sample
#|exponents easily by choosing a random 32-byte number, and with high probability,
#|will be within [0,p).
#|   `uint256_from_str(rnd_bytes(32))` is an exponent.
#|
#|Sometimes an exponent will be represented by objects of the python class  Fp,
#|which automatically handles arithmetic modulo p. 
#|The underlying 'long' value can be extracted as `p.n` if `type(p) is Fp`.
import sys
sys.path += ['elliptic-curves-finite-fields']
from finitefield.finitefield import FiniteField
from elliptic import EllipticCurve, Point, Ideal
import elliptic
import os
import random


#|## The the definition of secp256k1, Bitcoin's elliptic curve.

#| First define the finite field, Fq
q = 2**256 - 2**32 - 2**9 - 2**8 - 2**7 - 2**6 - 2**4 - 1
Fq = FiniteField(q,1) # elliptic curve over F_q

#| Then define the elliptic curve, always of the form y ** 2 = x ** 3 + {a6}
#|   (Weirerstrass Form)
curve = EllipticCurve(a=0, b=Fq(7)) # E: y ** 2 = x ** 3 + 7

#| base point, a generator of the group
Gx = Fq(0x79BE667EF9DCBBAC55A06295CE870B07029BFCDB2DCE28D959F2815B16F81798)
Gy = Fq(0x483ADA7726A3C4655DA4FBFC0E1108A8FD17B448A68554199C47D08FFB10D4B8)
G = Point(curve, Gx, Gy)

#| This is the order (# of elements in) the curve
p = order = 0xFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFEBAAEDCE6AF48A03BBFD25E8CD0364141
Fp = FiniteField(p,1)

#| Get the identity element
identity = Ideal(curve)

#|## Serialize and deserialize 32-byte (256-bit) numbers
#|
#|Since the underlying field, `Fq`, is 32 bytes, we can represent each point
#|as a 32-byte X coordinate and 32-byte Y coordinate. The following routines
#|serialize/deserialize such 32-byte numbers to strings.
#|
import struct
def uint256_from_str(s):
    """Convert bytes to uint256"""
    r = 0
    t = struct.unpack(b"<IIIIIIII", s[:32])
    for i in range(8):
        r += t[i] << (i * 32)
    return r

def uint256_to_str(s):
    """Convert bytes to uint256"""
    assert 0 <= s < 2**256
    t = []
    for i in range(8):
        t.append((s >> (i * 32) & 0xffffffff))
    s = struct.pack(b"<IIIIIIII", *t)
    return s

#|## Compute Square Roots
#|
#|This easy sqrt works for this curve, not necessarily all curves
#|https://en.wikipedia.org/wiki/Quadratic_residue#Prime_or_prime_power_modulus
#|
#|There is not always a solution in this `Fq` (for around half the values)
def sqrt(a):
    # q: modulus of the underlying finitefield
    assert type(a) is Fq

    assert (q - 1) % 2 == 0 and (q+1)%4 == 0
    legendre = a ** ((q-1)//2)
    if legendre == Fq(-1): raise ValueError # no solution
    else: return a ** ((q+1)//4)

    
#|## Solve for y given x, making use of the efficient square root above
#|
#|Because of the fact `y**2 = (-y)**2`, for every x value in the field, there are
#|generally two curve points with that x coordinate (corresponding to the points
#|(x,y) and (-y,x)), where we can solve for y efficiently as `sqrt(x**3 + 7)`.
def solve(x):
    # Solve for y, given x
    # There are two possible points that satisfy the curve,
    # an even and an odd. We choose the odd one.
    assert type(x) is Fq
    y = sqrt(x**3 + 7)
    assert y*y == x**3 + 7
    if y.n % 2 == 0: y = -y
    if not curve.testPoint(x, y): raise ValueError
    return Point(curve, x, y)


#|## Serialize and deserialize elliptic curve points
#|
#|Because we have an easy way to solve for `y` given `x`, (more specifically,
#|a canonical version of two possible points with the same `x`), we can 
#|represent any pont as the `x` coordinate, and a byte indicating whether
#|`y` is even or odd.
def ser(point):
    # Returns a 33-byte string
    assert curve.testPoint(point.x, point.y)
    s = '0'
    sign = int(point.y.n % 2 == 0)
    s += str(sign)
    s += uint256_to_str(point.x.n).hex()
    assert len(s) == 66 and type(s) == str
    return s

def deser(s):
    s = bytes.fromhex(s)
    assert len(s) == 33
    sign = int(s[0])
    assert sign in (0,1)
    x = uint256_from_str(s[1:])
    assert 0 <= x < q
    # Note: this checks that X is the coordinate of a valid point
    point = solve(Fq(x)) 
    if sign: point.y = -point.y
    return point

#|## Generate a random point on the curve
import os
def make_random_point(rnd_bytes=os.urandom):
    # 32-byte string for x coordinate
    while True:
        # Not all x values are valid, find out by rejection sampling
        x = uint256_from_str(rnd_bytes(32))
        try: point = solve(Fq(x))
        except ValueError: continue
        break

    # Generate a random bit whether to flip the Y coordinate
    if ord(rnd_bytes(1)) % 2 == 0:
        point.y = -point.y
    return point

#|## Experiments
#|
#|Play around with the following. Convince yourself that
#|secp256k1 is a group.

A = make_random_point()
B = make_random_point()
C = make_random_point()

#|# identity element behaves correctly
assert identity + A == A == A + identity
assert identity + B == B == B + identity
assert identity + C == C == C + identity

#|# Associativity
assert A + (B + C) == (A + B) + C

#|# We can compute inverses
assert (-A) + A == identity
assert (-B) + B == identity
assert (-C) + C == identity

#|# Raising any element to group order results in identity
assert A * order == identity


#| ## How to implement exponentiation (actually scalar multiplication)

#|(see Goldwasser and Bellare, page 258)
def mult(m, A):
    assert type(m) in (int, int)
    assert type(A) is Point
    X = {}
    X[0] = A
    y = identity
    i = 0
    while m > 0:
        if m % 2 == 1:
            y += X[i] # Group operation (point addition)
        X[i+1] = X[i] + X[i] 
        i += 1
        m = m//2 # Divide (dropping the least significant bit)
        if m == 0: return y

#|# Test multiplication
assert 5 * G == mult(5, G)

def precompute_table(m, A):
    # TODO, if you like
    pass

def mult_precompute(m, A, pow2table=None):
    # TODO, if you like
    pass

#| ## Plot points
def plot_point(p, *args, **kwargs):
    assert type(p) is Point
    assert p != identity
    plt.plot(float(p.x.n), float(p.y.n), *args, **kwargs)

try:
    #raise Exception("skipping drawings")
    #import matplotlib.pyplot as plt
    plt.ion()
except:
    #print("Skipping drawings")
    pass
else:
    plt.figure(1);
    plt.clf();
    plt.xlim(0,float(p))
    plt.ylim(0,float(p))
    plot_point(G,  marker='o', label='G')
    for i in range(2,10):
        plot_point(i*G, marker='o', label='%d*G'%i)
    plt.legend()
    plt.ylabel('X coordinate [0,q]')
    plt.ylabel('Y coordinate [0,q]')
