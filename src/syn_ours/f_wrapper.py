import dump
import gevent
from collections import defaultdict

def syn_wrapper(base):
    class Syn_FWrapper(base):
        def __init__(self, sid, pid, _f2p, _p2f, _f2a, _a2f, _f2z, _z2f):
            self.curr_round = 1
            self.todo = defaultdict(list)
            base.__init__(self, sid, pid, _a2f, _f2a, _z2f, _f2z, _p2f, _f2p)
    
        def exec_in_o1(self, f, args=()):
            self.todo[self.curr_round+1].append( (f, args) )
            self.f2a.write( ('exec',self.curr_round+1,len(self.todo[self.curr_round+1])-1) )
      
        def get_round(self):
            return self.curr_round


