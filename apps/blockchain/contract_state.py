from math import floor, ceil
from uc.itm import UCWrappedFunctionality
from uc.utils import wait_for
from collections import defaultdict
import logging


class Flags:
    OK = 0
    DISPUTE = 1
    PENDING = 2

#class Contract_Statei_and_bcast(UCWrappedFunctionality):
class Contract_State:
    def __init__(self, update_f):
        self.bestRound = -1
        self.state = None
        self.flag = Flags.OK
        self.deadline = None
        self.applied = set()

        self.deadline_amount = 7
        self.received_input = defaultdict(bool)
        self.round_input = defaultdict(dict)

    def evidence(self, r, state_, out, sigs, tx):
        print('r: {}, state_: {}, out: {}, sigs: {}'.format(r, state_, out, sigs))
        #if r > self.bestRound:
        #    # TODO: check all signatures
        #    if self.flag == Flags.DISPUTE:
        #        self.flag = Flags.OK
        #        self.broadcast( ("EventOffChain", r) )
        #    self.bestRound = r
        #    self.state = state_

        #    # TODO: invoke aux contract
        #    self.applied.add(r)
        #else:
        #    self.pump.write('')

    def dispute(self, r, tx):
        T = self.block_number()
        if r == self.bestRound + 1:
            if self.flag == Flag.DISPUTE:
                self.flag = Flad.DISPUTE
                self.deadline = T + self.deadline_amount 
                self.broadcast( ("EventDispute", r, self.dealine) )
            else:
                self.pump.write('')
        else:
            self.pump.write('')

    def resolve(self, r, tx):
        T = self.block_number()
        if r == self.bestRound + 1:
            if self.flag == Flag.PENDING:
                if T >= self.deadline:
                    self.state, o = self.update_f(self.state, self.round_input[r], [])
                    self.flag = Flag.OK
                    self.broadcast( ("EventOffchain", r, self.state) )
                    self.bestRound += 1
                else: self.pump.write('')
            else: self.pump.write('')
        else: self.pump.write('')

    def input(self, pid, r, inp, tx):
        if not self.received_input[pid]:
            self.received_input[pid] = True
            self.round_input[self.round][pid] = inp
        else:
            self.pump.write('')

    def party_msg(self, tx):
        print('tx', tx)
        getattr(self, tx['func'])(*tx['args'], tx)
                
