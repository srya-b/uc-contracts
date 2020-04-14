import dump
import gevent
from collections import defaultdict, deque
from itm import UCWrapper
from enum import Enum
from utils import MessageTag

class AsyncWrapper(UCWrapper):

        
    def __init__(self, channels, pump):
        self.delay = 0
        self.runqueue = deque()
        self.leaks = list()
        self.pump = pump
        
        UCWrapper.__init__(self, 'wrapper', 'wrapper', channels)

    def func_msg(self, msg):
        imp = msg.imp
        msg = msg.msg
        sender, msg = msg
        if msg[0] == MessageTag.LEAK:
            self.leaks.append((sender, msg[1]))
        elif msg[0] == MessageTag.EVENTUALLY:
            func, args = msg[1]
            self.runqueue.append((sender, msg[1]))
            self.leaks.append((sender, func.__name__))
            self.delay = max(self.delay, 1) #self.delay += 1
        self.write('w2f', (sender, (MessageTag.OK,)))

    def env_msg(self, msg):
        imp = msg.imp
        msg = msg.msg
        if msg[0] == MessageTag.ADVANCE:
            if self.delay > 0:
                self.delay = self.delay-1
                self.write('w2a', (MessageTag.ADVANCE,))
            elif len(self.runqueue) > 0:
                sender, funcargs = self.runqueue.popleft()
                self.write('w2f', (sender, (MessageTag.EXECUTE, funcargs)))
            else: self.pump.write("pump")
        else: self.pump.write("pump")

    def adv_msg(self, msg):
        imp = msg.imp
        msg = msg.msg
        if msg[0] == MessageTag.EXECUTE and msg[1] < len(self.runqueue) and msg[1] > 0:
            sender, funcargs = self.runqueue[msg[1]]
            del self.runqueue[msg[1]]
            self.write('w2f', (sender, (MessageTag.EXECUTE, funcargs)))
        elif msg[0] == MessageTag.DELAY and msg[1] >= 0:
            if imp >= msg[1]:
                self.delay += msg[1]
            else:
                self.write('w2a', MessageTag.REJECT, imp-1)
        elif msg[0] == MessageTag.SEND_LEAKS:
            leaks = self.leaks.copy()
            self.leaks.clear()
            self.write('w2a', (MessageTag.SEND_LEAKS, leaks))
        else:
            print(msg)
            self.pump.write("pump")
