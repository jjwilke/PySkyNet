from pdfget import ArticleParser, PDFArticle, Journal, Page
from htmlparser import URLLister
from htmlexceptions import HTMLException

import sys
import re

from selenium import selenium

class InformaQuery:
    
    def __init__(self, volume, page):
        self.volume = volume
        self.page = page

    def run(self):
        self.selenium = selenium("localhost", 4444, "*chrome", "http://www.informaworld.com/")
        self.selenium.start()
        sel = self.selenium
        sel.open("/smpp/search~db=all~searchmode=citation?newsearch=true")
        sel.click("//input[@name='sourcematch' and @value='exact']")
        sel.type("source", "molecular physics")
        sel.type("volume", "%d" % self.volume)
        sel.type("page", "%s" % self.page)
        sel.click("//input[@value='Search']")
        sel.wait_for_page_to_load("30000")
        self.html = sel.get_html_source()
        self.text = sel.get_body_text()
        self.selenium.stop()

class InformaJournal(Journal):

    def url(self, volume, issue, page):

        self.validate()
        
        query = InformaQuery(volume, page)
        query.run()
        url_list = URLLister()
        url_list.feed(query.html)
        pdfurl = "http://www.informaworld.com/" + url_list["Full Text PDF"]

        print query.text
        issue = int(re.compile("Issue\s+(\d+)").search(query.text).groups()[0])

        return pdfurl, issue
            

class MolPhys(InformaJournal):
    
    name = "Molecular Physics"


