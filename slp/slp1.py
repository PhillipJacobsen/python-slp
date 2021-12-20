# -*- coding:utf-8 -*-

import slp
import sys
import traceback

from slp import dbapi
from bson import Decimal128


def manage(contract):
    """
    Dispatch the contract according to its type.
    """
    try:
        assert contract.get("legit", False) is None
        return getattr(
            sys.modules[__name__], "apply_%s" % contract["tp"].lower()
        )(contract)
    except AssertionError:
        slp.LOG.error("Contract %s already applied", contract)
    except AttributeError:
        slp.LOG.error("Unknown contract type %s", contract["tp"])


def apply_genesis(contract):
    tokenId = contract["id"]
    try:
        # initial quantity should avoid decimal part
        assert contract["qt"] % 1 == 0
        # blockchain transaction amount have to match GENESIS cost
        assert contract["cost"] >= slp.JSON["GENESIS cost"]["aslp1"]
        # GENESIS contract have to be sent to master address
        assert contract["receiver"] == slp.JSON["master address"]
    except AssertionError:
        slp.LOG.error("invalid contract: %s", traceback.format_exc())
        return dbapi.set_legit(contract, False)
    else:
        # register Decimal128 for accounting precision
        slp.DECIMAL128[tokenId] = lambda v, de=contract.get('de', 0): \
            Decimal128(f"%.{de}f" % v)
        # get the token id associated decimal128 builder and convert qt value
        _decimal128 = slp.DECIMAL128[tokenId]
        # convert global sypply as decimal128 and compute minted supply. If
        # token is not mintable, mint global supply on contract creation and
        # credit with global supply on owner wallet creation
        globalSupply = _decimal128(contract["qt"])
        minted = _decimal128(0.) if contract.get("mi", False) else globalSupply
        # add new contract and new owner wallet into database
        check = [
            dbapi.db.contracts.insert_one(
                dict(
                    tokenId=tokenId, height=contract["height"],
                    index=contract["index"], type="aslp1", name=contract["na"],
                    owner=contract["emitter"], globalSupply=globalSupply,
                    paused=False, minted=minted, burned=_decimal128(0.),
                    exited=_decimal128(0.)
                )
            ),
            dbapi.db.wallets.insert_one(
                dict(
                    address=contract["emitter"], tokenId=tokenId,
                    blockStamp=f"{contract['height']}#{contract['index']}",
                    balance=minted, owner=True, frozen=False
                )
            )
        ]
        # set contract as legit if no errors (insert_one returns False if
        # element already exists in database)
        return dbapi.set_legit(contract, check.count(False) == 0)


def apply_burn(contract):
    tokenId = contract["id"]
    try:
        # burned quantity should avoid decimal part
        assert contract["qt"].to_decimal() % 1 == 0
        # BURN contract have to be sent to master address
        assert contract["receiver"] == slp.JSON["master address"]
        # get contract and wallet
        token = dbapi.find_contract(tokenId=tokenId)
        wallet = dbapi.find_wallet(
            address=contract["emitter"], tokenId=tokenId
        )
        # token and wallet exists
        assert token is not None
        assert wallet is not None
        # wallet is realy the owner
        assert wallet.get("owner", False) is True
        # token not paused by owner
        assert token.get("paused", False) is False
        # owner may burn only from his balance
        assert wallet["balance"].to_decimal() >= contract["qt"]
    except AssertionError:
        slp.LOG.error("invalid contract: %s", traceback.format_exc())
        return dbapi.set_legit(contract, False)
    else:
        return dbapi.set_legit(
            contract, dbapi.upsert_wallet(
                contract["emitter"], tokenId, dict(
                    blockStamp=f"{contract['height']}#{contract['index']}",
                    balance=slp.DECIMAL128[tokenId](
                        wallet["balance"].to_decimal() - contract["qt"]
                    )
                )
            )
        )


def apply_mint(contract):
    return False
    # tokenId = contract["id"]

    # try:
    #     assert contract["qt"] % 1 == 0
    #     assert contract["receiver"] == slp.JSON["master address"]
    #     token = dbapi.find_contract(**{"tokenId": tokenId})
    #     owner = dbapi.find_wallet(
    #         **dict(address=contract["emitter"], tokenId=tokenId)
    #     )
    #     # token and owner exists
    #     assert token and owner
    #     # owner is realy the owner
    #     assert owner.get("owner", False) is True
    #     # token not paused by owner
    #     assert token.get("paused", False) is False
    #     # owner may mint accourding to global supply limit
    #     current_supply = (
    #         token["burned"].to_decimal() + token["minted"].to_decimal() +
    #         token["exited"].to_decimal()
    #     )
    #     allowed_supply = token["globalSupply"].to_decimal()
    #     assert current_supply + qt < allowed_supply
    # except AssertionError:
    #     line = traceback.format_exc().split("\n")[-3].strip()
    #     slp.LOG.error("invalid contract: %s\n%s", line, contract)
    #     return dbapi.set_legit(contract, False)
    # else:
    #     new_balance = Decimal128(
    #         "%s" % (owner["balance"].to_decimal() + qt)
    #         )
    #     )
    #     return dbapi.set_legit(
    #         contract, dbapi.upsert_wallet(
    #             contract["emitter"], tokenId, dict(
    #                 blockStamp=f"{contract['height']}#{contract['index']}",
    #                 balance=new_balance
    #             )
    #         )
    #     )


def apply_send(contract):
    tokenId = contract["id"]
    try:
        token = dbapi.find_contract(tokenId=tokenId)
        emitter = dbapi.find_wallet(
            address=contract["emitter"], tokenId=tokenId
        )
        # token and emitter exists
        assert token is not None
        assert emitter is not None
        # token not paused by owner
        assert token.get("paused", False) is False
        # emitter not frozen by owner
        assert emitter.get("frozen", False) is False
        # emitter balance is okay
        assert emitter["balance"].to_decimal() > contract["qt"]
        # receiver is a valid address
        # chain.is_valid_address(contract["receiver"])
    except AssertionError:
        slp.LOG.error("invalid contract: %s", traceback.format_exc())
        return dbapi.set_legit(contract, False)
    else:
        return dbapi.set_legit(
            contract, dbapi.exchange_token(
                tokenId, f"{contract['height']}#{contract['index']}",
                contract["emitter"], contract["receiver"], contract["qt"]
            )
        )


def apply_freeze(contract):
    return False
    # tokenId = contract["id"]
    # try:
    #     token = dbapi.find_contract(**{"tokenId": tokenId})
    #     owner = dbapi.find_wallet(
    #         **dict(address=contract["emitter"], tokenId=tokenId)
    #     )
    #     receiver = dbapi.find_wallet(
    #         **dict(address=contract["receiver"], tokenId=tokenId)
    #     )
    #     # token and owner exists
    #     assert token and owner
    #     # owner is realy the owner
    #     assert owner.get("owner", False) is True
    #     # receiver is not already frozen
    #     assert receiver.get("frozen", False) is False
    # except AssertionError:
    #     line = traceback.format_exc().split("\n")[-3].strip()
    #     slp.LOG.error("invalid contract: %s\n%s", line, contract)
    #     return dbapi.set_legit(contract, False)
    # else:
    #     return dbapi.set_legit(
    #         contract, dbapi.upsert_wallet(
    #             contract["receiver"], tokenId, dict(
    #                 blockStamp=f"{contract['height']}#{contract['index']}",
    #                 frozen=True
    #             )
    #         )
    #     )


def apply_unfreeze(contract):
    return False


def apply_newowner(contract):
    return False


def apply_pause(contract):
    return False


def apply_resume(contract):
    return False
