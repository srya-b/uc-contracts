from collections import defaultdict

global commap
global corrupted
global itmmap
global adversary

commap = {}
itmmap = {}
adversary = None
corrupted = defaultdict(bool)


FUNCTIONALITY = 0
PARTY = 1
ADVERSARY = 2
SIMULATOR = 3

def cset(sid,pid,tag,itm):
    if (sid,pid) not in commap:
        commap[sid,pid] = tag
        itmmap[sid,pid] = itm
def cset2(sid,pid,tag):
    if (sid,pid) not in commap:
        commap[sid,pid] = tag

def isf(sid,pid):
    try:
        return commap[sid,pid] == FUNCTIONALITY
    except KeyError:
        return False

def isadversary(sid,pid):
    try:
        return commap[sid,pid] == ADVERSARY
    except KeyError:
        return False

def isparty(sid,pid):
    try:
        return commap[sid,pid] == PARTY
    except KeyError:
        return False

def getitm(sid,pid):
    try:
        return itmmap[sid,pid]
    except KeyError:
        return None

def itmstring(sid,pid):
    try:
        return str(getitm(sid,pid))
    except:
        return ''

def setAdversary(itm):
    global adversary
    sid,pid = itm.sid,itm.pid
    cset(sid,pid,ADVERSARY,itm)
    adversary = itm
    #print('ADVERSARY', sid, pid)

def setFunctionality(itm):
    sid,pid = itm.sid,itm.pid
    cset(sid,pid,FUNCTIONALITY,itm)
    #print('FUNCTIONALITY', sid, pid)

def setFunctionality2(sid,pid):
    cset2(sid,pid,FUNCTIONALITY)

def setParty(p):
    sid,pid = p.sid,p.pid
    cset(sid,pid,PARTY,p)
    #print('PARTY', sid, pid)

def setParties(parties):
    for p in parties:
        setParty(p)

def corrupt(sid,pid):
    global corrupted
    corrupted[sid,pid] = True

def isdishonest(sid,pid):
    global corrupted
    return corrupted[sid,pid]

def ishonest(sid,pid):
    global corrupted
    return not corrupted[sid,pid]

def id2input(self, identifier):
    global itmmap
    return itmmap[identifier].input

def id2backdoor(self, identifier):
    global itmmap
    return itmmap[identifier].backdoor
    

import dump
import gevent
from gevent.event import AsyncResult, Event
from gevent.queue import Queue, Channel, Empty

'''
There are 2 options with channels:
    1. The channels are greenlets themselves where they wait for
        the AsyncResult to be set and then write the result to the
        input of the 'to' itm. However, the channel itself needs
        to be the input to the itm, otherwise there's just an extra
        layer that ads another call to it.
    2. Calling 'write' on the channel writes to the input tape of the
        'to' itm. This allows the same interface for the party that's
        writing, but the recipient can be someone different. If the
        simulator want to run a sandbox of the adversary, then the 
        desired construction is that all channels connect to the 
        simulator and the simulator can control the output messages
        to the actual intended recipient.

Design Decision:
    * Instead 'to' and 'fro' will be just identifiers of the form
        (sid,pid). Having 'to' be the AsyncResult itself means the 
        code will still be at the mercy of having to spawn itms
        in a specific order based on the protocol at hand. Which
        really blows.
    * Can't be ^ (above) either. If 'to' is the identifier and the
        itm is got from 'comm' then you're fucked because you have 
        to fake an identifier and register is in 'comm' for the 
        simulator to be able to sandbox run the adversary and
        intercept outputs.
    * Actually, shit the channel has to be the AsyncResult itself
        that's the only way. That's the way it was the first time
        idk how I convinced myself to change it. rip
'''
class GenChannel(Event):
    def __init__(self, i=-1):
        Event.__init__(self)
        self._data = None
        self.i = i

    def write(self,data):
        if not self.is_set():
            #print('\033[93m \t\tWriting {} id={}\033[0m'.format(data,self.i))
            self._data = data; self.set()
        else: 
            raise Exception("\033[1mwriting to channel already full. Writing {} in {}\033[0m".format(data,self.i))
            dump.dump()

    def read(self): 
        #print('\033[91m Reading message: {} id={}\033[0m'.format(self._data,self.i)); 
        return self._data
    def reset(self, s=''): 
        #print('\033[1m Resetting id={}, string={}\033[0m'.format(self.i,s)); 
        self.clear()

