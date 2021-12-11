# -*- coding:utf-8 -*-

import os
import slp
import json
import queue
import pickle
import hashlib
import traceback
import threading

from slp import serde, dbapi
from usrv import req


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
        return resp


def dump_webhook_token(token):
    authorization = token[:32]  # "fe944e318edb02b979d6bf0c87978b64"
    verification = token[32:]   # "0c8e74e1cbfe36404386d33a5bbd8b66"
    filename = os.path.join(
        os.path.dirname(__file__),
        hashlib.md5(authorization.encode("utf-8")).hexdigest() + ".key"
    )
    with open(filename, "wb") as out:
        pickle.dump({
                "verification": verification,
                "hash": hashlib.sha256(token.encode("utf-8")).hexdigest()
            },
            out
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
    peer = slp.JSON["api peer"]
    data, page = [None], 1
    result = []
    while len(data) > 0:
        data = req.GET.api.blocks(
            blockId, "transactions", page=page, peer=peer
        ).get("data", [])
        result += data
        page += 1
    return result


def get_current_height():
    return True or False


def is_valid_transaction(txId):
    return True or False


def is_valid_address(address):
    return True or False


def manage_block(**request):
    # webhook security check
    headers = request.get("headers", {})
    if not check_webhook_token(headers.get("Authorization", "?")):
        return False
    # get transactions from block
    block = request.get("data", {})
    tx_list = get_block_transactions(block["id"])

    for index, tx in zip(list(range(len(tx_list))), tx_list):
        try:
            contract = serde.unpack_slp(tx["vendorField"])
        except Exception as error:
            slp.LOG.error("%r\n%s" % (error, traceback.format_exc()))
        else:
            slp_type, contract = contract.items()
            if contract["tp"] == "GENESIS":
                contract.update(
                    owner=tx["senderId"],
                    id=dbapi.get_token_id(
                        slp_type, contract["sy"], block["height"], tx["id"]
                    )
                )
            if dbapi.add_reccord(
                block["height"], index, tx["id"], slp_type, **contract
            ):
                Chainer.JOB.put(contract)


def manage_confirm(msg):
    pass


class Chainer(threading.Thread):

    JOB = queue.Queue()
    LOCK = threading.Lock()
    STOP = threading.Event()

    def __init__(self, *args, **kwargs):
        threading.Thread.__init__(self)
        self.daemon = True
        self.start()
        slp.LOG.info("Chainer %s set", id(self))

    def run(self):
        # controled infinite loop
        while not Chainer.STOP.is_set():
            try:
                contract = Chainer.JOB.get()
                if "slp1" in contract:
                    if contract["slp1"]["tp"] == "GENESIS":
                        dbapi.add_slp1_contract(**contract)
            except Exception as error:
                slp.LOG.error("%r\n%s" % (error, traceback.format_exc()))
                Chainer.LOCK.release()


def stop():
    Chainer.LOCK.release()
    Chainer.STOP.set()
