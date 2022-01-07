from uc.itm import ITM


class UCFunctionality(ITM):
    def __init__(self, k, bits, crupt, sid, pid, channels, pump):
        self.crupt = crupt
        self.handlers = {
            channels['p2f'] : self.party_msg,
            channels['a2f'] : self.adv_msg,
        }
        
        ITM.__init__(self, k, bits, sid, pid, channels, self.handlers, pump)

        self.party_msgs = {}
        self.adv_msgs = {}

    def is_honest(self, sid, pid):
        return (sid,pid) not in self.crupt

    def is_dishonest(self, sid, pid):
        return not self.is_honest(sid, pid)

    def wrapwrite(self, msg):
        return msg

    def adv_msg(self, msg):
        if msg[0] in self.adv_msgs:
            self.adv_msgs[msg[0]](*msg[1:])
        else:
            self.pump.write('')

    def party_msg(self, m):
        sender,msg = m
        if msg[0] in self.party_msgs:
            self.party_msgs[msg[0]](sender, *msg[1:])
        else:
            raise Exception('unknown message', msg)
            self.pump.write('')

    def env_msg(self, msg):
        Exception("env_msg needs to be defined")


