#!/usr/bin/env python

from setuptools import setup

setup(
    name='dtx-core',
    version='0.10.7',
    description='Django Twisted Extensions - Core',
    author='Alexander Zykov',
    author_email='tiger@mano.email',
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
        'dtx.nodes',
    ],
    data_files=[
    ],
    install_requires = [
        'Twisted>=16.1.1',
        'autobahn>=0.13.0',
        'mako>=0.9.0',
        'netifaces>=0.8',
        'PyYAML>=3.11',
        'pyOpenSSL>=16.0.0',
        'service-identity>=16.0.0',
        'ujson>=1.35',
    ],
    classifiers = [
        'Intended Audience :: Developers',
        'License :: OSI Approved :: MIT License',
        'Operating System :: OS Independent',
        'Programming Language :: Python',
    ],
    zip_safe=False,
)
