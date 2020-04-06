import dump
import gevent
from collections import defaultdict, deque
from itm import UCWrapper
from enum import Enum

class AsyncWrapper(UCWrapper):
    class MessageType(Enum):
        LEAK = 1
        EVENTUALLY = 2
        ADVANCE = 3
        EXECUTE = 4
        DELAY = 5
        SEND_LEAKS = 6
        REJECT = 7
        
    def __init__(self, sid, pid, channels):
        self.delay = 0
        self.runqueue = deque()
        self.leaks = list()

        UCWrapper.__init__(self, self.sid, self.pid, self.channels)

    def func_msg(self, msg):
        sender, msg = msg
        msg = msg.msg
        imp = msg.imp
        if msg[0] == MessageType.LEAK:
            self.leaks.append((sender, msg[1]))
        elif msg[0] == MessageType.EVENTUALLY:
            func, args = msg[1]
            self.runqueue.append((sender, msg[1]))
            self.leaks.append((sender, func.__name__))

    def env_msg(self, msg):
        sender, msg = msg
        msg = msg.msg
        imp = msg.imp
        if msg[0] == MessageType.ADVANCE:
            if self.delay > 0:
                delay = delay-1
                self.write('w2a', MessageType.ADVANCE)
            elif len(self.runqueue) > 0:
                sender, funcargs = self.runqueue.popleft()
                self.write('w2f', ((self.sid, sender), (MessageType.EXECUTE, funcargs)))

    def adv_msg(self, msg):
        sender, msg = msg
        msg = msg.msg
        imp = msg.imp
        if msg[0] == MessageType.EXECUTE and msg[1] < len(self.runqueue) and msg[1] > 0:
            sender, funcargs = self.runqueue[msg[1]]
            del self.runqueue[msg[1]]
            self.write('w2f', ((self.sid, sender), (MessageType.EXECUTE, funcargs)))
        elif msg[0] == MessageType.DELAY and msg[1] >= 0:
            if imp >= msg[1]:
                self.delay += msg[1]
            else:
                self.write('w2a', MessageType.REJECT, imp-1)
        elif msg[0] == MessageType.SEND_LEAKS:
            leaks = self.leaks.copy()
            self.leaks.clear()
            self.write('w2a', (MessageType.SEND_LEAKS, leaks))
