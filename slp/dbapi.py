# -*- coding:utf-8 -*-

import slp

from slp import node


def manage_input(msg):
    if not slp.BLOCKCHAIN_NODE:
        node.send_message({
            "confirm": dict(
                msg["input"], **{"from": f"http://{slp.PUBLIC_IP}:{slp.PORT}"}
            )
        })
    else:
        pass
