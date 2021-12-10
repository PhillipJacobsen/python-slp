# -*- coding:utf-8 -*-

import slp
import json
import queue
import hashlib
import threading
import traceback

from slp import node, chain, dbapi
from usrv import srv


@srv.bind("/block", methods=["POST"])
def listen_blockchain(**request):
    if request["method"] == "POST":
        chain.manage_block(**request)


# listen requests to /message endpoint
@srv.bind("/message", methods=["HEAD", "POST"])
def manage_message(**request):
    if request["method"] == "POST":
        return {"queued": Messenger.put(request)}


# listen requests to /peers endpoint
@srv.bind("/peers", methods=["GET"])
def send_peers(**request):
    if request["method"] == "GET":
        return list(node.PEERS)


class Memory(queue.Queue):

    LOCK = threading.Lock()

    def __contains__(self, item):
        with Memory.LOCK:
            return Memory.hash_item(item) in self.queue

    def put(self, item, block=True, timeout=None):
        item_h = Memory.hash_item(item)
        with Memory.LOCK:
            if item_h not in self.queue:
                if self.full():
                    self.get()
                queue.Queue.put(self, item_h, block, timeout)
                return True

    @staticmethod
    def hash_item(item):
        return hashlib.md5(
            json.dumps(item, sort_keys=True, separators=(",", ":"))
            .encode("utf-8")
        ).hexdigest()


class Messenger(threading.Thread):
    """
    Daemon message manager.
    """

    JOB = queue.Queue()
    LOCK = threading.Lock()
    STOP = threading.Event()
    MEM = Memory(slp.JSON.get("message memory size", 20))

    def __init__(self, *args, **kwargs):
        threading.Thread.__init__(self)
        self.daemon = True
        self.start()
        slp.LOG.info("Messenger %s set", id(self))

    def run(self):
        # controled infinite loop
        while not Messenger.STOP.is_set():
            try:
                request = Messenger.JOB.get()
                msg = request.get("data", {})

                slp.LOG.info("performing message: %r", msg)

                if "hello" in msg:
                    node.manage_hello(msg)
                elif "input" in msg:
                    # get wallet address from header and put to contract
                    headers = request.get("headers", {})
                    msg["input"]["wallet"] = headers["Wallet-Address"]
                    dbapi.manage_input(msg)
                elif "confirm" in msg:
                    chain.manage_confirm(msg)

            except Exception as error:
                slp.LOG.error("%r\n%s" % (error, traceback.format_exc()))
                Messenger.LOCK.release()

    @staticmethod
    def put(request):
        # try to memorize message
        queued = Messenger.MEM.put(request.get("data", {}))
        # memorized
        if queued:
            Messenger.JOB.put(request)
        return queued


def stop():
    Messenger.LOCK.release()
    Messenger.STOP.set()
