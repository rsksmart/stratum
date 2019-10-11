Stratum mining pool
===================

Demo implementation of bitcoin mining pool using Stratum mining protocol.

For Stratum mining protocol specification, please visit http://mining.bitcoin.cz/stratum-mining.

Contact
-------

This pool implementation is provided by http://mining.bitcoin.cz. You can contact
me by email info(at)bitcoin.cz or on IRC #stratum on freenode.

RSK changes
===========

The following changes were applied in order for the pool to work properly:

- Change a library used by Stratum. In file /usr/local/lib/python2.7/dist-packages/stratum/websocket_transport.py replace
```python
from autobahn.websocket import
``` 
with 
```python 
from autobahn.twisted.websocket import
```
