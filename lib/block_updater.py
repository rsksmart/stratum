from twisted.internet import reactor, defer
from stratum import settings

import util
import json
import psutil
import os
from mining.interfaces import Interfaces

import stratum.logger
log = stratum.logger.get_logger('block_updater')

class BlockUpdater(object):
    '''
        Polls upstream's getinfo() and detecting new block on the network.
        This will call registry.update_block when new prevhash appear.

        This is just failback alternative when something
        with ./bitcoind -blocknotify will go wrong.
    '''

    def __init__(self, registry, bitcoin_rpc):
        self.bitcoin_rpc = bitcoin_rpc
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
        when = settings.PREVHASH_REFRESH_INTERVAL - (Interfaces.timestamper.time() - self.registry.last_update) % \
               settings.PREVHASH_REFRESH_INTERVAL
        return when

    @defer.inlineCallbacks
    def run(self):
        pid = psutil.Process(os.getpid())
        update = False

        try:
            log.info(json.dumps({"rsk" : "[RSKLOG]", "tag" : "[PROCESS]", "start" : Interfaces.timestamper.time(), "data" : {"threads" : [{"pid" : x[0], "cpu_percent" : psutil.Process(x[0]).cpu_percent()} for x in pid.threads()], "memory_percent" : pid.memory_percent()}}))
            if self.registry.last_block:
                current_prevhash = "%064x" % self.registry.last_block.hashPrevBlock
            else:
                current_prevhash = None

            prevhash = yield self.bitcoin_rpc.prevhash()
            if prevhash and prevhash != current_prevhash:
                start = Interfaces.timestamper.time()
                logid = util.id_generator()
                log.info("New block! Prevhash: %s" % prevhash)
                update = True
                log.info(json.dumps({"uuid" : logid, "rsk" : "[RSKLOG]", "tag" : "[BTC_NEW_BLOCK_PARENT]", "start" : start, "elapsed" : Interfaces.timestamper.time() - start}))

            elif Interfaces.timestamper.time() - self.registry.last_update >= settings.MERKLE_REFRESH_INTERVAL:
                log.info("Merkle update! Prevhash: %s" % prevhash)
                update = True

            if update:
                self.registry.update_block()
                log.info(json.dumps({"rsk" : "[RSKLOG]", "tag" : "[BTC_NEW_WORK_UNIT]", "uuid" : util.id_generator(), "start" : start, "elapsed" : Interfaces.timestamper.time() - start}))

        except Exception:
            log.exception("UpdateWatchdog.run failed")
        finally:
            self.schedule()
