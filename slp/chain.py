# -*- coding:utf-8 -*-

"""
`chain` module is designed to manage webhook subscription with blockchain and
process validated blocks. Idea here is to extract SLP smartbridge transactions
and embed it in a Mongo DB document.

Document structure:

name|description|type
-|-|-
height|transaction block height|unsigned long long
index|transaction index in block|short
txid|transaction id|hexidecimal
slp_type|SLP contract type|string
emitter|sender wallet address|base58
receiver|receiver wallet address|base58
cost|transaction amount|unsigned long long
tx|blockchain transaction id|hexadecimal
tp|type of action|string
id|token ID|hexidecimal
de|decimal places|short: 0..8
qt|quantity|unsigned long long
sy|symbol / ticker|string
na|token name|string
du|document URI|string (`ipfs://` scheme)
no|notes|string
pa|pausable|boolean: Default false
mi|mintable|boolean: Default false
ch|smartbridge chunck|short
dt|data|string
"""

import os
import sys
import slp
import json
import queue
import pickle
import hashlib
import traceback
import threading
import importlib

from slp import serde, dbapi
from usrv import req


def get_token_id(slp_type, symbol, blockheight, txid):
    """
    Generate token id.
    """
    raw = "%s.%s.%s.%s" % (slp_type.upper(), symbol, blockheight, txid)
    return hashlib.md5(raw.encode("utf-8")).hexdigest()


def subscribe():
    """
    Webhook subscription management.
    """

    webhook = os.path.join(os.path.dirname(__file__), "webhook.json")
    if os.path.exists(webhook):
        return False

    data = req.POST.api.webhooks(
        peer=slp.JSON["webhook peer"],
        target=f"http://{slp.PUBLIC_IP}/blocks",
        event="block.applied",
        conditions=[
            {"key": "numberOfTransactions", "condition": "gte", "value": "1"}
        ]
    ).get("data", {})

    if data != {}:
        data["key"] = dump_webhook_token(data.pop("token"))
        with open(webhook, "w") as f:
            json.dump(data, f)
    slp.LOG.info("Subscribed to %s", slp.JSON["webhook peer"])


def unsubscribe():
    """
    Webhook subscription management.
    """

    webhook = os.path.join(os.path.dirname(__file__), "webhook.json")
    if not os.path.exists(webhook):
        return False

    with open(webhook) as f:
        data = json.load(f)
        resp = req.DELETE.api.webhooks(
            data["id"],
            peer=slp.JSON["webhook peer"]
        )
        if resp.get("status", 300) < 300:
            os.remove(data["key"])
            os.remove(webhook)
        slp.LOG.info("Unsubscribed from %s", slp.JSON["webhook peer"])
        return resp


def dump_webhook_token(token):
    """
    Secure webhook token management.
    """
    authorization = token[:32]
    verification = token[32:]
    filename = os.path.join(
        os.path.dirname(__file__),
        hashlib.md5(authorization.encode("utf-8")).hexdigest() + ".key"
    )
    with open(filename, "wb") as out:
        pickle.dump(
            {
                "verification": verification,
                "hash": hashlib.sha256(token.encode("utf-8")).hexdigest()
            }, out
        )
    return filename


def check_webhook_token(authorization):
    """
    Secure webhook token check.
    """
    filename = os.path.join(
        os.path.dirname(__file__),
        hashlib.md5(authorization.encode("utf-8")).hexdigest() + ".key"
    )
    try:
        with open(filename, "rb") as in_:
            data = pickle.load(in_)
    except Exception:
        return False
    else:
        token = authorization + data["verification"]
        return hashlib.sha256(
            token.encode("utf-8")
        ).hexdigest() == data["hash"]


# TODO: make it robust if any timeout occur ?
def get_block_transactions(blockId):
    data, page, result = [None], 1, []
    peer = slp.JSON["api peer"]
    while len(data) > 0:
        data = req.GET.api.blocks(
            blockId, "transactions", page=page, peer=peer, headers=slp.HEADERS
        ).get("data", [])
        result += data
        page += 1
    return result


