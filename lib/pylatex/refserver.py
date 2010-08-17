from skynet.utils.utils import traceback, debugloc
from skynet.socket.server import Server, ServerRequest, ServerAnswer
from pylatex.pybib import Bibliography
import threading
import sys
import os

class CiteRequest(ServerRequest):

    def __init__(self):
        ServerRequest.__init__(self, CiteServer.REQUEST_PORT, CiteAnswer)

class CiteAnswer(ServerAnswer):

    def __init__(self):
        ServerAnswer.__init__(self, CiteServer.ANSWER_PORT)

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

class CiteServer(Server):

    REQUEST_PORT = 22347
    ANSWER_PORT = 22348

    REBUILD = "rebuild"

    def __init__(self):
        Server.__init__(self, self.REQUEST_PORT, self.ANSWER_PORT)
        self.bib = Bibliography()
        self.lock = threading.RLock()
        buildthread = CiteBibBuild(self.lock, self.bib)
        buildthread.start()

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

    def process(self, obj):
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
        return record
            

