from htmlparser import URLLister
from pdfget import ArticleParser, PDFArticle, Journal
from htmlexceptions import HTMLException

import sys

class RSCArticle(PDFArticle):
    pass
    
class RSCParser(ArticleParser):

    def reset(self):
        ArticleParser.reset(self)

        #treat paragraph breaks as divisions
        self.start_p = self.start_div
        self.end_p = self.end_div
        self.title_text = self.append_text
        self.citation_text = self.append_text


    def start_a(self, attrs):
        if self.text_frame == "citation":
            citation = self.get_text()
            entries = citation.split(",")
            page = int(entries[-1].split()[0])
            self.article.set_pages(page, page)
            self.articles.append(self.article)

            self.article = None
            self.text_frame = None

        else:
            title = self.get_html_attr("title", attrs)
            if title and "Select for access" in title:
                self.text_frame = "title"
                href = self.get_href(attrs)
                url = "http://www.rsc.org" + href
                self.article = RSCArticle()
                self.article.set_pdfurl(url)

    def end_a(self):
        if self.text_frame == "title":
            title = self.get_text()
            self.article.set_title(title)
            self.text_frame = "citation"

class RSCJournal(Journal):

    def get_articles(self, volume, issue):
        year = self.year1 + volume - 1
        mainurl = self.template % (year, volume, volume, year, issue)

        from htmlparser import fetch_url
        response = fetch_url(mainurl)
        if not response:
            return []

        parser = RSCParser()
        parser.feed(response)
        return parser

    def url(self, volume, issue, page):
        self.validate("template", "year1")
        parser = self.get_articles(volume, issue)
        for article in parser:
            if article.start_page == page:
                url_list = URLLister()
                response = fetch_url(article.url)
                url_list.feed(response)
                pdflink = "http://www.rsc.org" + url_list["PDF"]
                return pdflink, issue

class PCCP(RSCJournal):

    name = "Physical Chemistry Chemical Physics"
    year1 = 1999
    template = "http://www.rsc.org/Publishing/Journals/CP/article.asp?Journal=CP5&VolumeYear=%d%d&Volume=%d&JournalCode=CP&MasterJournalCode=CP&SubYear=%d&type=Issue&Issue=%d&x=11&y=14"

