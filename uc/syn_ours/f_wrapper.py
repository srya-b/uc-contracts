import gevent
from uc.itm import ITM, UCGlobalF
from collections import defaultdict
from numpy.polynomial.polynomial import Polynomial
import logging

log = logging.getLogger(__name__)

'''
This wrapper exists in the UC execution in both the real and ideal worlds
as a standalone ITM. In a way this can be seen as a functionality where 
it acts as a trusted third party that does what it is expected to do.

THe logic behind the wrapper is to enable synchronout communication in UC.
Recall from the original formulation of the UC framework, all communication 
is asynchronous. This means that the adversary can arbitrarily delay message
delivery between any two parties. Synchronous communication requires that 
message delay has a known upper bound. This means that the synchronous world
proceeds in rounds. 

The wrappers generalizes the idea of message delivery by instead allowing 
synchronous execution of code blocks. The protocol parties and funutonalities
can schedule codeblocks to be executed synchronously in the same way as a message
normally would be. The upper bound delay is added to the codeblock when 
scheduled but the adversary can control which round it executes the codeblock
with the ``exec'' call. The adversary can not have complete control over 
the execution of codeblocks and the progression of rounds so the environment
can try to advance the wrapper through ``poll''. Eventually the delay parameter
will reach 0 with enough ``poll'' calls causing the next codeblock to be popped
off the queue and executed. 

Party/Functionality Interface

-- ``schedule''   : this message by a party of a functionality comes with a 
                    codeblock to execute (in the form of a function and input
                    parameters), and the environment specified upper-bound on delay
                    delta. Scheduling a codeblock saves it to the ``todo'' list
                    which the maximum delay assinged by default. This means that new
                    codeblocks are automatically inserted into todo[curr_round + delta].
                    Additionally this increments a ``delay'' parameter.

-- ``clock-round'': the functionality just writes the current clock round back to the 
                    calling party.

-- ``call me''    : (party only) Part of a synchronous model is input completeness: every honest party
                    is able to give input in each round that it wants to. A party passes in a round
                    number, r, with the ``call-me'' message. The wrapper schedules the
                    caling party to be activated in round ``todo[curr_round + r]''

-- ``leak''       : there are two was of leaking information to the adversary:
                    1). directly write the leak onto the tape of the adverasry (activating it)
                    2). buffer the leaks in the functionality that the adversary can ask for
                    In this wrapper we opt for #2 simply because it simplifies protocols
                    and functionalities.

Adversary Interface

-- ``delay''      : There is a
-- 
'''
class Syn_FWrapper(UCGlobalF):
    def __init__(self, k, bits, crupt, sid, tag, channels, pump, poly, importargs):
        self.curr_round = 1
        self.delay = 0
        self.todo = { self.curr_round: [] }
        self.leaks = []
        # TODO keep the round here until something happens
        # alternate theory: the round won't change unless something exists todo
        # in future rounds
        #self.adv_callme(self.curr_round)
        self.total_queue_ever = 0
        UCGlobalF.__init__(self, k, bits, crupt, 'wrap', 'me', channels, poly, pump, importargs)
        self.handlers[self.channels['_2w']] = self._2w_msg

    def party_clock_round(self, sender):
        self.write( 'w2p', (sender, self.curr_round))

    def func_clock_round(self):
        self.write( 'w2f', self.curr_round )

    def print_todo(self):
        p_dict = {}
        for k in self.todo:
            o = []
            for sender, ch, f,args in self.todo[k]:
                #o.append((f.__name__, args))
                o.append((f, args))
            p_dict[k] = o
        print('\n\033[1m', str(p_dict), '\033[0m\n')

    def adv_callme(self, r):
        if r not in self.todo: self.todo[r] = []
        #self.todo[r].append( (lambda: self.w2a.write(('shoutout',)), ()) )
        #self.todo[r].append( (lambda: self.write('w2a', ('shoutout',)), ()) )
        self.todo[r].append( ('adv', 'w2a', 'shoutout', ()) )
        self.total_queue_ever += 1
        self.print_todo()
        self.delay += 1
        self.write('w2a', ('OK',))

    def _2wschedule(self, sender, f, args, delta, imp):
        log.debug('\033[1mFschedule\033[0m delta: {}, import: {}, sender: {}'.format(imp, delta, sender))
        # add to the runqueue
        if self.curr_round+delta not in self.todo:
            self.todo[self.curr_round + delta] = []
        self.todo[self.curr_round + delta].append( (sender, 'w2_', f,args) )
        self.total_queue_ever += 1
        log.debug('total_queue_ever: {}'.format(self.total_queue_ever))
        
        # leaks the schedule
        idx = len(self.todo[self.curr_round + delta])-1
        r = self.curr_round + delta
        self.leaks.append( (sender, ('schedule', r, idx, f), 0) )

        self.print_todo()
        # add to the delay and return control to sender
        self.delay += 1
        print('done scheduling')
        self.write('w2_', (sender, ('OK',)) )

    def fschedule(self, sender, f, args, delta, imp):
        log.debug('\033[1mFschedule\033[0m delta: {}, import: {}, sender: {}'.format(imp, delta, sender))
        # add to the runqueue
        if self.curr_round+delta not in self.todo:
            self.todo[self.curr_round + delta] = []
        self.todo[self.curr_round + delta].append( (sender, 'w2f', f,args) )
        self.total_queue_ever += 1
        log.debug('total_queue_ever: {}'.format(self.total_queue_ever))
        
        # leaks the schedule
        idx = len(self.todo[self.curr_round + delta])-1
        r = self.curr_round + delta
        self.leaks.append( (sender, ('schedule', r, idx, f), 0) )

        self.print_todo()
        # add to the delay and return control to sender
        self.delay += 1
        self.write('w2f', (sender, ('OK',)) )

    def pschedule(self, sender, f, args, delta):
        log.debug('\033[1mPschedule\033[0m {} {}'.format(sender, delta))
        # add to runqueue
        if self.curr_round+delta not in self.todo:
            self.todo[self.curr_round + delta] = []
        self.todo[self.curr_round + delta].append( (sender, 'w2p', f,args) )
        self.total_queue_ever += 1
        log.debug('total_queue_ever: {}'.format(self.total_queue_ever))

        # leak the schedule
        idx = len(self.todo[self.curr_round + delta])-1
        r = self.curr_round + delta
        self.leaks.append( (sender, ('schedule', r, idx, f), 0) )
    
        # add to delay and return control to sender
        self.delay += 1
        self.write('w2p', (sender, ('OK',)) )

    def adv_delay(self, t, imp):
        self.assertimp(imp, t)
        self.delay += t
        self.write('w2a', ('OK',) )

    def adv_execute(self, r, i):
        sender, ch, f,args = self.todo[r].pop(i)
        self.print_todo()
        if ch == 'w2a':
            self.write( ch, ('exec', f, args) )
        else:
            self.write( ch, (sender, ('exec', f, args)) )

    def next_round(self):
        rounds = self.todo.keys()
        for r in sorted(rounds):
            if r >= self.curr_round and len(self.todo[r])>0:
                return r
        return self.curr_round

    def leak(self, rch, sender, msg, imp):
        log.debug("Leaking information, sender={}, msg={}".format(sender, msg))
        self.leaks.append( (sender, msg, imp) )
        self.write( rch, (sender, ('OK',)) ) 

    def poll(self, imp):
        self.assertimp(imp, 1)
        print('f_wrapper:: poll message from z:: delay: {}'.format(self.delay))
        if self.delay > 0:
            self.delay -= 1
            self.write('w2a', ('poll',) )
        else:
            self.curr_round = self.next_round()
            r = self.curr_round
            if len(self.todo[r]): self.adv_execute(r, 0)
            else: self.pump.write("dump")#dump.dump()

    def clock_round(self, sender, channel):
        self.write( channel, (sender, ('round', self.curr_round)) )

    def env_msg(self, d):
        msg = d.msg
        imp = d.imp
        if msg[0] == 'poll':
            self.poll(imp)
        else:
            sender,msg = msg
            if msg[0] == 'schedule':
                self.pschedule(sender, msg[1], msg[2], msg[3], imp)
            else: self.pump.write("dump")

    def func_msg(self, d):
        msg = d.msg
        imp = d.imp
        sender,msg = msg
        if msg[0] == 'schedule':
            self.fschedule(sender, msg[1], msg[2], msg[3], imp)
        elif msg[0] == 'leak':
            self.leak( 'w2f', sender, msg[1], imp)
        elif msg[0] == 'clock-round':
            self.write( 'w2f', (sender, (('round', self.curr_round))) )
        else:
            print('dump')
            self.pump.write("dump")

    def _2w_msg(self, d):
        msg = d.msg 
        imp = d.imp
        sender,msg = msg
        
        if msg[0] == 'schedule':
            self._2wschedule(sender, msg[1], msg[2], msg[3], imp)
        else:
            self.pump.write('')

    # TODO revisit this to see if adversary can delay callme actions
    def party_callme(self, r):
        if r not in self.todo: self.todo[r] = []
        #self.todo[r].append( (lambda: self.w2a.write(('shotout',)), ()) )
        self.todo[r].append( (lambda: self.write('w2a', ('shotout',)), ()) )
        #self.w2p.write( ('OK',) )
        self.write('w2p', ('OK',) )

    def party_msg(self, d):
        msg = d.msg
        imp = d.imp
        sender,msg = msg
        if msg[0] == 'schedule':
            self.pschedule(msg[1], msg[2], msg[3])
        elif msg[0] == 'clock-round':
            self.clock_round(sender, 'w2p')
        elif msg[0] == 'callme':
            self.party_callme(sender)
        elif msg[0] == 'leak':
            self.leak( 'w2p', sender, msg, imp)
        else:
            #dump.dump()
            self.pump.write("dump")
    def adv_get_leaks(self):
        total_import = 0
        output = []
        for leak in self.leaks:
            sender,msg,imp = leak
            total_import += imp
            output.append( (sender, msg, imp) )
        #self.channels['w2a'].write( output, total_import )
        self.write( 'w2a', output, total_import )
        self.leaks = []

    def adv_msg(self, d):
        msg = d.msg
        imp = d.imp
        #print('msg', msg)
        if msg[0] == 'delay':
            self.adv_delay(msg[1], imp)
        elif msg[0] == 'exec':
            self.adv_execute(msg[1], msg[2])
        elif msg[0] == 'callme':
            self.adv_callme(msg[1])
        elif msg[0] == 'get-leaks':
            self.adv_get_leaks()
        else:
            self.pump.write("dump")

