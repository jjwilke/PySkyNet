
from pdfget import ArticleParser, PDFArticle
from htmlexceptions import HTMLException

import sys

class APSArticle(PDFArticle):
    pass
    
class APSParser(ArticleParser):

    def reset(self):
        ArticleParser.reset(self)

        #treat paragraph breaks as divisions
        self.start_p = self.start_div
        self.end_p = self.end_div
        self.pages_text = self.append_text
        self.title_text = self.append_text
        self.author_text = self.append_text
        self.blank_text = self.append_text

    def start_a(self, attrs):
        if self.a_frame == "pages":
            href = self.get_href(attrs)
            self.article.set_pdfurl(href)

    def end_a(self):
        if self.a_frame == "title": 
            self.a_frame = None
            title = self.get_text()
            self.article.set_title(title)
            self.text_frame = "author"
            self.a_frame = None

    def start_strong(self, attrs):
        if self.text_frame == "title":
            self.a_frame = "title"

    def end_div(self):
        if self.text_frame == "author":
            self.get_text()
            self.text_frame = "blank"
        elif self.text_frame == "blank":
            self.get_text()
            self.text_frame = "pages"
            self.a_frame = "pages"
        elif self.text_frame == "pages":
            import re
            text = self.get_text()
            text = re.compile("(\d+.*)PDF", re.DOTALL).search(text).groups()[0]
            match = map(int, re.compile("\d+").findall(text))

            if len(match) == 1:
                page = match[0]
                self.article.set_pages(page, page)
            elif len(match) == 2:
                start, end = match
                self.article.set_pages(start, end)
            else:
                raise HTMLException("%s is not valid text input for APS parser" % text)

            self.text_frame = None
            self.a_frame = None
        
        ArticleParser.end_div(self)

    def _start_aps_toc_articleinfo(self, attrs):
        self.text_frame = "title"
        self.article = APSArticle()

    def _end_aps_toc_articleinfo(self):
        self.articles.append(self.article)
        self.article = None
        self.text_frame = None


class APSJournal:

    #the base url
    baseurl = None

    #the volume start at which the journal switched over numbering system
    volstart = None

    abbrev = None

    #some pages get precedeed by a letter, e.g. R4151
    pageletter = None

    def url(self, volume, issue, page):

        if not self.baseurl:
            raise HTMLException("Class %s does not have base url" % self.__class__)
        if not self.volstart:
            raise HTMLException("Class %s does not have volume start" % self.__class__)
        if not self.abbrev:
            raise HTMLException("Class %s does not have abbreviation" % self.__class__)
        
        if volume >= self.volstart: #get the issue from the page number
            pagestr = "%d" % page
            if pagestr[0] == "0":
                issue = int(pagestr[1])
            else:
                issue = int(pagestr[:2])
            
        
        mainurl = "%s/toc/%s/v%d/i%d" % (self.baseurl, self.abbrev, volume, issue)

        from htmlparser import fetch_url
        response = fetch_url(mainurl)

        parser = APSParser()
        parser.feed(response)
        for article in parser:
            if article.start_page == page:
                url = self.baseurl + article.url
                return url, issue

class PRL(APSJournal):

    #the base url
    baseurl = "http://prl.aps.org"

    #the volume start at which the journal switched over numbering system
    volstart = 87

    abbrev = "PRL"

    pageletter = ""

class PRA(APSJournal):

    #the base url
    baseurl = "http://pra.aps.org"

    #the volume start at which the journal switched over numbering system
    volstart = 61

    abbrev = "PRA"

    pageletter = "R"

