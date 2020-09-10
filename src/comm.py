"""
comm.py

in charge of the relationship between (session_id, process_id) to the corresponding ITM and its tag/character.

There are four tags/character:
    FUNCTIONALITY = 0
    PARTY = 1
    ADVERSARY = 2
    SIMULATOR = 3
"""
from collections import defaultdict

global commap # mapping from (sid, pid) to the corresponding tag/character
global corrupted # mapping from (sid, pid) to bool, representing if corrupted
global itmmap # mapping from (sid, pid) to the corresponding itm
global adversary # type: itm

commap = {}
itmmap = {}
adversary = None
corrupted = defaultdict(bool)


FUNCTIONALITY = 0
PARTY = 1
ADVERSARY = 2
SIMULATOR = 3

#def cset(sid,pid,tag,itm):
#    if (sid,pid) not in commap:
#        commap[sid,pid] = tag
#        itmmap[sid,pid] = itm
#def cset2(sid,pid,tag):
#    if (sid,pid) not in commap:
#        commap[sid,pid] = tag
#
#def isf(sid,pid):
#    try:
#        return commap[sid,pid] == FUNCTIONALITY
#    except KeyError:
#        return False
#
#def isadversary(sid,pid):
#    try:
#        return commap[sid,pid] == ADVERSARY
#    except KeyError:
#        return False
#
#def isparty(sid,pid):
#    try:
#        return commap[sid,pid] == PARTY
#    except KeyError:
#        return False
#
#def getitm(sid,pid):
#    try:
#        return itmmap[sid,pid]
#    except KeyError:
#        return None
#
#def itmstring(sid,pid):
#    try:
#        return str(getitm(sid,pid))
#    except:
#        return ''
#
#def setAdversary(itm):
#    global adversary
#    sid,pid = itm.sid,itm.pid
#    cset(sid,pid,ADVERSARY,itm)
#    adversary = itm
#
#def setFunctionality(itm):
#    sid,pid = itm.sid,itm.pid
#    cset(sid,pid,FUNCTIONALITY,itm)
#
#def setFunctionality2(sid,pid):
#    cset2(sid,pid,FUNCTIONALITY)
#
#def setParty(itm):
#    sid,pid = itm.sid,itm.pid
#    cset(sid,pid,PARTY,itm)
#
#def setParties(itms):
#    for p in itms:
#        setParty(p)

def corrupt(sid,pid):
    global corrupted
    corrupted[sid,pid] = True

def isdishonest(sid,pid):
    global corrupted
    return corrupted[sid,pid]

def ishonest(sid,pid):
    global corrupted
    return not corrupted[sid,pid]