class Channel(Event):
    def __init__(self, to, fro):
        Event.__init__(self)
        self.to = to; self.fro = fro
        self._data = None

    def _write(self, data):
        self._data = data; self.set()
    def read(self): return self._data
    def reset(self): self.clear()

class Many2FChannel(Event):
    def __init__(self, to):
        Event.__init__(self)
        self.to = to
        self._data = None
    def _write(self, data):
        self._data = data; self.set()
    def read(self): return self._data
    def reset(self): self.clear()

class M2F():
    def __init__(self, fro,  m2f):
        self.m2f = m2f
        self.fro = fro
    def write(self, data): self.m2f._write( (self.fro, True, data) )


class P2F(Channel):
    def __init__(self, *args): Channel.__init__(self, *args)
    def write(self, data): self._write( (self.fro, True, data) ) 
   
class Z2P(Channel):
    def __init__(self, *args): Channel.__init__(self, *args)
    def write(self, data): self._write( data )

class Z2A(Channel):
    def __init__(self, *args): Channel.__init__(self, *args)
    def write(self, data): self._write( data )

class A2P(Channel):
    def __init__(self, *args): Channel.__init__(self, *args)
    def write(self, data): self._write( data )

class P2G(Channel):
    def __init__(self, *args): Channel.__init__(self, *args)
    def write(self, data): self._write( (self.fro, True, (True, data)) )

class F2G(Channel):
    def __init__(self, *args): Channel.__init__(self, *args)
    def write(self, data): self._write( (self.fro, True, data) ) 

class A2G(F2G):
    def __init__(self, *args): Channel.__init__(self, *args)

class A2P(Channel):
    def __init__(self, *args): Channel.__init__(self, *args)
    def write(self, data): self._write(data)
    
class F2P(Channel):
    def __init__(self, *args): Channel.__init__(self, *args)

#class Channel(object):
#    '''
#        'to': identity of receiving party
#        'fro': Simply the identity of the writing party.
#                Furthermore, a channel can only be written to
#                by the correct party, not just anyone.
#    '''
#    def __init__(self, to, fro):
#        self.to = to
#        self.fro = fro
#        self._data = AsyncResult()
#
#class P2F(Channel):
#    def __init__(self, *args):
#        Channel.__init__(self, *args)
#
#    def write(self, data):
#        print('DEBUG: Writing {} ==> {}'.format(self.fro,self.to))
#        id2input(self.to).set( (self.fro, True, data) )
#
#class P2G(Channel):
#    ''' See comments above '''
#    def __init__(self, *args):
#        Channel.__init__(self, *args)
#
#    def write(self, data):
#        print('DEBUG: Writing {} ==> {}'.format(self.fro,self.to))
#        id2input(self.to).set( (self.fro, True, (True, data)) )
#
#class F2G(Channel):
#    ''' See above '''
#    def __init__(self, *args):
#        Channel.__init__(*args)
#
#    def write(self, data):
#        x,y = data
#        assert type(x) == bool
#        assert type(y) == tuple
#        id2input(self.to).set( (self.fro, True, data) )
#
#class A2G(F2G):
#    def __init__(self, *args):
#        F2G.__init__(self, *args)
#
#    def write(self, data):
#        x,y = data
#        assert type(x) == bool 
#
#class A2P(Channel):
#    def __init__(self, *args):
#        F2G.__init__(self, *args)
#    
#class F2P(Channel):
#    def __init__(self, *args):
#        Channel.__init__(self, *args)
