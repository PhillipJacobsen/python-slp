# -*- coding:utf-8 -*-

import slp
import queue
import random
import decimal
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
db.rejected.create_index([("height", 1), ("index", 1)], unique=True)
db.contracts.create_index("tokenId", unique=True)
# ---

# Build Decimal128 builders for all aslp1 token
for reccord in db.journal.find({"tp": "GENESIS", "slp_type": "aslp1"}):
    slp.DECIMAL128[reccord["id"]] = \
        lambda v, de=reccord.get('de', 0): Decimal128(f"%.{de}f" % v)


def set_legit(filter, value=True):
    value = bool(value)
    db.journal.update_one(filter, {'$set': {"legit": value}})
    return value


def blockstamp_cmp(a, b):
    """
    Blockstamp comparison. Returns True if a higher than b.
    """
    height_a, index_a = [int(e) for e in a.split("#")]
    height_b, index_b = [int(e) for e in b.split("#")]
    if height_a > height_b:
        return True
    elif height_a == height_b:
        return index_a >= index_b
    else:
        return False


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
    """
    fields = dict(
        [k, v] for k, v in kw.items()
        if k in slp.JSON["slp fields"]
    )

    if kw.get("tp", "") == "GENESIS":
        fields.update(pa=kw.get("pa", False))
        if slp_type.endswith("1"):
            fields.update(mi=kw.get("mi", False))

    if not slp.validate(**fields):
        slp.LOG.error("field validation did not pass")
        slp.dumpJson(
            dict(
                slp.loadJson(f"unvalidated.{slp_type}", ".json"),
                **{f"{height}#{index}": fields}
            ), f"unvalidated.{slp_type}", ".json"
        )
        return False

    try:
        contract = dict(
            height=height, index=index, txid=txid,
            slp_type=slp_type, emitter=emitter, receiver=receiver,
            cost=cost, legit=None, **fields
        )
        db.journal.insert_one(contract)
    except Exception as error:
        slp.LOG.error("%r\n%s", error, traceback.format_exc())
        return False
    else:
        return contract


def find_contract(**filter):
    return db.contracts.find_one(filter)


def find_wallet(**filter):
    return db.wallets.find_one(filter)


def upsert_contract(tokenId, values):
    try:
        query = {"tokenId": tokenId}
        update = {"$set": dict(
            [k, v] for k, v in values.items()
            if k in "tokenId,height,index,type,name,owner,"
                    "globalSupply,paused,minted,burned"
        )}
        db.contracts.update_one(query, update)
    except Exception as error:
        slp.LOG.error("%r\n%s", error, traceback.format_exc())
        return False
    return True


def upsert_wallet(address, tokenId, values):
    try:
        query = {"tokenId": tokenId, "address": address}
        update = {"$set": dict(
            [k, v] for k, v in values.items()
            if k in "address,tokenId,blockStamp,balance,owner,frozen"
        )}
        db.wallets.update_one(query, update)
    except Exception as error:
        slp.LOG.error("%r\n%s", error, traceback.format_exc())
        return False
    return True


def exchange_token(tokenId, sender, receiver, qt):
    # find sender wallet from database
    _sender = find_wallet(address=sender, tokenId=tokenId)
    # get Decimal128 builder according to token id and convert qt to Decimal
    _decimal128 = slp.DECIMAL128[tokenId]
    qt = decimal.Decimal(qt)

    if _sender:
        # find receiver wallet from database
        _receiver = find_wallet(address=receiver, tokenId=tokenId)
        # create it with needed
        if _receiver is None:
            db.wallets.insert_one(
                dict(
                    address=receiver, tokenId=tokenId, blockStamp="0#0",
                    balance=_decimal128(0.), owner=False, frozen=False
                )
            )
            new_balance = qt
        else:
            new_balance = _receiver["balance"].to_decimal() + qt
        # first update receiver
        if upsert_wallet(
            receiver, tokenId, {"balance": _decimal128(new_balance)}
        ):
            slp.LOG.debug("    < %s received %s", receiver, qt)
            # if reception is a success, update emitter
            if upsert_wallet(
                sender, tokenId, {
                    "balance":
                        _decimal128(_sender["balance"].to_decimal() - qt)
                }
            ):
                # and return True if success
                slp.LOG.debug("    > %s sent %s", sender, qt)
                return True
    else:
        slp.LOG.error(
            "%s wallet does not exists with contract %s", sender, tokenId
        )
        return False


def select_peers():
    peers = []
    candidates = req.GET.api.peers(
        peer=slp.JSON["api peer"],
        orderBy="height:desc",
        headers=slp.HEADERS
    ).get("data", [])
    for candidate in candidates[:20]:
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
        try:
            Processor.LOCK.release()
        except Exception:
            pass
        finally:
            Processor.STOP.set()

    def run(self):
        timeout = req.EndPoint.timeout
        req.EndPoint.timeout = 30
        # load last processing mark if any
        mark = slp.loadJson("processor.mark", ".json")
        peers = select_peers()
        # get last good peer if any else choose a random one
        peer = mark.get("peer", random.choice(peers))
        # determine where to start
        start_height = max(
            min(slp.JSON["milestones"].values()),
            mark.get("last parsed block", 0)
        )
        last_reccord = list(db.journal.find().sort("height", -1).limit(1))
        if len(last_reccord):
            start_height = max(last_reccord[0]["height"], start_height)

        block_per_page = 100
        page = start_height // block_per_page

        slp.LOG.info("Start downloading blocks from height %s", start_height)

        # controled infinite loop
        Processor.STOP.clear()
        while not Processor.STOP.is_set():
            try:

                blocks = req.GET.api.blocks(
                    peer=peer, page=page,
                    limit=block_per_page, orderBy="height:asc",
                    headers=slp.HEADERS
                )

                if blocks.get("status", False) == 200:
                    mark = {"peer": peer}

                    if blocks.get("meta", {}).get("next", False) is None:
                        slp.LOG.info("End of blocks reached")
                        Processor.stop()

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
                            mark["last parsed block"] = block["height"]
                            slp.dumpJson(mark, "processor.mark", ".json")

                    page += 1

                else:
                    slp.LOG.info("No block from %s", peer)
                    if len(peers) == 1:
                        peers = select_peers()
                    if peer in peers:
                        peers.remove(peer)
                    peer = random.choice(peers)

            except Exception as error:
                slp.LOG.error("%r\n%s", error, traceback.format_exc())

        req.EndPoint.timeout = timeout
        slp.LOG.info("Processor %d task exited", id(self))
        chain.Chainer()
