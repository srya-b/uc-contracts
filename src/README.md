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

4. **A simulated honest party.** The purpose of this party is to be an honest party from any other protocol session that the environment can use to interact with G_ledger. In the (G)UC setting, the environment is only allowed to simulate honest parties of other protocol session. The simulated party just runs the empty protocol, i.e. it is a dummy party. The simulated party is initialized like the others above:
```simparty = z_sim_party(simpartyid[0], simpartyid[1], ITMPassthrough, ledger_itm, a2sp, sp2f, z2sp)```

5. **Starting a payment channel hybrid-world experiment.**
There are a few things to keep in mind when passing input to the parties and the adversary. First I'll outline a few of the useful functions that abstract away a lot of the low-level interaction details:
* `z_inputs(msg, *z2ps)` takes in a message and writes to the inputs of each of the channels `z2ps` the `msg` one after another. The environment must wait until control is returned to it before writing to the next channel in the list.
* `z_ping(*z2ps)` sends a `ping` message to the input channels, like the `z_inputs(...)` above. The ping message is crucial as the a lot of the message passing it done through polling. This is to accomodate the write-once rule in the case where a functionality has to 'output' some message to all of the parties. The ping messages, generally, tell the called itms to poll for messages from relevant functionalities and process them. In the case of **Pi_pay**, as an example, the `ping` operation checks **F_state** for a new state and sends it's own inputs to **F_state**. The rules for how to do it will be clear below.
* `z_mine_blocks(n, z2p, z2p.to)` will progress the ledger by `n` rounds. The `hybrid.py` makes it clear how to use it.
* `z_set_delays(z2a, advitm, ledger_itm, [...])` is used by the environment to tell the adversary to delay transactions by a certain number of rounds, specified in `[...]`. The order of 'delays' set in `[...]` will be applied to the current transactions waiting to be assigned a delay in the order they were submitted to the ledger. Example: if the input is `[1,2,3]`, the transactions `[tx1, tx2, tx3]` will be delays by 1, 2, and 3 rounds respectively. 
* `z_tx_inputs(z2a, advitm, ledger_itm, <msg>, z2sp, z2ps*)` functions much like `z_inputs(...)` where it writes the `<msg>` on the input to the parties `z2ps`. The function also expects a transaction to be created somewhere in the activation, therefore will write the input, wait for control to return to the environment and set a delay of 0 to the transaction generated. The purpose of this function is to make it easy to set an input and force a transaction through in the next round in a simple way. 

6. **Actually running some input**. `hybrid.py` has examples of everything talked about here. This is specific to the payment channels at the moment:
```
z_inputs(('input',([],0)), z2p1, z2p2)
z_mine_blocks(1, z2sp, z2sp.to)
z_ping(z2p1,z2p2)
```
As specified in the functionality and pay protocol, the first input is empty to initialize the first state for **F_state**.
In the honest case for the parties, the new state is delivered (i.e. ready to be polled, in our case) in **O(1)** rounds. The round is controlled by on-chain rounds (which will be changed) so `z_mine_blocks` is called to make it available. `z_ping` then makes the parties `p1` and `p2` poll **F_state** for the new state and give it their current inputs (will empty as well as the environment hasn't provided any input yet)

The `state` at the end of this code will be `(0, [], 0, [])` at the parties and `(0, [], 0, [])` at **F_state**

```
z_mint_mine(z2sp, z2a, advitm, ledger_itm, pl, pr)
```
The parties need to be able to deposit money into the account. This mines a block with the simulated party and gives 10 coins to `pl` and `pr`. It assigned a delay of 0 to the txs and progresses the round by 1 to execute them.

```
z_tx_inputs(z2a, advitm, ledger_itm, ('deposit', 10), z2sp, z2p1, z2p2)
```
This deposits money into the channel by both `p1` and `p2`. The tx calls the contract so is delayed by 0 and the round is incremented.

**Note**: at this point **F_state** doesn't know about the transaction yet. It must poll the ledger for contract transactions. This will happen automaticall next time **F_state** is activated.

```
# Only one input
1| z_inputs(('pay', 2), z2p1)
2| z_ping(z2p1)
3| z_mine_blocks(8, z2sp, z2sp.to)
4| z_ping(a2fstate)
5| z_mine_blocks(1, z2sp, z2sp.to)
```
In this example, `p1` is providing some input and `p2` doesn't provide any, forcing the round the end due to the deadline.
The environment instructs `p1` to pay `p2` 2 coins. The environment then `pings` p1, which will read any new state **F_state** has a give **F_state** its input. This also forces **F_state** to see the deposit transaction. To force the end of the round, 8 on-chain rounds are executed. **F_state** is pinged and it checks the deadline and executes a state update. Finally one more round to deliver the state to the parties.

```
1| # Only one input by pr
2| z_inputs(('withdraw',5), z2p2)
3| z_inputs(('pay',2), z2p2)
4| z_ping(z2p2)
5| z_mine_blocks(8, z2sp, z2sp.to)
6| z_ping(a2fstate)
7| z_set_delays(z2a, advitm, ledger_itm, [0])
8| z_mine_blocks(1, z2sp, z2sp.to)
```
This case is similar, `p2` is paying 2 to `p1` and withdrawing coins in the same round. Similarly, only `p2` needs to be pinged, the rounds are incremented, **F_state** executes the state transition, but this time a transactions emerges! This is due to the withdraw. Line 7 tells the adversary to set the delay of the transaction and the last line delivers the state to the parties.

```
# two input
1| z_inputs(('pay',2), z2p1)
2| z_ping(z2p1, z2p2)
3| z_mine_blocks(1, z2sp, z2sp.to)
```
When both parties give input, the code is much simpler. Environment gives the input, pings both. Since they both gave input to **F_state** it will execute the state transition, and the last line delivers the state to the parties .

```
1| print('[GET BALANCE] \n\t', z_get_balance(pl, simparty, ledger_itm), '\n\t', z_get_balance(pr, simparty, ledger_itm), '\n\t', z_get_balance(simparty, simparty, ledger_itm))
```
Finally this just checkes the coin balances of all parties to confirm the withdraw was correctly processed. 

### Easier Way
This might seem pretty complicated, but once you understand the rules of the functionality, every round follows a similar structure depending on how many parties are giving input. **Even if you don't give input to both parties, if you ping both parties it will force a default input and force a state transition in F_state. This is also a good option for easy of use.
