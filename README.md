# uc-contract
This is a python implementation of the UC framework alongside the changes required for smart contract applications to be expressed.


## Installation
Use `pip install -r requirements.txt` to install all required pip modules for this project. Don't forget to run `pip install -e uc/` to install this `uc/` local module before running the codes inside this project. Python version is **>= 3.5.3**.


## Folder structure

`paper/`: Our proposed paper. Using Makefile to compile the PDF.

`papers/`: Other reference papers.

`uc/`: Python UC module

`apps/`: Examples of using python UC module


### Files under `uc/`
> more detailed explanation of `uc/` could be referred to the `README.md` inside `uc/` folder.

`itm.py`: basic class of Interactive Turing Machine(ITM).

`adversary.py`: basic class of adversary.

`exeuc.py`: {execute|create} (wrapped)UC.

`utils.py`: utility functions that are used by ITM.

`sync_ours/`: Our implementation under synchronous assumption.

`async_ours/`: Our implementation under asynchronous assumption. The postfix of `_bracha` refers to the [*Asynchornous Byzentine Agreement Protocols*](https://core.ac.uk/reader/82523202) proposed by Gabriel Bracha.

`{sync|async}_ours/f_bracha.py`: ideal functionality + simulator

`{sync|async}_ours/prot_bracha.py`: protocol

`{sync|async}_ours/env1.py`: environment. It executes `ideal functionality` and `protocol`, and then run the distinguisher function to check that if the output transcripts are the same. It is falsifiable.

`sync_katz/`: Katz's implementation under synchronous assumption ([ref](https://eprint.iacr.org/2011/310.pdf))


### Files under `uc/`
`bracha/`: example of bracha protocol

`commitment/`: example of commitment protocol

`payment/`: example of uni-directional payment channel


## Other modules used in this project

`gevent`: [gevent](https://www.gevent.org/) is a [coroutine](https://en.wikipedia.org/wiki/Coroutine)-based Python networking library that uses `greenlet` to provide a high-level synchronous API on top of the `libev` or `libuv` event loop.

Features include:

- Fast event loop based on `libev` or `libuv`.

- Lightweight execution units based on `greenlets`.

- API that re-uses concepts from the Python standard library (for examples there are events and queues).

- Cooperative sockets with SSL support

- Cooperative DNS queries performed through a threadpool, dnspython, or c-ares.

- Monkey patching utility to get 3rd party modules to become cooperative

- TCP/UDP/HTTP servers

- Subprocess support (through gevent.subprocess)

- Thread pools

(above are excerpted from [official website](https://www.gevent.org/))

`inspect` (built-in): The inspect module provides several useful functions to help get information about live objects such as modules, classes, methods, functions, tracebacks, frame objects, and code objects.

