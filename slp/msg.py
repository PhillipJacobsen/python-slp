# -*- coding:utf-8 -*-

import slp
import queue
import threading
import traceback

from slp import node, chain, dbapi
from usrv import srv


# listen requests to /message endpoint
@srv.bind("/message", methods=["HEAD", "POST"])
def manage_message(**request):
    if request["method"] == "POST":
        Messenger.JOB.put(request)
        return "request queued"


# listen requests to /peers endpoint
@srv.bind("/peers", methods=["GET"])
def send_peers(**request):
    if request["method"] == "GET":
        return list(node.PEERS)


class Messenger(threading.Thread):

    JOB = queue.Queue()
    LOCK = threading.Lock()
    STOP = threading.Event()

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
                    msg["input"]["wallet"] = headers.get("Wallet-Address")
                    dbapi.manage_input(msg)
                elif "confirm" in msg:
                    chain.manage_confirm(msg)

            except Exception as error:
                slp.LOG.error("%r\n%s" % (error, traceback.format_exc()))
                Messenger.LOCK.release()

    def send(self, message):
        pass
