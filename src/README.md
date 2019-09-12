# uc-contract
This is a python implementation of the UC framework alongside the changes required for smart contract applications to be expressed.
The only dependency of the project is **gevent** and the version of python is **3.5.3**.

## How to run an experiment for a payment channel

### Hybrid world.
The file `./src/hybrid.py` shows a typical environment working on a real payment channel protocol implemented in the hybrid world with access to F_state and G_ledger. I'll walk through the file here:

1. **The first step in creating the environment** is to create all the requisite communication channels that the ITMs will use. The channels are all imported here :
  `from comm import P2F, P2G, F2G, A2G, A2P, Many2FChannel, M2F, Z2P, A2P, Z2A`

The channels are implemented using `gevent.Event` so that ITMs can `wait` and become active when another ITM writes on the channel. All of the channels except `Many2FChannel` and `M2F` are identical except in name (for clarity). Regular channels have one ITM on either end of it. In the case of `Many2FChannel` there is one destination, but multiple ITMs can send to that destination by creating `M2F` channels that point to 1 `Many2FChannel`

``` 
(P_1) M2F ----
             |
(P_2) M2F --------> Many2FChannel (F_state)
             |
(P_3) M2F ----
```

2. **Initializing all the requisite ITMs** can be complicated as there are a lot of channels to connect and pid's to look after. The `utils.py` file is packed with helper functions to create and start ITMs for you. As an example this is how the ledger functionality is initiated:
```g_ledger, protected, ledger_itm = z_start_ledger(ledgerid[0],ledgerid[1],Ledger_Functionality,ProtectedITM, a2ledger, f2ledger, m2ledger)```
The first to parameters are specifying the `sid` and `pid` of the ledger. The next two funtionalities are unimportant but tell the function which class to create and which function to execute (`ProtectedITM`). finally all the channels to the ledger.

3. **Create the parties in the execution**:
```rparties = z_real_parties('sid2', [2,3], ITMProtocol, Pay_Protocol, state_itm, ledger_itm, caddr, [a2p1,a2p2], [p2fstate1,p2fstate2], [p2ledger1, p2ledger2], [z2p1,z2p2])```
These parties aren't ideal so they must run the payment channel protocol. The function `z_start_real_parties` can start any number of parties that must connect to the same functonality. In this case, 2 parties are being created with `pid`s 2 and 3. The ITM that will be created is of type `ITMProtocol`, the protocol being run inside them is `Pay_Protocol`, the F_state ITM that they must talk to is `state_itm`, the ledger is `ledger_itm`, the address of the contract that F_state is initialized with is `caddr` and then channels from the adversary, to F_state, to G_ledger, and from the enviroment is passed in for each of the two parties, respectively. 

4. **Running a payment channel hybrid-world experiment.**
