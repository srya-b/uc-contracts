import dump
from itm import ITMFunctionality

class Syn_Bracha_Functionality(ITMFunctionality):
    def __init__(self, sid, pid, _a2f, _f2a, _z2f, _f2z, _p2f, _f2p):
        self.ssid = sid[0]
        self.parties = sid[1]
        self.f2p = _f2p; self.p2f = _p2f
        self.f2a = _f2a; self.a2f = _a2f
        self.f2z = _f2z; self.z2f = _z2f

        channels = [_a2f, _z2f, _p2f]
        handlers = {
            _a2f: self.adv_msg,
            _p2f: self.party_msg,
            _z2f: self.env_msg,
        }
        ITMFunctionality.__init__(self, sid, pid, channels, handlers)

    
    def exec_in_o1(self, *args):
        raise Exception("'send_in_o1' unimpemented. A wrapper must derive this functionality and implement this function.")

    def exec_in_oD(self, delta, *args):
        raise Exception("'send_in_oD' unimpemented. A wrapper must derive this functionality and implement this function.")

    def send_output(self, to, msg):
        self.f2p.write( (to, msg) )

    '''Dealer, assumed to be pid=1 gives some input and invokes
    the synchronous wrapper around it to deliver the output to all
    of the parties in O(1) time.'''
    def party_input(self, pid, inp):
        if pid == 1:
            for p in self.parties:
                self.exec_in_o1(self.send_output, (p,))
        dump.dump() 

    def party_msg(self, msg):
        print('Party msg in bracha')
        sender,msg = msg
        sid,pid = sender
        if msg[0] == 'input':
            self.party_input(pid, msg[1])
        elif msg[0] == 'output':
            self.party_output(pid)
        else: dump.dump()

    def adv_msg(self, msg):
        dump.dump()
    def env_msg(self, msg):
        dump.dump()

