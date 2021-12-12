# -*- coding:utf-8 -*-

import slp
import traceback

from pymongo import MongoClient

#
# MONGO DB DEFINITION ---
db = MongoClient(slp.JSON.get("mongo url", None))[slp.JSON["database name"]]
# --- databases ---
db.journal.create_index([("height", 'text'), ("index", 'text')], unique=True)
db.contracts.create_index("tokenId", unique=True)
# --- states ---
db.wallets.create_index(
    [("address", 'text'), ("tokenId", 'text')],
    unique=True
)
db.supply.create_index("tokenId", unique=True)
# ---


def add_reccord(height, index, txid, slp_type, emitter, receiver, cost, **kw):
    """
    Add a reccord in the journal.

    Args:
        height (int): block height.
        index (int): transaction index in the block.
        txid (str): transaction id as hex.
        slp_type (str): see SLP contract types.
        **kw (keyword args): contract field values.

    Returns:
        bool: `True` if success else `False`.

    Raises:
        Exception if reccord already in journal.
    """
    fields = dict(
        [k, v] for k, v in kw.items()
        if k in "tp,id,de,qt,sy,na,du,no,pa,mi,ch,dt"
    )
    if not slp.validate(**fields):
        slp.LOG.error("field validation did not pass")
        return False
    try:
        db.journal.insert_one(
            dict(
                height=height, index=index, txid=txid,
                slp_type=slp_type, emitter=emitter, receiver=receiver,
                cost=cost, legit=None, **fields
            )
        )
    except Exception as error:
        slp.LOG.error("%r\n%s", error, traceback.format_exc())
        return False
    return True
