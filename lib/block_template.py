import StringIO
import binascii
import struct
import json
import util
import merkletree
import halfnode
from mining.interfaces import Interfaces
from coinbasetx import CoinbaseTransaction

# Remove dependency to settings, coinbase extras should be
# provided from coinbaser
from stratum import settings
import stratum.logger
log = stratum.logger.get_logger('block_template')

class BlockTemplate(halfnode.CBlock):
    '''Template is used for generating new jobs for clients.
    Let's iterate extranonce1, extranonce2, ntime and nonce
    to find out valid bitcoin block!'''

    coinbase_transaction_class = CoinbaseTransaction

    def __init__(self, timestamper, coinbaser, job_id, rsk=None):
        super(BlockTemplate, self).__init__()

        self.job_id = job_id
        self.timestamper = timestamper
        self.coinbaser = coinbaser

        self.prevhash_bin = '' # reversed binary form of prevhash
        self.prevhash_hex = ''
        self.timedelta = 0
        self.curtime = 0
        self.target = 0
        #self.coinbase_hex = None
        self.merkletree = None
        if rsk != None:
            self.rsk_flag = True

        self.broadcast_args = []

        # List of 4-tuples (extranonce1, extranonce2, ntime, nonce)
        # registers already submitted and checked shares
        # There may be registered also invalid shares inside!
        self.submits = []

    def fill_from_rpc(self, data):
        '''Convert getblocktemplate result into BlockTemplate instance'''
        #txhashes = [None] + [ binascii.unhexlify(t['hash']) for t in data['transactions'] ]
        txhashes = [None] + [ util.ser_uint256(int(t['hash'], 16)) for t in data['transactions'] ]
        mt = merkletree.MerkleTree(txhashes)

        if 'rsk_flag' in data and 'rsk_header' in data and data['rsk_header'] != None:
            coinbase = self.coinbase_transaction_class(self.timestamper, self.coinbaser, data['coinbasevalue'],
                            data['coinbaseaux']['flags'], data['height'], settings.COINBASE_EXTRAS, data)
        else:
            coinbase = self.coinbase_transaction_class(self.timestamper, self.coinbaser, data['coinbasevalue'],
                            data['coinbaseaux']['flags'], data['height'], settings.COINBASE_EXTRAS)

        self.height = data['height']
        self.nVersion = data['version']
        self.hashPrevBlock = int(data['previousblockhash'], 16)
        self.nBits = int(data['bits'], 16)
        self.hashMerkleRoot = 0
        self.nTime = 0
        self.nNonce = 0
        self.vtx = [ coinbase, ]

        for tx in data['transactions']:
            t = halfnode.CTransaction()
            t.deserialize(StringIO.StringIO(binascii.unhexlify(tx['data'])))
            self.vtx.append(t)

        self.curtime = data['curtime']
        self.timedelta = self.curtime - int(self.timestamper.time())
        self.merkletree = mt
        if 'rsk_flag' in data:
            self.target = int(data['rsk_diff'], 16)
            print "BLOCK TEMPLATE TARGET: %s" % self.target
        else:
            self.target = util.uint256_from_compact(self.nBits)

        # Reversed prevhash
        self.prevhash_bin = binascii.unhexlify(util.reverse_hash(data['previousblockhash']))
        self.prevhash_hex = "%064x" % self.hashPrevBlock

        self.broadcast_args = self.build_broadcast_args()

    def register_submit(self, extranonce1, extranonce2, ntime, nonce):
        '''Client submitted some solution. Let's register it to
        prevent double submissions.'''

        t = (extranonce1, extranonce2, ntime, nonce)
        if t not in self.submits:
            self.submits.append(t)
            return True
        return False

    def build_broadcast_args(self):
        '''Build parameters of mining.notify call. All clients
        may receive the same params, because they include
        their unique extranonce1 into the coinbase, so every
        coinbase_hash (and then merkle_root) will be unique as well.'''
        logid = util.id_generator()
        start = Interfaces.timestamper.time()
        job_id = self.job_id
        prevhash = binascii.hexlify(self.prevhash_bin)
        (coinb1, coinb2) = [binascii.hexlify(x) for x in self.vtx[0]._serialized]
        merkle_branch = [binascii.hexlify(x) for x in self.merkletree._steps]
        version = binascii.hexlify(struct.pack(">i", self.nVersion))
        nbits = binascii.hexlify(struct.pack(">I", self.nBits))
        ntime = binascii.hexlify(struct.pack(">I", self.curtime))
        log.info(json.dumps({"uuid" : logid, "start" : start, "elapsed" :  Interfaces.timestamper.time() - start, "rsk" : "[RSKLOG]",
                             "tag" : "[BBCARG]", "data" : {"job_id" : job_id, "prevhash" : prevhash,
                             "coinb1" : coinb1, "coinb2" : coinb2, "merkle_branch" : merkle_branch, "version" : version,
                             "nbits" : nbits, "ntime" : ntime}}))
        #log.info("%s - [RSKLOG] - [BBCARG] - %s - %s - Arguments: job_id: %s, prevhash: %s, coinb1: %s, coinb2: %s, merkle_branch: %s, version: %s, nbits: %s, ntime: %s",
        #         logid, start, Interfaces.timestamper.time() - start, job_id, prevhash, coinb1, coinb2, merkle_branch, version, nbits, ntime)
        clean_jobs = True

        return (job_id, prevhash, coinb1, coinb2, merkle_branch, version, nbits, ntime, clean_jobs)

    def serialize_coinbase(self, extranonce1, extranonce2):
        '''Serialize coinbase with given extranonce1 and extranonce2
        in binary form'''
        (part1, part2) = self.vtx[0]._serialized
        return part1 + extranonce1 + extranonce2 + part2

    def check_ntime(self, ntime):
        '''Check for ntime restrictions.'''
        if ntime < self.curtime:
            return False

        if ntime > (self.timestamper.time() + 1000):
            # Be strict on ntime into the near future
            # may be unnecessary
            return False

        return True

    def serialize_header(self, merkle_root_int, ntime_bin, nonce_bin):
        '''Serialize header for calculating block hash'''
        r  = struct.pack(">i", self.nVersion)
        r += self.prevhash_bin
        r += util.ser_uint256_be(merkle_root_int)
        r += ntime_bin
        r += struct.pack(">I", self.nBits)
        r += nonce_bin
        return r

    def finalize(self, merkle_root_int, extranonce1_bin, extranonce2_bin, ntime, nonce):
        '''Take all parameters required to compile block candidate.
        self.is_valid() should return True then...'''

        self.hashMerkleRoot = merkle_root_int
        self.nTime = ntime
        self.nNonce = nonce
        self.vtx[0].set_extranonce(extranonce1_bin + extranonce2_bin)
        self.sha256 = None # We changed block parameters, let's reset sha256 cache
