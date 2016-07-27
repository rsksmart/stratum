from twisted.internet import reactor, defer
from stratum import settings

import util
import json
from mining.interfaces import Interfaces

import stratum.logger
log = stratum.logger.get_logger('rsk_block_updater')

class RSKBlockUpdater(object):
    '''
        Polls upstream's getinfo() and detecting new block on the network.
        This will call registry.update_block when new prevhash appear.

        This is just failback alternative when something
        with ./bitcoind -blocknotify will go wrong.
    '''

    def __init__(self, registry, rootstock_rpc):
        self.rootstock_rpc = rootstock_rpc
        self.registry = registry
        self.clock = None
        self.schedule()

    def schedule(self):
        when = self._get_next_time()
        #log.debug("Next prevhash update in %.03f sec" % when)
        #log.debug("Merkle update in next %.03f sec" % \
        #          ((self.registry.last_update + settings.MERKLE_REFRESH_INTERVAL)-Interfaces.timestamper.time()))
        self.clock = reactor.callLater(when, self.run)

    def _get_next_time(self):
        when = settings.RSK_POLL_PERIOD - (Interfaces.timestamper.time() - self.registry.rsk_last_update) % \
               settings.RSK_POLL_PERIOD
        return when

    @defer.inlineCallbacks
    def run(self):
        rsk_update = False

        try:
            if Interfaces.timestamper.time() - self.registry.rsk_last_update >= settings.RSK_POLL_PERIOD:
                print "--- ### UPDATING RSK ### ---"
                rsk_update = True
                print "--- ### END UPDATING RSK ### ---"
            if rsk_update:
                self.registry.rsk_update_block()

        except Exception:
            log.exception("RSKUpdateWatchdog.run failed")
        finally:
            self.schedule()
