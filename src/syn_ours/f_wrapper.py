import dump
import gevent
from itm import ITM
from collections import defaultdict

class Syn_FWrapper(ITM):
    def __init__(self, sid, pid, _f2p, _p2f, _f2a, _a2f, _f2z, _z2f):
        self.curr_round = 1
        self.todo = defaultdict(list)
        base.__init__(self, sid, pid, _a2f, _f2a, _z2f, _f2z, _p2f, _f2p)
        self.totalD = defaultdict(int)
        self.delta = 1

    def exec_in_o1(self, f, args=()):
        self.todo[self.curr_round+1].append( (f, args) )
        # tell adversary about: request, round, index in todo
        #self.f2a.write( ('exec',self.curr_round+1,len(self.todo[self.curr_round+1])-1) )
 
    def poll(self):
        if len(self.todo[self.curr_round]) == 0: dump.dump; return

        f,args = self.todo[self.curr_round].pop(0)
        f(*args)

        if len(self.todo[self.curr_round]) == 0:
            self.curr_round += 1
        # TODO: tell adversary of the round change? 

    def delay(self, oldr, newr, idx):
        if idx < len(self.todo[oldr]) and self.delta > 1:
            # TODO bound the delay
            task = self.todo[oldr].pop(idx)
            self.todo[newr].append( task )

    def get_round(self):
        return self.curr_round


    def party_msg(self, msg):
        print('Party message in the wrapper')
        # wrapper doesn't care about this
        base.party_msg(self, msg)

    def adv_msg(self, msg):
        if msg[0] == 'poll':
            pass
        elif msg[0] == 'delay':
            pass
        else:
            base.adv_msg(self, msg)

    def env_msg(self, msg):
        if msg[0] == 'poll':
            pass
        else:
            base.env_msg(msg)
return Syn_FWrapper
             
