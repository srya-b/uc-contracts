import dump
import gevent
from itm import ITMFunctionality
from comm import ishonest, isdishonest, isadversary
from queue import Queue as qqueue
from hashlib import sha256
from collections import defaultdict
from gevent.queue import Queue, Channel

def U_Pay(state, inputs, aux_in, rnd):
    if state == None: state = (0,[],0,[])
    try:
        cred_l,oldarr_l,cred_r,oldarr_r = state
    except ValueError:
        print('Can not unpack state')
        cred_l,oldarr_l,cred_r,oldarr_r = (0,[],0,[])
    cred = (cred_l,cred_r)
    #print('credL,credR', cred)
    oldarr = (oldarr_l,oldarr_r)
    #print('oldarrL,oldarrR', oldarr)
    if aux_in:
        deposits = aux_in
    else:
        deposits = (0,0)
    #print('Inputs:', inputs, 'Cred:', cred, 'Oldarr:', oldarr, 'Auxin:', aux_in)
    p_l=0; p_r=1
    pay = [0,0]
    wd = [0,0]
    newarr = [[],[]]
    for p_i in [p_l,p_r]:
        if inputs[p_i] == None: inputs[p_i] = ([],0)
        arr_i,wd_i = inputs[p_i]
        #print('Inputs Loop', arr_i, wd_i)
        #newarr_i=[]
        while len(arr_i):
            e = arr_i.pop(0)
            #print('While loop, e:', e, 'deposits:', deposits[p_i])
            if e+pay[p_i] <= deposits[p_i] + cred[p_i]:
                if p_i == p_l: newarr[p_r].append(e)
                elif p_i == p_r: newarr[p_l].append(e)
                #newarr[p_i].append(e)
                pay[p_i] += e
        if wd_i > deposits[p_i] + cred[p_i] - pay[p_i]: wd[p_i] = 0
        else: wd[p_i] = wd_i
    cred_l += pay[p_r] - pay[p_l] - wd[p_l]
    cred_r += pay[p_l] - pay[p_r] - wd[p_r]

    if wd[p_l] != 0 or wd[p_r] != 0: 
        aux_out = (wd[p_l], wd[p_r])
    else: aux_out = None
    new_state = (cred_l, newarr[p_l], cred_r, newarr[p_r])
    return (new_state, aux_out)


class Contract_Pay(object):
    def __init__(self, address, call, out):
        self.address = address
        self.call = call
        self.out = out
        self.p_l = 0
        self.p_r = 0
        self.deposits_l = 0
        self.deposits_r = 0

    def init(self, p_l, p_r, tx):
        self.p_l = p_l
        self.p_r = p_r

    def deposit(self, tx):
        if tx['sender'] != self.p_l and tx['sender'] != self.p_r:
            return 0
        if tx['sender'] == self.p_l:
            self.deposits_l += tx['value']
        else:
            self.deposits_r += tx['value']
        self.out(('Deposit', self.deposits_l, self.deposits_r), tx['sender'])
        return 1

    def output(self, msg, tx):
        wd_l,wd_r = msg
        self.call(self.p_l, self.address, (), wd_l)
        self.call(self.p_r, self.address, (), wd_r)
        return 1

