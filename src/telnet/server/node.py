#
# -*- coding: utf-8 -*-
#

import socket

from django.conf import settings

from dtx.core import logger
log = logger.log(__name__)

def start(host, port, colored=True):
    with log.enter() as tm:
        for family, socktype, proto, canonname, sockaddr in socket.getaddrinfo(host, port, 0, 0, socket.SOL_TCP):
            log.msg(u'AddrInfo: {}'.format((family, socktype, proto, canonname, sockaddr)))
            sa_host, sa_port = sockaddr
            log.err('NOT IMPLEMENTED')
