import comm
import gevent
from itm import ITM, UCAdversary, UCWrappedAdversary
from gevent.queue import Queue, Channel, Empty
from gevent.event import AsyncResult

class DummyAdversary(UCAdversary):
    '''Implementation of the dummy adversary. Doesn't do anything locally,
     just forwards all messages to the intended party. Z communicates with
    corrupt parties through dummy adversary'''
    # TODO Dummy tracks v = in - (out + lengths of all inputs) halt if
    #      v < k
    def __init__(self, k, bits, crupt, sid, pid, channels, pump, poly, importargs):
        UCAdversary.__init__(self, k, bits, crupt, sid, pid, channels, poly, pump, importargs)
    
    def __str__(self):
        return str(self.F)

    def read(self, fro, msg):
        print(u'{:>20} -----> {}, msg={}'.format(str(fro), str(self), msg))

    def env_msg(self, d):
        msg = d.msg
        imp = d.imp
        if msg[0] == 'A2F':
            t,msg,iprime = msg
            self.write('a2f', msg, iprime )
        elif msg[0] == 'A2P':
            t,msg,iprime = msg
            self.write('a2p', msg, iprime )
        else: 
            self.pump.write("dump")

    def party_msg(self, d):
        msg = d.msg
        imp = d.imp
        assert imp == 0
        self.channels['a2z'].write( ('P2A', msg) )

    def func_msg(self, d):
        msg = d.msg
        imp = d.imp
        assert imp == 0
        self.channels['a2z'].write( ('F2A', msg) )


class DummyWrappedAdversary(UCWrappedAdversary):
    '''Implementation of the dummy adversary. Doesn't do anything locally,
     just forwards all messages to the intended party. Z communicates with
     corrupt parties through dummy adversary'''
    def __init__(self, k, bits, crupt, sid, pid, channels, pump, poly, importargs):
        UCWrappedAdversary.__init__(self, k, bits, crupt, sid, pid, channels, poly, pump, importargs)
    
    def __str__(self):
        return str(self.F)

    def read(self, fro, msg):
        print(u'{:>20} -----> {}, msg={}'.format(str(fro), str(self), msg))

    '''
        Messages from the environment inteded for the dummy address can 
        carry import and also specify in the message body how much import 
        to forward with the message being sent. Dummy adversary as specified
        in the UC paper accepts messages of the form (i, (msg, ..., i')) where 
        i is the import sent to the dummy and i' is the import to be sent by
        the dummy to other parties.
    '''
    def env_msg(self, d):
        msg = d.msg
        imp = d.imp
        if msg[0] == 'A2F':
            t,msg,iprime = msg
            self.write('a2f', msg, iprime )
        elif msg[0] == 'A2P':
            t,msg,iprime = msg
            self.write('a2p', msg, iprime )
        elif msg[0] == 'A2W':
            t,msg,iprime = msg
            self.write('a2w', msg, iprime )
        else: self.pump.write("dump")#dump.dump()

    def party_msg(self, d):
        msg = d.msg
        imp = d.imp
        assert imp == 0
        self.channels['a2z'].write( ('P2A', msg) )

    def func_msg(self, d):
        msg = d.msg
        imp = d.imp
        assert imp == 0
        self.channels['a2z'].write( ('F2A', msg) )

    def wrapper_msg(self, d):
        msg = d.msg
        imp = d.imp
        assert imp == 0
        self.channels['a2z'].write( ('W2A', msg) )

