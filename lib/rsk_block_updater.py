from twisted.internet import reactor, defer
from stratum import settings
import util
import json
from mining.interfaces import Interfaces

import stratum.logger
log = stratum.logger.get_logger('rsk_block_updater')

class RSKBlockUpdater(object):
    '''
        RSK block updater functionality.
    '''

    def __init__(self, registry, rootstock_rpc):
        self.rootstock_rpc = rootstock_rpc
        self.registry = registry
        self.clock = None
        if hasattr(settings, 'RSK_POLL_PERIOD') and settings.RSK_POLL_PERIOD != 0:
            self.timer = settings.RSK_POLL_PERIOD
        else:
            self.timer = settings.PREVHASH_REFRESH_INTERVAL
        self.schedule()


    def shutdown(self):
        self.rootstock_rpc = None
        self.registry = None

    def schedule(self):
        when = self._get_next_time()
        self.clock = reactor.callLater(when, self.run)

    def _get_next_time(self):
        when = self.timer - (Interfaces.timestamper.time() - self.registry.rsk_last_update) % \
               self.timer
        return when

    def yielder(self):
        '''
        Necessary as twisted expects self.run to return a generator.
        '''
        log.debug("")

    @defer.inlineCallbacks
    def run(self):
        if self.rootstock_rpc.active:
            start = Interfaces.timestamper.time()
            rsk_update = False
            try:
                log.debug(str("RSKBLOCKUPDATER.RUN: " + str(Interfaces.timestamper.time() - self.registry.rsk_last_update)))
                if Interfaces.timestamper.time() - self.registry.rsk_last_update >= self.timer:
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
