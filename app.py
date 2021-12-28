# -*- coding:utf-8 -*-
# FOR TESTING PURPOSE ONLY ---

import io
import os
import sys
import slp
import signal

from usrv import srv
from slp import sync, node, msg, api


def deploy(host="0.0.0.0", port=5001):
    """
    Deploy slp node on ubuntu as system daemon.
    """
    normpath = os.path.normpath
    executable = normpath(sys.executable)
    gunicorn_conf = os.path.normpath(
        os.path.abspath(
            os.path.expanduser("~/ark-listener/gunicorn.conf.py")
        )
    )

    with io.open("./slp.service", "w") as unit:
        unit.write(u"""[Unit]
Description=Side ledger Protocol service
After=network.target
[Service]
User=%(usr)s
WorkingDirectory=%(wkd)s
Environment=PYTHONPATH=%(path)s
ExecStart=%(bin)s/gunicorn 'app:SlpApp()' \
--bind=%(host)s:%(port)s --workers=1 --access-logfile -
Restart=always
[Install]
WantedBy=multi-user.target
""" % {
            "usr": os.environ.get("USER", "unknown"),
            "wkd": normpath(sys.prefix),
            "path": os.path.abspath(
                normpath(os.path.dirname(slp.__path__[0]))
            ),
            "bin": os.path.dirname(executable),
            "port": port,
            "host": host
        })

    if os.system("%s -m pip show gunicorn" % executable) != "0":
        os.system("%s -m pip install gunicorn%s" % executable)
    os.system("chmod +x ./slp.service")
    os.system("sudo cp %s %s" % (gunicorn_conf, normpath(sys.prefix)))
    os.system("sudo mv --force ./slp.service /etc/systemd/system")
    os.system("sudo systemctl daemon-reload")
    if not os.system("sudo systemctl restart slp"):
        os.system("sudo systemctl start slp")


class SlpApp(srv.MicroJsonApp):

    def __init__(self, host="127.0.0.1", port=5000, loglevel=20):
        srv.MicroJsonApp.__init__(self, host, port, loglevel)
        sync.Processor()
        node.Broadcaster()
        msg.Messenger()
        signal.signal(signal.SIGTERM, SlpApp.kill)

    @staticmethod
    def kill():
        sync.Processor.stop()
        node.Broadcaster.stop()
        node.Broadcaster.broadcast({"bye": "Exiting system"})
        msg.Messenger.stop()
        msg.Messenger.put({})
        sync.chain.BlockParser.stop()
        sync.chain.BlockParser.JOB.put({})


if __name__ == "__main__":

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
