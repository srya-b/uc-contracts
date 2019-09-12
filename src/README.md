# uc-contract
This is a python implementation of the UC framework alongside the changes required for smart contract applications to be expressed.
The only dependency of the project is **gevent** and the version of python is **3.5.3**.

## Directories
1. Paper - the latex version of the paper so far
2. Papers - different, but relevant paper pdfs
3. src - the actual implementation


## How to run an experiment for a payment channel

### Hybrid world.
The file `./src/hybrid.py` shows a typical environment working on a real payment channel protocol implemented in the hybrid world with access to F_state and G_ledger. I'll walk through the file here:

1. The first step in creating the environment is to create all the requisite communication channels that the ITMs will use. The channels are all imported here :

```from comm import P2F, P2G, F2G, A2G, A2P, Many2FChannel, M2F, Z2P, A2P, Z2A```
