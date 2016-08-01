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

    def shutdown(self):
        self.rootstock_rpc = None
        self.registry = None

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

    def yielder(self):
        log.debug("")

    @defer.inlineCallbacks
    def run(self):
        if self.rootstock_rpc.active:
            start = Interfaces.timestamper.time()
            rsk_update = False
            try:
                log.debug(str("RSKBLOCKUPDATER.RUN: " + str(Interfaces.timestamper.time() - self.registry.rsk_last_update)))
                if Interfaces.timestamper.time() - self.registry.rsk_last_update >= settings.RSK_POLL_PERIOD:
                    rsk_update = True
                    log.info(json.dumps({"uuid" : util.id_generator(), "rsk" : "[RSKLOG]", "tag" : "[RSK_WORK_RECEIVED]", "start" : start, "elapsed" : Interfaces.timestamper.time() - start}))
                if rsk_update:
                    self.registry.rsk_update_block()
            except Exception:
                log.exception("RSKUpdateWatchdog.run failed")
            finally:
                self.schedule()
                yield self.yielder()
        else:
            rsk_update = True
            self.shutdown()