class Pay_Protocol(object):
    def __init__(self,sid,pid,F_state,G,C, p2f, p2g ):
        self.sid = sid
        self.pid = pid
        self.sender = (sid,pid)
        self.F_state = F_state
        self.first = True

        self.G = G
        self.C = C
        self.p2f = p2f; self.p2g = p2g
        self.outputs = defaultdict(Queue)

        self.arr = []
        self.oldarr = []
        self.pay = 0
        self.wd = 0
        self.oldwd = 0
        self.paid = 0
        self._state = None
        self.buffer = defaultdict(list)

    def __str__(self):
        return '\033[92mProt_pay(%s,%s)\033[0m' % (self.sid, self.pid)

    def write(self, to, msg):
        print(u'\033[92m{:>20}\033[0m -----> {}, msg={}'.format('Protpay(%s,%s)' % (self.sid,self.pid), str(to), msg))

    def round_number(self):
        return self.G.subroutine_call((
            (self.sid,self.pid), True,
            (True, ('block-number',))
        ))

    def input_pay(self, amt):
        contract = self.G.subroutine_call( (self.sender, True, ('contract-ref', self.C)) )    
        myaddr = self.G.subroutine_call( (self.sender, True, ('get-addr', self.sender)) )
        if contract.p_l == myaddr:
            deposit_i = contract.deposits_l
        elif contract.p_r == myaddr:
            deposit_i = contract.deposits_r
        if amt <= deposit_i + self.paid - self.pay - self.wd:
            self.arr.append(amt)
            self.pay += amt
        #print('** input_pay dump **')
        dump.dump()

    def input_withdraw(self, amt):
        contract = self.G.subroutine_call( (self.sender, True, ('contract-ref', self.C)) )    
        myaddr = self.G.subroutine_call( (self.sender, True, ('get-addr', self.sender)) )

        if contract.p_l == myaddr:
            deposit_i = contract.deposits_l
        elif contract.p_r == myaddr:
            deposit_i = contract.deposits_r

        if amt <= deposit_i + self.paid - self.pay - self.wd:
            self.wd += amt
        else:
            print('im a real twat arent i')
        #print('** input_withdraw dump **')
        dump.dump()

    def input_deposit(self, amt):
        #print('depositing amt', amt)
        self.write(self.G, ('deposit',()))
        #self.G.input.set((
        #    self.sender, 
        #    True, 
        #    ('transfer', self.C, amt, ('deposit',()), 'doesntmatter')
        #))

        self.p2g.write( ('transfer', self.C, amt, ('deposit',()), 'doesntmatter') )

    def input_input(self, msg):
        self.write(self.F_state, msg)
        #self.F_state.input.set((
        #    self.sender, True, msg
        #))
        #print('Writing the input')
        self.p2f.write( msg )

    def input_f_state(self, state):
        cred_l,new_l,cred_r,new_r = state
        contract = self.G.subroutine_call( (self.sender, True, ('contract-ref', self.C)) )    
        myaddr = self.G.subroutine_call( (self.sender, True, ('get-addr', self.sender)) )

        if contract.p_l == myaddr:
            new_i = new_l
        elif contract.p_r == myaddr:
            new_i = new_r

        for e in new_i:
            self.outputs[0] = ('receive', e)
            self.paid += e

        #if self.arr != self.arr or self.wd != self.wd:
        #print('1111 wd', self.wd, 'oldwd', self.oldwd, 'arr', self.arr, 'oldarr', self.oldarr)
        msg = ('input', (list(self.arr),self.wd-self.oldwd))
        self.oldarr = list(self.arr); self.oldwd = self.wd
        self.write(self.F_state, msg)
        #self.F_state.input.set((
        #    self.sender, True, msg
        #))
        self.arr = list();# self.wd = 0
        self.oldarr = list(self.arr); #self.oldwd = self.wd
        #print('2222 wd', self.wd, 'oldwd', self.oldwd, 'arr', self.arr, 'oldarr', self.oldarr)
        self.p2f.write( msg )
        #else:
        #    dump.dump()
        

    def check_f_state(self):
        outputs = self.F_state.subroutine_call( (self.sender, True, ('get-output',)))
        if len(outputs):
            #print('New state from F_state', outputs)
            while len(outputs):
                o = outputs.get()
                if o != self._state:
                    print("(%s,%s) Finally a new state from F_state" % (self.sid,self.pid), o, self._state)
                    self._state = o
                    break
            self.input_f_state(o)
        else:
            dump.dump()
    
    def input_ping(self):
        self.check_f_state() 

    def input_msg(self, sender, msg):
        sid,pid = None,None
        if sender:
            sid,pid = sender

        #if self.first:
        #    '''Send (0,0) to F_state'''
        #    self.write(self.F_state,('input',(0,0)))
        #    self.first = False
        #    self.F_state.input.set((
        #        self.sender, True, ('input', (0,0))
        #    ))
    
        if sid == self.sid and pid == self.pid:
            #self.check_f_state()
            if msg[0] == 'pay':
                self.input_pay(msg[1])
            elif msg[0] == 'deposit':
                self.input_deposit(msg[1])
            elif msg[0] == 'withdraw':
                self.input_withdraw(msg[1])
            elif msg[0] == 'input':
                #print('INPUT MSG AT PAYPROT', msg)
                self.input_input(msg)
            elif msg[0] == 'ping':
                self.input_ping()
            else: dump.dump()
        else: dump.dump()

class Adv:
    def __init__(self, sid, pid, G, F, crony, c_payment, a2g):
        self.sid = sid
        self.pid = pid
        self.sender = (sid,pid)
        self.crony = crony
        self.G = G
        self.F = F
        self.a2g = a2g

    def __str__(self):
        return '\033[91mAdversary (%s, %s)\033[0m' % (self.sid, self.pid) 

    def write(self, to, msg):
        print('\033[91m{:>20}\033[0m -----> {}, msg={}'.format('Adversary (%s,%s)' % (self.sid, self.pid), str(to), msg))

    #def input_delay_tx(self, fro, nonce, rounds):
    #    msg=('delay-tx', fro, nonce, rounds)
    #    self.write(self.G, msg)
    #    self.G.backdoor.set((
    #        self.sender,
    #        True,
    #        (False, msg)
    #    ))
    
    def input_tick(self, permutation):
        msg = (self.sender, True, (True, ('tick', perm)))
        self.write(self.G, msg)
        self.G.backdoor.set((
            self.sender,
            True,
            (True, ('tick', perm))
        ))
    
    '''
        Get contract code at addr
    '''
    def subroutine_get_contract(self, addr):
        # Get the mapping from (sid,pid) of F to address
        f_addr = self.G.subroutine_call((
            (self.sid,self.pid),
            True,
            ('get-addr', addr)
        ))

        assert f_addr is not None

        if f_addr == addr:
            print('LULZ')
            return 'lulz'


    def input_party(self, to, msg):
        self.write(self.crony, msg)
        self.crony.backdoor.set(msg)

    def input_msg(self, msg):
        if msg[0] == 'delay-tx':
            self.input_delay_tx(msg[1], msg[2], msg[3])
        elif msg[0] == 'party-input':
            self.input_party(msg[1], msg[2])
        elif msg[0] == 'tick':
            self.input_tick(msg[1])
        else:
            #print('** adv input_msg dump **')
            dump.dump()

    def subroutine_msg(self, msg):
        if msg[0] == 'get-contract':
            return self.subroutine_get_contract(msg[1])

