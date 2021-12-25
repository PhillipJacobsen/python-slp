# -*- coding:utf-8 -*-

"""
SLP2 contract execution module.
"""

import slp
import sys
import traceback

from slp import dbapi
from slp.serde import _pack_varia


def _pack_meta(**data):
    serial = b""
    metadata = sorted(data.items(), key=lambda i: len("%s%s" % i))
    for key, value in metadata:
        serial += _pack_varia(key, value)
    return serial


def manage(contract, **options):
    """
    Dispatch the contract according to its type.
    """
    try:
        assert contract.get("legit", False) is None
        result = getattr(
            sys.modules[__name__], "apply_%s" % contract["tp"].lower()
        )(contract, **options)
        if result is False:
            dbapi.db.rejected.insert_one(contract)
        return result
    except AssertionError:
        slp.LOG.error("Contract %s already applied", contract)
    except AttributeError:
        slp.LOG.error("Unknown contract type %s", contract["tp"])


def apply_genesis(contract, **options):
    tokenId = contract["id"]
    try:
        # blockchain transaction amount have to match GENESIS cost
        assert contract["cost"] >= slp.JSON["GENESIS cost"]["aslp1"]
        # GENESIS contract have to be sent to master address
        assert contract["receiver"] == slp.JSON["master address"]
        # return True if assertion only asked (test if contract is valid)
        if options.get("assert_only", False):
            return True
    except AssertionError:
        slp.LOG.debug("!%s", contract)
        slp.LOG.error("invalid contract: %s", traceback.format_exc())
        return dbapi.set_legit(contract, False)
    else:
        # add new contract and new owner wallet into database
        check = [
            dbapi.db.contracts.insert_one(
                dict(
                    tokenId=tokenId, height=contract["height"],
                    index=contract["index"], type="aslp2", name=contract["na"],
                    owner=contract["emitter"], document=contract["du"],
                    notes=contract.get("no", None), paused=False
                )
            ),
            dbapi.db.slp2.insert_one(
                dict(
                    address=contract["emitter"], tokenId=tokenId,
                    blockStamp=f"{contract['height']}#{contract['index']}",
                    owner=True, metadata=b""
                )
            )
        ]
        # set contract as legit if no errors (insert_one returns False if
        # element already exists in database)
        return dbapi.set_legit(contract, check.count(False) == 0)


def apply_newowner(contract, **options):
    tokenId = contract["id"]
    blockstamp = f"{contract['height']}#{contract['index']}"
    try:
        # TOKEN check ---
        token = dbapi.find_contract(tokenId=tokenId)
        # token exists
        assert token is not None
        # EMITTER check ---
        emitter = dbapi.find_slp2_wallet(
            address=contract["emitter"], tokenId=tokenId
        )
        # emitter exists
        assert emitter is not None
        # emitter is realy the owner
        assert emitter.get("owner", False) is True
        # check if contract blockstamp higher than emitter one
        assert dbapi.blockstamp_cmp(blockstamp, emitter["blockStamp"])
        # RECEIVER check ---
        receiver = dbapi.find_slp2_wallet(
            address=contract["receiver"], tokenId=tokenId
        )
        # receiver if exists is not already frozen
        if receiver is not None:
            assert receiver.get("frozen", False) is False
        # return True if assertion only asked (test if contract is valid)
        if options.get("assert_only", False):
            return True
    except AssertionError:
        slp.LOG.debug("!%s", contract)
        slp.LOG.error("invalid contract: %s", traceback.format_exc())
        return dbapi.set_legit(contract, False)
    else:
        blockstamp = f"{contract['height']}#{contract['index']}"
        check = []
        if receiver is None:
            check.append(
                dbapi.db.slp2.insert_one(
                    dict(
                        address=contract["receiver"], tokenId=tokenId,
                        blockStamp=blockstamp, owner=True, metadata=b""
                    )
                )
            )
            receiver = dbapi.find_slp2_wallet(
                address=contract["receiver"], tokenId=tokenId
            )
        check += [
            dbapi.update_slp2_wallet(
                receiver["address"], tokenId, {
                    "owner": True, "blockStamp": blockstamp,
                    "metadata": receiver["metadata"] + emitter["metadata"]
                }
            ),
            dbapi.update_slp2_wallet(
                emitter["address"], tokenId,
                {"owner": False, "blockStamp": blockstamp, "metadata": b""}
            )
        ]
        return dbapi.set_legit(contract, check.count(False) == 0)


def apply_pause(contract, **options):
    tokenId = contract["id"]
    blockstamp = f"{contract['height']}#{contract['index']}"
    try:
        # GENESIS check ---
        reccord = dbapi.find_reccord(id=tokenId, tp="GENESIS")
        assert reccord is not None and reccord["pa"] is True
        # PAUSE contract have to be sent to master address
        assert contract["receiver"] == slp.JSON["master address"]
        # TOKEN check ---
        token = dbapi.find_contract(tokenId=tokenId)
        # token exists
        assert token is not None
        # token not paused by owner
        assert token.get("paused", False) is False
        # EMITTER check ---
        emitter = dbapi.find_slp2_wallet(
            address=contract["emitter"], tokenId=tokenId
        )
        # emitter exists
        assert emitter is not None
        # emitter is realy the owner
        assert emitter.get("owner", False) is True
        # check if contract blockstamp higher than emitter one
        assert dbapi.blockstamp_cmp(blockstamp, emitter["blockStamp"])
        # return True if assertion only asked (test if contract is valid)
        if options.get("assert_only", False):
            return True
    except Exception:
        slp.LOG.debug("!%s", contract)
        slp.LOG.error("invalid contract: %s", traceback.format_exc())
        return dbapi.set_legit(contract, False)
    else:
        return dbapi.set_legit(
            contract, dbapi.update_contract(tokenId, {"paused": True})
        )


