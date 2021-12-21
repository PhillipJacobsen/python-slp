# -*- coding:utf-8 -*-

"""
SLP1 contract execution module.
"""

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
        # token and wallet exists
        assert token is not None
        # token not paused by owner
        assert token.get("paused", False) is False
        wallet = dbapi.find_wallet(
            address=contract["emitter"], tokenId=tokenId
        )
        assert wallet is not None
        # wallet is realy the owner
        assert wallet.get("owner", False) is True
        # owner may burn only from his balance
        assert wallet["balance"].to_decimal() >= contract["qt"]
    except AssertionError:
        slp.LOG.error("invalid contract: %s", traceback.format_exc())
        return dbapi.set_legit(contract, False)
    else:
        _decimal128 = slp.DECIMAL128[tokenId]
        check = [
            # remove quantity from owner wallet
            dbapi.upsert_wallet(
                contract["emitter"], tokenId, dict(
                    blockStamp=f"{contract['height']}#{contract['index']}",
                    balance=_decimal128(
                        wallet["balance"].to_decimal() - contract["qt"]
                    )
                )
            ),
            dbapi.upsert_contract(
                tokenId, dict(
                    burned=_decimal128(
                        token["burned"].to_decimal() + contract["qt"]
                    )
                )
            )
        ]
        return dbapi.set_legit(contract, check.count(False) == 0)


def apply_mint(contract):
    tokenId = contract["id"]
    try:
        # minted quantity should avoid decimal part
        assert contract["qt"].to_decimal() % 1 == 0
        # BURN contract have to be sent to master address
        assert contract["receiver"] == slp.JSON["master address"]
        token = dbapi.find_contract(tokenId=tokenId)
        # token and owner exists
        assert token is not None
        # token not paused by owner
        assert token.get("paused", False) is False
        wallet = dbapi.find_wallet(
            address=contract["emitter"], tokenId=tokenId
        )
        assert wallet is not None
        # wallet is realy the owner
        assert wallet.get("owner", False) is True
        # owner may mint accourding to global supply limit
        current_supply = (
            token["burned"].to_decimal() + token["minted"].to_decimal() +
            token["exited"].to_decimal()
        )
        allowed_supply = token["globalSupply"].to_decimal()
        assert current_supply + contract["qt"] <= allowed_supply
    except AssertionError:
        slp.LOG.error("invalid contract: %s", traceback.format_exc())
        return dbapi.set_legit(contract, False)
    else:
        _decimal128 = slp.DECIMAL128[tokenId]
        check = [
            dbapi.upsert_wallet(
                contract["emitter"], tokenId, dict(
                    blockStamp=f"{contract['height']}#{contract['index']}",
                    balance=slp.DECIMAL128[tokenId](
                        wallet["balance"].to_decimal() + contract["qt"]
                    )
                )
            ),
            dbapi.upsert_contract(
                tokenId, dict(
                    burned=_decimal128(
                        token["minted"].to_decimal() + contract["qt"]
                    )
                )
            )
        ]
        return dbapi.set_legit(contract, check.count(False) == 0)


def apply_send(contract):
    tokenId = contract["id"]
    try:
        token = dbapi.find_contract(tokenId=tokenId)
        # token and emitter exists
        assert token is not None
        # token not paused by owner
        assert token.get("paused", False) is False
        emitter = dbapi.find_wallet(
            address=contract["emitter"], tokenId=tokenId
        )
        assert emitter is not None
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


def apply_newowner(contract):
    tokenId = contract["id"]
    try:
        # TOKEN check ---
        token = dbapi.find_contract(tokenId=tokenId)
        # token exists
        assert token is not None
        # EMITTER check ---
        emitter = dbapi.find_wallet(
            address=contract["emitter"], tokenId=tokenId
        )
        # emitter exists
        assert emitter is not None
        # emitter is realy the owner
        assert emitter.get("owner", False) is True
        # RECEIVER check ---
        receiver = dbapi.find_wallet(
            address=contract["receiver"], tokenId=tokenId
        )
        # receiver is not already frozen
        if receiver is not None:
            assert receiver.get("frozen", False) is False
    except AssertionError:
        slp.LOG.error("invalid contract: %s", traceback.format_exc())
        return dbapi.set_legit(contract, False)
    else:
        check = [
            dbapi.exchange_token(
                tokenId, f"{contract['height']}#{contract['index']}",
                contract["emitter"], contract["receiver"],
                emitter["balance"].to_decimal()
            ),
            dbapi.upsert_wallet(emitter["address"], tokenId, {"owner": False}),
            dbapi.upsert_wallet(receiver["address"], tokenId, {"owner": True})
        ]
        return dbapi.set_legit(contract, check.count(False) == 0)


def apply_freeze(contract):
    return False


def apply_unfreeze(contract):
    return False


def apply_pause(contract):
    return False


def apply_resume(contract):
    return False
