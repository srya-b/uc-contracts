import polynomial
from polynomial import polynomials_over
from betterpairing import ZR
from elliptic_curve import Subgroup
from field import GF, GFElement

field = GF(Subgroup.BLS12_381)
Poly = polynomials_over(field)
rand_poly = Poly.random(degree=5)


omega = polynomial.get_omega(field, 2**3, seed=1)
x = rand_poly.evaluate_fft(omega, 2**3)
print(x)
poly2 = Poly.interpolate_fft(x, omega)

print(rand_poly)
print(poly2)
