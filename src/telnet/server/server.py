#
# -*- coding: utf-8 -*-
#

from twisted.internet.protocol import ServerFactory
from twisted.conch import manhole, telnet, insults

from dtx.utils.snippets import manhole

from dtx.core import logger
log = logger.log(__name__)

class TelnetFactory(ServerFactory):

    def __init__(self,colored=True):
        self.colored = colored

    def buildProtocol(self,addr):
        with log.enter(obj=self) as tm:
            namespace = {}
            mh = manhole.ColoredManhole if self.colored else manhole.Manhole
            return manhole.TelnetTransport(manhole.TelnetBootstrapProtocol,insults.insults.ServerProtocol,mh,namespace)

