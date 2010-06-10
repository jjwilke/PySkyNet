from pdfget import ArticleParser, PDFArticle, Page
from htmlexceptions import HTMLException
import sys

class ISIError(Exception):
    pass

class JournalNotFoundError(Exception):
    pass

class ISIArticle(PDFArticle):

    journal_map = {
        "journal of chemical physics" : "jcp",
        "journal of mathematical physics" : "jmp",
        "physical review a" : "pra",
        "phys rev a" : "pra",
        "physical review letters" : "prl",
        "angewandte chemie-international edition" : "ange",
        "international journal of quantum chemistry" : "ijqc",
        "journal of physical organic chemistry" : "jpoc",
        "journal of computational chemistry" : "jcc",
        "chemical physics letters" : "cpl",
        "chemical physics" : "chemphys",
        "physics reports" : "physrep",
        "journal of the american chemical society" : "jacs",
        "inorganic chemistry" : "ioc",
        "journal of organic chemistry" : "joc",
        "journal of physical chemistry" : "jpc",
        "journal of physical chemistry a" : "jpc a",
        "journal of physical chemistry b" : "jpc b",
        "journal of chemical theory and computation" : "jctc",
        "physical chemistry chemical physics" : "pccp",
    }
    
    def set_journal(self, journal):
        try:
            journal = self.journal_map[journal.lower()]
        except KeyError:
            raise JournalNotFoundError(journal)
        PDFArticle.set_journal(self, journal)

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

def walkISI(files):
    from webutils.pdfget import download_pdf
    for file in files:
        parser = ISIParser()
        text = open(file).read()
        parser.feed(text)
        for article in parser:
            print article
            download_pdf(article.journal, article.volume, article.issue, article.start_page)

    


