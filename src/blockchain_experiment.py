import gevent
from gevent.queue import Channel, Queue
from collections import defaultdict
from itm import ITMFunctionality, ITMPassthrough, ITMAdversary, createParties
from utils import z_mine_blocks, z_send_money, z_get_balance, z_mine_block_perm
from g_ledger import Ledger_Functionality, Blockchain_IdealProtocol
import dump
from protected_wrapper import Protected_Wrapper, ProtectedITM
import comm

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
'''
Blockchain functionality
'''
idealf = Ledger_Functionality('sid', 0)
#protected = Protected_Wrapper(idealf)
#idealitm = ITMFunctionality('sid', 0)
protected, idealitm = ProtectedITM('sid', 0, idealf)
#idealitm.init(idealf)
#idealitm.init(protected)
comm.setFunctionality(idealitm)

'''
Ideal world parties
'''
parties = createParties('sid', range(2,4), idealitm)
comm.setParties(parties)
for party in parties:
    gevent.spawn(party.run)


# start ideal adversary
#adversary = ITMAdversary('sid', 1)
#adversary.init(idealitm)
#idealf.set_backdoor(adversary.leak)
#comm.setAdversary(adversary)
#gevent.spawn(adversary.run)

# start passthrough party itms
#parties = [ITMPassthrough('sid', i) for i in range(2,4)]
#comm.setParties(parties)
#for party in parties:
#    party.init(idealitm)

#for party in parties:
#    gevent.spawn(party.run)
#functionality = gevent.spawn(idealitm.run)
### IDEAL WORLD ###

### REAL WORLD ###
### REAL WORLD ###

'''
Start functionality itms
'''
gevent.spawn(idealitm.run)

'''
Adversary
'''
adversary = ITMAdversary('sid', 6)
comm.setAdversary(adversary)
gevent.spawn(adversary.run)

simparty = ITMPassthrough('sid1', 23)
comm.setParty(simparty)
simparty.init(idealitm)
gevent.spawn(simparty.run)

### EXPERIMENT ###
#addr1 = 'abcd'
#addr2 = 'beef'

p1 = parties[0]
p2 = parties[1]

print('P1:', p1.sid, p1.pid)
print('P2:', p2.sid, p2.pid)

z_mine_blocks(1, p1, idealitm)
z_mine_blocks(1, p2, idealitm)

caddress = p1.subroutine_call(
    ('get-caddress',)
)
print('caddress:', caddress)

# get balance through subroutine
p1_balance = p1.subroutine_call(
    ('getbalance', (p1.sid, p1.pid))
)
print('p1balance:', p1_balance)
p2_balance = p2.subroutine_call(
    ('getbalance', (p2.sid, p2.pid))
)
print('p2balance:', p2_balance)

# create contract
p1.input.set(
    ('contract-create', caddress, 0, (c_counter,(12,)), False, 'bad')
)
dump.dump_wait()

print('Contract create input set')

z_mine_blocks(10, p1, idealitm)

# submit two transactions
p1.input.set(
    ('transfer', caddress, 0, ('count',()), 'shit')
)
dump.dump_wait()

p2.input.set(
    ('transfer', caddress, 0, ('count',()), 'ahead') 
)
dump.dump_wait()

z_mine_blocks(10, p2, idealitm)

first_count = p1.subroutine_call(
    ('read-output', [((p1.sid,p1.pid),2)])
)
second_count = p2.subroutine_call(
    ('read-output', [((p2.sid,p2.pid),1)])
)

assert first_count[0][0] == 13, str(first_count)
assert second_count[0][0] == 14, str(second_count)

print('First count', first_count[0][0])
print('Second count', second_count[0][0])

'''
Adversary now reorders the transactions so the counts are flipped
'''
p1.input.set(
    ('transfer', caddress, 0, ('count',()), 'shit')
)
dump.dump_wait()

p2.input.set(
    ('transfer', caddress, 0, ('count',()), 'ahead') 
)
dump.dump_wait()

z_mine_blocks(7, simparty, idealitm) 
z_mine_block_perm([1,0], adversary)

first_count = p1.subroutine_call(
    ('read-output', [((p1.sid,p1.pid),3)])
)
second_count = p2.subroutine_call(
    ('read-output', [((p2.sid,p2.pid),2)])
)

print('First count', first_count[0][0])
print('Second count', second_count[0][0])

assert first_count[0][0] == 16, str(first_count[0][0])
assert second_count[0][0] == 15, str(second_count[0][0])


