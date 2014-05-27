#
# -*- coding: utf-8 -*-
#

import os
import hashlib
import uuid
import traceback
import datetime
import user_agents
import logging
import mimetypes

from datetime import tzinfo, timedelta, datetime

from twisted.internet.defer import inlineCallbacks, returnValue, Deferred
from twisted.internet import task
from twisted.internet import reactor

from django.conf import settings

from django.utils import translation
from django.utils.translation import ugettext_lazy as _
from django.utils.translation import ugettext
from django.utils.translation import ugettext_noop
from django.utils.translation import get_language

from django.contrib.staticfiles import finders

from dtx.utils.snippets.sorted_collection import SortedCollection
from dtx.memcache import client as dtx_memcache

from dtx.core import logger
log = logger.log(__name__)

static_files_by_path = SortedCollection(key=lambda x: x.path)

class StaticFileInfo:
    def __init__(self, path, body_digest, mime_type, mime_charset):
        self.path = path
        self.path_digest = hashlib.md5(path).hexdigest()
        self.body_digest = body_digest
        self.mime_type = mime_type
        self.mime_charset = mime_charset
        self.mtime = os.stat(path).st_mtime

    @classmethod
    def create(cls, path, body_digest, mime_type, mime_charset):
        global static_files_by_path
        info = cls(path, body_digest, mime_type, mime_charset)
        static_files_by_path.insert(info)
        return info
    
    @classmethod
    def find_by_name(cls, file_name):
        global static_files_by_path
        try:
            file_info = static_files_by_path.find(file_name)
            try:
                if (int(os.stat(file_name).st_mtime / 100) > int(file_info.mtime / 100)):
                    log.msg(u'File {} has been modified'.format(file_name), logLevel=logging.WARNING)
                    static_files_by_path.remove(file_info)
                    return None
                return file_info
            except:
                log.msg(traceback.format_exc(), logLevel=logging.ERROR)
                static_files_by_path.remove(file_info)
                return None
        except ValueError:
            return None
        
@inlineCallbacks
def serve(request, path, file, headers=[]):
    with log.enter() as tm:
        if settings.DEBUG:
            file_name = finders.find(file)
        else:
            file_name = os.path.join(path, file)
        file_info = None
        try:
            file_info = StaticFileInfo.find_by_name(file_name)
        except ValueError:
            pass
        if (not file_info) or (not request.setETag(file_info.body_digest)):
            path_digest = hashlib.md5(file_name).hexdigest()
            tm.msg(u'Checking MemCache...')
            flags, data = yield dtx_memcache.get(path_digest)
            if (not data):
                tm.msg(u'Loading {}...'.format(file_name))
                try:
                    with open(file_name, 'rb') as fd:                
                        data = fd.read()
                        try:
                            tm.msg(u'Saving to MemCache...')
                            stored = yield dtx_memcache.set(path_digest, data)
                        except:
                            log.msg(traceback.format_exc(), logLevel=logging.ERROR)
                            pass
                except:
                    log.msg(traceback.format_exc(), logLevel=logging.ERROR)
                    data = None
            if (data):
                if (not file_info):
                    tp, cs = mimetypes.guess_type(file_name)
                    if (not tp):
                        tp = 'application/octet-stream'
                    body_digest = hashlib.md5(data).hexdigest()
                    tm.msg(u'Digest: {}'.format(body_digest))
                    file_info = StaticFileInfo.create(file_name, body_digest, tp, cs)
                if (file_info.mime_charset):
                    ct = '{}; charset={}'.format(file_info.mime_type, file_info.mime_charset)
                    tm.msg(u'Content-Type: {}'.format(ct))
                    request.setHeader("Content-Type", ct)
                else:
                    ct = file_info.mime_type
                    tm.msg(u'Content-Type: {}'.format(ct))
                    request.setHeader("Content-Type", ct)                
                for h, v in headers:
                    tm.msg(u'{}: {}'.format(h, v))
                    request.setHeader(h, v)
            returnValue(data)
    yield
