#
# -*- coding: utf-8 -*-
#

import socket

from importlib import import_module
from django.conf import settings

from dtx.web import server as dtx_web_server

from dtx.core import logger
log = logger.log(__name__)

def start(host, port, sites=None):
    with log.enter() as tm:
        for family, socktype, proto, canonname, sockaddr in socket.getaddrinfo(host, port, 0, 0, socket.SOL_TCP):
            sa_host, sa_port = sockaddr
            log.msg('Starting HTTP at {}:{}'.format(sa_host, sa_port))
            uri = 'http://{}:{}/'.format(sa_host, sa_port)
            dtx_web_server.DtxWebSite.listen(uri, sites)
	    '''
            from dtx.web.client.defer import remote_nodes
            for pattern, urlconf in sites:
                try:
                    m = import_module(urlconf)
                    remote_nodes.addWorker(uri, urlconf)
                except:
                    pass
            '''

