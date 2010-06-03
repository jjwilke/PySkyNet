from pdfget import ArticleParser, PDFArticle, Journal
from htmlparser import URLLister
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

class ACSJournal(Journal):

    def get_issue(self, volume, page):
        from htmlparser import fetch_url
        import re
        mainurl = "http://pubs.acs.org/loi/%s/%d" % (self.id, volume)
        response = fetch_url(mainurl)
        url_list = URLLister()
        url_list.feed(response)
        for name in url_list:
            if not "Issue" in name or not "Volume" in name:
                continue

            volcheck, issue, start, end = map(int, re.compile("Volume\s(\d+)[,]\sIssue\s(\d+)[,]\spp[.]\s(\d+).*?(\d+)").search(name).groups())
            if volcheck == volume and start <= page and end >= page:
                return issue

        return 0

    def url(self, volume, issue, page):

        self.validate("id")

        if not issue:
            issue = self.get_issue(volume, page)

        if not issue:
            raise HTMLException("Unable to find issue for volume %d, page %d" % (volume, page))

        mainurl = "http://pubs.acs.org/toc/%s/%d/%d" % (self.id, volume, issue)

        from htmlparser import fetch_url
        response = fetch_url(mainurl)

        parser = ACSParser()
        parser.feed(response)
        for article in parser:
            if article.start_page == page:
                return article.url, issue

        raise HTMLException("No matching entry for %d %d %d" % (volume, issue, page))

class JACS(ACSJournal):
    name = "Journal of the American Chemical Society"
    id = "jacsat"

class JCTC(ACSJournal):
    name = "Journal of Chemical Theory and Computation"
    id = "jctcce"

class JPC(ACSJournal):
    name = "Journal of Physical Chemistry"
    baseurl = "http://pubs.acs.org/toc/jpchax"

class JPCA(ACSJournal):
    name = "Journal of Physical Chemistry A"
    id = "jpcafh"

class JPCB(ACSJournal):
    name = "Journal of Physical Chemistry B"
    id = "jpcbfk"

class JOC(ACSJournal):
    name = "Journal of Organic Chemistry"
    id = "joceah"

class InorgChem(ACSJournal):
    name = "Inorganic Chemistry"
    id = "inocaj"
    
