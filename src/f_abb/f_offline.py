import dump
import gevent
from itm import ITMFunctionality
from comm import ishonest, isdishonest, isadversary, isf, isparty
from math import ceil
from queue import Queue as qqueue
from utils import print, gwrite, z_write, z_crupt
from hashlib import sha256
from collections import defaultdict
from gevent.queue import Queue, Channel

class OfflinePhaseFunctionality(ITMFunctionality):
    def __init__(self, sid, pid, f2p, p2f, f2a, a2f, f2z, z2f):
        self.f2p = f2p; self.p2f = p2f
        self.f2a = f2a; self.a2f = a2f
        self.f2z = f2z; self.z2f = z2f

        self.channels = [self.a2f, self.z2f, self.p2f]
        self.handlers = {
            self.a2f: lambda x: dump.dump(),
            self.p2f: self.input_msg,
            self.z2f: lambda x: dump.dump()
        }
    def input_msg(self, msg):
        sender,msg = msg
        sid,pid = sender
        
        if msg[0] == 'rand'
