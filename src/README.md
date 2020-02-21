# uc-contract
This is a python implementation of the UC framework alongside the changes required for smart contract applications to be expressed.
The only dependency of the project is **gevent** and the version of python is **3.5.3**.

## Tutorial
This tutorial will run though how to create create the ideal world functionality and and the real protocol in this framework and run a UC experiment with an user-specified environment. 
First, we introduce the basic ITMs for protocol participants and the adversary.

### Implementing a protocol and creating ITMs that execute it
The basic functionality of an ITM is located in `itm.py`. This file defines a bunch of classes that implement different kind of ITMs. Theroretically, all ITMs are the same, but due to differences in what they can do, ITMs for the adversary, functionalities, passthrough parties, and parties running a protocol are different classes. 

#### ITMs
All communication between ITMs (i.e. one ITM writing to the input tape of another ITM) is handled through channels described by the `GenChannel` class. The channel inherits `gevent.Event` that provides a signal to waiting threads in the program.
There's also simple read/write functions. Nothing too interesting.

There are three main ITM classes, `ITMFunctionality`, `ITMProtocol`, `ITMPassthrough`. There is usually no need to directly access these classes. Most often they will be used through the wrappers `FunctionalityWrapper`, `ProtocolWrapper`, `PassthroughWrapper`. These wrappers provide some neat functionality:
* They spawn ITMs of the type at the first message sent to them. Dynamic creation of ITMs is a handly tool for the environment.
* It routes messages to the ITMs they wrap around.

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

**Note**: this protocol actually inherits from `ITMSyncProtocol` (from `itm.py`) which defines Katz-specific functionality that this protool will use.
