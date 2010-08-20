from papers.pdfget import ArticleParser, PDFArticle, Page, download_pdf
from papers.index import Library
from papers.archive import Archive, MasterArchive
from papers.utils import Cleanup
from skynet.utils.utils import save, load, clean_line, capitalize_word, traceback
from webutils.htmlexceptions import HTMLException
from webutils.htmlparser import URLLister
from papers.utils import Cleanup
from skynet.pysock import Communicator

import sys
import re
import os.path

from selenium import selenium

class ISIServer:

    def run(self):
        while 1:
            ret = ""
            try:
                obj = self.server.acceptObject()
                method = getattr(self, obj.method)
                sys.stdout.write("Running %s\n" % obj.method)
                ret = ""
                if obj.args:
                    ret = method(obj.args)
                else:
                    ret = method()
            except Exception, error:
                sys.stderr.write("%s\n%s\n" % (traceback(error), error))

            comm = Communicator(self.ANSWER_PORT)
            if ret:
                comm.sendObject(ret)
            else:
                comm.sendObject(ISIVoid())
            comm.close()
