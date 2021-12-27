# -*- coding:utf-8 -*-

"""
Provide database REST interface.
"""

from slp import dbapi
from usrv import srv


@srv.bind("/<collection:srt>/find")
def find(collection, **kw):
    try:
        kw = dict(
            [k, v] for k, v in kw.items()
            if k not in "headers,url,data,method"
        )
        orderBy = dict(
            [field, -1 if order in "desc,Desc,DESC" else 1]
            for field, order in [
                order_by.split(":") for order_by in
                kw.pop("orderBy", "").split(",")
            ]
        )
        page = kw.pop("page", 1)

        return {
            "status": 200,
            "meta": {"page": page, "limit": 100},
            "data": list(
                getattr(dbapi.db, collection).find(kw).sort(orderBy)
                .skip(page-1 * 100).limit(100)
            )
        }
    except Exception:
        return {"status": 501, "msg": "Internal Error"}


@srv.bind("/<collection:srt>/find_one")
def find_one(collection, **kw):
    try:
        kw = dict(
            [k, v] for k, v in kw.items()
            if k not in "headers,url,data,method"
        )

        return {
            "status": 200, "meta": None,
            "data": getattr(dbapi.db, collection).find(kw)
        }
    except Exception:
        return {"status": 501, "msg": "Internal Error"}
