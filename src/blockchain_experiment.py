import gevent
from gevent.queue import Channel, Queue
from collections import defaultdict
from itm import ITMFunctionality, ITMPassthrough, ITMAdversary
from g_ledger import Ledger_Functionality, Blockchain_IdealProtocol
import dump

### CONTRACTS ###
class c_counter:
    def __init__(self, call, out):
        self.out = out
        self.call = call

    def init(self, start, tx):
        self.val = start
        return 1

    def count(self, tx): 
        self.val += 1
        self.out(self.val, tx['sender'])
        return 1 


### IDEAL WORLD ###
idealf = Ledger_Functionality('sid', 0)
idealitm = ITMFunctionality('sid', 0)
idealitm.init(idealf)

# start ideal adversary
adversary = ITMAdversary('sid', 1)
adversary.init(idealitm)
gevent.spawn(adversary.run)

# start passthrough party itms
parties = [ITMPassthrough('sid', i) for i in range(2,4)]
for party in parties:
    party.init(idealitm)

for party in parties:
    gevent.spawn(party.run)
functionality = gevent.spawn(idealitm.run)
### IDEAL WORLD ###

### REAL WORLD ###
### REAL WORLD ###


### EXPERIMENT ###
addr1 = 'abcd'
addr2 = 'beef'

p1 = parties[0]
p1.input.set(
    ('tick', addr1)
)

dump.dump_wait()
#gevent.sleep()

p2 = parties[1]
p2.input.set(
    ('tick', addr2)
)

#gevent.sleep(5)

caddress = p1.subroutine_call(
    ('get-caddress', addr1)
)
print('caddress:', caddress)

dump.dump_wait()

# get balance through subroutine
p1_balance = p1.subroutine_call(
    ('getbalance', addr1)
)
print('p1balance:', p1_balance)
p2_balance = p2.subroutine_call(
    ('getbalance', addr2)
)
print('p2balance:', p2_balance)

# create contract
p1.input.set(
    ('contract-create', caddress, 0, (c_counter,(12,)), False, addr1)
)
dump.dump_wait()

for i in range(10):
    p1.input.set(
        ('tick', addr1)
    )
    dump.dump_wait()


# submit two transactions
#  p1 expects 0 -> 1
#  p2 expects 1 -> 2
p1.input.set(
    ('transfer', caddress, 0, ('count',()), addr1)
)
dump.dump_wait()

p2.input.set(
    ('transfer', caddress, 0, ('count',()), addr2) 
)

dump.dump_wait()

for i in range(10):
    p2.input.set(
        ('tick', addr2)
    )
    dump.dump_wait()


print(p1.subroutine_call(
    ('read-output', ([(addr1,2)]))
))
print(p2.subroutine_call(
    ('read-output', ([(addr2,1)]))
))

#  

