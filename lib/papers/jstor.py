from pdfget import ArticleParser, PDFArticle, Journal, Page
from htmlexceptions import HTMLException

from selenium import selenium

import sys


class JstorQuery:

    def run(self, name, volume, page):
        self.selenium = selenium("localhost", 4444, "*chrome", "http://www.jstor.org/")
        self.selenium.start()

        sel = self.selenium
        sel.open("/action/showArticleLocator")
        sel.remove_selection("journalTitle", "label=All Titles")
        sel.add_selection("journalTitle", "label=%s"  % name)
        sel.type("Volume", "%d" % volume)
        sel.type("StartPage", "%s" % page)
        sel.click("articleLocatorSubmit")
        sel.wait_for_page_to_load("30000")
        self.html = sel.get_html_source()

        #sel.open("/archive/")
        #sel.type("vol_num", "%d" % volume)
        #sel.type("page_num", "%s" % page)
        #sel.click("journal_search_volume_go")
        #sel.wait_for_page_to_load("30000")

        self.selenium.stop()

class JstorJournal(Journal):

    def url(self, volume, issue, page):

        from htmlparser import URLLister, fetch_url
        import re

        query = JstorQuery()
        query.run(self.name, volume, page)
        url_list = URLLister()
        url_list.feed(query.html)
        url = url_list["PDF"]
        #parse away the nonsense
        match = re.compile("redirectUri[=](.*)").search(url)
        if not match:
            raise HTMLException("No page found for volume %d for %s" % (volume, self.name))

        nextlink = match.groups()[0]
        fullurl = "http://www.jstor.org" + nextlink
        return fullurl, 0

class Science(JstorJournal):

    name = "Science"

    
