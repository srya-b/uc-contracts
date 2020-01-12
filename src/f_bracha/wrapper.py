import dump
import gevent
from itm import ITMFunctionality
from comm import ishonest, isdishonest, isadversary, isf, isparty, GenChannel
from math import ceil
from queue import Queue as qqueue
from utils import print, gwrite, z_write
from hashlib import sha256
from collections import defaultdict
from gevent.queue import Queue, Channel

class WrapperSynchronous(object):
    def __init__(self, sid, pid, _p2f,_f2p, _p2a,_a2p, _p2z,_z2p):
        self.sid = sid
        self.ssid,self.fcls,self.fparams = self.sid[0],self.sid[1],self.sid[2]
        self.pid = self.pid
        self.p2f = _p2f; self.f2p = _f2p
        self.p2a = _p2a; self.a2p = _a2p
        self.p2z = _p2z; self.z2p = _z2p
        
        self.f2w2p,self.p2w2f = GenChannel(),GenChannel()
        self.a2w2p,self.p2w2a = GenChannel(),GenChannel()
        self.z2w2p,self.p2w2z = GenChannel(),GenChannel()

        self.F = self.fcls( (self.ssid,self.fparams), self.pid,
                            self.p2w2f,self.f2w2p,
                            self.p2w2a,self.a2w2p,
                            self.p2w2z,self.z2w2p)

        self.clock_round = 1

    def wait_for(self, chan):
        r = gevent.wait(objects=[chan],count=1)
        r = r[0]
        fro,msg = r.read()
        chan.reset()
        return fro,msg

    def run(self):
        while True:
            ready = gevent.wait(
                objects=[self.a2f, self.z2f, self.p2f],
                count=1
            )
            r = ready[0]

            if r == self.z2f:
                self.z2f.reset()
                dump.dump()
            elif r == self.a2f:
                self.
                
