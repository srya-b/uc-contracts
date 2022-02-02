# MultiSession Commitment
The traditional commitment protocol is one-shot meaning it only allows commitment to *one* value. 
More often than not a protocol requires commitment to multiple values throughout the protocol.
This example application shows two ways to implement a multi-commit in UC: one using the multisession operator defined in `uc/multisession.py` and one that simply appends an `id` to each commitment.

### What's the difference?
The difference is re-usability of code.

The multisession extension of a protocol does the following:
```python
# a protocol whose messages to the hybrid functionality 
# that look like this
(pid, msg)

# turn into this when it is wrapped in !p
(pid, (ssid, msg))
```
The consequence of this is that the hybrid functionality must change how it parses/handles incoming messages.
A functionality that works with a single-shot commitment protocol, such as `F_CRS` here, can not be reused with `!prot_com`. 
Instead, to use `!prot_com` (and, therefore, `!F_com`) we create `F_mcrs` which handles messages from different subsessions of a protocol inside `!p`.


Another equally valid approach is to design the functionality and protocol like `f_mcom.py` and `prot_mcom.py` where the `id` of each commitment is managed internally and no messages from `prot_mcom` to `f_crs` include any information about multiple sessions. 

### Running Examples
The files for the latter case of multi-commit (protocol internally handles different sessions and reuses `f_crs`) is contained within `prot_mcom.py`, `f_mcom`, `sim_mcom`, and `f_crs`. 
The example is run in any of `env_honest.py`, `env_malleable.py`.

The multisession extension of the commitment to achieve pederesen multicommit is contained in `prot_com.py`, `f_com.py`, and `f_mcrs.py`. There is no simluator for this way of doing it but creating one given `sim_mcom.py` shouldn't be very hard. You can run this example and see the different message *types* with `env_bangfcom.py`. 
