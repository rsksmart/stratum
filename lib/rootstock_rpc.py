'''
    Implements simple interface to rootstock's RPC.
'''

import base64
import simplejson as json
from twisted.internet import defer
from twisted.web import client
from mining.interfaces import Interfaces
from lib import util
from util import Singleton
import stratum.logger
from stratum import settings
log = stratum.logger.get_logger('rootstock_rpc')

class RootstockRPC(object):
    __metaclass__ = Singleton
    '''
    Rootstock RPC class
    '''

    def __init__(self, rsk_host, rsk_port, rsk_username, rsk_password):
        log.debug("Got to Rootstock RPC")
        client.HTTPClientFactory.noisy = False
        client.HTTPClientFactory.timeout = settings.RSK_POLL_PERIOD
        self.active = True

        self.rskd_url = 'http://%s:%d' % (rsk_host, rsk_port)
        self.rskd_cred = base64.b64encode("%s:%s" % (rsk_username, rsk_password))
        self.headers = {
            'Content-Type' : 'text/json',
            'Authorization' : 'Basic %s' % self.rskd_cred,
        }
        self.rskds = True
        self.has_rsk_submitblock = False
        self.rsk_blockhashformergedmining = None
        self.rsk_header = None
        self.rsk_last_header = None
        self.rsk_target = None
        self.rsk_miner_fees = None
        self.rsk_parent_hash = None
        self.rsk_last_parent_hash = None
        self.rsk_notify = None
        self.rsk_new = None
        self.rsk_debug = ''

    def _call_raw(self, data):
        #client.Headers
        return client.getPage(
            url=self.rskd_url,
            method='POST',
            headers=self.headers,
            postdata=data
        )

    def _call(self, method, params):
        return self._call_raw(json.dumps({
            'jsonrpc': '2.0',
            'method': method,
            'params': params,
            'id': '1',
        }))

    def shutdown(self):
        self.active = False
        self.rskds = False
        self.has_rsk_submitblock = False
        self.rsk_blockhashformergedmining = None
        self.rsk_header = None
        self.rsk_last_header = None
        self.rsk_target = None
        self.rsk_miner_fees = None
        self.rsk_parent_hash = None
        self.rsk_last_parent_hash = None
        self.rsk_notify = None
        self.rsk_new = None
        self.rsk_debug = ''

    @defer.inlineCallbacks
    def submitblock(self, block_hex):
        '''
        Rootstock RPC mnr_submitBitcoinBlock handler
        '''
        if self.active:
            resp = (yield self._call('mnr_submitBitcoinBlock', [block_hex,]))
            if json.loads(resp)['result'] is None:
                defer.returnValue(True)
            else:
                defer.returnValue(False)

    @defer.inlineCallbacks
    def getwork(self):
        '''
        RSK getwork implementation
        '''
        if self.active:
            try:
                resp = (yield self._call('mnr_getWork', []))
                defer.returnValue(json.loads(resp)['result'])
            except Exception as e:
                log.exception("RSK getwork failed: %s", e)
                raise
