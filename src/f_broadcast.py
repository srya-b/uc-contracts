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
        self.newoutputs = defaultdict(list)
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
                        #if self.round not in self.poutputs[peer]:
                        #    self.poutputs[peer][self.round] = []
                        #self.poutputs[peer][self.round].append( msg )
                        self.newoutputs[peer].append( (msg,p) )

    def ping(self):
        self.process_buffer()
        dump.dump()

    def subroutine_read(self, pid):
        r = list(self.newoutputs[pid])
        self.newoutputs[pid] = []
        return r
        #return self.poutputs[pid]

    def input_bcast(self, pid, msg):    
        #print('THIS NIGGA RIGHT HURRR TRYING TO BCAST', pid, msg)
        #dump.dump()
        if not self.gave_input[pid]:
            self.buffer( msg, 1, pid )
        dump.dump()

    def input_msg(self, sender, msg):   
        #print('INPUT MSG', sender, msg)
        sid,pid = sender
        self.process_buffer()
        if pid in self.peers or pid == -1:
            if msg[0] == 'bcast':
                self.input_bcast(pid, msg[1])
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



class Broadcast_Functionality2(object):
#    def __init__(self, _sid, _pid, G, *peers):
    def __init__(self, _sid, _pid, _f2p, _f2a, _f2z, _2f, f2_, caster, *peers):
        self.sid = _sid; self.pid = _pid
        self.sender = (_sid, _pid)
        self.caster = caster
        self.peers = peers
        self.poutputs = defaultdict(dict)
        self.newoutputs = defaultdict(list)
        self.outputs = defaultdict(Queue)
        self.buffer_output = defaultdict(list)
        # TODO: register and extract time
        self.round = 0; self.lastround = -1
        self.gave_input = defaultdict(bool)
#        self.G = G
        #self.f2c = None; self.clock = None
        self.f2p = _f2p
        self.f2a = _f2a
        self.f2z = _f2z
        self._2f = _2f
        self.f2_ = f2_
        #self.leaks = set()
        self.leaks = []
        
        print('[F_bcast] \n\tsid={} pid={}\n\tpeers={}\n\tsender={}'.format(self.sid,self.pid,self.peers,self.caster))

    def __str__(self):
        return '\033[92mF_bc\033[0m'

    def write(self, to, msg):
        #print(u'\033[92m{:>20}\033[0m -----> {}, msg={}'.format('F_pay', str(to), msg))
        gwrite(u'92m', 'F_bc', str(to), msg)
   
    def set_clock(self, f2c, clock):
        self.f2c = f2c; self.clock = clock

    def util_read_clock(self):
        self.f2_.write( ((420,'G_clock'), ('clock-read',)) )
        r = gevent.wait(objects=[self._2f],count=1)
        r = r[0]
        fro,rnd = r.read()
        self._2f.reset()
        return rnd

    def subroutine_block_number(self):
        self.f2_.write( ((69,'G_ledger'), (True, ('block-number',))) )
        r = gevent.wait(objects=self._2f, count=1)
        r = r[0]
        fro,blockno = r.read()
        self._2f.reset()
        return blockno

    def leak(self, msg, r):
        print('msg', msg, 'r', r)
        self.leaks.append( (msg,r) ) 

    def getLeaks(self):
        r = list(self.leaks)
        self.leaks = list()
        self.f2a.write( r )

    def deliver(self, msg, pid):
        if pid not in self.peers: print('pid', pid, 'peers', self.peers); raise Exception; dump.dump()
        # Check if there are unconsumed messages, if so --> error because dummy adv didn't deliver
        rnd = self.util_read_clock()
        m,r = msg
        if r > self.round: raise Exception("r={}, self.round={}, rnd={}".format(r,self.round,rnd))
        for _msg in self.buffer_output[ r ]:
            if _msg == m:
                print('\t \033[1m found msg={} in buffer={}\033[0m'.format(m, _msg))
                #dump.dump()
                self.f2p.write( ((self.sid,pid), m) )
                #self.buffer_output[r].remove( _msg )
                #print('\n\t \033[1m [F_bcast] removed msg={} from buffer={}\033[0m'.format(_msg, self.buffer_output[r]))
                return
        raise Exception("Msg={} not in buffer={}".format(msg, self.buffer_output))
    # TODO meaningful checks
    def check_except(self):
        #rnd = self.util_read_clock()
        #if rnd > 1:
        #    for i in range(0, rnd):
        #        if len(self.buffer_output[ i ]) > 0:
        #            raise Exception("there were messages from previous rounds ({}) not delivered, buffer={}".format(rnd, self.buffer_output[i]))
        #else:
        #    print('Bitch ass')
        pass

    def buffer(self, msg, delta):
        #print('Delay this', msg, 'for', delta, 'rounds, right now at', self.util_read_clock())
        rnd = self.util_read_clock()
        self.leak( msg, rnd+delta )
        self.buffer_output[ rnd+delta ].append( msg )

    def process_buffer(self):
        rnd = self.util_read_clock()
        if rnd > self.round:
            self.lastround = self.round
            self.round = rnd
            for r in range(self.lastround+1, self.round+1):
                print('Round', r, 'buffer', self.buffer_output[r])
                for msg in self.buffer_output[ r ]:
                    for peer in self.peers:
                        self.newoutputs[peer].append( msg )

    def ping(self):
        #self.process_buffer()
        self.check_except()
        dump.dump()

    def subroutine_read(self, pid):
        r = list(self.newoutputs[pid])
        self.newoutputs[pid] = []
        return r
        #return self.poutputs[pid]

    def input_read(self, pid):
        r = list(self.newoutputs[pid])
        self.newoutputs[pid] = []
        self.f2p.write( ((self.sid,pid), r) )

    def input_bcast(self, msg):    
        #print('THIS NIGGA RIGHT HURRR TRYING TO BCAST', pid, msg)
        #dump.dump()
        #if not self.gave_input[self.caster]:
        self.buffer( msg, 1 )
        dump.dump()

    def update_time(self):
        rnd = self.util_read_clock()
        if rnd > self.round:
            self.lastround = self.round
            self.round = rnd

    def input_msg(self, sender, msg):   
        #print('INPUT MSG', sender, msg)
        sid,pid = sender
        #self.process_buffer()
        self.check_except()
        self.update_time()
        if pid in self.peers or pid == -1:
            if msg[0] == 'bcast':
                if pid == self.caster:
                    self.input_bcast(msg[1])
                else: raise Exception; dump.dump()
            elif msg[0] == 'read':
                self.input_read(pid)
            else: dump.dump()
        else: 
            raise Exception
            dump.dump()

    def subroutine_msg(self, sender, msg):
        sid,pid = sender
        if msg[0] == 'read': return self.subroutine_read(pid)

    def adversary_msg(self, msg):
        self.update_time()
        if msg[0] == 'ping': self.ping()
        elif msg[0] == 'get-leaks':
            self.getLeaks()
        elif msg[0] == 'deliver': 
            print('\n\t delivering!! \n')
            self.deliver(msg[1], msg[2])
        else: dump.dump()
            




     
