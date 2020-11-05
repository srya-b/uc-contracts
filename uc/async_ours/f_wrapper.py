import dump
import gevent
from itm import ITM, UCWrapper
from collections import defaultdict
from numpy.polynomial.polynomial import Polynomial
import logging

log = logging.getLogger(__name__)

class Async_FWrapper(UCWrapper):
    def __init__(self, channels, pump, poly, importargs):
        self.curr_round = 1
        self.delay = 0
        self.leaks = []
        self.todo = []
        self.pump = pump
        # TODO keep the round here until something happens
        # alternate theory: the round won't change unless something exists todo
        # in future rounds
        #self.adv_callme(self.curr_round)
        self.total_queue_ever = 0
        UCWrapper.__init__(self, 'wrap', 'me', channels, poly, importargs)

    def party_clock_round(self, sender):
        self.write( 'w2p', (sender, self.curr_round))

    def print_todo(self):
        p_dict = [(f.__name__,args) for f,args in self.todo]
        print('\n\033[1m', str(p_dict), '\033[0m\n')

    def fschedule(self, sender, f, args, imp):
        log.debug('\033[1mFschedule\033[0m import: {}, sender: {}'.format(imp, sender))
        # add to the runqueue
        self.todo.append( (f,args) )
        self.total_queue_ever += 1
        log.debug('total_queue_ever: {}'.format(self.total_queue_ever))
        
        # leaks the schedule
        idx = len(self.todo)-1
        self.leaks.append( (sender, ('schedule', idx, f.__name__), 0) )

        self.print_todo()
        # add to the delay and return control to sender
        self.delay += 1
        self.write('w2f', (sender, ('OK',)) )

    def pschedule(self, sender, f, args):
        log.debug('\033[1mPschedule\033[0m {}'.format(sender))
        # add to runqueue
        self.todo.append( (f,args) )
        self.total_queue_ever += 1
        log.debug('total_queue_ever: {}'.format(self.total_queue_ever))

        # leak the schedule
        idx = len(self.todo)-1
        self.leaks.append( (sender, ('schedule', idx, f.__name__), 0) )
    
        # add to delay and return control to sender
        self.delay += 1
        self.write('w2p', (sender, ('OK',)) )

    def adv_delay(self, t, imp):
        self.assertimp(imp, t)
        self.delay += t
        self.write('w2a', "OK" )

    def adv_execute(self, i):
        self.print_todo()
        print('i', i)
        f,args = self.todo.pop(i)
        self.print_todo()
        f(*args)

    def leak(self, sender, msg, imp):
        log.debug("Leaking information, sender={}, msg={}".format(sender, msg))
        self.leaks.append( (sender, msg, imp) )

    def poll(self, imp):
        self.assertimp(imp, 1)
        if self.delay > 0:
            self.delay -= 1
            self.write('w2a', ('poll',) )
        else:
            if len(self.todo): self.adv_execute(0)
            else: self.pump.write("dump")

    def env_msg(self, d):
        msg = d.msg
        imp = d.imp
        if msg[0] == 'poll':
            self.poll(imp)
        else:
            self.pump.write("dump")

    def func_msg(self, d):
        msg = d.msg
        imp = d.imp
        sender,msg = msg
        if msg[0] == 'schedule':
            self.fschedule(sender, msg[1], msg[2], imp)
        elif msg[0] == 'leak':
            self.leak(sender, msg[1], imp)
        else:
            self.pump.write("dump")

    # TODO revisit this to see if adversary can delay callme actions
    def party_callme(self):
        self.todoappend( (lambda: self.write('w2a', ('shotout',)), ()) )
        self.write('w2p', ('OK',) )

    def party_msg(self, d):
        msg = d.msg
        imp = d.imp
        sender,msg = msg
        if msg[0] == 'schedule':
            self.pschedule(msg[1], msg[2])
        elif msg[0] == 'callme':
            self.party_callme()
        elif msg[0] == 'leak':
            self.leak(sender, msg, imp)
        else:
            self.pump.write("dump")

    def adv_callme(self):
        self.todoappend( (lambda: self.write('w2a', ('shoutout',)), ()) )
        self.write('w2a', ('OK',) )

    def adv_get_leaks(self):
        total_import = 0
        output = []
        for leak in self.leaks:
            sender,msg,imp = leak
            total_import += imp
            output.append( (sender, msg, imp) )
        self.write( 'w2a', output, total_import )
        self.leaks = []

    def adv_msg(self, d):
        msg = d.msg
        imp = d.imp
        #print('msg', msg)
        if msg[0] == 'delay':
            self.adv_delay(msg[1], imp)
        elif msg[0] == 'exec':
            self.adv_execute(msg[1])
        elif msg[0] == 'callme':
            self.adv_callme()
        elif msg[0] == 'get-leaks':
            self.adv_get_leaks()
        else:
            self.pump.write("dump")

