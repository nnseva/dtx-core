from twisted.internet import reactor

import codecs
import datetime
import copy
import sys

from twisted.internet.protocol import ServerFactory
from twisted.conch import manhole, telnet, insults, recvline

from dtx.core import logger
log = logger.log(__name__)

TRANSMIT_BINARY = chr(0)

class TelnetBootstrapProtocol(telnet.TelnetBootstrapProtocol):
    def connectionMade(self):
        for opt in (TRANSMIT_BINARY,):
            self.transport.do(opt).addErrback(log.err)
        #for opt in (TRANSMIT_BINARY,):
        #    self.transport.will(opt).addErrback(log.err)
        return telnet.TelnetBootstrapProtocol.connectionMade(self)

    def enableRemote(self, opt):
        # FIX: The sigtrap flag messes up the client processing multibyte utf-8 characters
        # (particularly russian lowercase 'ya' and some others) and probably other 8-bit
        # encodings, so the sigtrap is disabled here, instead of the original code.
        if opt == telnet.LINEMODE:
            self.transport.requestNegotiation(telnet.LINEMODE, telnet.MODE + chr(0))
            return True
        if opt == TRANSMIT_BINARY:
            self.transport.will(opt).addErrback(log.err)
            return True
        return telnet.TelnetBootstrapProtocol.enableRemote(self, opt)

    def enableLocal(self, opt):
        if opt in (TRANSMIT_BINARY,):
            return True
        return telnet.TelnetBootstrapProtocol.enableLocal(self, opt)

from exceptions import UnicodeDecodeError

class UManholeMixin:
    decode_buffer = ''
    input_encoding = 'utf-8'
    output_encoding = 'utf-8'

    def connectionMade(self):
        # ENHANCEMENT: adding some number of calls for the command line
        # to change current encoding easy.
        #
        # use it like:
        # >>> get_input_encoding()
        # 'utf-8'
        # >>> set_encoding('cp1251')
        # >>> get_input_encoding()
        # 'cp1251'
        #
        # TODO: automatically recognize
        # the client encoding.
        for n in (
            'set_input_encoding',
            'get_input_encoding',
            'set_output_encoding',
            'get_output_encoding',
            'set_encoding',
        ):
            self.namespace[n] = getattr(self,n)
        self.parent.connectionMade(self)
        # FIX: the Windows TELNET client sends 0x08 byte instead of
        # 0x7F which is used by the Unix telnet client for BACKSPACE key.
        #
        # TODO: it probably might be fixed using client handshaking instead
        # of processing this code.
        self.keyHandlers.update({
            '\x08':self.handle_BACKSPACE,
        })

    def safe_encoding(self,encoding):
        try:
            ''.decode(encoding)
        except:
            log.msg('The encoding %s is wrong' % repr(encoding))
            return 'ascii'
        return encoding

    def safe_input_encoding(self):
        return self.safe_encoding(self.input_encoding)

    def safe_output_encoding(self):
        return self.safe_encoding(self.output_encoding)

    def set_input_encoding(self,encoding):
        self.input_encoding = self.safe_encoding(encoding)

    def set_output_encoding(self,encoding):
        self.output_encoding = self.safe_encoding(encoding)

    def set_encoding(self,encoding):
        self.set_input_encoding(encoding)
        self.set_output_encoding(encoding)
        if encoding == 'cp1251':
            self.terminal.write('-->\r\n"\x98"\r\n-->"\xD8"\r\n')

    def get_input_encoding(self):
        return self.input_encoding

    def get_output_encoding(self):
        return self.output_encoding

    def keystrokeReceived(self, keyID, modifier):
        # uncomment the following to see original codes sent to the function
        #if not isinstance(keyID,str):
        #    print 'received keyID:%s' % keyID
        #else:
        #    print 'received key code:%s' % ord(keyID)
        m = self.keyHandlers.get(keyID)
        if m is not None:
            self.decode_buffer = ''
            m()
        else:
            # FIX: processing of multibyte encodings like utf-8
            # recognizing incomplete sequences by the exception thrown.
            self.decode_buffer += keyID
            c = None
            try:
                c = self.decode_buffer.decode(self.safe_input_encoding()).encode(self.safe_output_encoding())
            except UnicodeDecodeError,ex:
                # The exception here may mean several significantly different circumstations:
                # either error while recognizing one-byte encoding, or long byte sequence
                # received incompletely, or error while receiving long byte sequence.
                # TODO: these circumstances should be differentiated from the codecs module, but
                # there is no any proper way found in the implemented python library code.
                enc = self.safe_input_encoding()
                if not enc.startswith('ut') or len(self.decode_buffer) > 5:
                    log.msg("Can not handle byte sequence in %s: %s" % (self.safe_input_encoding(),''.join(['%02X' % ord(c) for c in self.decode_buffer])))
                    self.decode_buffer = ''
                return
            self.decode_buffer = ''
            keyID = c
            # FIX: the keyID 'character' sent to the following call
            # may be multibyte in case of multibyte output encoding.
            # It helps backend code to process current cursor
            # position properly.
            #
            # TODO: ideally the keyID here should be of the unicode type
            # but it requires a lot of changes in the backend classes.
            self.characterReceived(keyID, False)

    def lineReceived(self,data):
        # FIX: when the characterReceived method code sends a data here,
        # we are ready to change the type of the passed data to unicode
        # for the proper processing in the interpreter later.
        self.parent.lineReceived(self,data.decode(self.safe_output_encoding()))

    def getSource(self):
        # FIX: there are two sources of lines to return - the interpreter with
        # incomplete statement set, and the current line buffer.
        #
        # Just because we have sent unicode for processing in the interpreter before,
        # it stores seqence of the unicode strings, while the line buffer
        # of self is filled by the sequence of multybyte characters sent as keyID.
        #
        # So we need convert the both sources of lines to the unified form.
        # Using str with output encoding instead of unicode just because
        # of the backend code which requires a lot of changes to be unicode-ready.
        ibuffer = u'\n'.join(self.interpreter.buffer).encode(self.safe_output_encoding())
        lbuffer = ''.join(self.lineBuffer)
        return ibuffer + '\n' + lbuffer

    def addOutput(self, data, async = False):
        # FIX: this method is called by the FileWrapper in case of
        # print statements and error handling in the evaluated code.
        #
        # When the code is passed to the interpreter, the output
        # stream is always utf-8-encoded for unknown reason. It was checked
        # experimentally on the Windows platform with cp1251 system encoding.
        if isinstance(data,str):
            data = data.decode('utf-8','ignore')
        # Sometimes the print statement sends unicode instead of the str string
        # to the output stream. It happens f.e. when the print statement
        # prints unicode string. So we need to process unicode data
        # sent to the stream. The str data was converted to the unicode just above.
        # Explicit unicode convertion below is for safety purposes.
        data = unicode(data).encode(self.safe_output_encoding(),'backslashreplace')
        self.parent.addOutput(self, data, async)

    def handle_RETURN(self):
        # FIX: we can safely put the line buffer to the history directly,
        # instead of the byte concatenation in the original code.
        #
        # It helps the backend code to process current cursor position
        # properly when the history line is used in case of multibyte
        # encoding like utf-8
        if self.lineBuffer:
            self.historyLines.append(self.lineBuffer)
        self.historyPosition = len(self.historyLines)
        return recvline.RecvLine.handle_RETURN(self)

