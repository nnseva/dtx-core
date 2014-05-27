#
# -*- coding: utf-8 -*-
#

from django.conf import settings

from twisted.protocols.memcache import DEFAULT_PORT

from dtx.memcache import client as dtx_memcache_client

from dtx.core import logger
log = logger.log(__name__)

def start(host='localhost', port=DEFAULT_PORT):
    with log.enter() as tm:
        node = dtx_memcache_client.CacheProtocol.connect(host, port)
        log.msg('Connecting to MemCache at {}:{}'.format(host, port))
        return node
