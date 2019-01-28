import gevent
from gevent.event import AsyncResult
from gevent.queue import Queue, Empty, Channel
from g_ledger import Ledger_Functionality
from collections import defaultdict
from hashlib import sha256

# Contract which implements the state channel.
# It is passed into the F_Ledger functionality as 
# a callable contract.
def c_state(call, out):
    bestRound = -1
    state = None
    flag = 0
    deadline = None
    applied = set()
    U = None
    n = None
    delta = None
    aux_contract = None

    def init(_U, _n, _delta, _aux_contract, tx):
        U = _U
        n = _n
        delta = _delta
        aux_contract = _aux_contract
        return 1

    def evidence(_r, _state, _out, sigs, tx):
        if _r <= bestRound:
            return 0

        if flag == 1:   # flag == DISPUTE
            flag = 0    # flag := OKAY
            out(('EventOffChain', _r), tx['sender'])
        bestRound = _r
        call(aux_contract, tx['sender'], _out, 0)
        applied.add(r)

    def dispute(_r, tx):
        if _r != bestRound+1:
            return 0
        if flag != 0:   # flag != OKAY
            return 0
        flag = 1        # flag := DISPUTE
        deadline = tx['blocknumber'] + delta
        out(('EventDispute', _r, deadline), tx['sender'])
        
    def resolve(_r, tx):
        if r != bestRound + 1:
            return 0
        if flag != 1:   # flag != DISPUTE
            return 0
        if tx['blocknumber'] < deadline:
            return 0

    return {
            'init':init,
            'evidence':evidence,
            'dispute':dispute,
            'resolve':resolve
           }


def U_state(state, inputs, aux_in):
    if state is None:
        state = 0

    action = 0
    for i in range(2):
        action += inputs[i]

    if action == 2:
        state += 1
    
    aux_out = None
    return (aux_out, state)


# The current state protocol can only support 2 parties
# because multicast to all other parties is not realizable
# in the real world in this case. There may be a way around
# this but this dev certainly doesn't know what it is.
def State_Protocol(F_Ledger):
    class StateProtocol(object):
        N = 2
        leader = 0

        def __init__(self, sid, myid):
            self.sid = sid
            self.myid = myid
            self.N = 2
            self.F_Ledger = F_Ledger

            self.input = Channel()
            self.output = Channel()

        def _set_others(self, parties):
            self.parties = parties

        def _run(self):
            assert self.myid != self.leader
            caddress = self.input.get()
            print('address from leader:', caddress)

            # Give a 0 the first round so the state isn't changed
            # but the round number is.


        def _run_leader(self):
            assert self.myid == self.leader

            # Deploy the contract for everyone else
            F_Ledger.input.put((self.myid, 'abcd', ('tick',)))
            gevent.sleep()
            caddress = sha256(b'abcd' + b'1').hexdigest()[24:]
            print('Leader contract address:', caddress)
            F_Ledger.input.put((self.myid,'abcd',
                ('contract-create', caddress, 1, 
                    (c_state, 
                        (U_state, 2, 5, 'aux')
                    )
                )
            ))
            gevent.sleep()
            F_Ledger.input.put((self.myid, 'abcd',
                ('tick',)
            ))
            gevent.sleep()
  
            # give address to others
            for i in self.parties:
                if i.myid is not self.myid:
                    i.input.put(caddress)

            # Wait for input from the other person
            # Assumption in code is 2 parties only
            _inputs = []

            while not self.input.empty():
                _inputs.append(self.input.get())

            # add your own input
            _inputs.append(1)
            
            return

            _round_inputs = defaultdict(list)
            _current_round = 0
            while True:
                msg = self.input.get()
                cmd,caller,r,data = msg
                if cmd == 'INPUT':
                    _round_inputs[current_round].append(data)

    return StateProtocol



def main_loop():
    N = 2
#    F_blockchain = Ledger_Functionality('sid',
#        [contract_state(state_update,N,1)],
#        N, 1, 10)
    F_Ledger = Ledger_Functionality('sid')

    StateProtocol = State_Protocol(F_Ledger)

    p1 = StateProtocol('sid', 0)
    p2 = StateProtocol('sid', 1)
    parties = [p1,p2]

    p1._set_others(parties)
    p2._set_others(parties)

    functionality = gevent.spawn(F_Ledger.run)
    prot2 = gevent.spawn(p2._run)
    prot1 = gevent.spawn(p1._run_leader)

    while True:
        gevent.sleep()
     

if __name__=="__main__":
    g = gevent.spawn(main_loop)
    gevent.joinall([g])
     

#def contract_state(update_func, N, delta):
#    bestRound = -1
#    state = None
#    flag = 0
#    deadline = None
#    applied = set()
#    U = update_func
#    n = N
#    D = delta
#
#    def evidence(g, _r, _state, _out, sigs):
#        if _r <= bestRound:
#            return
#       
#        _events = []
#        # Should be call to another contract (tricky)
#        # checksig(sigs)
#
#        if flag == 1:
#            flag = 0
#            _events.append(('Off-Chain', bestRound + 1))
#        bestRound = _r
#        state = _state
#        
#        # invoke C.aux_input(out)  ??
#
#        applied = applied.add(r)
#
#    def dispute(_r):
#        if _r != bestRound + 1:
#            return
#        if flag != 0:
#            return
#
#        flag = 1
#        deadline = g.blocknumber() + T
#    
# def State_Protocol(F_Ledger):
# 
#     class StateProtocol(object):
#         N = 2
#         _leader = [0 for _ in range(N)]
#         def __init__(self, sid, myid):
#             self.sid = sid
#             self.myid = myid
#             self.N = 2
#             self.F_Ledger = F_Ledger
# 
#             self.input = Channel()
#             self.output = Channel()
# 
#         def _set_others(self, parties):
#             self.parties = parties
# 
#         def _run_leader(self):
#             if not sum(_leader):
#                 _leader[self.myid] = 1 
#             if not _leader[self.myid]:
#                 return
# 
#             _round_inputs = {}
#     
#             _current_round = 0
#             while True:
#                 msg = self.input.get()
#                 cmd,callerid,r,data = msg
#                 if cmd == 'INPUT':
#                      
# 
#     return StateProtocol
