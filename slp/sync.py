# -*- coding:utf-8 -*-

import slp
import queue
import random
import traceback
import threading

from usrv import req
from slp import dbapi, chain


class Processor(threading.Thread):

    STOP = threading.Event()

    def __init__(self, *args, **kwargs):
        threading.Thread.__init__(self)
        self.daemon = True
        self.start()
        slp.LOG.info("Processor %s set", id(self))

    @staticmethod
    def stop():
        Processor.STOP.set()

    def run(self):
        timeout = req.EndPoint.timeout
        req.EndPoint.timeout = 30
        # load last processing mark if any
        mark = slp.loadJson("processor.mark", ".json")
        peers = chain.select_peers()
        # get last good peer if any else choose a random one
        peer = mark.get("peer", random.choice(peers))
        # determine where to start
        start_height = max(
            min(slp.JSON["milestones"].values()),
            mark.get("last parsed block", 0)
        )
        last_reccord = list(
            dbapi.db.journal.find().sort("height", -1).limit(1)
        )
        if len(last_reccord):
            start_height = max(last_reccord[0]["height"], start_height)

        block_per_page = 100
        page = start_height // block_per_page - 1

        slp.LOG.info("Start downloading blocks from height %s", start_height)
        last_parsed = start_height

        # controled infinite loop
        chain.BlockParser()
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
                        slp.LOG.info("End of block pages reached")
                        Processor.stop()

                    blocks = [
                        b for b in blocks.get("data", [])
                        if b["transactions"] > 0 and
                           b["height"] > last_parsed
                    ]

                    slp.LOG.info(
                        "Parsing %d blocks from page %d", len(blocks), page
                    )

                    if len(blocks):
                        for block in blocks:
                            chain.BlockParser.JOB.put(block)
                            mark["last parsed block"] = block["height"]
                            slp.dumpJson(mark, "processor.mark", ".json")
                            last_parsed = block["height"]

                    page += 1

                else:
                    slp.LOG.info("No block from %s", peer)
                    if len(peers) == 1:
                        peers = chain.select_peers()
                    if peer in peers:
                        peers.remove(peer)
                    peer = random.choice(peers)

            except Exception as error:
                slp.LOG.error("%r", error)
                slp.LOG.debug("traceback data:\n%s", traceback.format_exc())

        req.EndPoint.timeout = timeout
        slp.LOG.info("Processor %d task exited", id(self))
