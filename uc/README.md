# SAUCy
This is an imlementation of the basic UC framework. It provides code to specify functionalities, protocols, and adversaries, and provides an execution environment to run real and ideal word executions. 


## Installation
Installation is easy (we assume `python>=3.5`)
* Clone the repo and go into the `uc_contracts/` directory.
* Install the dependencies with ```pip install -r uc/requirements.txt```
* Install the the `uc` module as a working module with ```pip install -e .```

If you're able to run `python uc/apps/coinflip/env.py` successfully and get output you're good to go!

## Folder structure

* `uc/`: Python UC module that implements the basic framework
  * `itm.py`: implements the ITM
  * `protocol.py`: the base class for all protocols and the `ProtocolWrapper` and the `DummyParty`
  * `functionality.py`: the base class for all functionalities
  * `adversary.py`: the base for all adversaries and the `DummyAdversary`
  * `execuc.py`: executes a UC experiment given an environment, functionality, protocol, and adversary
  * `compose.py`: a composition operator for protocols and simulators
  * `utils.py`: some handy functions
* `uc/apps/`: Examples of using the Python UC module
  * `commitment/`: an example of a bit commitment in the random oracle model
  * `coinflip/`: a coin flip that uses bit commitment
  * `simplecomp/`: composition example, deplaces F_com with commitment protocol

## Things unique from the UC framework
We use a construct called the `ProtocolWrapper` in `protocol.py`. This wrapper encapsulates the "protocol" and internaly creates instances of the protocol as protocol parties. It also routes messages to/from the protocol parties based on the intended `pid` recipient of the messages that it receives. 
Protocols in UC are usually not in any kind of wrapper and therefore, from their point of view, are communicating over a channel directly to the functionality or the environment. Therefore, the `ProtocolWrapper` ensures this is the view of the parties. 
A consequence of the wrapper is that the functionality, adversary, and environment need to know the `pid` of the messages received by the wrapper. 
The parties themselves don't add their `pid` to messages because they "think" they are directly communicating to other with a dedicated channel. Therefore, the wrapper appends the `pid` of the sending parties to all outgoing messages by them.
**See the docstring for the `ProtocolWrapper` for a more in depth explanation.**
