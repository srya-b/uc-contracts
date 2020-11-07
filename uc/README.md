# uc-contract
This is a python implementation of the UC framework alongside the changes required for smart contract applications to be expressed.


## Tutorial
This tutorial will run though how to create the ideal world functionality and and the real protocol in this framework and run a UC experiment with an user-specified environment.
First, we introduce the basic ITMs for protocol participants and the adversary.


### Implementing a protocol and creating ITMs that execute it
The UC framework is based on interactive turing machines (ITMs) that are defined by input and output tapes.
An ITM has several input tapes that other ITMs can write to, and it, in turn, can write to the tapes of other ITMs.
In an execution of a UC experiment only one ITM can be activated at any time.
At the beginning the environment is activate and it activates other ITMs by writing to their input tapes.
If an ITM completes execution and doesn't activate another ITM, the environment is activated again.


### ITMs
The basic ITM class, `class ITM`, is defined in `itm.py`.

* Every ITM has an identity made up of `(sid, pid)`. `sid` is the id for this protocol session, `pid` is the ID of the ITM within this this session.
* Instead of using common tapes for all ITMs to write to, we use uni-directional channels.
The `channels` dictionary consists of pairs of channels to communicate to other ITMs.
For example a protocol party can read/write from/to a functionality, the adversary or the environment.
Therefore, the `channels` would be populated with `channels['p2f'], channels['f2p'], channels['p2a']` and so on.
Channels are uni-directional so each communication path consists of 2 channels.
* The ITM is also parammeterized by `handlers` that are functions which are called when a specific channel is written to.
Classes inheriting the basic `ITM` class define the handlers for each channel they read on.


### Handling Import
The new import mechanism in the UC paper is used to guarantee polynomial time execution of  UC experiment.
The basic idea is that there are a finite number of import tokens that are bound by a polynomial and ITMs require
import tokens to be able to do some computation.
This repo implements import as an optional mechanism.


#### Disabling Import
ITMs also accept a dictionary `importargs` that determine things about the import mechanism.


# INCOMPLETE and OUT OF DATE BELOW

#### Adversary
In `adversary.py` you'll find the DummyAdversary. This adversary doesn't do anything except forward messages from the environment. (This is the strongest adversary against which a protocol can be proven secure.)
The DummyAdversary defines a function `corrupt` that the environment can call to corrupt parties.
The adversary keeps a set of all corrupted parties that's available to everyone.
For special frameworks, like the Katz Synchronous UC (citation needed) framework, a new adversary needs to be derived that modifies the corrupt function to conform to the framework. You can find the extension of this adversary in `syn_katz/adv.py`.


#### Example (Bracha Broadcast)
Here I walk through an example and all the parts requires to implement a protocol as an ITM in this framework.
Take a look at `f_bracha/prot_bracha.py`. There is 1 classes in this file: `Bracha_Protocol` (the implementation of the bracha broadcast protocol found here: TODO).

```python
class Bracha_Protocol(ITMSyncProtocol):
    def __init__(self, sid, pid, _p2f, _f2p, _p2a, _a2p, _p2z, _z2p):
        # All protocols do this (below)
        self.p2f = _p2f; self.f2p = _f2p
        self.p2a = _p2a; self.a2p = _a2p
        self.p2z = _p2z; self.z2p = _z2p
        self.channels_to_read = [self.a2p, self.z2p, self.f2p]
        self.handlers = {
            self.a2p: lambda x: dump.dump(),
            self.f2p: lambda x: dump.dump(),
            self.z2p: self.input_msg
        }
```

The parameters for the constructors of most protocols will be exactly the same: an `sid`, a `pid`, and channels to communicated with other ITMs. For example, `_p2f` is for this ITM to write to a functionality (in reality, the functionality wrapper).
Furthermore, every protocol inherits functions from some ITM class. Therefore, this class must mark which channels it will read on with `self.channels_to_read` (`a2p`, `z2p`, `f2p`) and which functions handle messages on those channels in `self.handlers`.
For this ITM we define a funtion `input_msg` that handles messages coming from the environment. The other two channels don't do anything for two reasons:
* `f2p`: In this experiment there are no functionalities that write to this party on their own.
* `a2p`: This protocol, by it's very existence is honest (corrupt parties in the real world are replaced with a passthrough party) and therefore, will never expect messages from the adversary.