def read_vendorField(vendorField):
    contract = False
    try:
        contract = json.loads(vendorField)
    except Exception:
        try:
            contract = serde.unpack_slp(vendorField)
        except Exception:
            pass
    return False if not isinstance(contract, dict) else contract


def manage_block(**request):
    """
    Dispatch webhook request.
    """
    # webhook security check
    auth = request.get("headers", {}).get("authorization", "?")
    if not check_webhook_token(auth):
        return False
    # get block header
    body = request.get("data", {})
    block = body.get("data", {})
    slp.LOG.info("Genuine block header received:\n%s", block)
    # parse block
    return parse_block(block)


def parse_block(block):
    """
    Search valid SLP vendor fields in all transactions from specified block.
    If any, it is normalized and registered as a rreccord in journal.
    """
    # get transactions from block
    tx_list = get_block_transactions(block["id"])
    loop = zip(list(range(len(tx_list))), tx_list)
    # search for SLP vendor fields in transfer type transactions
    for index, tx in [
        (i+1, t) for i, t in loop
        if t["type"] == 0 and
        t.get("vendorField", False)
    ]:
        # try to read contract from vendor field
        contract = read_vendorField(tx["vendorField"])
        if contract:
            try:
                slp_type, fields = list(contract.items())[0]
                slp.LOG.info(
                    "> SLP contract found: %s->%s", slp_type, fields["tp"]
                )
                # compute token id for GENESIS contracts
                if fields["tp"] == "GENESIS":
                    fields.update(id=get_token_id(
                        slp_type, fields["sy"], block["height"], tx["id"]
                    ))
                # add wallets information and cost
                fields.update(
                    emitter=tx["sender"], receiver=tx["recipient"],
                    cost=int(tx["amount"])
                )
                # tweak numeric values
                if "de" in fields:
                    fields["de"] = int(fields["de"])
                if "qt" in fields:
                    fields["qt"] = float(fields["qt"])
                # add a new reccord in journal
                reccord = dbapi.add_reccord(
                    block["height"], index, tx["id"], slp_type, **fields
                )
                # -
                if reccord is not False:
                    slp.LOG.info("Document %s added to journal", reccord)
                    # send contract application as job
                    Chainer.JOB.put(reccord)
            except Exception as error:
                slp.LOG.info(
                    "Error occured with tx %s in block %d",
                    tx["id"], block["height"]
                )
                slp.LOG.error("%r\n%s", error, traceback.format_exc())
    return True


class Chainer(threading.Thread):

    JOB = queue.Queue()
    LOCK = threading.Lock()
    STOP = threading.Event()

    def __init__(self, *args, **kwargs):
        self.__kw = kwargs
        threading.Thread.__init__(self)
        self.daemon = True
        self.start()
        slp.LOG.info("Chainer %s set", id(self))

    @staticmethod
    def stop():
        try:
            Chainer.LOCK.release()
        except Exception:
            pass
        finally:
            Chainer.STOP.set()

    def run(self):
        DEBUG = self.__kw.get("debug", False)
        slp.LOG.debug("Chainer launch with debug set to %s", DEBUG)
        # controled infinite loop
        while not Chainer.STOP.is_set():
            try:
                reccord = Chainer.JOB.get()
                module = f"slp.{reccord['slp_type'][1:]}"
                if module not in sys.modules:
                    importlib.__import__(module)
                execution = sys.modules[module].manage(reccord)
                slp.LOG.info("Contract execution: -> %s", execution)
                if not execution:
                    dbapi.db.rejected.insert_one(reccord)
                    if DEBUG:
                        raise Exception("Debug stop !")
                else:
                    # broadcast to peers ?
                    pass
            except ImportError:
                slp.LOG.info(
                    "No modules found to handle '%s' contracts",
                    reccord['slp_type']
                )
            except Exception as error:
                Chainer.stop()
                dbapi.Processor.stop()
                slp.LOG.error("%r\n%s", error, traceback.format_exc())
