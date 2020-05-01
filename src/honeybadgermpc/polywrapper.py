import honeybadgermpc.polynomial as polynomial
from honeybadgermpc.polynomial import polynomials_over, EvalPoint
from honeybadgermpc.betterpairing import ZR
from honeybadgermpc.elliptic_curve import Subgroup
from honeybadgermpc.field import GF, GFElement
import numpy as np
from honeybadgermpc.reed_solomon_wb import make_wb_encoder_decoder
'''
n = 10
t = n // 3
omega_n = int(np.log2(n)) + 1

field = GF(Subgroup.BLS12_381)
Poly = polynomials_over(field)
rand_poly = Poly.random(degree=t)
print(rand_poly)

omega = polynomial.get_omega(field, 2**omega_n, seed=0)
x = rand_poly.evaluate_fft(omega, 2**omega_n)
print(x)
for i in range(0, 2**omega_n):
    print(rand_poly(omega**i))
    
encode, decode, solve_system = make_wb_encoder_decoder(n, t+1, Subgroup.BLS12_381, point=EvalPoint(field, n, True))
coeffs = decode(x[:t+1] + [None] * (n-2*t-1) + x[n-t:n])
print(coeffs)
'''
class PolyWrapper:
    def __init__(self, n):
        self.n = n
        self.t = n // 3
        self.omega_n = int(np.log2(n)) + 1

        self.field = GF(Subgroup.BLS12_381)
        self.Poly = polynomials_over(self.field)

        self.omega = polynomial.get_omega(self.field, 2**self.omega_n, seed=0)
        self.encode, self.decode, self.solve_system = make_wb_encoder_decoder(self.n, self.t+1, Subgroup.BLS12_381, point=EvalPoint(self.field, self.n, True))
    '''
    points - list of points where points[idx] contains f(w**idx)
    '''
    def random_with_pairs(self, pairs):
        pairs = [(self.omega**i, share) for (i, share) in pairs]
        assert len(pairs) <= self.t + 1
        pairs.extend([(self.omega**(self.n+1+i), self.field.random()) for i in range(len(pairs)-(self.t+1))])
        return self.Poly.interpolate(pairs)
        
    def random_with_secret(self, secret):
        return self.Poly.interpolate([(self.omega**self.n, secret) if i == 0 else (self.omega**i, self.field.random()) for i in range(self.t+1)])
    def random(self, points=None):
        if points is None:
            return self.Poly.random(degree=self.t)
        points = points.copy()
        count = len(points)-points.count(None)
        if count >= self.t+1:
            print("Not random")
            try:
                return self.Poly.interpolate([(self.omega**i, p) for i, p in enumerate(points) if p is not None])
            except:
                coeffs = self.reconstruct(points)
                return self.Poly(coeffs)
        else:
            elems = [x for x in range(len(points)) if points[x] is None][:self.t+1-count]
            for elem in elems: points[elem] = self.field.random()
            return self.Poly.interpolate([(self.omega**i, p) for i, p in enumerate(points) if p is not None])
    def reconstruct(self, points):
        try:
            return self.Poly(self.decode(points))
        except:
            return None
    def share(self, f, i):
        return f(self.omega**i)
    def secret(self, f):
        return self.share(f, self.n)