import dump
import gevent
from itm import ITMFunctionality
from comm import ishonest, isdishonest, isadversary, setFunctionality
from utils import gwrite, print
from queue import Queue as qqueue
from hashlib import sha256
from collections import defaultdict
from gevent.event import AsyncResult
from gevent.queue import Queue, Channel

class Broadcast_Functionality(object):
    def __init__(self, _sid, _pid, G, *peers):
        self.sid = _sid; self.pid = _pid
        self.sender = (_sid, _pid)
        self.peers = peers
        self.poutputs = defaultdict(dict)
        self.outputs = defaultdict(Queue)
        self.buffer_output = defaultdict(list)
        # TODO: register and extract time
        self.round = 0; self.lastround = -1
        self.gave_input = defaultdict(bool)
        self.G = G
        self.bnumber = self.subroutine_block_number()
        print('BNUMBER', self.bnumber)

        self.f2c = None; self.clock = None
    
    def __str__(self):
        return '\033[92mF_bc\033[0m'

    def write(self, to, msg):
        #print(u'\033[92m{:>20}\033[0m -----> {}, msg={}'.format('F_pay', str(to), msg))
        gwrite(u'92m', 'F_bc', str(to), msg)
   
    def set_clock(self, f2c, clock):
        self.f2c = f2c; self.clock = clock

    def util_read_clock(self):
        return self.clock.subroutine_msg( self.sender, ('clock-read',))

    def subroutine_block_number(self):
        return self.G.subroutine_call((
            (self.sid,self.pid),
            True,
            ('block-number',)
        ))

    def buffer(self, msg, delta, p):
        #print('Delay this', msg, 'for', delta, 'blocks, right now at', self.subroutine_block_number())
        #self.buffer_output[ self.subroutine_block_number()+delta ].append( (msg,p) )
        print('Delay this', msg, 'for', delta, 'rounds, right now at', self.util_read_clock())
        self.buffer_output[ self.util_read_clock()+delta ].append( (msg,p) )

    def process_buffer(self):
        #rnd = self.subroutine_block_number()
        rnd = self.util_read_clock()
        if rnd > self.round:
            self.lastround = self.round
            self.round = rnd
            for r in range(self.lastround+1, self.round+1):
                print('Round', r, 'buffer', self.buffer_output[r])
                for msg,p in self.buffer_output[ r ]:
                    for peer in self.peers:
                        if self.round not in self.poutputs[peer]:
                            self.poutputs[peer][self.round] = []
                        #self.poutputs[peer][self.round].append( (msg,p) )
                        self.poutputs[peer][self.round].append( msg )

    def ping(self):
        self.process_buffer()
        dump.dump()

    def subroutine_read(self, pid):
        return self.poutputs[pid]

    def input_bcast(self, pid, msg):    
        print('THIS NIGGA RIGHT HURRR TRYING TO BCAST', pid, msg)
        dump.dump()
        if not self.gave_input[pid]:
            self.buffer( msg, 1, pid )
        else: dump.dump()

    def input_msg(self, sender, msg):   
        #print('INPUT MSG', sender, msg)
        sid,pid = sender
        self.process_buffer()
        if pid in self.peers or pid == -1:
            if msg[0] == 'bcast':
                self.input_bcast(pid, msg)
            else: dump.dump()
        else: dump.dump()

    def subroutine_msg(self, sender, msg):
        sid,pid = sender
        if msg[0] == 'read': return self.subroutine_read(pid)

    def adversary_msg(self, msg):
        if msg[0] == 'ping': self.ping()
        else: dump.dump()
            
    
def BroadcastITM(sid, pid, G, a2f, f2f, p2f, *p):
    f = Broadcast_Functionality(sid, pid, G, *p)
    itm = ITMFunctionality(sid,pid,a2f,f2f,p2f)
    itm.init(f)
    setFunctionality(itm)
    return f,itm







     
