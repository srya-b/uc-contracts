from ast import literal_eval
from uc.itm import GenChannel, wrapwrite
from uc.functionality import UCFunctionality
from uc.protocol import UCProtocol
import logging, gevent

log = logging.getLogger(__name__)

def bangF(f):
    def _f(k, bits, crupt, sid, channels, pump):
        return Bang_F(k, bits, crupt, sid, channels, pump, f)
    return _f

class Bang_F(UCFunctionality):
    def __init__(self, k, bits, crupt, sid, channels, pump, f):
        UCFunctionality.__init__(self, k, bits, crupt, sid, channels, pump)

        self.f = f

        self.p2f_channels = {}
        self.f2p_channels = {}
        self.a2f_channels = {}
        self.f2a_channels = {}

    def newssid(self, ssid):
        _p2f = GenChannel('p2ssid')
        _a2f = GenChannel('a2ssid')

        _f2p = wrapwrite( self.channels['f2p'], lambda x: (x[0], (ssid, x[1])) )
        _f2a = wrapwrite( self.channels['f2a'], lambda x: (x[0], (ssid, x[1])) )
    
        self.p2f_channels[ssid] = _p2f
        self.f2p_channels[ssid] = _f2p
        self.a2f_channels[ssid] = _a2f
        self.f2a_channels[ssid] = _f2a

        _f = self.f(self.k, self.bits, self.crupt, ssid, {'p2f': _p2f, 'f2p': _f2p, 'a2f': _a2f, 'f2a': _f2a}, self.pump)
        gevent.spawn(_f.run)

    def get_channel(self, _2ssid, ssid):
        if ssid in _2ssid: return _2ssid[ssid]
        else:
            self.newssid(ssid)
            return _2ssid[ssid]

    def party_msg(self, m):
        sender,(ssid,msg) = m
        p2ssid_chan = self.get_channel(self.p2f_channels, ssid)
        p2ssid_chan.write( (sender, msg) )

    def adv_msg(self, m):
        ssid,msg = m
        a2ssid_chan = self.get_channel(self.a2f_channels, ssid)
        a2ssid_chan.write( msg )


def bangP(p):
    def _p(k, bits, crupt, sid, pid, channels, pump):
        return Bang_P(k, bits, crupt, sid, pid, channels, pump, p)
    return _p

class Bang_P(UCProtocol):
    def __init__(self, k, bits, sid, pid, channels, pump, p):
        UCProtocol.__init__(self, k, bits, crupt, sid, pid, channels, pump)

        self.p = p

        self.z2p_channels = {}
        self.p2z_channels = {}
        self.p2f_channels = {}
        self.f2p_channels = {}

    def newssid(self, ssid):
        _z2p = GenChannel('z2ssid')
        _f2p = GenChannel('f2ssid')

        _p2z = wrapwrite( self.channels['p2z'], lambda x: (x[0], (ssid, x[1])) )
        _p2f = wrapwrite( self.channels['p2f'], lambda x: (x[0], (ssid, x[1])) )
    
        self.z2p_channels[ssid] = _z2p
        self.p2z_channels[ssid] = _p2z
        self.p2a_channels[ssid] = _p2f
        self.f2p_channels[ssid] = _f2p

        _p = self.p(self.k, self.bits, ssid, self.pid, {'p2f': _p2f, 'f2p': _f2p, 'a2f': _a2f, 'f2a': _f2a}, self.pump)
        gevent.spawn(_f.run)

    def get_channel(self, _2ssid, ssid):
        if ssid in _2ssid: return _2ssid[ssid]
        else:
            self.newssid(ssid)
            return _2ssid[ssid]

    def env_msg(self, m):
        ssid,msg = m
        z2ssid_chan = self.get_channel(self.z2p_channels, ssid)
        z2ssid_chan.write( msg )

    def func_msg(self, m):
        ssid,msg = m
        f2ssid_chan = self.get_channel(self.f2p_channels, ssid)
        f2ssid_chan.write( msg )


#class Prot_Squash(UCProtocol):
#    def __init__(self, k, bits, sid, pid, channels, pump):
#        UCProtocol.__init__(self, k, bits, crupt, sid, pid, channels, pump)
#        
#    
#    def env_msg(self, msg):
#        ssid1,(ssid2, msg) = msg
#        ssid3 = str((ssid1, ssid2[0]))
#        sid3 = ssid2[1]
#        self.write(ch='p2f', msg=((ssid3, sid3), msg))
#
#    def func_msg(self, msg):
#        ssid3,msg = msg
#        (ssid1, ssid20),sid3 = literal_eval(ssid3)
#        ssid = (ssid20, sid3)
#        self.write(ch='p2z', msg=(ssid1, (ssid, msg)))
    
         
