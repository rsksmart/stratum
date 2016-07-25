'''
    Implements simple interface to bitcoind's RPC.
'''

import simplejson as json
import base64
import traceback
from twisted.internet import defer
from twisted.web import client

import stratum.logger
log = stratum.logger.get_logger('bitcoin_rpc')

class BitcoinRPC(object):

    def __init__(self, host, port, username, password, rsk_host=None, rsk_port=None, rsk_username=None, rsk_password=None):
        log.debug("Got to Bitcoin RPC")
        self.bitcoin_url = 'http://%s:%d' % (host, port)
        self.credentials = base64.b64encode("%s:%s" % (username, password))
        self.headers = {
            'Content-Type': 'text/json',
            'Authorization': 'Basic %s' % self.credentials,
        }
        client.HTTPClientFactory.noisy = False
        self.has_submitblock = False
        '''
        RSK specific settings; if BitcoinRPC is given RSKD settings, set it up

        if rsk_host != None:
            self.rskd_url = 'http://%s:%d' % (rsk_host, rsk_port)
            self.rskd_cred = base64.b64encode("%s:%s" % (rsk_username, rsk_password))
            self.rskd_headers = {
                'Content-Type' : 'text/json',
                'Authorization' : 'Basic %s' % self.rskd_cred,
            }
            self.rskds = True
            self.has_rsk_submitblock = False
            self.rsk_blockhashformergedmining = None
            self.rsk_header = None
            self.rsk_last_header = None
            self.rsk_diff = None
            self.rsk_miner_fees = None
            self.rsk_parent_hash = None
            self.rsk_last_parent_hash = None
            self.rsk_notify = None
            self.rsk_new = None
            self.rsk_debug = ''
        '''

    def _call_raw(self, data, rsk=None):
        client.Headers
        if rsk is None:
            return client.getPage(
                url=self.bitcoin_url,
                method='POST',
                headers=self.headers,
                postdata=data,
            )
        else:
            return client.getPage(
                url = self.rskd_url,
                method = 'POST',
                headers = self.headers,
                postdata = data
            )

    def _call(self, method, params, rsk=None):
        if rsk is None:
            return self._call_raw(json.dumps({
                    'jsonrpc': '2.0',
                    'method': method,
                    'params': params,
                    'id': '1',
                }))
        else:
            return self._call_raw(json.dumps({
                    'jsonrpc': '2.0',
                    'method': method,
                    'params': params,
                    'id': '1',
                }), rsk)

    @defer.inlineCallbacks
    def submitblock(self, block_hex, rsk=None):
        if rsk is None:
            resp = (yield self._call('submitblock', [block_hex,]))
            if json.loads(resp)['result'] == None:
                defer.returnValue(True)
            else:
                defer.returnValue(False)
        else:
            print "------ ### RSK SUBMIT BLOCK ### ------"
            print block_hex
            resp = (yield self._call('mnr_submitBitcoinBlock', [block_hex,], True))
            if json.loads(resp)['result'] == None:
                defer.returnValue(True)
            else:
                defer.returnValue(False)
            print "---- ### END_RSK SUBMIT BLOCK ### ----"

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
    def getwork(self):
        '''
        RSK getwork implementation
        '''
        try:
            resp = (yield self._call('mnr_getWork', [], True))
            defer.returnValue(json.loads(resp)['result'])
        except Exception as e:
            log.exception("RSK getwork failed: %s", e)
            raise

    '''
    from lib.bitcoin_rpc import BitcoinRPC
    btcrpc = BitcoinRPC('127.0.0.1', 32592, 'admin', 'admin', '127.0.0.1', 4444, 'admin', 'admin')
    '''


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
