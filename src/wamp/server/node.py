#
# -*- coding: utf-8 -*-
#

import socket

from django.conf import settings

from dtx.wamp import server as dtx_wamp_server

from dtx.core import logger
log = logger.log(__name__)

def start(host, port, apps):
    with log.enter() as rt:
        for family, socktype, proto, canonname, sockaddr in socket.getaddrinfo(host, port, 0, 0, socket.SOL_TCP):
            log.msg(u'AddrInfo: {}'.format((family, socktype, proto, canonname, sockaddr)))
            def unpack_sockaddr(*args):
                return args[:2]
            sa_host, sa_port = unpack_sockaddr(*sockaddr)
            log.msg('Starting WAMP at {}:{}'.format(sa_host, sa_port))
            uri = 'ws://{}:{}/'.format(sa_host, sa_port)
            dtx_wamp_server.ServerProtocol.listen(uri, apps, debug=False)
