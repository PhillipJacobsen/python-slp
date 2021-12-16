# -*- coding:utf-8 -*-

import slp
import queue
import random
import threading
import traceback

from slp import chain
from usrv import req
from pymongo import MongoClient
from bson.decimal128 import Decimal128


#
# MONGO DB DEFINITION ---
db = MongoClient(slp.JSON.get("mongo url", None))[slp.JSON["database name"]]
# --- databases ---
db.journal.create_index([("height", 1), ("index", 1)], unique=True)
db.contracts.create_index("tokenId", unique=True)
# --- states ---
db.wallets.create_index(
    [("address", 'text'), ("tokenId", 'text')],
    unique=True
)
db.supply.create_index("tokenId", unique=True)
# ---

# Build Decimal128 reccords
for reccord in db.journal.find({"tp": "GENESIS", "slp_type": "aslp1"}):
    slp.DECIMAL128[reccord["id"]] = \
        lambda v, de=reccord.get('de', 0): Decimal128(f"%.{de}f" % v)


def add_reccord(height, index, txid, slp_type, emitter, receiver, cost, **kw):
    """
    Add a reccord in the journal.

    Args:
        height (int): block height.
        index (int): transaction index in the block.
        txid (str): transaction id as hex.
        slp_type (str): see SLP contract types.
        emitter (str): sender id wallet.
        receiver (str): recipient id wallet.
        cost (int): amount of transaction.
        **kw (keyword args): contract field values.

    Returns:
        bool: `True` if success else `False`.

    Raises:
        Exception if reccord already in journal.
    """
    fields = dict(
        [k, v] for k, v in kw.items()
        if k in "tp,id,de,qt,sy,na,du,no,pa,mi,ch,dt"
    )
    if not slp.validate(**fields):
        slp.LOG.error("field validation did not pass")
        return False
    try:
        db.journal.insert_one(
            dict(
                height=height, index=index, txid=txid,
                slp_type=slp_type, emitter=emitter, receiver=receiver,
                cost=cost, legit=None, **fields
            )
        )
    except Exception as error:
        slp.LOG.error("%r\n%s", error, traceback.format_exc())
        return False
    return True


def select_peers():
    peers = []
    candidates = req.GET.api.peers(
        peer=slp.JSON["api peer"],
        orderBy="height:desc",
        headers=slp.HEADERS
    ).get("data", [])
    for candidate in candidates:
        api_port = candidate.get("ports", {}).get(
            "@arkecosystem/core-api", -1
        )
        if api_port > 0:
            peers.append("http://%s:%s" % (candidate["ip"], api_port))
    return peers


class Processor(threading.Thread):

    JOB = queue.Queue()
    LOCK = threading.Lock()
    STOP = threading.Event()

    def __init__(self, *args, **kwargs):
        threading.Thread.__init__(self)
        self.daemon = True
        self.start()
        slp.LOG.info("Processor %s set", id(self))

    @staticmethod
    def stop():
        Processor.LOCK.release()
        Processor.STOP.set()

    def run(self):
        timeout = req.EndPoint.timeout
        req.EndPoint.timeout = 30

        peers = select_peers()
        peer = random.choice(peers)

        last_mark = slp.loadJson("processor.mark", ".json")
        start_height = max(
            min(slp.JSON["milestones"].values()),
            last_mark.get("last parsed block", 0)
        )

        if start_height == 0:
            try:
                start_height = db.journal.find(
                    {"$query": {}, "$orderby": {"_id": -1}}
                ).limit(1).next().get("height", 0)
            except StopIteration:
                start_height = 0

        block_per_page = 100
        page = start_height // block_per_page - 1

        slp.LOG.info("Start downloading blocks from height %s", start_height)

        # controled infinite loop
        while not Processor.STOP.is_set():
            try:

                blocks = req.GET.api.blocks(
                    peer=peer, page=page,
                    limit=block_per_page, orderBy="height:asc",
                    headers=slp.HEADERS
                )

                if blocks.get("status", False) == 200:
                    blocks = [
                        b for b in blocks.get("data", [])
                        if b["transactions"] > 0 and b["height"] > start_height
                    ]

                    slp.LOG.info(
                        "Parsing %d blocks (page %d)", len(blocks), page
                    )

                    if len(blocks):
                        for block in blocks:
                            chain.parse_block(block)

                    slp.dumpJson(
                        {"last parsed block": blocks["data"][-1]["height"]},
                        "processor.mark", ".json"
                    )

                    page += 1

                else:
                    slp.LOG.info("No block from %s", peer)
                    peer = random.choice(peers)

            except Exception as error:
                slp.LOG.error("%r\n%s", error, traceback.format_exc())
                Processor.stop()

        req.EndPoint.timeout = timeout
        slp.LOG.info("Processor %d task finished", id(self))
