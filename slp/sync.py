# -*- coding:utf-8 -*-

import slp
import queue
import random
import traceback
import threading

from usrv import req
from slp import dbapi

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
        last_reccord = list(dbapi.db.journal.find().sort("height", -1).limit(1))
        if len(last_reccord):
            start_height = max(last_reccord[0]["height"], start_height)

        block_per_page = 100
        page = start_height // block_per_page - 1

        slp.LOG.info("Start downloading blocks from height %s", start_height)

        # # controled infinite loop
        # Processor.STOP.clear()
        # while not Processor.STOP.is_set():
        #     try:

        #         blocks = req.GET.api.blocks(
        #             peer=peer, page=page,
        #             limit=block_per_page, orderBy="height:asc",
        #             headers=slp.HEADERS
        #         )

        #         if blocks.get("status", False) == 200:
        #             mark = {"peer": peer}

        #             if blocks.get("meta", {}).get("next", False) is None:
        #                 slp.LOG.info("End of blocks reached")
        #                 Processor.stop()

        #             blocks = [
        #                 b for b in blocks.get("data", [])
        #                 if b["transactions"] > 0 and
        #                    b["height"] >= start_height
        #             ]

        #             slp.LOG.info(
        #                 "Parsing %d blocks (page %d)", len(blocks), page
        #             )

        #             if len(blocks):
        #                 for block in blocks:
        #                     chain.parse_block(block)
        #                     mark["last parsed block"] = block["height"]
        #                     slp.dumpJson(mark, "processor.mark", ".json")

        #             page += 1

        #         else:
        #             slp.LOG.info("No block from %s", peer)
        #             if len(peers) == 1:
        #                 peers = select_peers()
        #             if peer in peers:
        #                 peers.remove(peer)
        #             peer = random.choice(peers)

        #     except Exception as error:
        #         slp.LOG.error("%r\n%s", error, traceback.format_exc())

        # req.EndPoint.timeout = timeout
        # slp.LOG.info("Processor %d task exited", id(self))
        # chain.Chainer()