def apply_resume(contract, **options):
    tokenId = contract["id"]
    blockstamp = f"{contract['height']}#{contract['index']}"
    try:
        # GENESIS check ---
        reccord = dbapi.find_reccord(id=tokenId, tp="GENESIS")
        assert reccord is not None and reccord["pa"] is True
        # RESUME contract have to be sent to master address
        assert contract["receiver"] == slp.JSON["master address"]
        # TOKEN check ---
        token = dbapi.find_contract(tokenId=tokenId)
        # token exists
        assert token is not None
        # token not paused by owner
        assert token.get("paused", False) is True
        # EMITTER check ---
        emitter = dbapi.find_slp2_wallet(
            address=contract["emitter"], tokenId=tokenId
        )
        # emitter exists
        assert emitter is not None
        # emitter is realy the owner
        assert emitter.get("owner", False) is True
        # check if contract blockstamp higher than emitter one
        assert dbapi.blockstamp_cmp(blockstamp, emitter["blockStamp"])
        # return True if assertion only asked (test if contract is valid)
        if options.get("assert_only", False):
            return True
    except Exception:
        slp.LOG.debug("!%s", contract)
        slp.LOG.error("invalid contract: %s", traceback.format_exc())
        return dbapi.set_legit(contract, False)
    else:
        return dbapi.set_legit(
            contract, dbapi.update_contract(tokenId, {"paused": False})
        )


def apply_authmeta(contract, **options):
    tokenId = contract["id"]
    blockstamp = f"{contract['height']}#{contract['index']}"
    try:
        # GENESIS check ---
        reccord = dbapi.find_reccord(id=tokenId, tp="GENESIS")
        assert reccord is not None
        # TOKEN check ---
        token = dbapi.find_contract(tokenId=tokenId)
        # token exists
        assert token is not None
        # token not paused by owner
        assert token.get("paused", False) is False
        # EMITTER check ---
        emitter = dbapi.find_slp2_wallet(
            address=contract["emitter"], tokenId=tokenId
        )
        # emitter exists
        assert emitter is not None
        # emitter is realy the owner
        assert emitter.get("owner", False) is True
        # RECEIVER check ---
        receiver = dbapi.find_slp2_wallet(
            address=contract["receiver"], tokenId=tokenId
        )
        # receiver should not exists
        assert receiver is None
        # return True if assertion only asked (test if contract is valid)
        if options.get("assert_only", False):
            return True
    except Exception:
        slp.LOG.debug("!%s", contract)
        slp.LOG.error("invalid contract: %s", traceback.format_exc())
        return dbapi.set_legit(contract, False)
    else:
        blockstamp = f"{contract['height']}#{contract['index']}"
        return dbapi.set_legit(
            contract, dbapi.db.slp2.insert_one(
                dict(
                    address=contract["receiver"], tokenId=tokenId,
                    blockStamp=blockstamp, owner=False, metadata=b""
                )
            )
        )


def apply_addmeta(contract, **options):
    tokenId = contract["id"]
    blockstamp = f"{contract['height']}#{contract['index']}"
    try:
        # GENESIS check ---
        reccord = dbapi.find_reccord(id=tokenId, tp="GENESIS")
        assert reccord is not None
        # ADDMETA contract have to be sent to master address
        assert contract["receiver"] == slp.JSON["master address"]
        # TOKEN check ---
        token = dbapi.find_contract(tokenId=tokenId)
        # token exists
        assert token is not None
        # token not paused by owner
        assert token.get("paused", False) is False
        # EMITTER check ---
        emitter = dbapi.find_slp2_wallet(
            address=contract["emitter"], tokenId=tokenId
        )
        # emitter exists
        assert emitter is not None
        # check if contract blockstamp higher than emitter one
        assert dbapi.blockstamp_cmp(blockstamp, emitter["blockStamp"])
        # return True if assertion only asked (test if contract is valid)
        if options.get("assert_only", False):
            return True
    except Exception:
        slp.LOG.debug("!%s", contract)
        slp.LOG.error("invalid contract: %s", traceback.format_exc())
        return dbapi.set_legit(contract, False)
    else:
        data = (
            emitter["metadata"] +
            _pack_meta(**{contract["na"]: contract["dt"]})
        )
        print(data)
        return dbapi.set_legit(
            contract, dbapi.update_slp2_wallet(
                emitter["address"], tokenId,
                {"blockStamp": blockstamp, "metadata": data}
            )
        )


def apply_revokemeta(contract, **options):
    return False


def apply_voidmeta(contract, **options):
    return False


def apply_clone(contract, **options):
    return False
