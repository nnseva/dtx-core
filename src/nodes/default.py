#
# -*- coding: utf-8 -*-
#

from django.conf import settings

from dtx import process, node

from dtx.core import logger
log = logger.log(__name__)

default_port = 80 if not settings.DEBUG else 8000

def config(**kwargs):
    result = {
        'DTX_WEB_HOST': [
            u'127.0.0.1',
        ],
        'DTX_WEB_SITES': [
            (
                u'.*',
                'wsgi',
            ),
        ],
    }
    result['DTX_WEB_PORT'] = int(kwargs.get('port', settings.DTX_WEB_PORT if hasattr(settings, 'DTX_WEB_PORT') else default_port))
    return result

def start(**kwargs):
    node.start('dtx.memcache.client.node')
    
    conf = config(**kwargs)
    
    host = conf['DTX_WEB_HOST']
    port = conf['DTX_WEB_PORT']
    sites = conf['DTX_WEB_SITES']
    
    try:
        from setproctitle import setproctitle
        setproctitle('django-twisted @ port {}'.format(port))
    except:
        pass

    for host in conf['DTX_WEB_HOST']:
        log.msg('Starting web node at {}:{}...'.format(host, port))
        node.start('dtx.web.server.node',
            host=host, 
            port=port,
            sites=sites
        )