#
# -*- coding: utf-8 -*-
#

import os
import sys
import logging

from importlib import import_module

from twisted.internet import reactor

from django.conf import settings as django_settings

from dtx.core import logger
log = logger.log(__name__, enabled=django_settings.DEBUG)

def start(node, *args, **kwargs):
    mod = import_module(node)
    return mod.start(*args, **kwargs)

__all__ = [
    'start',
]
