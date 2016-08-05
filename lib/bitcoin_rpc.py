'''
    Implements simple interface to bitcoind's RPC.
'''

import simplejson as json
import base64
import traceback
from twisted.internet import defer
from twisted.web import client
from mining.interfaces import Interfaces
from lib import util
import stratum.logger
log = stratum.logger.get_logger('bitcoin_rpc')

class BitcoinRPC(object):

    def __init__(self, host, port, username, password):
        log.debug("Got to Bitcoin RPC")
        self.bitcoin_url = 'http://%s:%d' % (host, port)
        self.credentials = base64.b64encode("%s:%s" % (username, password))
        self.headers = {
            'Content-Type': 'text/json',
            'Authorization': 'Basic %s' % self.credentials,
        }
        client.HTTPClientFactory.noisy = False
        self.has_submitblock = False

    def _call_raw(self, data):
        client.Headers
        return client.getPage(
            url=self.bitcoin_url,
            method='POST',
            headers=self.headers,
            postdata=data,
        )

    def _call(self, method, params):
        return self._call_raw(json.dumps({
                'jsonrpc': '2.0',
                'method': method,
                'params': params,
                'id': '1',
            }))

    def _sb_debug_callback(self, data):
        log.info(json.dumps({"rsk" : "[RSKLOG]", "tag" : "[BTC_SB_RESPONSE]", "data" : data}))

    @defer.inlineCallbacks
    def submitblock(self, block_hex):                
        resp = (yield self._call('submitblock', [block_hex,]))
        if json.loads(resp)['result'] is None:
            defer.returnValue(True)
        else:
            defer.returnValue(False)


    @defer.inlineCallbacks
    def getinfo(self):
         resp = (yield self._call('getinfo', []))
         defer.returnValue(json.loads(resp)['result'])

    @defer.inlineCallbacks
    def getblocktemplate(self):
        try:
            resp = (yield self._call('getblocktemplate', [{}]))
            defer.returnValue(json.loads(resp)['result'])
        # if internal server error try getblocktemplate without empty {} # ppcoin
        except Exception as e:
            if (str(e) == "500 Internal Server Error"):
                resp = (yield self._call('getblocktemplate', []))
                defer.returnValue(json.loads(resp)['result'])
            else:
                raise

    @defer.inlineCallbacks
    def prevhash(self):
        resp = (yield self._call('getblocktemplate', []))
        try:
            print(json.loads(resp)['result']['previousblockhash'])
            defer.returnValue(json.loads(resp)['result']['previousblockhash'])
        except Exception as e:
            log.exception("Cannot decode prevhash %s" % str(e))
            raise

    @defer.inlineCallbacks
    def validateaddress(self, address):
        resp = (yield self._call('validateaddress', [address,]))
        defer.returnValue(json.loads(resp)['result'])
