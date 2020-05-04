from collections import defaultdict

global commap
global corrupted
global itmmap
global adversary

commap = {}
itmmap = {}
adversary = None
corrupted = defaultdict(bool)

wrapmap = {}


FUNCTIONALITY = 0
PARTY = 1
ADVERSARY = 2
SIMULATOR = 3

def cset(sid,pid,tag,itm):
    if (sid,pid) not in commap:
        commap[sid,pid] = tag
        itmmap[sid,pid] = itm
def cset2(sid,pid,tag):
    if (sid,pid) not in commap:
        commap[sid,pid] = tag

def isf(sid,pid):
    try:
        return commap[sid,pid] == FUNCTIONALITY
    except KeyError:
        return False

def isadversary(sid,pid):
    try:
        return commap[sid,pid] == ADVERSARY
    except KeyError:
        return False

def isparty(sid,pid):
    try:
        return commap[sid,pid] == PARTY
    except KeyError:
        return False

def getitm(sid,pid):
    try:
        return itmmap[sid,pid]
    except KeyError:
        return None

def itmstring(sid,pid):
    try:
        return str(getitm(sid,pid))
    except:
        return ''

def setAdversary(itm):
    global adversary
    sid,pid = itm.sid,itm.pid
    cset(sid,pid,ADVERSARY,itm)
    adversary = itm

def setFunctionality(itm):
    sid,pid = itm.sid,itm.pid
    cset(sid,pid,FUNCTIONALITY,itm)

def setFunctionality2(sid,pid,itm=None):
    if itm is None:
        cset2(sid,pid,FUNCTIONALITY)
    else:
        cset(sid, pid, FUNCTIONALITY, itm)

def setParty(p):
    sid,pid = p.sid,p.pid
    cset(sid,pid,PARTY,p)

def setParties(parties):
    for p in parties:
        setParty(p)

def corrupt(sid,pid):
    global corrupted
    corrupted[sid,pid] = True

def isdishonest(sid,pid):
    global corrupted
    return corrupted[sid,pid]

def ishonest(sid,pid):
    global corrupted
    return not corrupted[sid,pid]
    
def addwrapper(sid,wrapper):
    wrapmap[sid] = wrapper 
