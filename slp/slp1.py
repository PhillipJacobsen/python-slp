# -*- coding:utf-8 -*-

import slp
import sys
import traceback

from slp import dbapi
from bson import Decimal128


def manage(contract):
    try:
        return getattr(
            sys.modules[__name__], "apply_%s" % contract["tp"].lower()
        )(contract)
    except AttributeError:
        slp.LOG.error("Unknown contract type %s", contract["tp"])


def apply_genesis(contract):
    try:
        # initial quantity should avoid decimal part
        assert contract["qt"] % 1 == 0
        assert contract["cost"] >= slp.JSON["GENESIS cost"]["aslp1"]
        assert contract["receiver"] == slp.JSON["master address"]
    except AssertionError:
        line = traceback.format_exc().split("\n")[-3].strip()
        slp.LOG.error("invalid contract: %s\n%s", line, contract)
        return dbapi.set_legit(contract, False)

    tokenId = contract["id"]
    # add Decimal128 for accounting precision
    slp.DECIMAL128[tokenId] = \
        lambda v, de=contract.get('de', 0): \
        Decimal128(f"%.{de}f" % v)
    qt = slp.DECIMAL128[tokenId](contract["qt"])
    # add contract
    check = [
        dbapi.upsert_contract(
            tokenId,
            height=contract["height"], index=contract["index"], type="aslp1",
            name=contract["na"], owner=contract["emitter"], globalSupply=qt,
            paused=False,
        )
    ]
    # add owner ballance if not mintable
    if not contract.get("mi", False):
        check.append(
            dbapi.upsert_wallet(
                contract["emitter"], tokenId,
                lastUpdate=f"{contract['height']}#{contract['index']}",
                balance=qt, owner=True, frozen=False
            )
        )
    # set contract as legit if no Errors
    return dbapi.set_legit(contract, check.count(False) == 0)


def apply_burn(contract):
    return True or False


def apply_mint(contract):
    return True or False


def apply_send(contract):
    return True or False


def apply_freeze(contract):
    return True or False


def apply_unfreeze(contract):
    return True or False


def apply_newowner(contract):
    return True or False


def apply_pause(contract):
    return True or False


def apply_resume(contract):
    return True or False


                # # `legit` is set to None (ie have to be applied next)
                # # if tx amount okay else False (ie will not be applied)
                # legit = None if (
                #     cost <= int(tx["amount"]) and (
                #         tx["recipientId"] == slp.JSON["master wallet"]
                #         if fields["tp"] != "SEND" else True
                #     )
                # ) else False
#                     # cost = slp.JSON["per token cost"][slp_type] * fields["qt"]
# def get_token_supply(tokenId):
#     supply = db.supply.find_one({"tokenId": tokenId})
#     return supply or {"error": "no contract found for tokenId %s" % tokenId}


# def transfer_token(tokenId, address, qt):
#     wallet = db.wallets.find_one({"address": address, "tokenId": tokenId})
#     if wallet:
#         db.wallets.update_one(wallet, {"$inc": {"balance": qt}})
#     else:
#         db.wallets.insert_one({
#             "tokenId": tokenId, "address": address, "balance": qt
#         })

# def add_slp1_contract(emitter, id, na, sy, qt, de, no, du, pa=False, mi=False):
#     contract = dict(
#         tokenId=id, owner=emitter, slpType="slp1",
#         name=na, symbol=sy, notes=no, uri=du,
#         globalSupply=qt, decimals=de,
#         pausable=pa, mintable=mi
#     )

#     try:
#         quantity = slp.Quantity(qt, de=de)
#         db.contrats.insert_one(contract)
#         db.supply.insert_one(
#             {"tokenId": id}, {
#                 "tokenId": id, "exchanged": 0,
#                 "minted": 0 if mi else quantity.q, "burned": 0,
#                 "frozen": False
#             }
#         )
#         if not mi:
#             transfer_token(id, emitter, qt)
#     except Exception as error:
#         slp.LOG.error("%r\n%s", error, traceback.format_exc())
#         return False
#     return True


# def mint(height, timestamp, owner, id, qt):
#     contract = db.contracts.find({"tokenId": id})
#     if contract:
#         transfer_token(id, owner, qt.q)
#         db.accountings.insert_one(
#             dict(
#                 height=height, timestamp=timestamp, tokenId=id,
#                 address=owner, minted=qt.q
#             )
#         )
#     return {"error": "no contract found for tokenId %s" % id}


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


# # def apply_input(msg):
# #     if not slp.BLOCKCHAIN_NODE:
# #         node.send_message({
# #             "confirm": dict(
# #                 msg["input"], **{"from": f"http://{slp.PUBLIC_IP}:{slp.PORT}"}
# #             )
# #         })
# #     else:
# #         # apply contract to database
# #         pass


# # def apply_confirm(msg):
# #     pass


# # def validate(contract):
# #     supply = db.supply.find(tokenId=contract["tokenId"])
# #     if supply.count() == 1:
# #         if not supply["frozen"]:
# #             #if is_legit(contract):
# #                 return contract
# #     return False