class ColoredManhole(UManholeMixin,manhole.ColoredManhole):
    parent = manhole.ColoredManhole
    pass

class Manhole(UManholeMixin,manhole.Manhole):
    parent = manhole.Manhole
    pass

class TelnetTransport(telnet.TelnetTransport):
    # to see what happens just uncomment the following
    #my_stdin = sys.stdin
    #my_stdout = sys.stdout
    #my_stderr = sys.stderr
    def dataReceived(self,data):
        # to see what happens just uncomment the following
        #print >>self.my_stdout,"RECEIVED DATA:%s" % ' '.join(['%02X' % ord(c) for c in data])
        #print >>self.my_stdout,"RECEIVED CHAR:%s" % ' '.join(['%2s' % (c if ord(c) >= 32 and ord(c) < 128 else '?') for c in data])
        telnet.TelnetTransport.dataReceived(self,data)
        # FIX: The Windows TELNET implementation sends '\r' alone instead of '\r\00' sequence when
        # the RETURN key is pressed. Here is the 'overwrite' fix to make the backend code
        # RETURN key processing bug even.
        if self.state == 'newline':
            self.applicationDataReceived('\r')
            self.state = 'data'

    def write(self,data):
        # to see what happens just uncomment the following
        #print >>self.my_stdout,"WRITE DATA:%s" % ' '.join(['%02X' % ord(c) for c in data])
        #print >>self.my_stdout,"WRITE CHAR:%s" % ' '.join(['%2s' % (c if ord(c) >= 32 and ord(c) < 128 else '?') for c in data])
        return telnet.TelnetTransport.write(self,data)

if __name__ == '__main__':
    # The code below creates unsafe telnet server (without authentication)
    # providing manhole interface on the 23457 port. It can be used for testing purposes,
    # when this module is called directly.
    #
    # You can safely import the module to get fixed manhole classes for your own.
    import logging

    class CMDFactory(ServerFactory):
        def __init__(self,colored=True):
            self.colored = colored

        def buildProtocol(self,addr):
            namespace = {}
            manhole = ColoredManhole if self.colored else Manhole
            return TelnetTransport(TelnetBootstrapProtocol,insults.insults.ServerProtocol,manhole,namespace)

    logging.basicConfig(level=logging.DEBUG)
    observer = log.PythonLoggingObserver()
    observer.start()
    cmdport = 23457

    cmdlistener = reactor.listenTCP(cmdport, CMDFactory(bool('colored' in sys.argv)))

    reactor.run()
