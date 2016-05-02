#
# -*- coding: utf-8 -*-
#

from django.conf import settings

from dtx import process, node

from dtx.core import logger
log = logger.log(__name__)

def config(**kwargs):
    result = {
        'DTX_WEB_HOST' = [
            u'127.0.0.1',
        ],
        'DTX_WEB_PORT': 80 if settings.DEBUG else 8000
        'DTX_WEB_SITES': [
            (
                u'.*',
                'wsgi',
            ),
        ]
    }
    port = kwargs.get('port', settings.DTX_WEB_PORT)
    result.port = port if port
    return result

def start(**kwargs):
    node.start('dtx.memcache.client.node')
    
    conf = config(**kwargs)
    
    try:
        from setproctitle import setproctitle
        setproctitle('django-twisted @ port {}'.format(conf.DTX_WEB_HOST))
    except:
        pass

    for host in settings.DTX_PUBLIC_ADDRESSES:
        log.msg('Starting web node at {}:{}...'.format(conf.DTX_WEB_HOST, conf.DTX_WEB_PORT))
        node.start('dtx.web.server.node',
            host=conf.DTX_WEB_HOST, 
            port=conf.DTX_WEB_PORT,
            sites=conf.DTX_WEB_SITES
        )