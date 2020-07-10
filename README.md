# uc-contract
This is a python implementation of the UC framework alongside the changes required for smart contract applications to be expressed.


## Folder structure

`paper/`: Our proposed paper. Using Makefile to compile the PDF.

`papers/`: Other reference papers.

`src/sync_ours`: Our implementation under synchronous assumption.

`src/async_ours`: Our implementation under asynchronous assumption. The postfix of `_bracha` refers to the [*Asynchornous Byzentine Agreement Protocols*](https://core.ac.uk/reader/82523202) proposed by Gabriel Bracha.

`src/{sync|async}_ours/f_bracha.py`: ideal functionality + simulator

`src/{sync|async}_ours/prot_bracha.py`: protocol

`src/{sync|async}_ours/env1.py`: environment. It executes `ideal functionality` and `protocol`, and then run the distinguisher function to check that if the output transcripts are the same. It is falsifiable.

`src/sync_katz`: Katz's implementation under synchronous assumption ([ref](https://eprint.iacr.org/2011/310.pdf))


### Files under `src/`
> more detailed explanation of files under `src/` could refer to the `README.md` inside `src/` folder.

`src/`: it is also a local python module.

`src/itm.py`: basic class of Interactive Turing Machine(ITM)

`src/adversary.py`: basic class of adversary

`src/comm.py`: TODO

`src/dump.py`: TODO

`src/exeuc.py`: {execute|create} (wrapped)UC.

`src/utils.py`: TODO


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

