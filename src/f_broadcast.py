import gevent
from gevent.queue import Queue, Channel
from collections import defaultdict

class Broadcast_Functionality(object):
    def __init__(self, sid, pid):
        self.sid = sid
        self.pid = pid

        self.outputs = defaultdict(Queue)




