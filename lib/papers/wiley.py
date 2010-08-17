from papers.pdfget import ArticleParser, PDFArticle, Journal, Page
from webutils.htmlexceptions import HTMLException
from webutils.htmlparser import fetch_url

import sys
import re
import time

class WileyArticle(PDFArticle):
    pass


class WileyQuery:

    def __init__(self, baseurl, volume, page, selenium):
        self.volume = volume
        self.page = page
        self.selenium = selenium
        self.baseurl = baseurl

    def run(self):
        sel = self.selenium
        sel.open(self.baseurl)
        sel.click("link=*ll Issue*")
        sel.wait_for_page_to_load(30000)
        loc=sel.get_location()
        text =  sel.get_body_text()
        year = re.compile("(\d+)\s*[-]\s*Volume\s%s\s" % self.volume).search(text).groups()[0]
        url = "%s?activeYear=%s" % (loc, year)
        text = fetch_url(url)
        regexp = "Volume\s*%d.*?Issue[s]?\s*(\d+)[-]?\d*.*?Pages\s*(\d+)[-](\d+)" % self.volume
        matches = re.compile(regexp, re.DOTALL).findall(text)
        issue = 0
        for iss, start, end in matches:
            iss, start, end = map(int, (iss, start, end))
            if start <= self.page and end >= self.page:
                issue = iss
                break
        if not issue:
            raise HTMLException("Could not find issue number")

        sel.click("link=*Volume %d*" % self.volume)
        time.sleep(0.5)
        sel.click("link=*Issue*%d*" % issue)
        sel.wait_for_page_to_load(30000)
        sel.click("link=*page*%s*" % self.page)
        sel.wait_for_page_to_load(30000)
        location = sel.get_location()
        base = location.split("/")[:-1]
        base.append("pdf")
        pdfurl = "/".join(base)
        return pdfurl, issue
    
class WileyParser(ArticleParser):

    def reset(self):
        ArticleParser.reset(self)

        #treat paragraph breaks as divisions
        self.start_p = self.start_div
        self.end_p = self.end_div
        self.title_text = self.append_text
        self.citation_text = self.append_text
        self.a_text = self.append_text
        self.pdf_text = self.append_text
        self.frame = None

    def _start_listingContent(self, attrs):
        self.frame = "article"

    def _end_listingContent(self):
        self.frame = None
        self.text_frame = None
        self.articles.append(self.article)
        self.article = None

    def start_strong(self, attrs):
        if self.frame == "article":
            self.text_frame = "title"

            if self.article:
                self.articles.append(self.article)

            self.article = WileyArticle()

    def end_strong(self):
        if self.frame == "article":
            self.text_frame = "citation"
            title = self.get_text()
            self.article.set_title(title)

    def start_a(self, attrs):
        if self.text_frame == "citation":
            self.text_frame = "a"
            self.href = self.get_href(attrs)

            #parse for the page number
            text = self.get_text()
            start, end = map(Page, re.compile("Pages[:]\s*(\d+)[-](\d+)").search(text).groups())
            self.article.set_pages(start, end)

            self.text_frame = "pdf"

        elif self.text_frame == "pdf":
            self.href = self.get_href(attrs)

    def end_a(self):
        if self.text_frame == "pdf":
            text = self.get_text()
            if "PDF" in text: #this is the link I want
                url = "http://www3.interscience.wiley.com" + self.href
                self.article.set_pdfurl(url)
                self.text_frame = None

class WileyPDFFetcher(ArticleParser):

    def reset(self):
        ArticleParser.reset(self)

        self.url = None

    def start_frame(self, attrs):
        name = self.get_html_attr("name", attrs)
        if not name == "main":
            return

        id = self.get_html_attr("id", attrs)
        if not id == "main":
            return

        src = self.get_html_attr("src", attrs)
        self.url = src
        

class WileyJournal(Journal):

    def url(self, selenium):
        volume = self.volume
        page = self.page
        issue = self.issue
        
        query = WileyQuery(self.baseurl, volume, page, selenium)
        url, issue = query.run()
        text = fetch_url(url)
        regexp = 'pdfDocument.*?(http.*?)["]'
        pdfurl = re.compile(regexp, re.DOTALL).search(text).groups()[0]
        return pdfurl, issue

class AngeChem(WileyJournal):

    name = "Angewandte Chemie"
    baseurl = "http://www3.interscience.wiley.com/journal/26737/home"

class IJQC(WileyJournal):

    name = "International Journal Of Quantum Chemistry"
    baseurl = "www3.interscience.wiley.com/journal/29830"

class JPOC(WileyJournal):

    name = "Journal of Physical Organic Chemistry"
    baseurl = "www3.interscience.wiley.com/journal/4569/home"

class JCC(WileyJournal):

    name = "Journal of Computational Chemistry"
    baseurl = "www3.interscience.wiley.com/journal/112750178/home"

class ChemPhysChem(WileyJournal):
    
    name = "ChemPhysChem"
    baseurl = "www3.interscience.wiley.com/journal/72514732/home"

