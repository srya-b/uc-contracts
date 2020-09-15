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

def corrupt(sid,pid):
    global corrupted
    corrupted[sid,pid] = True

def isdishonest(sid,pid):
    global corrupted
    return corrupted[sid,pid]

def ishonest(sid,pid):
    global corrupted
    return not corrupted[sid,pid]
