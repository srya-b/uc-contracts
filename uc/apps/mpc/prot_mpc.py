import os 
from ast import literal_eval
from uc import UCProtocol
from uc.utils import waits, wait_for
from poly import eval_poly

def MPC_Prot(mult_prog):
    def _p(k, bits, sid, pid, channels, pump):
        return _MPC_Prot(k, bits, sid, pid, channels, mult_prog, pump)
    return _p

def get_triple(_op):
    OpOutput,r = _op( ('RAND',) )
    a,b,ab = r
    return a,b,ab

def open_share(sh, _op):
    OpOutput,mp = _op( ('OPEN', sh) )
    return eval_poly(mp, 0)

def constant(v, _op):
    OpOutput,rsp = _op( ('CONST', v) )
    return rsp

def lin(xs, _op):
    OpOutput,rsp = _op( ('LIN', xs) )
    return rsp

def sub(x, a, _op):
    return lin( [(1,x), (-1,a)], _op)

def mpc_beaver(x, y, _op):
    a,b,ab = get_triple(_op)
    d = open_share( sub(x,a,_op), _op )
    e = open_share( sub(y,b,_op), _op )
    de = constant (d*e, _op)
    xy = lin( [(1,de),(1,ab),(d,b),(e,a)], _op )
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
        #self.env_msgs['myshare'] = self.env_myshare

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
            if m[0] == 'OpRes' or m[0] == 'OpOutput':
                self.commit( (op,args), m[1])
            else: self.commit( (op,args), m)

    def env_log(self):
        self.write('p2z', ('Log', self.log)) 
