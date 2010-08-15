from skynet.utils.utils import traceback
from skynet.pysock import Communicator
from pylatex.pybib import Bibliography
import threading
import sys
import os

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

class CiteBibBuild(threading.Thread):
    
    def __init__(self, lock, bib):
        self.bib = bib
        self.lock = lock
        threading.Thread.__init__(self)

    def run(self):
        import time
        lastupdate = -1
        while 1:
            #acquire the lock
            self.lock.acquire()
            #check to see if the server needs to be updated
            fstat = os.stat(Bibliography.ENDNOTE_XML_LIB)
            updatetime = fstat.st_mtime
            if updatetime != lastupdate:
                self.bib.clear()
                self.bib.buildRecords(Bibliography.ENDNOTE_XML_LIB)
                lastupdate = updatetime
            self.lock.release()
            time.sleep(3)

class CiteServer:

    REQUEST_PORT = 22347
    ANSWER_PORT = 22348

    REBUILD = "rebuild"

    def __init__(self):
        self.server = Communicator(self.REQUEST_PORT)
        self.server.bind()
        self.bib = Bibliography()

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

    def rebuild(self):
        self.bib.clear()
        self.bib.buildRecords(Bibliography.ENDNOTE_XML_LIB)

    def release_lock(self):
        try:
            self.lock.release()
        except Exception:
            pass

    def run(self):
        self.lock = threading.RLock()
        buildthread = CiteBibBuild(self.lock, self.bib)
        buildthread.start()
        while 1:
            try:
                obj = self.server.acceptObject()
                self.lock.acquire()
                record = ""
                if obj == self.REBUILD:
                    self.rebuild()
                    record = "completed"
                elif isinstance(obj, list):
                    record = self.get_record_from_citation(obj)
                elif isinstance(obj, str):
                    record = self.get_record_from_label(obj)
                self.release_lock()
                comm = Communicator(self.ANSWER_PORT)
                comm.sendObject(record)
                comm.close()
            except Exception, error:
                self.release_lock()
                sys.stderr.write("%s\n%s\n" % (traceback(error), error))
            

