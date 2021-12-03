# -*- coding:utf-8 -*-

import slp
import queue
import threading
import traceback

from usrv import req

PEERS = set([])


def broadcast(endpoint, msg, *peers):
    resp = []
    if isinstance(endpoint, req.EndPoint):
        for peer in peers or PEERS:
            resp.append(endpoint(peer=peer, _jsonify=msg))
    return resp


def send_message(msg, *peers):
    return Broadcaster.broadcast(req.POST.message, msg, *peers)


def discovery(*peers, peer=None):
    msg = {"hello": {"peer": peer or f"http://{slp.PUBLIC_IP}:{slp.PORT}"}}
    slp.LOG.debug(
        "launching a discovery of %s to %s peers",
        msg["hello"]["peer"], len(peers)
    )
    return Broadcaster.broadcast(req.POST.message, msg, *(peers or PEERS))


def prospect_peers(*peers):
    slp.LOG.debug("prospecting %s peers", len(peers))
    me = f"http://{slp.PUBLIC_IP}:{slp.PORT}"
    # for all new peer
    for peer in set(peers) - set([me]) - PEERS:
        # ask peer's peer list
        resp = req.GET.peers(peer=peer)
        # if it answerd
        if resp.get("status", -1) == 200:
            # add peer to peerlist and prospect peer's peer list
            PEERS.update([peer])
            peer_s_peer = set(resp.get("result", []))
            if len(PEERS - peer_s_peer):
                discovery(peer, me)
            prospect_peers(*(peer_s_peer - PEERS))


def manage_hello(msg):
    prospect_peers(*[msg["hello"]["peer"]])
    slp.LOG.info("discovered peers: %s", len(PEERS))


class Broadcaster(threading.Thread):

    JOB = queue.Queue()
    STOP = threading.Event()

    def __init__(self, *args, **kwargs):
        threading.Thread.__init__(self)
        self.daemon = True
        self.start()
        slp.LOG.info("Broadcaster %s set", id(self))

    @staticmethod
    def broadcast(*args):
        Broadcaster.JOB.put(args)

    def run(self):
        # controled infinite loop
        while not Broadcaster.STOP.is_set():
            try:
                endpoint, msg, *peers = Broadcaster.JOB.get()
                broadcast(endpoint, msg, *peers)
            except Exception as error:
                slp.LOG.error("%r\n%s" % (error, traceback.format_exc()))