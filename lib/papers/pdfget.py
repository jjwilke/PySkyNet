from webutils.htmlparser import HTMLParser, save_url
from webutils.htmlexceptions import HTMLException
from skynet.utils.utils import traceback, load, save
from pdfserver import PDFRequest

import sys
import os.path
import re

class URLNotPDFError(Exception):
    pass


class Page:
    
    INT = 0
    STR = 1
    PAGE = 2
    
    def __init__(self, text):
        self.value = text
        self.prefix = re.compile("([A-Z]*)\d+").search(text).groups()[0]
        try:
            self.number = int(re.compile("(\d+)").search(self.value).groups()[0])
        except Exception, error:
            raise Exception("%s is not valid Page input" % self.value)

    def __le__(self, other):
        case = self.get_case(other)
        if case == self.INT:
            return self.number <= other
        elif case == self.PAGE:
            return self.number <= other.number
        elif case == self.STR:
            return self.value <= other
        else:
            raise Exception("%s is not a valid comparison for Page" % other.__class__)

    def __ge__(self, other):
        case = self.get_case(other)
        if case == self.INT:
            return self.number >= other
        elif case == self.PAGE:
            return self.number >= other.number
        elif case == self.STR:
            return self.value >= other
        else:
            raise Exception("%s is not a valid comparison for Page" % other.__class__)

    def __lt__(self, other):
        case = self.get_case(other)
        if case == self.INT:
            return self.number < other
        elif case == self.PAGE:
            return self.number < other.number
        elif case == self.STR:
            return self.value < other
        else:
            raise Exception("%s is not a valid comparison for Page" % other.__class__)

    def __gt__(self, other):
        case = self.get_case(other)
        if case == self.INT:
            return self.number > other
        elif case == self.PAGE:
            return self.number > other.number
        elif case == self.STR:
            return self.value > other
        else:
            raise Exception("%s is not a valid comparison for Page" % other.__class__)

    def __eq__(self, other):
        case = self.get_case(other)
        if case == self.INT:
            return self.number == other
        elif case == self.PAGE:
            return self.value == other.value and self.number == other.number
        elif case == self.STR:
            return self.value == other
        else:
            raise Exception("%s is not a valid comparison for Page" % other.__class__)

    def __int__(self):
        return self.number

    def __str__(self):
        return self.value

    def get_case(self, other):
        if isinstance(other, basestring):
            return self.STR
        elif "Page" in str(other.__class__):
            return self.PAGE
        else:
            return self.INT

    def is_comparable(self, other):
        return self.prefix == other.prefix

    def get_issue(self):
        if self.value[0] == "0":
            return int(self.value[1])
        else:
            return int(self.value[:2])


class PDFArticle:
    
    def __init__(self):
        self.title = "No title"
        self.journal = "No journal"
        self.start_page = Page("0")
        self.end_page = Page("1")
        self.volume = 0
        self.issue = 0
        self.year = 0

    def __str__(self):
        return '%s %s %d pp %s-%s %d' % (self.title, self.journal, self.volume, self.start_page, self.end_page, self.year)

    def set_pdfurl(self, url):
        self.url = url

    def set_title(self, text):
        self.title = text

    def set_pages(self, start_page, end_page = None):
        self.start_page = start_page
        if not end_page:
            self.end_page = start_page
        else:
            self.end_page = end_page

    def set_journal(self, journal):
        from papers.utils import JournalCleanup
        self.journal = JournalCleanup.abbreviate(journal)

    def set_volume(self, volume):
        self.volume = volume

    def set_issue(self, issue):
        self.issue = issue

    def set_year(self, year):
        self.year = year

class ArticleParser(HTMLParser):

    def __iter__(self):
        return iter(self.articles)

    def __len__(self):
        return len(self.articles)

    def __bool__(self):
        return self.articles

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

class Issue:
    
    def __init__(self, num):
        self.pages = []
        self.number = num

    def add_page(self, page):
        self.pages.append(page)

    def __str__(self):
        str_arr = ["Issue %d" % self.number]
        for entry in self.pages:
            str_arr.append("\tp. %d" % entry)
        return "\n".join(str_arr)

