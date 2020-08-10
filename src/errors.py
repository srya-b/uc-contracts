class Error(Exception):
    pass

class WriteImportError(Error):
    """Raised when an ITM send a message to another ITM
    with some import but doesn't have enough.

    Attributes:
        itmid -- (sid,pid) of the ITM that failed.
    """
    def __init__(self, fro, msg, imp):
        self.fro = fro
        self.imp = imp
        self.msg = msg

class TickError(Error):
    """Raised when consuming potential with ``tick'' fails.

    Attributes:
    
    """
    def __init__(self, fro, amt):
        self.fro = fro
        self.amt = amt

