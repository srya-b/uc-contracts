import dump
import gevent
from collections import defaultdict, deque
from itm import ITM

class AsyncWrapper(ITM):
    def __init__(self, sid, pid, channels):
        self.sid = sid
        self.pid = pid

        self.f2w = channels['f2w']
        self.z2w = channels['z2w']
        self.a2w = channels['a2w']
        self.w2f = channels['w2f']
        self.w2z = channels['w2z']
        self.w2a = channels['w2a']
        self.channels = [self.f2w, self.z2w, self.a2w]
        self.handlers = {
            self.f2w: self.func_msg,
            self.z2w: self.env_msg,
            self.a2w: self.adv_msg
        }

        self.delay = 0
        self.runqueue = deque()
        self.leaks = list()

        ITM.__init__(self, self.sid, self.pid, self.channels, self.handlers)

    def func_msg(self, msg):
        if msg[0] == "leak":
            self.leaks.append(msg[1])
        elif msg[0] == "eventually":
            self.runqueue.append(msg[1])

    def env_msg(self, msg):
        if msg[0] == "advance":
            if self.delay > 0:
                delay = delay-1
                self.w2a.write("advance")
            elif len(self.runqueue) > 0:
                func, args = self.runqueue.popleft()
                func(*args)

    def adv_msg(self, msg):
        if msg[0] == "deliver" and msg[1] < len(self.runqueue) and msg[1] > 0:
            func, args = self.runqueue[msg[1]]
            del self.runqueue[msg[1]]
            func(args)
        elif msg[0] == "delay" and msg[1] >= 0:
            self.delay += msg[1]
        elif msg[0] == "sent_leaks":
            leaks = self.leaks.copy()
            self.leaks.clear()
            self.w2a.write(leaks)
