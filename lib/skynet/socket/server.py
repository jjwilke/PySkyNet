from skynet.utils.utils import traceback, debugloc
from skynet.socket.pysock import Communicator, SocketOpenError, SocketDie
from pylatex.pybib import Bibliography
import threading
import sys
import os

class ServerRequest:

    def __init__(self, request_port, answer_t):
        self.request_port = request_port
        self.answer_t = answer_t

    def close_answer(self, answer):
        try:
            comm = Communicator(answer.port)
            comm.open()
            comm.sendObject("die!")
            comm.close()
        except Exception, error:
            sys.stderr.write("%d\n%s\n%s\n" % (self.request_port, traceback(error), error))

    def run(self, obj):
        answer = self.answer_t()
        comm = Communicator(self.request_port)
        try:
            comm.open()
            answer.start()
            comm.sendObject(obj)
        except SocketOpenError, error:
            sys.stderr.write("%d\n%s\n%s\n" % (self.request_port, traceback(error), error))
            self.close_answer(answer)
            return #thread is already dead
        except Exception, error:
            sys.stderr.write("%d\n%s\n%s\n" % (self.request_port, traceback(error), error))
            self.close_answer(answer)
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

class ServerStop:
    pass

class Server:

    def __init__(self, request_port, answer_port = None):
        self.answer_port = answer_port
        self.request_port = request_port
        self.server = Communicator(self.request_port)
        self.server.bind()
        self.bib = Bibliography()

    def report(self):
        from pygui.gtkserver import report 
        report()

    def run(self):
        while 1:
            ret = ""
            try:
                obj = self.server.acceptObject()
                if isinstance(obj, ServerStop): #end
                    self.stop()
                    return

                ret = self.process(obj)
            except SocketDie:
                return
            except Exception, error:
                sys.stderr.write("%s\n%s\n" % (traceback(error), error))


            try:
                if self.answer_port:
                    comm = Communicator(self.answer_port)
                    comm.open()
                    comm.sendObject(ret)
                    comm.close()
            except SocketOpenError, error:
                sys.stderr.write("%d\n%s\n%s\n" % (self.answer_port, traceback(error), error))
            except Exception, error:
                sys.stderr.write("%s\n%s\n" % (traceback(error), error))


from threading import Thread

class ServerThread(Thread):

    def __init__(self, server):
        Thread.__init__(self)
        self.server = server

    def run(self):
        self.server.run()

class ServerManager:
    
    def __init__(self, server):
        self.thr = ServerThread(server)
        self.server = server

    def run(self):
        self.thr.start()

    def stop(self):
        comm = Communicator(self.server.request_port)
        comm.open()
        comm.sendObject(ServerStop())
        comm.close()
        self.thr.join()






