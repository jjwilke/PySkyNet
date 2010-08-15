from skynet.utils.utils import traceback
from skynet.pysock import Communicator
from pylatex.pybib import Bibliography
import threading
import sys

class CiteRequest:

    def __init__(self):
        pass

    def run(self, label):
        answer = CiteAnswer()
        answer.start()
        try:
            comm = Communicator(CiteServer.REQUEST_PORT)
            comm.open()
            comm.sendObject(label)
        except Exception, error:
            sys.stderr.write("%s\n" % error)
        comm.close()
        answer.join()
        return answer.response

class CiteAnswer(threading.Thread):

    def __init__(self):
        threading.Thread.__init__(self)
        self.response = None

    def run(self):
        comm = Communicator(CiteServer.ANSWER_PORT)
        comm.bind()
        self.response = comm.acceptObject()
        comm.close()

class CiteServer:

    REQUEST_PORT = 22347
    ANSWER_PORT = 22348

    def __init__(self):
        self.server = Communicator(self.REQUEST_PORT)
        self.server.bind()
        self.bib = Bibliography()
        self.bib.buildRecords(Bibliography.ENDNOTE_XML_LIB)

    def get_record_from_label(self, label):
        try:
            record = self.bib[label]
            return record
        except Exception, error:
            sys.stderr.write("error on label %s\n" % label)
            return ""

    def get_record_from_citation(self, citation):
        try:
            journal, volume, page = citation
            record = self.bib.findEntry(journal, volume, page)
            if not record:
                return ""
            return record
        except Exception, error:
            return ""

    def run(self):
        while 1:
            try:
                obj = self.server.acceptObject()
                record = ""
                if isinstance(obj, list):
                    record = self.get_record_from_citation(obj)
                elif isinstance(obj, str):
                    record = self.get_record_from_label(obj)
                comm = Communicator(self.ANSWER_PORT)
                comm.sendObject(record)
                comm.close()
            except Exception, error:
                sys.stderr.write("%s\n%s\n" % (traceback(error), error))
            