**Note**: this protocol actually inherits from `ITMSyncProtocol` (from `itm.py`) which defines Katz-specific functionality that this protool will use. The only difference is an additional action that happens on `corrupt`.

The handlers above refer to the function `input_msg`. This function is shown below:
```python
    def input_msg(self, msg):
        if msg[0] == 'input' and self.leader:
            self.input_input(msg[1])
        elif msg[0] == 'output':
            self.check_round_ok()
        else: dump.dump()
```
This function jst parses the message and calls the relevant functions. The `check_round_ok` function is a Katz-specific function that is already implemented in the base class. I'd recommend just checking out the paper to understand it better.
For the purposes of learning to use python-saucy it's not really important to understand the implementation of any of the Katz-specific function. It's sufficient to understand the pieces.


#### Running the real world
In the same file, `f_bracha/prot_bracha.py`, you'll find a sample environment that runs the real world, `test_all_honest()`.
The sid is set as follows, because the parties and functionalities in this run will parse that to learn the set of parties.
```python
sid = ('one', 4, (1,2,3))
```
Next all the channels that will be used are created:
```python
    f2p,p2f = GenChannel('f2p'),GenChannel('p2f')
    f2a,a2f = GenChannel('f2a'),GenChannel('a2f')
    f2z,z2f = GenChannel('f2z'),GenChannel('z2f')
    p2a,a2p = GenChannel('p2a'),GenChannel('a2p')
    p2z,z2p = GenChannel('p2z'),GenChannel('z2p')
    z2a,a2z = GenChannel('z2a'),GenChannel('a2z')
```

Next up we initialize the functionalities for this run. Here we use the functionality wrapper that spawns new ITMs on request.
```python
    f = FunctionalityWrapper(p2f,f2p, a2f,f2a, z2f,f2z)
    gevent.spawn(f.run)
    f.newcls('F_clock', Clock_Functionality)
    f.newcls('F_bd', BD_SEC_Functionality)
```
The channels are passed into the wrapper and the script must tell the wrapper what functionalities are to be included and the class that implements them.

Next we create the dummy adversary. In this case, as we're dealing with the Katz framework, the dummy adversary is modified a little by `KatzDummyAdversary` to also inform the functionality `F_clock` of the corruption.
```python
    advitm = KatzDummyAdversary('adv',-1, z2a,a2z, p2a,a2p, a2f,f2a)
    setAdversary(advitm)
    gevent.spawn(advitm.run)
```

Lastly we initialize the wrapper that handles the parties:
```python
    p = ProtocolWrapper(sid, z2p,p2z, f2p,p2f, a2p,p2a, Bracha_Protocol)
    gevent.spawn(p.run)
```

The last step in this environment is having to call `spawn` on the different parties that will be used in this round. This does defeat the purpose of the wrapper spawning parties on command, but the Katz framework already defines the set of parties in the `sid` of the functionalities.
Additionally, the Katz framework requires a special first action for all of the parties that necessitates having to call `spawn`.
```python
    # Start synchronization requires roundOK first to determine honest parties
    # giving input to a party before all have done this will result in Exception
    p.spawn(1); wait_for(a2z)
    p.spawn(2); wait_for(a2z)
    p.spawn(3); wait_for(a2z)
```

In the snippet above, there's a function call `wait_for(a2z)` in here. This function is at the heart of how the UC framework is implemented.
Namely, the control function that determines when control comes back to the environment. In python-saucy when and ITM is activates, it can either write to another ITM or dump control back to the environment with `dump.dump()` <-- you'll see that everywhere in the code.
`wait_for` tries to wait and read on the channel passed in to it. Gevent throws an error when it knows a waiting action will block foever. Therefore, `wait_for` waits for either a write on the channel specified or for some ITM to dump control back to the environment. `wait_for` is necessary after every write the environment makes. **In future iterations of the code base, I'll try to abstract away, but certainly there are times when you want to read on certain channels, as the environment, and assert certain outputs.**

Finally, environment starts passing input into the parties by writing to `z2p`:
```python
    ## DEALER INPUT
    z2p.write( (1, ('input',10)) )
    wait_for(a2z)
```

