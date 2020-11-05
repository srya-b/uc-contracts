import comm
import gevent
from itm import UCFunctionality

class ITMKatzSFE(UCFunctionality):
    def __init__(self, sid, pid, channels, handlers):
        self.sid = sid; self.pid = pid
        self.ssid = self.sid[0]
        self.Rnd = self.sid[1]
        self.parties = self.sid[2]

        self.x = dict( (p,None) for p in self.parties )
        self.y = dict( (p,None) for p in self.parties )
        self.t = dict( (p,len(self.parties)) for p in self.parties )
        self.l = 1
        self.crupted = set()
        UCFunctionality.__init__(self, sid, pid, channels, handlers)

    def function(self):
        raise Exception("ITMSyncFunctinality.function must be defined in the deriving class!")

    def outputs_set(self):
        for i in self.y.values():
            if i is None: return False
        return True

    def are_all_honest_0(self):
        for i in self.parties:
            if i not in self.crupted and self.t[i] != 0: return False
        return True

    def input_input(self, pid, v):
        # TODO can input be set more than once??
        self.x[pid] = v
        self.f2a.write( ('input', pid, v) )

    def input_output(self, pid):
        #if pid not in self.crupted and self.x[pid] is None:
        if comm.ishonest(self.sid, pid) and self.x[pid] is None:
            dump.dump(); return

        if self.t[pid] > 0:
            self.t[pid] = self.t[pid]-1
            if self.are_all_honest_0() and self.l < self.Rnd:
                self.l += 1
                for i in self.t: self.t[i] = len(self.parties)
            self.f2a.write( ('activated',pid) )
        elif self.t[pid] == 0 and self.l < self.Rnd:
            self.f2p.write( (pid, ('early',)) )
        else:
            if self.x[1] is not None and not self.outputs_set():
                self.y = self.function()
            self.f2p.write( (pid, self.y[pid]) )

