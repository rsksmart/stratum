RSK Stratum setup.
==================


Testing
=======

Bitcoind
--------

1) Create a directories for bitcoind, and two diretories one for each instance

> mkdir btcd
> cd btcd
> mkdir A
> mkdir B


2) Now we launch bitcoind in regtest mode

> bitcoind -server -listen -port=31591 -rpcuser=admin -rpcpassword=admin -rpcport=32591 -datadir=./A -connect=localhost:31592 -regtest -daemon -debug

> bitcoind -server -listen -port=31592 -rpcuser=admin -rpcpassword=admin -rpcport=32592 -datadir=./B -connect=localhost:31591 -regtest -daemon -debug


3) We now can verify that it is running

> bitcoin-cli -regtest -rpcconnect=127.0.0.1 -rpcuser=admin -rpcpassword=admin -rpcport=32591 getinfo


4) The output have to something like this

{
  "version": 120000,
  "protocolversion": 70012,
  "walletversion": 60000,
  "balance": 0.00000000,
  "blocks": 0,
  "timeoffset": 0,
  "connections": 2,
  "proxy": "",
  "difficulty": 4.656542373906925e-10,
  "testnet": false,
  "keypoololdest": 1458240195,
  "keypoolsize": 101,
  "paytxfee": 0.00000000,
  "relayfee": 0.00001000,
  "errors": ""
}

5) Check what getblocktemplate returns

> bitcoin-cli -regtest -rpcconnect=127.0.0.1 -rpcuser=admin -rpcpassword=admin -rpcport=32591 getblocktemplate

If it returns an error

```
error code: -10
error message:
Bitcoin is downloading blocks...
```

We generate a block to start

> bitcoin-cli -regtest -rpcconnect=127.0.0.1 -rpcuser=admin -rpcpassword=admin -rpcport=32591 generate 1

```
[
  "716162d5acae71e322ab4531e2ac0be0771f110c4fd213c4306f7b7d09e45094"
]
```

Now getblocktemplate should work

> bitcoin-cli -regtest -rpcconnect=127.0.0.1 -rpcuser=admin -rpcpassword=admin -rpcport=32591 getblocktemplate

The output should be something like

```
{
  "capabilities": [
    "proposal"
  ],
  "version": 4,
  "previousblockhash": "716162d5acae71e322ab4531e2ac0be0771f110c4fd213c4306f7b7d09e45094",
  "transactions": [
  ],
  "coinbaseaux": {
    "flags": ""
  },
  "coinbasevalue": 5000000000,
  "longpollid": "716162d5acae71e322ab4531e2ac0be0771f110c4fd213c4306f7b7d09e450944",
  "target": "7fffff0000000000000000000000000000000000000000000000000000000000",
  "mintime": 1458241314,
  "mutable": [
    "time",
    "transactions",
    "prevblock"
  ],
  "noncerange": "00000000ffffffff",
  "sigoplimit": 20000,
  "sizelimit": 1000000,
  "curtime": 1458241367,
  "bits": "207fffff",
  "height": 2
}
```


RootstockJ
----------

0) Install Oracle Java 8

  > sudo add-apt-repository ppa:webupd8team/java
  > sudo apt-get update
  > sudo apt-get install oracle-java8-installer

1) Checkout RootstockJ source in a directory named RootstockJ

  > git clone https://github.com/rootstock/rootstockJ.git

2) Generate fat jar for RootstockJ

  - Inside RootstockJ's directory (where it was cloned on step 1), run the following command:

  > gradle shadow

- The fat jar will be generated in ethereumj-core/build/libs/

3) Run miner

  > java -Dethereumj.conf.file=node1.conf -cp rootstock.jar io.rootstock.Start

  - rootstock.jar is the name of the fatjar.
  - Configuration file for node1 is named node1.conf.
  - node1.conf is in the same folder as the jar.
  - Node1 will be listening for RPC at 127.0.0.1:4444.

Stratum Installation Instructions
=================================

Python 2.7 must be installed. If it is not, this guide should be followed:
[Python installation instructions](http://docs.python-guide.org/en/latest/starting/installation/)

On Linux we must also install some additional packages.

  > sudo apt-get install python-pip python-dev libffi-dev libssl-dev libxml2-dev libxslt1-dev libjpeg8-dev zlib1g-dev

Pip must also be installed in order to install the required python packages. [Pip installation instructions](https://pip.pypa.io/en/stable/installing/)

We will set up a virtualenv in order to have an environment for Stratum. We will be using this implementation: [Virtualenv-burrito](https://github.com/brainsik/virtualenv-burrito)

Once these programs are installed, we will make an environment:

  > mkvirtualenv rskstratum

We will be in the rskstratum virtual environment, in which we must install several pip packages.

  > pip install twisted pyopenssl stratum simplejson pycrypto

A Stratum library file must be modified:
~/.virtualenvs/rskstratum/local/lib/python2.7/site-packages/stratum/websocket_transport.py:1

from
  > from autobahn.websocket import WebSocketServerProtocol, WebSocketServerFactory

to

  > from autobahn.twisted.websocket import WebSocketServerProtocol, WebSocketServerFactory

We will switch to the rsk-plugin branch:

  > git checkout rsk-plugin

The pool will be launched through the following command, once the bitcoind instances and rskd instance are running:

> twistd -ny launcher_demo.tac -l -

Once launched, a minerd instance can be pointed at the server:

> minerd -a sha256d -t 2 --url=stratum+tcp://192.168.0.121:3333 --userpass=user:pass
