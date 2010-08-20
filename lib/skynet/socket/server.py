from skynet.utils.utils import traceback, debugloc
from skynet.socket.pysock import Communicator, SocketOpenError
from pylatex.pybib import Bibliography
import threading
import sys
import os

class ServerRequest:

    def __init__(self, request_port, answer_t):
        self.request_port = request_port
        self.answer_t = answer_t

    def run(self, obj):
        answer = self.answer_t()
        answer.start()
        comm = Communicator(self.request_port)
        try:
            comm.open()
            comm.sendObject(obj)
        except SocketOpenError, error:
            sys.stderr.write("%d\n%s\n%s\n" % (self.request_port, traceback(error), error))
        except Exception, error:
            sys.stderr.write("%d\n%s\n%s\n" % (self.request_port, traceback(error), error))
        comm.close()
        answer.join()
        return answer.response

class ServerAnswer(threading.Thread):

    def __init__(self, port):
        threading.Thread.__init__(self)
        self.response = None
        self.port = port

    def run(self):
        comm = Communicator(self.port)
        try:
            comm.bind()
            self.response = comm.acceptObject()
        except SocketOpenError, error:
            sys.stderr.write("%d\n%s\n%s\n" % (self.port, traceback(error), error))
        except Exception, error:
            sys.stderr.write("%d\n%s\n%s\n" % (self.port, traceback(error), error))
        comm.close()

class Server:

    def __init__(self, request_port, answer_port):
        self.answer_port = answer_port
        self.request_port = request_port
        self.server = Communicator(self.request_port)
        self.server.bind()
        self.bib = Bibliography()

    def run(self):
        while 1:
            ret = ""
            try:
                obj = self.server.acceptObject()
                ret = self.process(obj)
            except Exception, error:
                sys.stderr.write("%s\n%s\n" % (traceback(error), error))

            try:
                comm = Communicator(self.answer_port)
                comm.sendObject(ret)
                comm.close()
            except SocketOpenError, error:
                sys.stderr.write("%d\n%s\n%s\n" % (self.answer_port, traceback(error), error))
            except Exception, error:
                sys.stderr.write("%s\n%s\n" % (traceback(error), error))

