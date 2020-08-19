import random
import os

random.seed(os.urandom(32))

def sample(k):
    r = ""
    for _ in range(k):
        r += str(random.randint(0,1))
    return r

print('10 random bits:', sample(10))
print('20 random bits:', sample(20))

