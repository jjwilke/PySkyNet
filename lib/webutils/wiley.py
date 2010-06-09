from pdfget import ArticleParser, PDFArticle, Journal
from htmlexceptions import HTMLException

import sys

class WileyArticle(PDFArticle):
    pass
    
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
            import re
            text = self.get_text()
            start, end = map(int, re.compile("Pages[:]\s*(\d+)[-](\d+)").search(text).groups())
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

    def url(self, volume, issue, page):
        
        self.validate("baseurl")

        cgi = "&volume=%d&issue=&pages=%d" % (volume, page)
        mainurl = self.baseurl + cgi

        print mainurl

        from htmlparser import fetch_url
        response = fetch_url(mainurl)

        parser = WileyParser()
        parser.feed(response)
        for article in parser:
            if not article: #failed url
                continue

            if article.start_page == page:
                print article
                
                #we don't quite have the article url yet
                response = fetch_url(article.url)
                pdfget = WileyPDFFetcher()
                pdfget.feed(response)
                url = pdfget.url.split("&PLAC")[0]
                return url, issue

class AngeChem(WileyJournal):

    name = "Angewandte Chemie"
    baseurl = "http://www3.interscience.wiley.com/search/allsearch?mode=citation&contextLink=blah&issn=%281521-3773%2C1521-3773%29"

class IJQC(WileyJournal):

    name = "International Journal Of Quantum Chemistry"
    baseurl = "http://www3.interscience.wiley.com/search/allsearch?mode=citation&contextLink=blah&issn=1097-461X"

class JPOC(WileyJournal):

    name = "Journal of Physical Organic Chemistry"
    baseurl = "http://www3.interscience.wiley.com/search/allsearch?mode=citation&contextLink=blah&issn=1099-1395"

class JCC(WileyJournal):

    name = "Journal of Computational Chemistry"
    baseurl = "http://www3.interscience.wiley.com/search/allsearch?mode=citation&contextLink=blah&issn=1096-987X"

class ChemPhysChem(WileyJournal):
    
    name = "ChemPhysChem"
    baseurl = "http://www3.interscience.wiley.com/search/allsearch?mode=citation&contextLink=blah&issn=1439-7641"

