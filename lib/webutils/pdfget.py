from htmlparser import HTMLParser
from urllib2 import HTTPError
import sys

class URLNotPDFError(Exception):
    pass

class PDFArticle:
    
    def __init__(self):
        self.title = "No title"
        self.journal = "No journal"
        self.start_page = 0
        self.end_page = 1
        self.volume = 0
        self.issue = 0
        self.year = 0

    def __str__(self):
        return '%s %s %d pp %d-%d %d' % (self.title, self.journal, self.volume, self.start_page, self.end_page, self.year)

    def set_pdfurl(self, url):
        self.url = url

    def set_title(self, text):
        self.title = text

    def set_pages(self, start_page, end_page = 0):
        self.start_page = start_page
        if not end_page:
            self.end_page = start_page
        else:
            self.end_page = end_page

    def set_journal(self, journal):
        self.journal = journal

    def set_volume(self, volume):
        self.volume = volume

    def set_issue(self, issue):
        self.issue = issue

    def set_year(self, year):
        self.year = year

class ArticleParser(HTMLParser):

    def __iter__(self):
        return iter(self.articles)

    def null_handler(self, args):
        pass

    def append_text(self, text):
        self.entries.append(text)

    def call_method(self, prefix, attr, args = None):
        method = "%s_%s" % (prefix, attr)
        if not hasattr(self, method):
            return

        method = getattr(self, method)
        if args:
            method(args)
        else:
            method()

    def get_text(self, delim = " "):
        text = delim.join(self.entries)
        self.entries = []
        return text

    def handle_data(self, text):
        self.call_method(self.text_frame, "text", text)

    def reset(self):
        HTMLParser.reset(self)
        self.articles = []
        self.article = None #the article currently being built
        self.entries = []
        self.a_frame = None
        self.text_frame = None

    def start_div(self, attrs):
        cls = self.get_html_attr("class", attrs)
        if cls:
            cls = cls.replace("-","_")

        self.push_frame("div", cls)
        if not cls: #no class attribute, move on
            return

        self.call_method("_start", cls, attrs)

    def end_div(self):
        cls = self.pop_frame("div")
        if not cls: #no class attribute, move on
            return

        self.call_method("_end", cls)

class Journal:

    def checkattr(self, attr):
        if not hasattr(self, attr):
            raise HTMLException("Class %s does not have attribue %s" % (self.__class__, attr))

def download_pdf(journal, volume, issue, page):
    from webutils.acs import JACS, JOC, InorgChem, JPCA, JPCB, JCTC, JPC
    from webutils.aip import JCP, JMP
    from webutils.sciencedirect import CPL, PhysRep, ChemPhys
    from webutils.springer import TCA
    from webutils.aps import PRL, PRA
    from webutils.wiley import AngeChem, IJQC, JPOC, JCC
    from webutils.rsc import PCCP

    journals = {
        "jacs" : JACS,
        "jctc" : JCTC,
        "jpca" : JPCA,
        "jpcb" : JPCB,
        "joc" : JOC,
        "jpc" : JPC,
        "ioc" : InorgChem,
        "jcp" : JCP,
        "jmp" : JMP,
        "cpl" : CPL,
        "physrep" : PhysRep,
        "chemphys" : ChemPhys,
        "tca" : TCA,
        "prl" : PRL,
        "pra" : PRA,
        "ange" : AngeChem,
        "ijqc" : IJQC,
        "pccp" : PCCP,
        "jpoc" : JPOC,
        "jcc" : JCC,
    }

    name = "%s %d %d %d" % (journal, volume, issue, page)
    try:
        jobj = journals[journal]()

        #we might have to fetch the issue
        url, issue = jobj.url(volume, issue, page)

        if not url: #nothing found
            return False

        filename = "%s.pdf" % name

        from webutils.htmlparser import save_url
        save_url(url, filename)
        text = open(filename).read()
        if not text[:4] == "%PDF":
            raise URLNotPDFError

        sys.stdout.write("SUCCESS: %s\n" % name)

        return True #return success

    except KeyError, error:
        sys.stderr.write("FAILURE: %s\tJournal not valid\n" %  name)
    except HTTPError, error:
        sys.stderr.write("FAILURE: %s\tURL not found\n" % name)
    except URLNotPDFError, error:
        sys.stderr.write("FAILURE: %s\tURL is not a PDF file\n" % name)

    return False


if __name__ == "__main__":
    url = "http://www.sciencedirect.com/science?_ob=MImg&_imagekey=B6TFN-4YPT1SW-2-13&_cdi=5231&_user=655127&_pii=S0009261410004835&_orig=browse&_coverDate=05%2F26%2F2010&_sk=995079998&view=c&wchp=dGLzVlz-zSkWb&md5=4920081f211a7a4eff29b6938aa3d16e&ie=/sdarticle.pdf"
    filename = "sdarticle.pdf"
    from webutils.htmlparser import save_url
    save_url(url, filename)
