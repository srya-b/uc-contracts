from uc.itm import GUCFunctionality

class GUCDummyFunctionality(GUCFunctionality):
    def __init__(self, k, bits, crupt, sid, pid, channels, poly, pump, importargs, gsid, _ssids):
        GUCFunctionality.__init__(self, k, bits, crupt, sid, pid, channels, poly, pump, importargs, gsid, _ssids)

        self.ssids = { 'Ledger': _ssids[0], 'Wrapper': _ssids[1] }
            
        self.party_msgs['ledger'] = self.to_ledger_msg
        self.party_msgs['wrapper'] = self.to_wrapper_msg

    def to_ledger_msg(self, imp, sender, msg):
        self.write( 'f2g', (self.gsid, (self.ssids['Ledger'], msg)), imp)

    def to_wrapper_msg(self, imp, sender, msg):
        self.write('f2g', (self.gsid, (self.ssids['Wrapper'], msg)), imp)

    def gfunc_msg(self, d):
        sender,msg = d.msg
        imp = d.imp
        self.write('f2p', ( (self.sid, 1), msg ), imp)
