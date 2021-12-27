# -*- coding:utf-8 -*-

import io
import os
import re
import json
import socket
import logging
import logging.handlers

with io.open(os.path.join(os.path.dirname(__file__), "slp.json")) as f:
    JSON = json.load(f)

ROOT = os.path.abspath(os.path.dirname(__file__))
BLOCKCHAIN_NODE = False
PUBLIC_IP = "127.0.0.1"
PORT = 5000

DECIMAL128 = {}
VALIDATION = {
    "tp": lambda value: value in JSON["input types"],
    "id": lambda value: re.match(r"^[0-9a-fA-F]{32}$", value) is not None,
    "qt": lambda value: isinstance(value, (int, float)),
    "de": lambda value: 0 <= value <= 8,
    "sy": lambda value: re.match(r"^[0-9a-zA-Z]{3,8}$", value) is not None,
    "na": lambda value: re.match(r"^.{3,24}$", value) is not None,
    "du": lambda value: (value == "") or (
        re.match(
            r"(https?|ipfs|ipns|dweb):\/\/[a-z0-9\/:%_+.,#?!@&=-]{3,180}",
            value
        )
    ) is not None,
    "no": lambda value: re.match(r"^.{0,180}$", value) is not None,
    "pa": lambda value: value in [True, False, 0, 1],
    "mi": lambda value: value in [True, False, 0, 1],
    "ch": lambda value: isinstance(value, int),
    "dt": lambda value: re.match(r"^.{0,256}$", value) is not None
}
HEADERS = {
    "API-Version": "3",
    "Content-Type": "application/json",
    "User-Agent": "Python/usrv - Side Ledger Protocol"
}

LOG = logging.getLogger("slp")
LOG.setLevel(JSON.get("log level", "DEBUG"))
# TODO: add log rotation parameters to slp.json
logpath = os.path.join(ROOT, ".log", f"{JSON['database name']}.log")
os.makedirs(os.path.dirname(logpath), exist_ok=True)
LOG.addHandler(
    logging.handlers.TimedRotatingFileHandler(logpath, when="H", interval=1)
)


def validate(**fields):
    tests = dict(
        [k, VALIDATION[k](v)] for k, v in fields.items() if k in VALIDATION
    )
    LOG.debug("validation result: %s", tests)
    return list(tests.values()).count(False) == 0


def set_public_ip():
    """Store the public ip of server in PUBLIC_IP global var"""
    global PUBLIC_IP
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        # doesn't even have to be reachable
        s.connect(('10.255.255.255', 1))
        PUBLIC_IP = s.getsockname()[0]
    except Exception:
        PUBLIC_IP = '127.0.0.1'
    finally:
        s.close()
    return PUBLIC_IP


def is_blockchain_node():
    global BLOCKCHAIN_NODE
    return os.path.exists(
        os.path.expanduser("~/.config/ark-core")
    )


def loadJson(name, folder=None):
    filename = os.path.join(JSON if not folder else folder, name)
    if os.path.exists(filename):
        with io.open(filename, "r", encoding="utf-8") as in_:
            data = json.load(in_)
    else:
        data = {}
    return data


def dumpJson(data, name, folder=None):
    filename = os.path.join(JSON if not folder else folder, name)
    try:
        os.makedirs(os.path.dirname(filename))
    except OSError:
        pass
    with io.open(filename, "w", encoding="utf-8") as out:
        json.dump(data, out, indent=4)
