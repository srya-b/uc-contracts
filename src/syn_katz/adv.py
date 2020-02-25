import comm
from adversary import DummyAdversary

class KatzDummyAdversary(DummyAdversary):
    def __init__(self, sid, pid, z2a, a2z, p2a, a2p, a2f, f2a):
        DummyAdversary.__init__(self, sid, pid, z2a, a2z, p2a, a2p, a2f, f2a)
    
    def input_corrupt(self, pid):
        print('or this one')
        comm.corrupt(self.sid, pid)
        self.a2f.write( ((self.sid, 'F_clock'), ('corrupt',(self.sid,pid))) )