class Volume:
    
    def __init__(self, number):
        self.issues = {}
        self.number = number

    def add_issue(self, issue):
        self.issues[issue.number] = issue

    def __str__(self):
        str_arr = ["Volume %d" % self.number]
        for entry in self.issues:
            str_arr.append("%s" % self.issues[entry])
        return "\n".join(str_arr)

class Journal:

    def __str__(self):
        return self.name

    def set_article(self, volume, issue, page):
        self.volume = volume
        self.issue = issue
        self.page = page
    
    def pickle_path(self):
        import papers.pdfget
        module_file = webutils.pdfget.__file__
        folder = os.path.split(module_file)[0]
        name = ".%s.profile" % self.name.replace("-","_").replace(" ","")
        pickle = os.path.join(folder, name)
        return pickle

    def profile_issue(self, volume, issue):
        import time
        articles = self.get_articles(volume.number, issue.number)
        time.sleep(3) #avert suspicion
        for article in articles:
            issue.add_page(article.start_page)

        return len(articles)

    def url(self, selenium):
        return None, 0

    def profile_volume(self, volume):
        num = 1

        keys = volume.issues.keys()
        if keys:
            keys.sort()
            num = keys[-1]

        nfound = 0
        while 1:
            if hasattr(self, "volstart"): #we don't need to go past this
                if num == self.volstart:
                    return None

            issue = Issue(num)
            n = self.profile_issue(volume, issue)
            if not n: #no articles found, we are done
                return nfound

            nfound += n
            volume.add_issue(issue)
            num += 1

                
    def profile(self, num = None):
        volumes = load(self.pickle_path())
        if not volumes:
            volumes = {}

        keys = volumes.keys() ; keys.sort()

        x = None
        if num:
            volume = Volume(num)
            x = num
        elif keys:
            num = keys[-1]
            volume = volumes[num]
        else:
            volume = Volume(num)

        try:
            while num == x:
                volumes[num] = volume
                nfound = self.profile_volume(volume)
                if not nfound: #no more
                    break
                save(volumes, pickle)

                #move to next
                num += 1
                volume = Volume(num)
        except Exception, error:
            save(volumes, pickle)
            sys.stderr.write(traceback(error) + "\n")
            raise error

    def validate(self, *xargs):
        self.checkattr("name")
        for attr in xargs:
            self.checkattr(attr)

    def checkattr(self, attr):
        if not hasattr(self, attr):
            raise HTMLException("Class %s does not have attribue %s" % (self.__class__, attr))

    def url(self, volume, issue, page):
        self.validate()
        return None, None

def profile_journal(journal, volume = None):
    from pdfglobals import PDFGetGlobals
    jobj = PDFGetGlobals.journals[journal]()
    jobj.profile(volume)

def download_pdf(journal, volume = 0, issue = 0, page = Page("0")):

    from pdfglobals import PDFGetGlobals

    name = "%s %d %d %s" % (journal, volume, issue, page)
    try:
        jobj = PDFGetGlobals.get_journal(journal)
        if not jobj: #no journal
            sys.stderr.write("FAILURE: %s\tJournal not valid\n" %  name)
            sys.stderr.write("\n".join(PDFGetGlobals.get_valid_journals()) + "\n")
            return None

        #we might have to fetch the issue
        url = None
        jobj.set_article(volume, issue, page)
        req = PDFRequest()
        ret = req.run(jobj)
        if not ret:
            return None

        url, issue = ret

        name = "%s %d %d %s" % (journal, volume, issue, page)
        filename = "%s.pdf" % name

        save_url(url, filename)
        text = open(filename).read()
        if not text[:4] == "%PDF":
            raise URLNotPDFError

        sys.stdout.write("SUCCESS: %s\n" % name)

        return filename #return success

    except URLNotPDFError, error:
        sys.stderr.write("FAILURE: %s\tURL is not a PDF file\n" % name)
    except Exception, error:
        sys.stderr.write("FAILURE: %s\tURL not found\n" % name)

    return None


if __name__ == "__main__":
    from papers.pdfglobals import run_testsuite
    run_testsuite()

