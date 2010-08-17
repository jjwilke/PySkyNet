from papers.pdfget import ArticleParser, PDFArticle, Journal, Page
from webutils.htmlparser import URLLister, fetch_url, HTMLParser
from webutils.htmlexceptions import HTMLException

import sys
import re

if __name__ == "__main__":
    unittest.main()

class IOPArticle(PDFArticle):
    pass

class IssueParser(ArticleParser):

    def __iter__(self):
        return iter(self.issues)

    def __getitem__(self, key):
        return self.issues[key]
        
    def reset(self):
        ArticleParser.reset(self)
        self.issue = None
        self.text_frame = None
        self.a_text = self.append_text
        self.issue_text = self.append_text
        self.issues = {}

    def start_a(self, attrs):
        if self.text_frame == "issue":
            pages = self.get_text()
            bounds = map(Page, re.compile("([RS]?\d+)[-]([RS]?\d+)").search(pages).groups())
            self.issues[self.issue] = bounds
        self.text_frame = 'a'

    def end_a(self):
        text = self.get_text()
        if "Number" in text:
            self.issue = int(re.compile("Number\s(\d+)").search(text).groups()[0])
            self.text_frame = "issue"
        else:
            self.text_frame = None

class StopIOP(Exception): pass

class IOPParser(ArticleParser):

    def reset(self):
        ArticleParser.reset(self)
        self.page_text = self.append_text
        self.a_text = self.append_text
        self.url = None

    def _start_paperEntry(self, attrs):
        self.text_frame = "page"
        self.article = IOPArticle()

    def start_a(self, attrs):
        if self.text_frame == "page":
            text = self.get_text().strip()
            match = re.compile("([RS]?\d+)").search(text)
            if not match: #skip this
                self.article = None
                self.text_frame = None
                return
            
            page = Page(match.groups()[0])
            self.article.set_pages(page)
            self.text_frame = None
        self.url = self.get_href(attrs)
        self.text_frame = 'a'

    def end_a(self):
        text = self.get_text()
        if self.article and "Full text" in text:
            self.article.set_pdfurl(self.url)

    def _end_paperEntry(self):
        self.text_frame = None
        if self.article:
            self.articles.append(self.article)
        self.article = None

class IOPJournal(Journal):

    def url(self, selenium):
        volume = self.volume
        page = self.page
        issue = self.issue

        self.validate("baseurl")
        toc = fetch_url("%s/%d" % (self.baseurl, volume))
        if not toc:
            raise HTMLException("No match found for %s %d %s" % (self.name, volume, page))

        #figure out the issue number
        issue_parser = IssueParser()
        issue_parser.feed(toc)
        for entry in issue_parser:
            start, end = issue_parser[entry]
            if page >= start and page <= end:
                issue = entry
                break

        toc = fetch_url("%s/%d/%d" % (self.baseurl, volume, issue))
        parser = IOPParser()
        parser.feed(toc)
        if hasattr(self, "baseurl2"):
            toc = fetch_url("%s/%d/%d" % (self.baseurl2, volume, issue))
            parser.feed(toc)

        for article in parser:
            if article.start_page == page:
               url = "http://iopscience.iop.org" + article.url
               return url, issue
        
        raise HTMLException("No match found for %s %d %s" % (self.name, volume, page))
            

class JPA(IOPJournal):
    
    name = "Journal of Physics A"
    baseurl = "http://iopscience.iop.org/1751-8121"

class JPB(IOPJournal):
    
    name = "Journal of Physics B"
    baseurl = "http://iopscience.iop.org/0953-4075"
    baseurl2 = "http://iopscience.iop.org/0022-3700"

class PhysScripta(IOPJournal):

    name = "Physica Scripta"
    baseurl = "http://iopscience.iop.org/1402-4896"

class JPCM(IOPJournal):

    name = "Journal of Physics: Condensed Matter"
    baseurl = "http://iopscience.iop.org/0953-8984"

