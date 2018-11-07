import gevent
from gevent.event import AsyncResult

def wait_for_inputs(pending):
    _done = set()
    _pending = set(pending)
    for e in pending:
        if e.ready():
            _done.add(e)
            _pending.remove(e)

    return _done,_pending


class ACS_Functionality(object):
    def __init__(self, sid, N, f):
        self.sid = sid
        self.N = N
        self.f = f
        self.inputs = [AsyncResult() for _ in range(N)]
        self.outputs = [AsyncResult() for _ in range(N)]

    def run(self):
        pending = set(self.inputs)
        ready = set()

        while True:
            done, pending = wait_for_inputs(pending)
            ready.update(done)

            if len(ready) >= self.N - self.f:
                break
            gevent.sleep()

        print('ACS_Functionality done')
        out = [inp.result() if inp.ready() else None for inp in self.inputs]

        for i in range(self.N):
            self.outputs[i].set(out)

def CommonSubset_IdealProtocol(N, f):
    class ACS_IdealProtocol(object):
        _instances = {}
        
        def __init__(self, sid, myid):
            if sid not in ACS_IdealProtocol._instances:
                ACS_IdealProtocol._instances[sid] = ACS_Functionality(sid, N, f)
            F_ACS = ACS_IdealProtocol._instances[sid]

            self.input = F_ACS.inputs[myid]
            self.output = F_ACS.outputs[myid]
            self.run = F_ACS.run

    return ACS_IdealProtocol


def local_io(parties):
    for i,p in enumerate(parties):
        p.input.set('hi'+str(i))

    for i,p in enumerate(parties):
        gevent.wait([p.output])
        print(i, p.output)


def test_acs_ideal(sid='sid', N=4, f=1):
    ACS = CommonSubset_IdealProtocol(N, f)
    parties = [ACS(sid, i) for i in range(N)]
    
    g1 = gevent.spawn(parties[0].run)
    g2 = gevent.spawn(local_io, parties)

#    gevent.joinall([g1,g2])

    while True:
        pass        

if __name__=='__main__':
    test_acs_ideal()


