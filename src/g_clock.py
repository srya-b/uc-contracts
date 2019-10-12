import dump
import comm
import copy
import gevent
import inspect
from itm import ITMFunctionality
from utils import print, gwrite
from queue import Queue as qqueue
from hashlib import sha256
from collections import defaultdict
from gevent.event import AsyncResult
from gevent.queue import Queue, Channel

class Clock_Functionality(object):
    def __init__(self, sid, pid, a2f):
        self.sid = sid; self.pid = pid
        self.sender = (sid,pid)
        self.a2f = a2f

        self.pregistry = defaultdict(list)
        self.fregistry = defaultdict(list)
        self.sids = set()
        self.sessionT = defaultdict(int)
        self.dp = defaultdict(int)        # (pid,sid) -> d
        self.dfsid = defaultdict(int)     # F,sid -> d
        self.outputs = None


    def check_and_step_round(self):
        for sid in self.sids:
            honestp = True; F = True
            for pid in self.pregistry[sid]:
                if comm.ishonest(sid,pid) and not self.dp[sid,pid]:
                    honestp = False
            print('All honst parties? (%s)' % sid, honestp)
            if not honestp: continue
            for pid in self.fregistry[sid]:
                if not self.dfsid[sid,pid]:
                    F = False
            print('All functionalities? (%s)' % sid, F)
            if not F: continue
            self.sessionT[sid] += 1

            for pid in self.pregistry[sid]:
                self.dp[sid,pid] = 0
            for pid in self.fregistry[sid]:
                self.dfsid[sid,pid] = 0

    def input_register(self, sender):
        sid,pid = sender
        self.sids.add(sid) 
        print('Regsitered sids', self.sids)
        if comm.isf(sid,pid):
            self.fregistry[sid].append(pid)
        elif comm.isparty(sid,pid):
            self.pregistry[sid].append(pid)

        dump.dump()
   
    def input_pclock_update(self, sender):
        sid,pid = sender
        if sid in self.pregistry and pid in self.pregistry[sid]:
            self.dp[sender] = 1
            self.check_and_step_round()
        dump.dump()

    def input_fclock_update(self, sender):
        sid,pid = sender
        if sid in self.fregistry and pid in self.fregistry[sid]:
            self.dfsid[sender] = 1
            self.check_and_step_round()
        dump.dump()

    def input_msg(self, sender, msg):
        if msg[0] == 'clock-update':
            if comm.isf(*sender): self.input_fclock_update(sender)
            elif comm.isparty(*sender): self.input_pclock_update(sender)
            else: print('clock update called by non-party'); dump.dump()
        elif msg[0] == 'register':
            self.input_register(sender)
        else:
            dump.dump()

    def subroutine_clock_read(self, sender):
        sid,pid = sender
        if sid in self.sids:
            return self.sessionT[sid]

    def subroutine_msg(self, sender, msg):
        if msg[0] == 'clock-read':
            return self.subroutine_clock_read(sender)


def ClockITM(sid, pid, a2f):
    f = Clock_Functionality(sid,pid, a2f)
    itm = ITMFunctionality(sid,pid,a2f,None,None)
    itm.init(f)
    comm.setFunctionality(itm)
    return f,itm


class FakeITM():
    def __init__(self, sid, pid):
        self.sid = sid; self.pid = pid

def test():
    c = Clock_Functionality('sid', 8, None)
    
    sids = ['sid', 'sid', 'sid', 'sid1', 'sid2', 'sid2']
    pids = [1,     2,     3,     1,      1,      2,    ]
    #       F      P      P      F       P       P

    comm.setFunctionality( FakeITM(sids[0], pids[0]) )
    comm.setFunctionality( FakeITM(sids[3], pids[3]) )
    comm.setParties([FakeITM(sids[1],pids[1]), FakeITM(sids[2],pids[2]), FakeITM(sids[4],pids[4]), FakeITM(sids[5],pids[5])])
    for sid in sids:
        print('T_sid for (%s):' % sid, c.subroutine_msg((sid,-1),('clock-read',)))
    for sid,pid in zip(sids,pids):
        c.input_msg((sid,pid), ('register',))
    for sid in sids:
        print('T_sid for (%s):' % sid, c.subroutine_msg((sid,-1),('clock-read',)))

    # only 'sid1' progresses
    c.input_msg(('sid1',1), ('clock-update',))
    print('Only sid1 progresses')
    for sid in sids:
        print('T_sid for (%s):' % sid, c.subroutine_msg((sid,-1),('clock-read',)))

    c.input_msg(('sid1',1), ('clock-update',))
    for sid in sids:
        print('T_sid for (%s):' % sid, c.subroutine_msg((sid,-1),('clock-read',)))

    c.input_msg(('sid1',1), ('clock-update',))
    c.input_msg(('sid',1), ('clock-update',))
    c.input_msg(('sid',2), ('clock-update',))
    c.input_msg(('sid',3), ('clock-update',))
    c.input_msg(('sid2',1), ('clock-update',))
    c.input_msg(('sid2',2), ('clock-update',))

    for sid in sids:
        print('T_sid for (%s):' % sid, c.subroutine_msg((sid,-1),('clock-read',)))

if __name__=='__main__':
    test()
