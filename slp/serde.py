# -*- coding:utf-8 -*-

"""
(c) THOORENS Bruno MIT Licence
Improvment of Side Level Protocol smartbridge use.
"""

import slp

import re
import struct
import binascii

# REGEXP for validation, can be used for webhook subscription
SLP = re.compile(slp.JSON["serialized regex"])
INPUT_TYPES = slp.JSON.get("input types", {})
TYPES_INPUT = dict([v, k] for k, v in INPUT_TYPES.items())


def _pack_varia(*varias):
    "pack a list of variable length strings"
    serial = b""
    for varia in [v.encode() for v in varias]:
        len_v = len(varia)
        serial += struct.pack("<B%ds" % len_v, len_v, varia)
    return serial


def _unpack_varia(data, *keys):
    "unpack a list of variable length string associated to specific keys"
    result = {}
    n = 0
    i = struct.calcsize("<B")
    for key in keys:
        size, = struct.unpack("<B", data[n:n+i])
        n += i
        value, = struct.unpack("<%ss" % size, data[n:n+size])
        result[key] = value.decode()
        n += size
    return result


def _unpack_meta(data):
    "unpack metadata from string and build the mapping"
    result = []
    n = 0
    i = struct.calcsize("<B")
    while n < len(data) - 1:
        size, = struct.unpack("<B", data[n:n+i])
        n += i
        value, = struct.unpack("<%ss" % size, data[n:n+size])
        result.append(value.decode())
        n += size
    return dict(zip(result[0::2], result[1::2]))


def _match_smartbridge(smartbridge):
    match = SLP.match(smartbridge)
    if match is not None:
        return match.groups()
    else:
        raise Exception("Not a valid smartbridge")


# -- SLP1 SERIALIZATION --
def pack_aslp1_genesis(de, qt, sy, na, du="", no="", pa=False, mi=False):
    fixed = struct.pack(
        "<BBQ??", INPUT_TYPES["GENESIS"],
        int(de), int(qt), bool(pa), bool(mi)
    )
    varia = _pack_varia(sy, na, du, no)
    return "aslp1://" + binascii.hexlify(fixed).decode() + varia.decode()


def pack_aslp1_fungible(tb, id, qt, no=""):
    fixed = struct.pack("<B16sQ", INPUT_TYPES[tb], binascii.unhexlify(id), qt)
    varia = _pack_varia(no)
    return "aslp1://" + binascii.hexlify(fixed).decode() + varia.decode()


def pack_aslp1_non_fungible(tb, id, no=""):
    fixed = struct.pack("<B16sQ", INPUT_TYPES[tb], binascii.unhexlify(id))
    varia = _pack_varia(no)
    return "aslp1://" + binascii.hexlify(fixed).decode() + varia.decode()


# -- SLP2 SERIALIZATION --
def pack_aslp2_genesis(sy, na, du="", no="", pa=False):
    fixed = struct.pack("<B?", INPUT_TYPES["GENESIS"], pa)
    varia = _pack_varia(sy, na, du, no)
    return "aslp2://" + binascii.hexlify(fixed).decode() + varia.decode()


def pack_aslp2_non_fungible(tb, id, no=""):
    fixed = struct.pack("<B16sQ", INPUT_TYPES[tb], binascii.unhexlify(id))
    varia = _pack_varia(no)
    return "aslp2://" + binascii.hexlify(fixed).decode() + varia.decode()


def pack_aslp2_addmeta(id, **data):
    metadata = sorted(data.items(), key=lambda i: len("%s%s" % i))
    # pack fixed size data
    fixed = struct.pack(
        "<B16s", INPUT_TYPES["ADDMETA"], binascii.unhexlify(id)
    )
    # smartbridge size - header size - 2*(fixed size + chunk size)
    spaceleft = 256 - len("slp2://") - 2*(len(fixed) + 1)
    # compute the metadata and return a list of smartbridges to contain
    # all the asked metadata
    result = []
    serial = b""
    remaining = spaceleft
    for key, value in metadata:
        if len(key) + len(value) < remaining - 2:
            ser = _pack_varia(key, value)
            serial += ser
            remaining -= len(ser)
        else:
            result.append(serial)
            serial = b"" + _pack_varia(key, value)
            remaining = spaceleft
    result.append(serial)
    # build all smartbridges adding chunk number between fixed and serial
    return [
        "aslp2://" + (
            binascii.hexlify(
                fixed + struct.pack("<B", result.index(serial) + 1)
            ).decode() + serial.decode()
        ) for serial in result
    ]


def pack_aslp2_voidmeta(id, tx):
    fixed = struct.pack(
        "<B16s128s", INPUT_TYPES["VOIDMETA"],
        binascii.unhexlify(id), binascii.unhexlify(tx)
    )
    return "aslp2://" + binascii.hexlify(fixed).decode()


# -- SLP1 DESERIALIZATION --
def unpack_aslp1_genesis(data):
    n = int(struct.calcsize("<BBQ??") * 2)
    fixed = binascii.unhexlify(data[:n])
    varia = data[n:].encode()
    result = dict(
        zip(["tp", "de", "qt", "pa", "mi"], struct.unpack("<BBQ??", fixed)),
        **_unpack_varia(varia, "sy", "na", "du", "no")
    )
    result["tp"] = TYPES_INPUT[result["tp"]]
    return {"aslp1": result}


