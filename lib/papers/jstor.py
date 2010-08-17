from papers.pdfget import ArticleParser, PDFArticle, Journal, Page
from webutils.htmlexceptions import HTMLException
from webutils.htmlparser import URLLister, fetch_url

from selenium import selenium

import sys
import re


class JstorQuery:

    def run(self, name, volume, page, sel):
        sel = self.selenium
        sel.open("http://www.jstor.org/action/showArticleLocator")
        sel.remove_selection("journalTitle", "label=All Titles")
        sel.add_selection("journalTitle", "label=%s"  % name)
        sel.type("Volume", "%d" % volume)
        sel.type("StartPage", "%s" % page)
        sel.click("articleLocatorSubmit")
        sel.wait_for_page_to_load("30000")
        self.html = sel.get_html_source()

class JstorJournal(Journal):

    def url(self, selenium):
        volume = self.volume
        page = self.page
        issue = self.issue

        query = JstorQuery()
        query.run(self.name, volume, page, selenium)
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

    
