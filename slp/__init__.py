# -*- coding:utf-8 -*-

import io
import os
import json
import socket
import logging

BLOCKCHAIN_NODE = False
PUBLIC_IP = "127.0.0.1"
PORT = 5000

LOG = logging.getLogger("slp")
LOG.setLevel("DEBUG")

with io.open(os.path.join(os.path.dirname(__file__), "slp.json")) as f:
    JSON = json.load(f)


class Quantity(float):

    lowest = -2**63
    highest = -lowest - 1

    q = property(lambda cls: int(cls*cls._k), None, None, "")

    def __new__(self, *a, **kw):
        self._de = kw.pop("de", 0)
        self._k = 10**self._de
        self._lowest = Quantity.lowest // self._k
        self._highest = Quantity.highest // self._k
        return float.__new__(
            self,
            round(float(*a, **kw)/self._k, self._de)
        )

    def __repr__(self):
        return f"Quantity(%.{self._de}f, {self._de})" % float(self)

    def __add__(self, other):
        val = float.__add__(self, other)
        return Quantity(self._check(val) * self._k, de=self._de)

    def __sub__(self, other):
        val = float.__sub__(self, other)
        return Quantity(self._check(val) * self._k, de=self._de)

    def __mul__(self, other):
        val = float.__mul__(self, other)
        return Quantity(self._check(val) * self._k, de=self._de)

    def __pow__(self, other):
        val = float.__pow__(self, other)
        return Quantity(self._check(val) * self._k, de=self._de)

    def __mod__(self, other):
        val = float.__mod__(self, other)
        return Quantity(self._check(val) * self._k, de=self._de)

    def __truediv__(self, other):
        val = float.__truediv__(self, other)
        return Quantity(self._check(val) * self._k, de=self._de)

    def __floordiv__(self, other):
        val = float.__floordiv__(self, other)
        return Quantity(self._check(val) * self._k, de=self._de)

    def __iadd__(self, other):
        val = float.__iadd__(self, other)
        return Quantity(self._check(val) * self._k, de=self._de)

    def __isub__(self, other):
        val = float.__isub__(self, other)
        return Quantity(self._check(val) * self._k, de=self._de)

    def __imul__(self, other):
        val = float.__imul__(self, other)
        return Quantity(self._check(val) * self._k, de=self._de)

    def __ipow__(self, other):
        val = float.__ipow__(self, other)
        return Quantity(self._check(val) * self._k, de=self._de)

    def __imod__(self, other):
        val = float.__imod__(self, other)
        return Quantity(self._check(val) * self._k, de=self._de)

    def __itruediv__(self, other):
        val = float.__itruediv__(self, other)
        return Quantity(self._check(val) * self._k, de=self._de)

    def __ifloordiv__(self, other):
        val = float.__ifloordiv__(self, other)
        return Quantity(self._check(val) * self._k, de=self._de)

    def _check(self, value):
        try:
            assert self._lowest <= value <= self._highest
        except AssertionError:
            raise Exception("%r can't be set to %s" % (value, self))
        return value


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
    pass
