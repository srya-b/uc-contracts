import dump
import gevent
from itm import ITM, UCWrapper
from collections import defaultdict
from numpy.polynomial.polynomial import Polynomial
import logging

log = logging.getLogger(__name__)

class Syn_FWrapper(UCWrapper):
    def __init__(self, channels, pump, poly):
        self.curr_round = 1
        self.delay = 0
        self.todo = { self.curr_round: [] }
        self.leaks = []
        self.pump = pump
        # TODO keep the round here until something happens
        # alternate theory: the round won't change unless something exists todo
        # in future rounds
        #self.adv_callme(self.curr_round)
        self.total_queue_ever = 0
        UCWrapper.__init__(self, 'wrap', 'me', channels, poly)

    def party_clock_round(self, sender):
        self.write( 'w2p', (sender, self.curr_round))

    def print_todo(self):
        p_dict = {}
        for k in self.todo:
            o = []
            for f,args in self.todo[k]:
                o.append((f.__name__, args))
            p_dict[k] = o
        print('\n\033[1m', str(p_dict), '\033[0m\n')

    def fschedule(self, sender, f, args, delta, imp):
        log.debug('\033[1mFschedule\033[0m delta: {}, import: {}, sender: {}'.format(imp, delta, sender))
        #print('\t\t f_name={}, args={}, delta={}'.format(f.__name__, args, delta))
        # add to the runqueue
        if self.curr_round+delta not in self.todo:
            self.todo[self.curr_round + delta] = []
        self.todo[self.curr_round + delta].append( (f,args) )
        self.total_queue_ever += 1
        log.debug('total_queue_ever: {}'.format(self.total_queue_ever))
        
        # leaks the schedule
        idx = len(self.todo[self.curr_round + delta])-1
        r = self.curr_round + delta
        self.leaks.append( (sender, ('schedule', r, idx, f.__name__), 0) )

        # add to the delay and return control to sender
        self.delay += 1
        #print('\t\033[92m[fschdeule] new delay\033[0m', self.delay)
        self.w2f.write( (sender, ('OK',)) )

    def pschedule(self, sender, f, args, delta):
        log.debug('\033[1mPschedule\033[0m {} {}'.format(sender, delta))
        # add to runqueue
        if self.curr_round+delta not in self.todo:
            self.todo[self.curr_round + delta] = []
        self.todo[self.curr_round + delta].append( (f,args) )
        self.total_queue_ever += 1
        log.debug('total_queue_ever: {}'.format(self.total_queue_ever))

        # leak the schedule
        idx = len(self.todo[self.curr_round + delta])-1
        r = self.curr_round + delta
        self.leaks.append( (sender, ('schedule', r, idx, f.__name__), 0) )
    
        # add to delay and return control to sender
        self.delay += 1
        self.w2p.write( (sender, ('OK',)) )

    def adv_delay(self, t):
        self.delay += t
        self.w2a.write( "OK" )

    def adv_execute(self, r, i):
        f,args = self.todo[r].pop(i)
        f(*args)

    def next_round(self):
        rounds = self.todo.keys()
        for r in sorted(rounds):
            if r >= self.curr_round and len(self.todo[r])>0:
                return r
        return self.curr_round

    def leak(self, sender, msg, imp):
        log.debug("Leaking information, sender={}, msg={}".format(sender, msg))
        self.leaks.append( (sender, msg, imp) )

    def poll(self):
        if self.delay > 0:
            self.delay -= 1
            self.w2a.write( ('poll',) )
        else:
            print('\n\nPoll executing a codeblock')
            print('round={}'.format(self.curr_round))
            self.print_todo()
            self.curr_round = self.next_round()
            r = self.curr_round
            print('new round={}'.format(r))
            if len(self.todo[r]): self.adv_execute(r, 0)
            else: self.pump.write("dump")#dump.dump()

    def clock_round(self, sender, channel):
        channel.write( (sender, ('round',self.curr_round)) )

    def env_msg(self, d):
        msg = d.msg
        imp = d.imp
        if msg[0] == 'poll':
            self.poll()
        else:
            self.pump.write("dump")

    def func_msg(self, d):
        msg = d.msg
        imp = d.imp
        sender,msg = msg
        if msg[0] == 'schedule':
            self.fschedule(sender, msg[1], msg[2], msg[3], imp)
        elif msg[0] == 'leak':
            self.leak(sender, msg[1], imp)
        else:
            #dump.dump()
            self.pump.write("dump")

    # TODO revisit this to see if adversary can delay callme actions
    def party_callme(self, r):
        if r not in self.todo: self.todo[r] = []
        self.todo[r].append( (lambda: self.w2a.write(('shotout',)), ()) )
        self.w2p.write( ('OK',) )

    def party_msg(self, d):
        msg = d.msg
        imp = d.imp
        sender,msg = msg
        if msg[0] == 'schedule':
            self.pschedule(msg[1], msg[2], msg[3])
        elif msg[0] == 'clock-round':
            self.clock_round(sender, self.w2p)
        elif msg[0] == 'callme':
            self.party_callme(sender)
        elif msg[0] == 'leak':
            self.leak(sender, msg, imp)
        else:
            #dump.dump()
            self.pump.write("dump")

    def adv_callme(self, r):
        if r not in self.todo: self.todo[r] = []
        self.todo[r].append( (lambda: self.w2a.write(('shoutout',)), ()) )
        self.w2a.write( ('OK',) )

    def adv_get_leaks(self):
        total_import = 0
        output = []
        for leak in self.leaks:
            sender,msg,imp = leak
            total_import += imp
            output.append( (sender, msg, imp) )
        self.channels['w2a'].write( output, total_import )
        self.leaks = []

    def adv_msg(self, d):
        msg = d.msg
        imp = d.imp
        #print('msg', msg)
        if msg[0] == 'delay':
            self.adv_delay(msg[1])
        elif msg[0] == 'exec':
            self.adv_execute(msg[1], msg[2])
        elif msg[0] == 'callme':
            self.adv_callme(msg[1])
        elif msg[0] == 'get-leaks':
            self.adv_get_leaks()
        else:
            #dump.dump()
            self.pump.write("dump")

