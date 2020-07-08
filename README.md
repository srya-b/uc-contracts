# uc-contract
This is a python implementation of the UC framework alongside the changes required for smart contract applications to be expressed.


## Folder structure

`paper/`: Our proposed paper. Using Makefile to compile the PDF.

`papers/`: Other reference papers.

`src/sync_ours`: Our implementation under synchronous assumption. 

`src/async_ours`: Our implementation under asynchronous assumption. The postfix of `_bracha` refers to the [*Asynchornous Byzentine Agreement Protocols*](https://core.ac.uk/reader/82523202) proposed by Gabriel Bracha.

`src/sync_katz`: Katz's implementation under synchronous assumption ([ref](https://eprint.iacr.org/2011/310.pdf))


