# -*- coding:utf-8 -*-
# FOR TESTING PURPOSE ONLY ---

import os
import sys

sys.path.append(os.path.abspath(os.path.dirname(__file__)))

if __name__ == "__main__":
    import slp
    from usrv import srv
    from slp import msg, node

    parser = srv.OptionParser(
        usage="usage: %prog [options] BINDINGS...",
        version="%prog 1.0"
    )
    parser.add_option(
        "-i", "--ip", action="store", dest="host", default=slp.PUBLIC_IP,
        help="ip to run from             [default: slp defaul public ip]"
    )
    parser.add_option(
        "-p", "--port", action="store", dest="port", default=slp.PORT,
        type="int",
        help="port to use                [default: slp default port]"
    )

    msg.Messenger()
    node.Broadcaster()

    (options, args) = parser.parse_args()
    slp.PUBLIC_IP = options.host
    slp.PORT = options.port
    srv.main()
