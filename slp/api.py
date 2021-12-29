# -*- coding:utf-8 -*-

"""
Provide database REST interface.
"""

import slp
import math
import traceback

from usrv import srv
from slp import dbapi, serde

SEARCH_FIELDS = "address,tokenId,blockStamp,owner,frozen,"
"slp_type,emitter,receiver,legit,tp,sy,id,pa,mi,"
"height,index,type,paused,symbol".split(",")

DECIMAL128_FIELDS = "balance,minted,burned,exited,globalSupply".split(",")


@srv.bind("/<str:collection>/find", methods=["GET"])
def find(collection, **kw):
    try:
        # get collection
        col = getattr(dbapi.db, collection)

        # pop pagination keys
        orderBy = kw.pop("orderBy", None)
        page = int(kw.pop("page", 1))

        # filter kw so that only database specified keys can be search on.
        # it also gets rid of request environ (headers, environ, data...)
        kw = dict([k, v] for k, v in kw.items() if k in SEARCH_FIELDS)

        # convert bool values
        for key in [
            k for k in ["owner", "frozen", "paused", "pa", "mi"] if k in kw
        ]:
            kw[key] = True if kw[key].lower() in ['1', 'true'] else False

        # convert integer values
        for key in [k for k in ["height", "index"] if k in kw]:
            kw[key] = int(kw[key])

        # computes count and execute first filter
        total = col.count_documents(kw)
        pages = int(math.ceil(total / 100.))
        cursor = col.find(kw)

        # apply ordering
        if orderBy is not None:
            cursor = cursor.sort(
                tuple(
                    [field, -1 if order in "desc,Desc,DESC" else 1]
                    for field, order in [
                        order_by.split(":") for order_by in orderBy.split(",")
                    ]
                )
            )

        # jump to asked page
        cursor = cursor.skip((page-1) * 100)

        # build data
        data = []
        for reccord in list(cursor.limit(100)):
            reccord.pop("_id", False)
            if "metadata" in reccord:
                reccord["metadata"] = serde._unpack_meta(reccord["metadata"])
            for key in [k for k in DECIMAL128_FIELDS if k in reccord]:
                reccord[key] = str(reccord[key].to_decimal())
            data.append(reccord)

        return {
            "status": 200,
            "meta": {
                "count": len(data),
                "totalCount": total,
                "page": page,
                "pageCount": pages
            },
            "data": data
        }

    except Exception as error:
        slp.LOG.error(
            "Error trying to fetch data : %s\n%s", kw, traceback.format_exc()
        )
        return {"status": 501, "msg": "Internal Error: %r" % error}
