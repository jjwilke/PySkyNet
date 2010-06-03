from pdfget import ArticleParser, PDFArticle
from htmlexceptions import HTMLException

import sys

class SpringerArticle(PDFArticle):
    pass



class SpringerStopException(Exception):
    pass

class IssueParser(ArticleParser):


    def reset(self):
        ArticleParser.reset(self)

        #treat paragraph breaks as divisions
        self.start_p = self.start_div
        self.end_p = self.end_div
        self.volume_frame = None
        self.url = None

    def feed(self, text, volume, issue):
        self.issue = issue
        self.volume = volume
        try:
            ArticleParser.feed(self, text)
        except SpringerStopException:
            return

    def volume_text(self, text):
        import re
        match = re.compile("Volume\s(\d+)").search(text)
        if match:
            self.volume_frame = int(match.groups()[0])
            self.text_frame = None
        else:
            self.text_frame = None

    def a_text(self, text):
        if not self.volume_frame == self.volume:
            return
        
        import re
        match1 = re.compile("Number\s(\d+)").search(text)
        match2 = re.compile("Numbers\s(\d+)[-](\d+)").search(text)

        if not match1 and not match2:
            return

        start_issue = end_issue = 0
        if match1:
            start_issue = end_issue = int(match1.groups()[0])
        elif match2:
            start_issue, end_issue = map(int, match2.groups())

        if self.issue >= start_issue and self.issue <= end_issue:
            self.url = self.href
            raise SpringerStopException

    def start_a(self, attrs):
        self.href = self.get_href(attrs)
        self.text_frame = 'a'

    def end_a(self):
        self.text_frame = None
        self.href = None

    def _start_listItemName(self, attrs):
        self.text_frame = "volume"

    def _end_listItemName(self):
        self.text_frame = None

class SpringerParser(ArticleParser):

    mainurl = "http://www.springerlink.com"

    def reset(self):
        ArticleParser.reset(self)

        #treat paragraph breaks as divisions
        self.start_p = self.start_div
        self.end_p = self.end_div

    def content_text(self, text):
        if text.strip() == "Article":
            self.a_frame = "title"
            self.text_frame = "title"
            self.article = SpringerArticle()

    def pdf_text(self, text):
        if "PDF" in text:
            url = self.mainurl + self.href
            self.article.set_pdfurl(url)
            self.text_frame = "pages"

    def pages_text(self, text):
        import re
        match = re.compile("(\d+)[-](\d+)").search(text)
        if match:
            start, end = map(int, match.groups())
            self.article.set_pages(start, end)
            self.articles.append(self.article)
            self.article = None
            self.text_frame = None
            self.a_frame = None

    def title_text(self, text):
        self.append_text(text)

    def start_a(self, attrs):
        if self.a_frame == "pdf":
            self.href = self.get_href(attrs)

    def end_a(self):
        if self.a_frame == "title":
            title = self.get_text()
            self.article.set_title(title)
            self.a_frame = "pdf"
            self.text_frame = "pdf"

    def _start_contentType(self, attrs):
        self.text_frame = "content"

    def _end_contentType(self):
        if self.text_frame == "content":
            self.text_frame = None

    def volume_text(self, text):
        import re
        match = re.compile("Volume\s(\d+)").search(text)
        if match:
            self.volume_frame = int(match.groups()[0])
            self.text_frame = None
        else:
            self.text_frame = None



class SpringerJournal:

    #the base url
    mainurl = SpringerParser.mainurl
    baseurl = None

    def url(self, volume, issue, page):
        if not self.baseurl:
            raise HTMLException("Class %s does not have base url" % self.__class__)
        if not self.name:
            raise HTMLException("Class %s does not have name" % self.__class__)

        from htmlparser import URLLister, fetch_url
        import re

        from utils.RM import load
        links = load(self.pickle)

        url = None
        for entry in links:
            vols = links[entry]
            if volume in vols:
                url = entry
                break

        if not url:
            raise HTMLException("No page found for volume %d for %s" % (volume, self.name))
        
        nexturl = self.mainurl + url
        response = fetch_url(nexturl)

        issparser = IssueParser()
        issparser.feed(response, volume, issue)

        #now have the url for the issue
        nexturl = self.mainurl + issparser.url
        response = fetch_url(nexturl)
        parser = SpringerParser()
        parser.feed(response)

        for article in parser:
            if article.start_page == page:
                return article.url, issue

class TCA(SpringerJournal):

    name = "Theoretical Chemistry Accounts"
    baseurl = "http://www.springerlink.com/content/1432-881X"
    pickle = "/Users/jjwilke/Python/lib/webutils/.springer.tca.links"


if __name__ == "__main__":

    from webutils.htmlparser import fetch_url, URLLister
    from utils.RM import save
    import re

    links = {}

    baseurl = "http://www.springerlink.com"
    url = "/content/1432-881X"
    regexp = "Volume\s(\d+)"
    try:
        while 1:
            response = fetch_url(baseurl + url)
            vols = map(int, re.compile(regexp).findall(response))
            vols.sort()
            print url
            print vols
            links[url] = vols
            url_list = URLLister()
            url_list.feed(response)
            url = url_list["Next Page"]
    except KeyError, error:
        print error

    save(links, ".springer.links")
    
