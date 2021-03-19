
from ecdsa import SigningKey, VerificationKey

class G_cert_inner(UCWrappedFunctionality):
    def __init__(self, k, bits, crupt, sid, pid, channels, pump, poly, importargs, target_pid):
        UCWrappedFunctionality.__init__(self, k, bits, crupt, sid, pid, channels, poly, importargs)
        self.handlers[self.channels['_2w']] = self.gfunc_msg

        self.target_pid = pid
        self.corrupt = False
        for (sid,pid) in crupt:
            if pid == self.target_pid:
                self.corrupt = True
        self.first = True

        self.sk = None
        self.vk = None


        def exec_genkey(self, sender):
            if not self.sk and not self.vk:
                _sid,_pid = sender
                self.sk = SigningKey.generate()
                self.vk = sk.verifyingkey
            self.write_and_wait_expect(
                ch='w2_', msg=((self.sid, self.pid), ('register', sender, self.vk)),
                read='_2w', expect=('OK',)
            )
            self.write( 'w2p', (sender, ('KeyGenOK',)) )

        def keygen(self, sender):
            _sid,_pid = sender
            if _sid == self.sid and self.is_honest(_sid, _pid):
                self.schedule('exec_genkey', (sender,), 1)

        def sign(self, _pid, _sid, m):
            self.write('w2_', , (::
            

        def party_msg(self, d):
            msg = d.msg
            imp = d.imp
            sender,msg = msg
            (sid,pid) = sender

            if msg[0] == 'keygen' and pid == self.target_pid and self.first:
                self.keygen(self, sender)
                self.first = False
            elif msg[0] == 'sign' and pid == self.target_pid
                self.sign(self, msg[1], msg[2])
            elif msg[0] == 'verify':
                self.verify(self, msg[1], msg[2], msg[3])
            else:
                self.write('w2p', (sender, ('OK',)))

        def adv_msg(self, d):
            msg = d.msg
            imp = d.imp
            
            if msg[0] == 'setkey':
                if not self.sk and not self.vk:
                    self.sk = msg[1]; self.vk = msg[2];
            else:
                self.pump.write('')
