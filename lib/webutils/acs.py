from pdfget import ArticleParser, PDFArticle
from htmlexceptions import HTMLException
import sys

class ACSArticle(PDFArticle):
    pass    

class ACSParser(ArticleParser):

    def reset(self):
        ArticleParser.reset(self)

        self.title_text = self.append_text
        self.pages_text = self.append_text
        self.citation_text = self.append_text

    def title_a(self, attrs):
        self.text_frame = "title"

    def pdf_a(self, attrs):
        title = self.get_html_attr("title", attrs)
        if title == "Hi-Res PDF":
            pdflink = self.get_html_attr("href", attrs)
            url = "http://pubs.acs.org" + pdflink
            self.article.set_pdfurl(url)

    def start_a(self, attrs):
        self.call_method(self.a_frame, "a", attrs)

    def end_a(self):
        pass

    def start_strong(self, attrs):
        if self.text_frame == "pages": #nuke the frame
            self.text_frame = None
            pages = self.get_text()
            import re
            matches = map(int, re.compile("\d+").findall(pages))
            start_page = end_page = 0
            if len(matches) == 1:
                if not "p " in pages:
                    raise Exception("%s is not a properly formatted page spec" % pages)
                start_page = end_page = matches[0]
            elif len(matches) == 2:
                if not "pp " in pages:
                    raise Exception("%s is not a properly formatted page spec" % pages)
                start_page, end_page = matches

            self.article.set_pages(start_page, end_page)
        
    def _start_articleBoxMeta(self, attrs):
        self.a_frame = "title"
        self.article = ACSArticle()

    def _end_articleBoxMeta(self):
        pass

    def _start_articleAuthors(self, attrs):
        #we are done with the title... commit the title to the article
        title = self.get_text()
        self.article.set_title(title)
        self.text_frame = None
        self.a_frame = None

    def _end_articleAuthors(self):
        self.text_frame = "pages"

    def _start_articleLinksIcons(self, attrs):
        self.a_frame = "pdf"

    def _end_articleLinksIcons(self):
        self.a_frame = None

        self.articles.append(self.article)
        self.article = None

class ACSJournal:

    baseurl = None

    def url(self, volume, issue, page):

        if not self.baseurl:
            HTMLException("Class %s does not have baseurl" % self.__class__)

        mainurl = "%s/%d/%d" % (self.baseurl, volume, issue)

        from htmlparser import fetch_url
        response = fetch_url(mainurl)

        print "Response received from %s" % mainurl

        parser = ACSParser()
        parser.feed(response)
        for article in parser:
            if article.start_page == page:
                return article.url, issue

        raise HTMLException("No matching entry for %d %d %d" % (volume, issue, page))

class JACS(ACSJournal):
    baseurl = "http://pubs.acs.org/toc/jacsat"

class JCTC(ACSJournal):
    baseurl = "http://pubs.acs.org/toc/jctcce"

class JPC(ACSJournal):
    baseurl = "http://pubs.acs.org/toc/jpchax"

class JPCA(ACSJournal):
    baseurl = "http://pubs.acs.org/toc/jpcafh"

class JPCB(ACSJournal):
    baseurl = "http://pubs.acs.org/toc/jpcbfk"

class JOC(ACSJournal):
    baseurl = "http://pubs.acs.org/toc/joceah"
    
class InorgChem(ACSJournal):
    baseurl = "http://pubs.acs.org/toc/inocaj"
    
