from uc.messages import *
from uc.typing import Callable, Tuple

class Schedule_Msg(MSG):
    def __init__(self,
            fptr  : Callable[..., None], 
            args  : Tuple, 
            delta : int, 
            imp   : int):
        MSG.__init__(self, ('schedule', fptr, args, delta), imp)
        self.fptr = fptr
        self.args = args
        self.delta = delta

class Delay_Msg(MSG):
    def __init__(self, 
            delay : int):
        MSG.__init__(self, ('delay', delay), delay)
        melf.delay = delay

class Poll_Msg(MSG):
    def __init__(self):
        MSG.__init__(self, ('poll',), 1)

class Exec_Msg(MSG):
    def __init__(self, 
            rnd : int, 
            idx : int):
        MSG.__init__(self, ('exec', rnd), 0)

def f(a,b):
    print(a,b)

args = (1,2)
delta = 3
imp = 4

s = Schedule_Msg(f, args, delta, imp)
