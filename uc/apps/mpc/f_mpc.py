from ast import literal_eval
from uc import UCFunctionality
from uc.utils import read_one, read
import sys
import logging
from poly import F53, randomWithZero, polyFromCoeffs
from collections import defaultdict

log = logging.getLogger(__name__)

opcodes = [
    'INPUT',
    'OPEN',
    'LIN',
    'CONST',
    'MULT',
    'RAND'
]

def do_mpc_op(has_mult, read_sharing, store_fresh, inputs, op, t, itm):
    op,args = op
    print('this is the op', op)
    if op == 'MULT':
        x,y = args
        print('its a MULT')
        if has_mult:
            print('has_mult: {}'.format(has_mult))
            xphi = read_sharing(x)
            yphi = read_sharing(y)
            phi = randomWithZero(t, x*y, itm)
            print('x', xphi)
            print('y', yphi)
            print('x*y', x*y)
            xy = store_fresh(phi)
            return xy
        else: raise Exception("no MULT")
    #elif op == 'LIN':
    elif op == 'OPEN':
        k = args
        phi = read_sharing(k)
        return phi
    elif op == 'CONST': 
        v = args
        #phi = polyFromCoeffs([v])
        phi = polyFromCoeffs([v])
        print('\npoly from coeffs: {}\n'.format(phi))
        k = store_fresh(phi)
        print('\nreturn k: {}\n'.format(k))
        return k
    #elif op == 'RAND':
    #elif op == 'INPUT':
    else:
        raise Exception("Not a real opcode: {}".format(op))



class fMPC_(UCFunctionality):
    def __init__(self, k, bits, crupt, sid, channels, pump):
        UCFunctionality.__init__(self, k, bits, crupt, sid, channels, pump)
        self.ssid = sid[0]
        sid = literal_eval(sid[1])
        self.n = sid[0]
        self.input_party = sid[1]

        self.has_mpc = True
        self.has_mult = True


        # log of operations and results
        self.ops = []

        # inputs provided by the input party
        self.inputs = []  # [Fq]

        # Maps share IDs to secrets
        # -- In MPC mode, these will be degree-t polys , in
        # -- ABB mode they will only be constant (degree-0)
        # self.share_table = {}
        self.share_table = defaultdict(lambda: None)

        # fresh handle
        self.freshCtr = 0

        # counters views by each of the parties
        self.initCtrs = [ (i,0) for i in range(self.n) ]
        self.counters = dict(self.initCtrs)

        self.party_msgs['log'] = self.party_log
        self.party_msgs['input'] = self.party_input
        self.party_msgs['op'] = self.party_op
        self.party_msgs['myshare'] = self.party_myshare

    def fresh(self):
        x = self.freshCtr
        self.freshCtr += 1
        return x

    def commit(self, op, outp):
        self.ops.append( (op, outp) )
        self.write( 'f2p', (self.input_party, ('OpOutput', outp)) )

    def party_op(self, sender, op):
        if sender == self.input_party and self.has_mpc:
            print('party op', op)
            def _storeFresh(phi):
                sh = self.fresh()
                self.share_table[sh] = phi
                return sh
            def _readSharing(sh):
                return self.share_table[sh]
            result = do_mpc_op(self.has_mult, _readSharing, _storeFresh, self.inputs, op, 1, self)
            self.commit(op, result)
        else:
            self.pump.write('')
    
    def party_log(self):
        self.pump.write('')

    def party_input(self):
        self.pump.write('')

    def party_myshare(self, sender, sh):
        if self.hash_mpc: 
            ms = self.share_table[sh]
            if ms is None:
                self.write('f2p', (sender, ('myshare', ms)))
            else:
                self.write('f2p', (sender, ('WrongFollow',)))
        else: raise Exception('MYSHARE with no MPC')
