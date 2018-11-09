import gevent
from gevent.event import AsyncResult
from gevent.queue import Queue, Empty, Channel
from blockchain_functionality import Ledger_Functionality
from collections import defaultdict

def state_update(s, inps):
    return (s+1)

def contract_state(update_func, N, delta):
    bestRound = -1
    state = None
    flag = 0
    deadline = None
    applied = set()
    U = update_func
    n = N
    D = delta

    def evidence(g, _r, _state, _out, sigs):
        if _r <= bestRound:
            return
       
        _events = []
        # Should be call to another contract (tricky)
        # checksig(sigs)

        if flag == 1:
            flag = 0
            _events.append(('Off-Chain', bestRound + 1))
        bestRound = _r
        state = _state
        
        # invoke C.aux_input(out)  ??

        applied = applied.add(r)

    def dispute(_r):
        if _r != bestRound + 1:
            return
        if flag != 0:
            return

        flag = 1
        deadline = g.blocknumber() + T
    

def State_Protocol(F_Ledger):

    class StateProtocol(object):
#        _instances = {}
        N = 2
        _leader = [0 for _ in range(N)]
        def __init__(self, sid, myid):
            self.sid = sid
            self.myid = myid
            self.N = 2
            self.F_Ledger = F_Ledger
#            if sid not in StateProtocol._instances:
#                StateProtocol._instances[sid] = Ledger_Funtctionality(
#                    sid,
#                    contracts,
#                    N
#                )

#            F_Ledger = StateProtocol._instances[sid]
            self.input = Channel()
            self.output = Channel()

        def _set_others(self, parties):
            self.parties = parties

        def _run_leader(self):
            if not sum(_leader):
                _leader[self.myid] = 1 
            if not _leader[self.myid]:
                return

            _round_inputs = []

            while True:
                msg = self.input.get()
                cmd,callerid,data = msg
                if cmd == 'INPUT':
                    if len(_round_inputs) and _round_inputs[0][1] == callerid: return

                    _round_inputs.append((cmd,callerid,data))
                    if len(_round_inputs) == 2:

                        # Send batch messages to each party (incuding self)
                        for p in parties:
                            p.input.put(('BATCH',self.myid,_round_inputs))

                

                
                        
                            

                

    return StateProtocol
                

    
def main_loop():
    N = 2
    F_blockchain = Ledger_Functionality('sid',
        [contract_state(state_update,N,1)],
        N, 1, 10)

    StateProtocol = State_Protocol(F_blockchain)

    p1 = StateProtocol('sid', 0)
    p2 = StateProtocol('sid', 1)
   
     

if __name__=="__main__":
    g = gevent.spawn(main_loop)
    gevent.joinall([g])
     