def unpack_aslp1_fungible(data):
    n = int(struct.calcsize("<B16sQ") * 2)
    fixed = binascii.unhexlify(data[:n])
    varia = data[n:].encode()
    result = dict(
        zip(["tp", "id", "qt"], struct.unpack("<B16sQ", fixed)),
        **_unpack_varia(varia, "no")
    )
    result["id"] = binascii.hexlify(result["id"]).decode()
    result["tp"] = TYPES_INPUT[result["tp"]]
    return {"aslp1": result}


def unpack_aslp1_non_fungible(data):
    n = int(struct.calcsize("<B16s") * 2)
    fixed = binascii.unhexlify(data[:n])
    varia = data[n:].encode()
    result = dict(
        zip(["tp", "id"], struct.unpack("<B16s", fixed)),
        **_unpack_varia(varia, "no")
    )
    result["id"] = binascii.hexlify(result["id"]).decode()
    result["tp"] = TYPES_INPUT[result["tp"]]
    return {"aslp1": result}


# -- SLP2 DESERIALIZATION --
def unpack_aslp2_genesis(data):
    n = int(struct.calcsize("<B?") * 2)
    fixed = binascii.unhexlify(data[:n])
    varia = data[n:].encode()
    result = dict(
        zip(["tp", "pa"], struct.unpack("<B?", fixed)),
        **_unpack_varia(varia, "sy", "na", "du", "no")
    )
    result["tp"] = TYPES_INPUT[result["tp"]]
    return {"aslp2": result}


def unpack_aslp2_non_fungible(data):
    n = int(struct.calcsize("<B16s") * 2)
    fixed = binascii.unhexlify(data[:n])
    varia = data[n:].encode()
    result = dict(
        zip(["tp", "id"], struct.unpack("<B16s", fixed)),
        **_unpack_varia(varia, "no")
    )
    result["id"] = binascii.hexlify(result["id"]).decode()
    result["tp"] = TYPES_INPUT[result["tp"]]
    return {"aslp2": result}


def unpack_aslp2_addmeta(data):
    n = int(struct.calcsize("<B16sB") * 2)
    fixed = binascii.unhexlify(data[:n])
    varia = data[n:].encode()
    result = dict(
        zip(["tp", "id", "ch"], struct.unpack("<B16sB", fixed)),
        **{"dt": _unpack_meta(varia)}
    )
    result["id"] = binascii.hexlify(result["id"]).decode()
    result["tp"] = TYPES_INPUT[result["tp"]]
    return {"aslp2": result}


def unpack_aslp2_voidmeta(data):
    # n = int(struct.calcsize("<B16s128s") * 2)
    fixed = binascii.unhexlify(data)
    # varia = data[n:].encode()
    result = dict(
        zip(["tp", "tx"], struct.unpack("<B16sB", fixed)),
        # **_unpack_meta(varia)
    )
    result["id"] = binascii.hexlify(result["id"]).decode()
    result["tx"] = binascii.hexlify(result["tx"]).decode()
    return {"aslp2": result}


MAP = {
    'aslp1': {
        "00": unpack_aslp1_genesis,
        "01": unpack_aslp1_fungible,
        "02": unpack_aslp1_fungible,
        "03": unpack_aslp1_fungible,
        "04": unpack_aslp1_non_fungible,
        "05": unpack_aslp1_non_fungible,
        "06": unpack_aslp1_non_fungible,
        "07": unpack_aslp1_non_fungible,
        "08": unpack_aslp1_non_fungible
    },
    'aslp2': {
        "00": unpack_aslp2_genesis,
        "04": unpack_aslp2_non_fungible,
        "05": unpack_aslp2_non_fungible,
        "06": unpack_aslp2_non_fungible,
        "09": unpack_aslp2_non_fungible,
        "10": unpack_aslp2_addmeta,
        "11": unpack_aslp2_non_fungible,
        "12": unpack_aslp2_voidmeta,
        "13": unpack_aslp2_non_fungible
    }
}


def pack_aslp1(*args, **kwargs):
    if args[0] in "BURN,SEND,MINT":
        smartbridge = pack_aslp1_fungible(*args, **kwargs)
    elif args[0] in "PAUSE,RESUME,NEWOWNER,FREEZE,UNFREEZE":
        smartbridge = pack_aslp1_non_fungible(*args, **kwargs)
    elif args[0] == "GENESIS":
        smartbridge = pack_aslp1_genesis(*args[1:], **kwargs)
    else:
        raise Exception("Unknown contract !")
    if len(smartbridge) <= 256:
        return smartbridge
    else:
        raise Exception("Bad smartbridge size (>256)")


def pack_aslp2(*args, **kwargs):
    if args[0] in "PAUSE,RESUME,NEWOWNER,AUTHMETA,REVOKEMETA,CLONE":
        smartbridge = pack_aslp2_non_fungible(*args, **kwargs)
    elif args[0] == "ADDMETA":
        smartbridge = pack_aslp2_addmeta(*args[1:], **kwargs)
    elif args[0] == "VOIDMETA":
        smartbridge = pack_aslp2_voidmeta(*args[1:], **kwargs)
    elif args[0] == "GENESIS":
        smartbridge = pack_aslp2_genesis(*args[1:], **kwargs)
    else:
        raise Exception("Unknown contract !")
    if len(smartbridge) <= 256:
        return smartbridge
    else:
        raise Exception("Bad smartbridge size (>256)")


def unpack_slp(smartbridge):
    slp_type, data = _match_smartbridge(smartbridge)
    if slp_type not in slp.JSON["slp types"]:
        raise Exception(
            "Expecting %s contract, not %s" % (
                " or ".join(slp.JSON["slp types"]),
                slp_type
            )
        )
    return MAP[slp_type][data[:2]](data)
