# -*- coding:utf-8 -*-

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
    return contract


def manage_block(**request):
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
            slp.LOG.info("> SLP vendorField found:\n%s", contract)
            try:
                slp_type, fields = list(contract.items())[0]
                # compute token id for GENESIS contracts
                if fields["tp"] == "GENESIS":
                    tokenId = get_token_id(
                        slp_type, fields["sy"], block["height"], tx["id"]
                    )
                    fields.update(id=tokenId)
                # add wallets information and cost
                fields.update(
                    emitter=tx["sender"], receiver=tx["recipient"],
                    cost=int(tx["amount"])
                )
                if "de" in fields:
                    fields["de"] = int(fields["de"])
                if "qt" in fields:
                    fields["qt"] = int(fields["qt"])
                # dbapi.add_reccord returns False if reccord already in
                # journal.
                if dbapi.add_reccord(
                    block["height"], index, tx["id"], slp_type, **fields
                ):
                    slp.LOG.info("Document %s added to journal", fields)
                    # send contract application as job
                    Chainer.JOB.put([slp_type, fields])
            except Exception as error:
                slp.LOG.info(
                    "Error occured with tx %s in block %d: vendorField=%s",
                    tx["id"], block["height"], contract
                )
                slp.LOG.error("%r\n%s" % (error, traceback.format_exc()))

    return True


class Chainer(threading.Thread):

    JOB = queue.Queue()
    LOCK = threading.Lock()
    STOP = threading.Event()

    def __init__(self, *args, **kwargs):
        threading.Thread.__init__(self)
        self.daemon = True
        self.start()
        slp.LOG.info("Chainer %s set", id(self))

    @staticmethod
    def stop():
        Chainer.LOCK.release()
        Chainer.STOP.set()

    def run(self):
        # controled infinite loop
        while not Chainer.STOP.is_set():
            try:
                slp_type, contract = Chainer.JOB.get()
                module = f"slp.{slp_type[1:]}"
                if module not in sys.modules:
                    importlib.__import__(module)
                slp.LOG.info(
                    "Contract execution:\n<-%s\n->%s",
                    contract,
                    sys.modules[module].manage(contract)
                )
            except ImportError:
                slp.LOG.info(
                    "No modules found to handle '%s' contracts", slp_type
                )
            except Exception as error:
                slp.LOG.error("%r\n%s", error, traceback.format_exc())
