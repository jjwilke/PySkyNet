from pdfget import ArticleParser, PDFArticle, Page
from papers.index import Library
from htmlexceptions import HTMLException
from utils.RM import save, load
import sys
import re
import os.path

class ISIError(Exception):
    pass

class JournalNotFoundError(Exception):
    pass

class ISIArticle(PDFArticle):

    journal_map = {
        "angewandte chemie-international edition" : "ange",
        "chemical physics" : "chemphys",
        "physics reports" : "physrep",
        "physics reports-review section of physics letters" : "physrep",
        "molecular physics" : "molphys",
    }

    def set_journal(self, journal):
        try:
            journal = self.journal_map[journal.lower()]
            PDFArticle.set_journal(self, journal)
        except KeyError:
            name = journal.lower().replace("of","").replace("the","").replace("and", "").replace("-"," ")
            initials = map(lambda x: x[0], name.strip().split())
            PDFArticle.set_journal(self, "".join(initials))

class ISIParser(ArticleParser):

    def reset(self):
        ArticleParser.reset(self)

        #treat paragraph breaks as divisions
        self.start_p = self.start_div
        self.end_p = self.end_div

        self.citation = []
        self.title = []

    def citation_text(self, text):
        self.citation.append(text)

    def title_text(self, text):
        self.title.append(text)

    def start_a(self, attrs):
        if self.a_frame == "ref":
            self.text_frame = "title"
            self.a_frame = "title"

    def end_a(self):
        if self.a_frame == "title":
            title = " ".join(self.title)
            self.title = []
            self.article.set_title(title)
            self.text_frame = "citation"
            self.a_frame = None

    def _start_citedRef(self, attrs):
        self.article = ISIArticle()
        self.a_frame = "ref"
        self.text_frame = "citation"

    def _end_citedRef(self):
        citation = " ".join(self.citation) ; self.citation = []
        import re
        regexp = "([A-Z \-]+)(\d+)\s[:]\s(\d+)\s(\d+)"

        #delete the DOI part
        doi = re.compile("DOI\s.*?\s").search(citation)
        if doi:
            doitext = doi.group()
            citation = citation.replace(doitext, "")

        match = re.compile(regexp).search(citation)
        if not match:
            citation = citation.replace("\n", " ")
            sys.stderr.write("FAILURE %s\tImproper citation format\n" % citation)
            self.article = None
            self.a_frame = None
            self.text_frame = None
            return

        journal, volume, page, year = match.groups()
        name = "%s %s %s %s" % (journal, volume, page, year)
        try:
            self.article.set_journal(journal.strip())
            self.article.set_volume(int(volume))
            self.article.set_pages(Page(page))
            self.article.set_year(int(year))
            self.articles.append(self.article)
        except JournalNotFoundError, error:
            sys.stderr.write("FAILURE %s\tJournal not found\n" % name)
        except ISIError, error:
            sys.stderr.write("FAILURE %s\tUnknown error\n" % name)

        self.text_frame = None
        self.a_frame = None
        self.article = None

class SavedRecordParser:
    
    def __init__(self):
        self.articles = []

    def __iter__(self):
        return iter(self.articles)

    def get_text(self, text, start, stop):
        regexp = "\n%s (.*?)\n%s " % (start.upper(), stop.upper())
        match = re.compile(regexp, re.DOTALL).search(text)
        if not match:
            return None

        return match.groups()[0].strip()

    def feed(self, text):
        journals = {}
        blocks = re.compile("PT\sJ(.*?)\nER", re.DOTALL).findall(text)
        for block in blocks:
            article = ISIArticle()

            journal = self.get_text(block, "so", "ab")
            if not journal: journal = self.get_text(block, "so", "sn")
            if not journal:
                print block
                sys.exit("no journal")
            article.set_journal(journal)

            volume = self.get_text(block, "vl", "is")
            if not volume: volume = self.get_text(block, "vl", "bp")
            if not volume:
                print block
                sys.exit("no volume")
            volume = int(volume)
            article.set_volume(volume)

            issue = self.get_text(block, "is", "bp")
            if not issue:
                issue = 0
            else:
                issue = int(re.compile("(\d+)").search(issue).groups()[0])
            article.set_issue(issue)

            page = self.get_text(block, "bp", "ep")
            if not page: page = self.get_text(block, "bp", "ut")
            if not page or "art. no." in page: page = self.get_text(block, "ar", "di")
            if not page: page = self.get_text(block, "ar", "ut")
            if not page:
                print block
                sys.exit("no page")
            page = Page(page)
            article.set_pages(page)
            self.articles.append(article)

            journals[journal] = 1
            
        """
        journals = journals.keys()
        journals.sort()
        print "\n".join(journals)
        sys.exit()
        """

def find(library, volume, page):
    for year in library:
        path = library.find(year, volume, page)
        if path:
            return path
    return None

def walkISI(files):
    from webutils.pdfget import download_pdf
    lib = Library()

    done = []
    if os.path.exists(".isi"):
        done = load(".isi")    

    for file in files:
        parser = SavedRecordParser()
        text = open(file).read()
        parser.feed(text)
        for article in parser:
            tag = "%s %d %s" % (article.journal, article.volume, article.start_page)
            name = "%s %d %d %s" % (article.journal, article.volume, article.issue, article.start_page)
            print "Downloading %s" % name,

            if tag in done:
                print " -> exists %s" % tag
                continue

            path = name + ".pdf"
            if os.path.isfile(path):
                print " -> exists %s" % path
                continue

            path = find(lib, article.volume, article.start_page)
            if path:
                print " -> exists %s" % path
                continue

            #check to see if we already have it
            path = download_pdf(article.journal, article.volume, article.issue, article.start_page)
            if path:
                print " -> %s" % path
                done.append(tag)
            else:
                print " -> FAILED"
            save(done, ".isi")
                

    


