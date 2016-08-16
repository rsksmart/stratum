from service import MiningService
from subscription import MiningSubscription
from twisted.internet import defer
import time
import traceback
import os

@defer.inlineCallbacks
def setup(on_startup):
    '''Setup mining service internal environment.
    You should not need to change this. If you
    want to use another Worker manager or Share manager,
    you should set proper reference to Interfaces class
    *before* you call setup() in the launcher script.'''

    from stratum import settings
    from interfaces import Interfaces

    # Let's wait until share manager and worker manager boot up
    (yield Interfaces.share_manager.on_load)
    (yield Interfaces.worker_manager.on_load)

    from lib.block_updater import BlockUpdater
    from lib.rsk_block_updater import RSKBlockUpdater
    from lib.template_registry import TemplateRegistry
    from lib.bitcoin_rpc import BitcoinRPC
    from lib.rootstock_rpc import RootstockRPC
    from lib.block_template import BlockTemplate
    from lib.coinbaser import SimpleCoinbaser

    import stratum.logger
    log = stratum.logger.get_logger('mining')
    log.info("CWD: %s", os.getcwd())
    log.info("### INITIALIZING RSK STRATUM - CONFIG.PY DUMP ###")
    with open("conf/config.py", "r") as f:
        for line in f:
            log.info(line)
    log.info("### INITIALIZING RSK STRATUM - END CONFIG.PY DUMP ###")

    if hasattr(settings, 'RSK_TRUSTED_HOST'):
        rootstock_rpc = RootstockRPC(settings.RSK_TRUSTED_HOST,
                                     settings.RSK_TRUSTED_PORT,
                                     settings.RSK_TRUSTED_USER,
                                     settings.RSK_TRUSTED_PASSWORD)
    else:
        rootstock_rpc = None

    bitcoin_rpc = BitcoinRPC(settings.BITCOIN_TRUSTED_HOST,
                             settings.BITCOIN_TRUSTED_PORT,
                             settings.BITCOIN_TRUSTED_USER,
                             settings.BITCOIN_TRUSTED_PASSWORD)

    log.info('Waiting for bitcoin RPC...')

    while True:
        try:
            result = (yield bitcoin_rpc.getblocktemplate())
            if isinstance(result, dict):
                log.info('Response from bitcoin RPC OK')
                break
        except Exception as e:
            time.sleep(1)

    coinbaser = SimpleCoinbaser(bitcoin_rpc, settings.CENTRAL_WALLET)
    (yield coinbaser.on_load)

    registry = TemplateRegistry(BlockTemplate,
                                coinbaser,
                                bitcoin_rpc,
                                settings.INSTANCE_ID,
                                MiningSubscription.on_template,
                                Interfaces.share_manager.on_network_block,
                                rootstock_rpc)

    # Template registry is the main interface between Stratum service
    # and pool core logic
    Interfaces.set_template_registry(registry)

    # Set up polling mechanism for detecting new block on the network
    # This is just failsafe solution when -blocknotify
    # mechanism is not working properly
    BlockUpdater(registry, bitcoin_rpc)
    if rootstock_rpc is not None:
        RSKBlockUpdater(registry, rootstock_rpc)

    log.info("MINING SERVICE IS READY")
    on_startup.callback(True)
