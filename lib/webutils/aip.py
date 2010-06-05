from pdfget import ArticleParser, PDFArticle, Journal
from htmlexceptions import HTMLException

import sys

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
        
        if volume >= self.volstart: #get the issue from the page number
            pagestr = "%d" % page
            if pagestr[0] == "0":
                issue = int(pagestr[1])
            else:
                issue = int(pagestr[:2])
        else:
            from utils.RM import save, load
            volumes = load(self.pickle_path())
            issues = volumes[volume].issues
            for entry in issues:
                issobj = issues[entry]
                if page in issobj.pages:
                    issue = entry
                    break
            
        parser = self.get_articles(volume, issue)
        for article in parser:
            if article.start_page == page:
                return article.url, issue

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

