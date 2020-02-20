class SFEFunctionality(object):
    def __init__(self, sid, pid, channels, handlers):
        self.sid = sid; self.pid = pid
        self.ssid = self.sid[0]
        self.Rnd = self.sid[1]
        self.parties = self.sid[2]

        self.channels = channels
        self.handlers = handlers

        self.x = dict( (p,None) for p in self.parties )
        self.y = dict( (p,None) for p in self.parties )
        self.t = dict( (p,len(self.parties)) for p in self.parties )
        self.l = 1
        self.crupted = set()

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

    def run(self):
        while True:
            ready = gevent.wait(
                objects=self.channels,
                count=1
            )
            assert len(ready) == 1
            r = ready[0]
            msg = r.read()
            r.reset()
            self.handlers[r](msg)


class SFEBrachaFunctionality(ITMSyncFunctionality):
    def __init__(self, sid, pid, _f2p, _p2f, _f2a, _a2f, _f2z, _z2f):
        self.f2p = _f2p; self.p2f = _p2f
        self.f2a = _f2a; self.a2f = _a2f
        self.f2z = _f2z; self.z2f = _z2f

        self.channels = [self.a2f, self.z2f, self.p2f]
        self.handlers = {
            self.a2f: self.adversary_msg,
            self.p2f: self.input_msg,
            self.z2f: lambda x: dump.dump()
        }
        ITMSyncFunctionality.__init__(self, sid, pid, self.channels, self.handlers)

        # Bracha only cares about honest dealer's input
        for p in self.parties:
            if p != 1:  # skip the dealer
                self.x[p] = 'bot'
    
    # Require to be implemented by base class ITMSyncFunctionality
    def function(self):
        return dict( (p,self.x[1]) for p in self.parties)

    def input_msg(self, msg):
        sender,msg = msg
        sid,pid = sender
        if msg[0] == 'input' and pid in self.parties:
            self.input_input(pid, msg[1])
        elif msg[0] == 'output' and pid in self.parties:
            self.input_output(pid)
        else: dump.dump()
    
    def adv_corrupt(self, pid):
        self.crupted.add(pid)
        dump.dump()

    def adversary_msg(self, msg):
        if msg[0] == 'corrupt':
            self.adv_corrupt(msg[1])
        else: dump.dump()
