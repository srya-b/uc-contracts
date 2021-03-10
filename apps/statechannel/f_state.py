from uc.itm import UCWrappedFunctionality
from uc.utils import wait_for, waits
from collections import defaultdict
import gevent
import logging

log = logging.getLogger(__name__)

class F_State(UCWrappedFunctionality):
    def __init__(self, k, bits, crupt, sid, pid, channels, pump, poly, importargs):
        self.ssid = sid[0]
        self.update_f = sid[1]
        self.contract_f = sid[2]
        self.parties = sid[3]
        self.delta = sid[4]
        UCWrappedFunctionality.__init__(self, k, bits, crupt, sid, pid, channels, poly, pump, importargs)

        self.aux_in = []
        self.ptr = 0
        self.state = None
        self.buf = None
        self.dealer = 1
        self.received_input = defaultdict(bool)
        self.round_input = defaultdict(dict)
        self.first_input_this_round = True
        self.round = 0

    def move_to_next_round(self, scheduled_clock_round):
        curr_round = self.clock_round()
        # if 3*DELTA has not passed yet schedule another code block 
        # if the current round is T schedule a code block for:
        # 3*DELTA - (T - scheduled_clock_round)
        if curr_round < (scheduled_clock_round + 3*self.delta):
            rounds_left_to_wait = (3*self.delta) - (curr_round - scheduled_clock_round)
            self.write_and_wait_expect(
                ch='f2w', msg=('schedule', 'move_to_next_round', (scheduled_clock_round,), rounds_left_to_wait),
                read='w2f', expect=('OK',))
            self.pump.write('')
        elif curr_round == (scheduled_clock_round + 3*self.delta):
            self.received_input = defaultdict(bool)
            for pid in self.parties:
                if pid not in self.round_input[self.round]:
                    self.round_input[self.round][pid] = None

            self.state, o = self.update_f(self.state, self.round_input[self.round], [])
            # TODO: send the output to parties in O(1) round

            print('\n\nNew state:', self.state)

            self.round += 1
            self.pump.write('')
        else:
            self.pump.write('')
            #raise Exception("wrapper didn't execute in time. WTF")

    def party_input(self, pid, inp):
        curr_clock_round = self.clock_round() 
        print('Curr_clock_round', curr_clock_round)
        if self.first_input_this_round:
            self.first_input_this_round = False
            # schedue a timeout for k*DELTA rounds from now
            self.write_and_wait_expect(
                ch='f2w', msg=('schedule', 'move_to_next_round', (curr_clock_round,), 3*self.delta),
                read='w2f', expect=('OK',)
            )

        self.received_input[pid] = True
        self.round_input[self.round][pid] = inp
        self.leak( ('input', pid, inp), 0 )
        print('received:', self.received_input)
        print('inputs:', self.round_input)

        self.write('f2p', ((self.sid, pid), 'OK'))

    def party_msg(self, d):
        msg = d.msg
        imp = d.imp
        sender,msg = msg
        sid,pid = sender

        if msg[0] == 'input' and pid in self.parties:
            _,inp = msg
            if not self.received_input[pid]:
                self.party_input(pid, inp)
            else:
                self.pump.write('')
        else:
            self.pump.write('')

    def wrapper_msg(self, d):
        msg = d.msg
        imp = d.imp

        if msg[0] == 'exec':
            _, name, args = msg
            f = getattr(self, name)
            f(*args)
        else:
            self.pump.write('')

