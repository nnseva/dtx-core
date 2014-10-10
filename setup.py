#!/usr/bin/env python

from setuptools import setup

setup(
    name='dtx-core',
    version='0.9.15',
    description='Django Twisted Extensions - Core',
    author='Alexander Zykov',
    author_email='tigernwh@gmail.com',
    url='https://github.com/TigerND/dtx-core',
    package_dir={
        'dtx': 'src'
    },
    packages=[
        'dtx',
        'dtx.core',
        'dtx.core.logger',
        'dtx.core.workflow',
        'dtx.utils',
        'dtx.utils.snippets',
        'dtx.memcache',
        'dtx.memcache.client',
        'dtx.telnet',
        'dtx.telnet.server',
        'dtx.web',
        'dtx.web.core',
        'dtx.web.core.serializers',
        'dtx.web.client',
        'dtx.web.client.defer',
        'dtx.web.server',
        'dtx.web.server.views',
        'dtx.wamp',
        'dtx.wamp.server',
        'dtx.management',
        'dtx.management.commands',
    ],
    data_files=[
    ],
    install_requires = [
        'Twisted>=14.0.0',
        'autobahn>=0.8.3',
        'mako>=0.9.0',
        'ipaddr>=2.1.10',
        'netifaces>=0.8',
        'PyYAML>=3.11',
        'ujson',
    ],
    classifiers = [
        'Intended Audience :: Developers',
        'License :: OSI Approved :: MIT License',
        'Operating System :: OS Independent',
        'Programming Language :: Python',
    ],
    zip_safe=False,
)
