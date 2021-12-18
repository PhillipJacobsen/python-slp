# -*- coding:utf-8 -*-

import slp
import sys
import traceback

from slp import dbapi
from bson import Decimal128


def manage(contract):
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
        # contract have to be sent to master address
        assert contract["receiver"] == slp.JSON["master address"]
    except AssertionError:
        line = traceback.format_exc().split("\n")[-3].strip()
        slp.LOG.error("invalid contract: %s\n%s", line, contract)
        return dbapi.set_legit(contract, False)
    # add Decimal128 for accounting precision
    slp.DECIMAL128[tokenId] = \
        lambda v, de=contract.get('de', 0): \
        Decimal128(f"%.{de}f" % v)
    qt = slp.DECIMAL128[tokenId](contract["qt"])
    # add contract
    check = [
        dbapi.db.contracts.insert_one(
            dict(
                tokenId=tokenId, height=contract["height"],
                index=contract["index"], type="aslp1", name=contract["na"],
                owner=contract["emitter"], globalSupply=qt, paused=False,
                minted=slp.DECIMAL128[tokenId](0.),
                burned=slp.DECIMAL128[tokenId](0.),
                exited=slp.DECIMAL128[tokenId](0.)
            )
        )
    ]
    # add owner ballance if not mintable
    if not contract.get("mi", False):
        check.append(dbapi.upsert_contract(dict(tokenId=tokenId, minted=qt)))
        check.append(
            dbapi.db.wallets.insert_one(
                dict(
                    address=contract["emitter"], tokenId=tokenId,
                    lastUpdate=f"{contract['height']}#{contract['index']}",
                    balance=qt, owner=True, frozen=False
                )
            )
        )
    # set contract as legit if no Errors
    return dbapi.set_legit(contract, check.count(False) == 0)


def apply_burn(contract):
    tokenId = contract["id"]
    try:
        assert contract["qt"] % 1 == 0
        assert contract["receiver"] == slp.JSON["master address"]
        token = dbapi.find_contract(**{"tokenId": tokenId})
        owner = dbapi.find_wallet(
            **dict(address=contract["emitter"], tokenId=tokenId)
        )
        # token and owner exists
        assert token and owner
        # emitter is realy the owner
        assert owner.get("owner", False) is True
        # token not paused by owner
        assert token.get("paused", False) is False
        # owner may burn only from his balance
        assert owner["balance"].to_decimal() >= contract["qt"]
    except AssertionError:
        line = traceback.format_exc().split("\n")[-3].strip()
        slp.LOG.error("invalid contract: %s\n%s", line, contract)
        return dbapi.set_legit(contract, False)
    else:
        new_balance = Decimal128(
            "%s" % (owner["balance"].to_decimal() - contract["qt"])
        )
        return dbapi.set_legit(
            contract, dbapi.upsert_wallet(
                contract["emitter"], tokenId, dict(
                    lastUpdate=f"{contract['height']}#{contract['index']}",
                    balance=new_balance
                )
            )
        )


def apply_mint(contract):
    tokenId = contract["id"]
    try:
        assert contract["qt"] % 1 == 0
        assert contract["receiver"] == slp.JSON["master address"]
        token = dbapi.find_contract(**{"tokenId": tokenId})
        owner = dbapi.find_wallet(
            **dict(address=contract["emitter"], tokenId=tokenId)
        )
        # token and owner exists
        assert token and owner
        # owner is realy the owner
        assert owner.get("owner", False) is True
        # token not paused by owner
        assert token.get("paused", False) is False
        # owner may mint accourding to global supply limit
        assert (
            token["burned"].to_decimal() + token["minted"].to_decimal() +
            token["exited"].to_decimal()
        ) < token["globalSupply"].to_decimal()
    except AssertionError:
        line = traceback.format_exc().split("\n")[-3].strip()
        slp.LOG.error("invalid contract: %s\n%s", line, contract)
        return dbapi.set_legit(contract, False)
    else:
        new_balance = Decimal128(
            "%s" % (owner["balance"].to_decimal() + contract["qt"])
        )
        return dbapi.set_legit(
            contract, dbapi.upsert_wallet(
                contract["emitter"], tokenId, dict(
                    lastUpdate=f"{contract['height']}#{contract['index']}",
                    balance=new_balance
                )
            )
        )


def apply_send(contract):
    tokenId = contract["id"]
    try:
        token = dbapi.find_contract(**{"tokenId": tokenId})
        emitter = dbapi.find_wallet(
            **dict(address=contract["emitter"], tokenId=tokenId)
        )
        # token and emitter exists
        assert token and emitter
        # token not paused by owner
        assert token.get("paused", False) is False
        # emitter not frozen by owner
        assert emitter.get("frozen", False) is False
        # emitter balance is okay
        assert emitter["balance"].to_decimal() > contract["qt"]
        # receiver is a valid address
        # chain.is_valid_address(contract["receiver"])
    except AssertionError:
        line = traceback.format_exc().split("\n")[-3].strip()
        slp.LOG.error("invalid contract: %s\n%s", line, contract)
        return dbapi.set_legit(contract, False)
    else:
        receiver = dbapi.find_wallet(
            **dict(address=contract["receiver"], tokenId=tokenId)
        )
        if receiver is None:
            dbapi.db.wallets.insert_one(
                dict(
                    address=contract["receiver"], tokenId=tokenId,
                    lastUpdate=f"{contract['height']}#{contract['index']}",
                    balance=slp.DECIMAL128[tokenId](0.), owner=False,
                    frozen=False
                )
            )
        return dbapi.set_legit(
            contract, dbapi.exchange_token(
                tokenId, contract["emitter"], contract["receiver"],
                contract["qt"]
            )
        )


def apply_freeze(contract):
    tokenId = contract["id"]
    try:
        token = dbapi.find_contract(**{"tokenId": tokenId})
        owner = dbapi.find_wallet(
            **dict(address=contract["emitter"], tokenId=tokenId)
        )
        receiver = dbapi.find_wallet(
            **dict(address=contract["receiver"], tokenId=tokenId)
        )
        # token and owner exists
        assert token and owner
        # owner is realy the owner
        assert owner.get("owner", False) is True
        # receiver is not already frozen
        assert receiver.get("frozen", False) is False
    except AssertionError:
        line = traceback.format_exc().split("\n")[-3].strip()
        slp.LOG.error("invalid contract: %s\n%s", line, contract)
        return dbapi.set_legit(contract, False)
    else:
        return dbapi.set_legit(
            contract, dbapi.upsert_wallet(
                contract["receiver"], tokenId, dict(
                    lastUpdate=f"{contract['height']}#{contract['index']}",
                    frozen=True
                )
            )
        )


def apply_unfreeze(contract):
    return True or False


def apply_newowner(contract):
    return True or False


def apply_pause(contract):
    return True or False


def apply_resume(contract):
    return True or False
