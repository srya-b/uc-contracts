from typing import Tuple

#class MSG:
#    def __init__(self, 
#            msg : Tuple, 
#            imp : int):
#        self.msg = msg
#        self.imp = imp
#    def __repr__(self):
#        return 'MSG:' + str((self.msg, self.imp))
#
#class MSG_Z2A_A2P(MSG):
#    def __init__(self, msg, to, imp):
#        MSG.__init__(self, msg, imp)
#        self.to = to
#
#class MSG_Z2A_A2F(MSG):
#    def __init__(self, msg, to, imp):
#        MSG.__init__(self, msg, imp)
#        self.to = to
#
#class MSG_F2A(MSG):
#    def __init__(self, msg, imp):
#        MSG.__init__(self, msg, imp) 
#
#class MSG_P2A(MSG):
#    def __init__(self, msg, imp):
#        MSG.__init__(self, msg, imp)

# haskell def
#   data SttCruptZ2A a b = SttCruptZ2A_A2P (PID, a) | SttCruptZ2A_A2F b deriving Show
class SttCruptZ2A: pass

class SttCruptZ2A_A2P(SttCruptZ2A):
    def __init__(self, _to, _msg):
        self.to = _to
        self.msg = _msg

class SttCruptZ2A_A2F(SttCruptZ2A):
    def __init__(self, _msg):
        self.msg = _msg

# haskell def
#   data SttCruptA2Z a b = SttCruptA2Z_P2A (PID, a) | SttCruptA2Z_F2A b deriving Show
class SttCruptA2Z: pass

class SttCruptA2Z_P2A(SttCruptA2Z):
    def __init__(self, _to, _msg):
        self.to = _to
        self.msg = _msg

class SttCruptA2Z_F2A(SttCruptA2Z):
    def __init__(self, _msg):
        self.msg = _msg

