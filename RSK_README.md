Specifics for RSK Stratum setup.

---

Para poder minar correctamente en un nodo local de Stratum, seguir la parte 'Testing'
de la guia de README_Rootstock.txt, que esta todo cubierto. Tambien habra que instalar
las diferentes librerias requeridas (twisted, stratum, pyopenssl - TODO: requirements.txt)

El archivo conf/settings_default.py se debe renombrar a config.py.
BITCOIN_TRUSTED_PORT corresponde al puerto RPC al cual nos vamos a conectar (32591)
CENTRAL_WALLET debe ser una direccion valida (generar con bitcoin-cli getnewaddress)

La funcion prevhash de bitcoin_rpc.py debe quedar asi, ya que no se utiliza mas getwork:

@defer.inlineCallbacks
def prevhash(self):
	resp = (yield self._call('getblocktemplate', []))
	try:
		print(json.loads(resp)['result']['previousblockhash'])
		defer.returnValue(json.loads(resp)['result']['previousblockhash'])
	except Exception as e:
		log.exception("Cannot decode prevhash %s" % str(e))
		raise

Habra que modificar una libreria que usa Stratum:
Ir a /usr/local/lib/python2.7/dist-packages/stratum/websocket_transport.py
Cambiar

from autobahn.websocket import

a from autobahn.twisted.websocket import

---

Launch command: twistd -ny launcher_demo.tac -l -
