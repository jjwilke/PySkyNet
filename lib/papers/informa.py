from papers.pdfget import ArticleParser, PDFArticle, Journal, Page
from webutils.htmlparser import URLLister
from webutils.htmlexceptions import HTMLException

import sys
import re
import time

from selenium import selenium

class InformaQuery:
    
    def __init__(self, journal, volume, page, selenium):
        self.journal = journal
        self.volume = volume
        self.page = page
        self.selenim = selenium

    def run(self):
        sel = self.selenium
        sel.open("/smpp/search~db=all~searchmode=citation?newsearch=true")
        sel.click("//input[@name='sourcematch' and @value='exact']")
        sel.type("source", self.journal.lower())
        sel.type("volume", "%d" % self.volume)
        sel.type("page", "%s" % self.page)
        sel.click("//input[@value='Search']")
        sel.wait_for_page_to_load("30000")
        self.html = sel.get_html_source()
        self.text = sel.get_body_text()

class InformaJournal(Journal):

    def url(self, selenium):

        self.validate()
        
        query = InformaQuery(self.name, self.volume, self.page, selenium)
        query.run()
        url_list = URLLister()
        url_list.feed(query.html)
        pdfurl = "http://www.informaworld.com/" + url_list["Full Text PDF"]

        self.issue = int(re.compile("Issue\s+(\d+)").search(query.text).groups()[0])

        return pdfurl, self.issue
            

class MolPhys(InformaJournal):
    name = "Molecular Physics"

class IRPC(InformaJournal):
    name = "International Reviews in Physical Chemistry"



