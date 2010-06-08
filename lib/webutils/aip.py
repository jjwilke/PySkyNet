from pdfget import ArticleParser, PDFArticle, Journal
from htmlparser import URLLister
from htmlexceptions import HTMLException

import sys
import re

from selenium import selenium

class AIPQuery:
    
    def __init__(self, volume, page):
        self.volume = volume
        self.page = page

    def run(self):
        self.selenium = selenium("localhost", 4444, "*chrome", "http://jcp.aip.org")
        self.selenium.start()
    
        sel = self.selenium
        sel.open("/jcpsa6")
        sel.type("vol", "%d" % self.volume)
        sel.type("pg", "%d" % self.page)
        sel.click("//input[@value='' and @type='submit']")
        sel.wait_for_page_to_load("30000")
        sel.wait_for_pop_up("_self", "30000")
        self.aiphtml = sel.get_html_source()
    
        self.selenium.stop()

if __name__ == "__main__":
    unittest.main()

class AIPArticle(PDFArticle):
    pass
    
class AIPParser(ArticleParser):

    def reset(self):
        ArticleParser.reset(self)

        #treat paragraph breaks as divisions
        self.start_p = self.start_div
        self.end_p = self.end_div

        self.title_text = self.append_text
        self.pages_text = self.append_text
        self.citation_text = self.append_text

    def links_text(self, text):
        if text == "Download PDF": #grab this link
            pdflink = self.href.replace("amp;", "")
            self.article.set_pdfurl(pdflink)

    def start_a(self, attrs):
        self.href = self.get_html_attr("href", attrs)

    def end_a(self):
        self.href = None

    def _start_dbttitle(self, attrs):
        self.a_frame = "title"
        self.text_frame = "title"
        self.article = AIPArticle()

    def _end_dbttitle(self):
        title = self.get_text()
        self.article.set_title(title)

        self.text_frame = None
        self.a_frame = None

    def _start_dbtcitation(self, attrs):
        self.text_frame = "citation"

    def _end_dbtcitation(self):
        self.text_frame = None
        citation = self.get_text()
        import re
        matches = map(int, re.compile("\d+").findall(citation))
        volume, page, year = matches[:3]

        #just set the pages like so
        self.article.set_pages(page, page)

    def _start_dbtdownload(self, attrs):
        self.a_frame = "links"
        self.text_frame = "links"

    def _end_dbtdownload(self):
        self.articles.append(self.article)
        self.article = None

        self.text_frame = None
        self.a_frame = None

class AIPJournal(Journal):

    def get_articles(self, volume, issue):
        mainurl = "%s/v%d/i%d" % (self.baseurl, volume, issue)

        from htmlparser import fetch_url
        response = fetch_url(mainurl)
        if not response:
            return []

        parser = AIPParser()
        parser.feed(response)
        return parser

    def url(self, volume, issue, page):

        self.validate("baseurl", "volstart")
        
        pagestr = "%d" % page
        if len(pagestr) == 5:
            pagestr = "0" + pagestr
        if volume >= self.volstart: #get the issue from the page number
            if pagestr[0] == "0":
                issue = int(pagestr[1])
            else:
                issue = int(pagestr[:2])

            parser = self.get_articles(volume, issue)
            for article in parser:
                if article.start_page == page:
                    return article.url, issue
        elif not issue:
            query = AIPQuery(volume, page)
            query.run()
            url_list = URLLister()
            url_list.feed(query.aiphtml)
            pdfurl = url_list["Download PDF"]
            regexp = re.compile("Issue\s(\d+)")
            for name in url_list:
                match = regexp.search(name)
                if match:
                    issue = int(match.groups()[0])
                    return pdfurl, issue
                    
            sys.exit()
            

class JCP(AIPJournal):
    
    name = "Journal of Chemical Physics"

    #the base url
    baseurl = "http://jcp.aip.org/jcpsa6"

    #the volume start at which the journal switched over numbering system
    volstart = 122

class JMP(AIPJournal):

    name = "Journal of Mathematical Physics"

    #the base url
    baseurl = "http://jmp.aip.org/jmapaq"

    #the volume start at which the journal switched over numbering system
    volstart = 46

