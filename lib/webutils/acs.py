from pdfget import ArticleParser, PDFArticle
from htmlexceptions import HTMLException

class ACSArticle(PDFArticle):
    
    def __init__(self):
        self.title = "No title"
        self.start_page = 0
        self.end_page = 1

    def __str__(self):
        return "%s pp %d-%d" % (self.title, self.start_page, self.end_page)

    def set_pdfurl(self, url):
        self.url = url

    def set_title(self, text):
        self.title = text

    def set_pages(self, text):
        import re
        matches = map(int, re.compile("\d+").findall(text))
        if len(matches) == 1:
            if not "p " in text:
                raise Exception("%s is not a properly formatted page spec" % text)
            self.start_page = self.end_page = matches[0]
        elif len(matches) == 2:
            if not "pp " in text:
                raise Exception("%s is not a properly formatted page spec" % text)
            self.start_page, self.end_page = matches

class ACSParser(ArticleParser):

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
            self.article.set_pages(pages)
        
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
        
        parser = ACSParser()
        parser.feed(response)
        for article in parser:
            if article.start_page == page:
                print article
                return article.url, issue

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
    
