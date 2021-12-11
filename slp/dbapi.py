# -*- coding:utf-8 -*-

import slp
import hashlib
import traceback

from slp import node, chain
from pymongo import MongoClient

#
# MONGO DB DEFINITION ---
# --- databases ---
db = MongoClient(slp.JSON.get("mongo url", None))[slp.JSON["database name"]]
db.contracts.create_index("tokenId", unique=True)
db.journal.create_index([("height", 'text'), ("index", 'text')], unique=True)
# --- states ---
db.wallets.create_index(
    [("address", 'text'), ("tokenId", 'text')],
    unique=True
)
db.supply.create_index("tokenId", unique=True)
# ---


def get_token_id(slp_type, symbol, blockheight, txid):
    """
    Generate token id.
    """
    raw = "%s.%s.%s.%s" % (slp_type, symbol, blockheight, txid)
    return hashlib.md5(raw.encode("utf-8")).hexdigest().Decode("utf-8")


def get_token_supply(tokenId):
    supply = db.supply.find_one({"tokenId": tokenId})
    return supply or {"error": "no contract found for tokenId %s" % tokenId}


def transfer_token(tokenId, address, qt: slp.Quantity):
    wallet = db.wallets.find_one({"address": address, "tokenId": tokenId})
    if wallet:
        return db.wallets.update_one(wallet, {"$inc": {"balance": qt.q}})
    else:
        return db.wallets.insert_one({
            "tokenId": tokenId, "address": address, "balance": qt.q
        })


#
# MONGO DB ATOMIC ACTION ---

# on block.applied
def add_reccord(height, index, txid, slp_type, **kw):
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
    try:
        db.journal.insert_one(
            dict(
                height=height, index=index, txid=txid,
                slp_type=slp_type, appliable=None,
                **dict(
                    [k, v] for k, v in kw.items()
                    if k in [
                        "tp", "id", "de", "qt", "sy", "na", "du", "no", "pa",
                        "mi", "ch", "dt", "wt", "pk"
                    ]
                )
            )
        )
    except Exception as error:
        slp.LOG.error("%r\n%s", error, traceback.format_exc())
        return False
    return True


def add_slp1_contract(owner, id, na, sy, qt, de, no, du, pa=False, mi=False):
    # if all checks pass create the contract document
    assert 3 <= len(sy) <= 8
    assert 3 <= len(na) <= 24
    assert 0 <= de <= 8
    assert len(no) <= 32
    assert len(du) <= 32

    contract = dict(
        tokenId=id, owner=owner, slpType="slp1",
        name=na, symbol=sy, notes=no, uri=du,
        globalSupply=qt, decimals=de,
        pausable=pa, mintable=mi
    )

    try:
        quantity = slp.Quantity(qt, de=de)
        db.contrats.insert_one(contract)
        db.supply.inserte_one(
            {"tokenId": tokenId}, {
                "tokenId": tokenId, "exchanged": 0, "minted": 0, "burned": 0,
                "frozen": False
            }
        )
        if not contract["mintable"]:
            transfer_token(tokenId, owner, quantity)
    except Exception as error:
        slp.LOG.error("%r\n%s", error, traceback.format_exc())
        return False
    return True


# def mint(height, timestamp, owner, tokenId, qt: slp.Quantity):
#     contract = db.contracts.find({"tokenId": tokenId})
#     if contract:
#         transfer_token(tokenId, owner, qt.q)
#         db.accountings.insert_one(
#             dict(
#                 height=height, timestamp=timestamp, tokenId=tokenId,
#                 address=owner, minted=qt.q
#             )
#         )
#     return {"error": "no contract found for tokenId %s" % tokenId}


# # def swap(height, timestamp, tokenId, sender, recipient, qt: slp.Quantity):
# #     quantity = qt.q
# #     sender = db.wallets.find_one(address=sender, tokenId=tokenId)
# #     if sender.get("balance", 0) >= quantity:
# #         # update wallet state
# #         db.wallets.update(sender, {'$inc': {"balance": -quantity}})
# #         transfer_token(tokenId, recipient, qt)
# #         # reccord transaction in accountings
# #         return db.accountings.insert_many(
# #             [
# #                 dict(
# #                     height=height, timestamp=timestamp, tokenId=tokenId,
# #                     address=sender, exchanged=-quantity
# #                 ),
# #                 dict(
# #                     height=height, timestamp=timestamp, tokenId=tokenId,
# #                     address=recipient, exchanged=quantity
# #                 )
# #             ]
# #         )
# #     return False


# # def burn(height, timestamp, owner, tokenId, qt: slp.Quantity):
# #     return db.accountings.insert_one(
# #         dict(
# #             height=height, timestamp=timestamp, tokenId=tokenId,
# #             address=owner, burned=qt.q
# #         )
# #     )


# # def freeze(tokenId):
# #     return db.supply.find_one_and_update(
# #         {"tokenId": tokenId},
# #         {"frozen", True}
# #     )


# # def unfreeze(tokenId):
# #     return db.supply.find_one_and_update(
# #         {"tokenId": tokenId},
# #         {"frozen", False}
# #     )


# # def manage_input(msg):
# #     if not slp.BLOCKCHAIN_NODE:
# #         node.send_message({
# #             "confirm": dict(
# #                 msg["input"], **{"from": f"http://{slp.PUBLIC_IP}:{slp.PORT}"}
# #             )
# #         })
# #     else:
# #         # apply contract to database
# #         pass


# # def manage_confirm(msg):
# #     pass


# # def validate(contract):
# #     supply = db.supply.find(tokenId=contract["tokenId"])
# #     if supply.count() == 1:
# #         if not supply["frozen"]:
# #             #if is_legit(contract):
# #                 return contract
# #     return False
