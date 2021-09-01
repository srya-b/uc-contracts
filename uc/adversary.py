import gevent
from uc.itm import ITM, UCAdversary, GUCAdversary
from gevent.queue import Queue, Channel, Empty
from gevent.event import AsyncResult
from collections import defaultdict

class DummyAdversary(UCAdversary):
    '''Implementation of the dummy adversary. Doesn't do anything locally,
     just forwards all messages to the intended party. Z communicates with
    corrupt parties through dummy adversary'''
    def __init__(self, k, bits, crupt, sid, pid, channels, pump, poly, importargs):
        UCAdversary.__init__(self, k, bits, crupt, sid, pid, channels, poly, pump, importargs)
        self.env_msgs['A2F'] = self.a2f
        self.env_msgs['A2P'] = self.a2p
        
    
    def __str__(self):
        return str(self.F)

    def read(self, fro, msg):
        print(u'{:>20} -----> {}, msg={}'.format(str(fro), str(self), msg))

    def a2f(self, msg, iprime):
        self.write(
            ch='a2f',
            msg=msg,
            imp=iprime
        )

    def a2p(self, msg, iprime):
        self.write(
            ch='a2p',
            msg=msg,
            imp=iprime
        )

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


#class DummyWrappedAdversary(UCWrappedAdversary):
class DummyGUCAdversary(GUCAdversary):
    '''Implementation of the dummy adversary. Doesn't do anything locally,
     just forwards all messages to the intended party. Z communicates with
     corrupt parties through dummy adversary'''
    def __init__(self, k, bits, crupt, sid, pid, channels, pump, poly, importargs, gsid, ssids):
        #UCWrappedAdversary.__init__(self, k, bits, crupt, sid, pid, channels, poly, pump, importargs)
        GUCAdversary.__init__(self, k, bits, crupt, sid, pid, channels, poly, pump, importargs, gsid, ssids)
        self.env_msgs['A2F'] = self.a2f
        self.env_msgs['A2P'] = self.a2p
        self.env_msgs['A2F'] = self.a2g
    
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
    #def env_msg(self, d):
    #    msg = d.msg
    #    imp = d.imp
    #    if msg[0] == 'A2F':
    #        t,msg,iprime = msg
    #        self.write('a2f', msg, iprime )
    #    elif msg[0] == 'A2P':
    #        t,msg,iprime = msg
    #        self.write('a2p', msg, iprime )
    #    elif msg[0] == 'A2W':
    #        t,msg,iprime = msg
    #        self.write('a2w', msg, iprime )
    #    else: self.pump.write("dump")#dump.dump()
    
    def a2f(self, msg, iprime):
        self.write(
            ch='a2f',
            msg=msg,
            imp=iprime
        )

    def a2p(self, msg, iprime):
        self.write(
            ch='a2p',
            msg=msg,
            imp=iprime
        )

    def a2g(self, msg, iprime):
        self.write(
            ch='a2g',
            msg=msg,
            imp=iprime
        )

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

    def gfunc_msg(self, d):
        msg = d.msg
        imp = d.imp
        assert imp == 0
        self.channels['a2z'].write( ('G2A', msg) )

