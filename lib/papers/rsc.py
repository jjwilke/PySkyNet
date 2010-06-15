from papers.pdfget import ArticleParser, PDFArticle, Journal, Page
from webutils.htmlexceptions import HTMLException
from webutils.htmlparser import URLLister, fetch_url

from selenium import selenium

import sys

class RSCArticle(PDFArticle):
    pass

class RSCQuery:
    
    def __init__(self, journal, volume, page):
        self.volume = volume
        self.page = page
        self.journal = journal
        self.rschtml = None

    def run(self):
        self.selenium = selenium("localhost", 4444, "*chrome", "http://www.rsc.org/")
        self.selenium.start()
        sel = self.selenium
        sel.open("/Publishing/Journals/articlefinder.asp")
        sel.select("journal_code", "label=%s" % self.journal)
        sel.type("year_volume", "%d" % self.volume)
        sel.type("fpage", "%s" % self.page)
        sel.click("//div[@id='content']/div[2]/div/div[2]/form/div[5]/input[2]")
        sel.wait_for_page_to_load("30000")
        self.rschtml = sel.get_html_source()
    
        self.selenium.stop()
    
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
            page = Page(entries[-1].split()[0])
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

        response = fetch_url(mainurl)
        if not response:
            return []

        parser = RSCParser()
        parser.feed(response)
        return parser

    def url(self, volume, issue, page):
        from webutils.htmlparser import fetch_url

        self.validate("template", "year1")
        response = None
        if not issue:
            query = RSCQuery(self.name, volume, page)
            query.run()
            response = query.rschtml
        else:
            parser = self.get_articles(volume, issue)
            for article in parser:
                if article.start_page == page:
                    response = fetch_url(article.url)
                    break

        if not response:
            raise HTMLException("No match found for %s %d %s" % (self.name, volume, page))

        url_list = URLLister()
        url_list.feed(response)
        pdflink = "http://www.rsc.org" + url_list["PDF"]
        return pdflink, issue

class PCCP(RSCJournal):

    name = "Physical Chemistry Chemical Physics"
    dropdown = "PCCP + Faraday Transactions"
    year1 = 1999
    template = "http://www.rsc.org/Publishing/Journals/CP/article.asp?Journal=CP5&VolumeYear=%d%d&Volume=%d&JournalCode=CP&MasterJournalCode=CP&SubYear=%d&type=Issue&Issue=%d&x=11&y=14"


class CSR(RSCJournal):

    name = "Chemical Society Reviews"
    dropdown = "Chem. Soc. Reviews + Royal Institute of Chemistry Reviews"
    year1 = 1972
    template = "http://www.rsc.org/publishing/journals/cs/article.asp?Journal=CS6&VolumeYear=%d%d&Volume=%d&JournalCode=CS&MasterJournalCode=CS&SubYear=%d&type=Issue&Issue=&x=13&y=9"

