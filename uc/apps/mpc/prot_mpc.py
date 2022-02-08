import os 
from ast import literal_eval
from uc import UCProtocol
from uc.utils import waits, wait_for

def MPC_Prot(mult_prog):
    def _p(k, bits, sid, pid, channels, pump):
        return _MPC_Prot(k, bits, sid, pid, channels, mult_prog, pump)
    return _p

def get_triple(_op):
    r = _op( ('RAND',) )
    a,b,ab = r
    return a,b,ab

def open_share(sh, _op):
    mp = _op( ('OPEN', sh) )
    return eval_poly(mp, 0)

def constant(v, _op):
    rsp = _op( ('CONST', v) )
    return rsp

def lin(xs, _op):
    rsp = _op( ('LIN', xs) )
    return rsp

def mpc_beaver(x, y, _op):
    a,b,ab = get_triple(_op)
    d = open_share( x - a )
    e = open_share( y - b )
    de = constant (d*e)
    xy = lin( [(1,de),(1,ab),(d,b),(e,a)] )
    return xy

class _MPC_Prot(UCProtocol):
    def __init__(self, k, bits, sid, pid, channels, mult_prog, pump):
        UCProtocol.__init__(self, k, bits, sid, pid, channels, pump)
        self.ssid, sid = sid
        sid = literal_eval(sid)
        self.n = sid[0]
        self.input_party = sid[1]

        self.mult_prog = mult_prog
        self.log = []

        self.env_msgs['op'] = self.env_op
        self.env_msgs['log'] = self.env_log

    def _op(self, opcode):
        m = self.write_and_wait_for('p2f', ('op', opcode), 'f2p')
        return m

    def commit(self, opcode, res):
        self.log += [(opcode,res)]
        self.write('p2z', ('OpOutput',res)) 

    def env_op(self, op):
        op,args = op
        if op == 'MULT':
            x,y = args
            xy = self.mult_prog(x, y, self._op)
            self.commit( ('MULT',(x,y)), xy )
        else:
            m = self.write_and_wait_for('p2f', ('op', (op, args)), 'f2p')
            self.commit( (op,args), m)

    def env_log(self):
        self.pump.write('')
