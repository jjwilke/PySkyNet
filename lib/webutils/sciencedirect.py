from pdfget import ArticleParser, PDFArticle, Journal
from htmlexceptions import HTMLException

import sys

class SDArticle(PDFArticle):
    pass


class SDParser(ArticleParser):

    def reset(self):
        ArticleParser.reset(self)

        #treat paragraph breaks as divisions
        self.start_p = self.start_div
        self.end_p = self.end_div

    def article_text(self, text):
        text = text.strip()
        if text:
            self.append_text(text)

    def td_text(self, text):
        import re
        text = text.strip()
        match = re.compile("\d+[.]").search(text)
        if not match:
            return

        match = match.group()
        if not len(match) == len(text): #exact match = good
            return

        self.text_frame = "article"
        self.a_frame = "article"

        if self.article:
            text = self.get_text("\n")

            #title is everything up to Pags
            match = re.compile("(.*)Pages").search(text)
            if not match:
                #ignore this and move on
                self.article = SDArticle()
                return

            title = match.groups()[0]
            self.article.set_title(title)

            #the page line is line 2
            match = re.compile("Pages\s(\d+)[-](\d+)").search(text)
            if not match:
                #ignore this and move on
                self.article = SDArticle()
                return

            start_page, end_page = map(int, match.groups())
            self.article.set_pages(start_page, end_page)
            
            self.articles.append(self.article)
            
            #and make a new one
            self.article = SDArticle()

        else:
            self.article = SDArticle()

    def a_text(self, text):
        self.append_text(text)
        if "PDF" in text:
            self.article.set_pdfurl(self.href)

    def start_a(self, attrs):
        self.href = self.get_href(attrs)
        if self.a_frame == "article":
            self.text_frame = "a"
    
    def end_a(self):
        if self.a_frame == "article":
            self.text_frame = "article"
        self.href = None

    def start_td(self, attrs):
        self.text_frame = "td"

    def end_td(self):
        if self.text_frame == "td":
            self.text_frame = None

class SDJournal(Journal):

    #the base url
    baseurl = None

    def url(self, volume, issue, page):
        
        self.validate("baseurl")

        from htmlparser import URLLister, fetch_url
        import re
        
        response = fetch_url(self.baseurl)
        url_list = URLLister()
        url_list.feed(response)

        nexturl = None
        for name in url_list:
            regexp = "Volumes\s(\d+)\s?[-]\s?(\d+)"
            match = re.compile(regexp).search(name)
            if not match:
                continue
            
            start, finish = map(int, match.groups())
            if volume >= start and volume <= finish:
                nexturl = url_list[name]
                break

        if not nexturl:
            raise HTMLException("Unable to find link for volume %d" % volume)

        nexturl = "http://www.sciencedirect.com%s" % nexturl
        response = fetch_url(nexturl)
        url_list.reset()
        url_list.feed(response)

        nexturl = None
        for name in url_list:
            match1 = re.compile("Volume\s(\d+)[,]\sIssue\s(\d+)").search(name)
            match2 = re.compile("Volume\s(\d+)[,]\sIssues\s(\d+)[-](\d+)").search(name)
            
            if not match1 and not match2:
                continue

            start_issue = 0
            end_issue = 0
            volcheck = 0
            if match1:
                volcheck, start_issue = map(int, match1.groups())
                end_issue = start_issue
            elif match2:
                volcheck, start_issue, end_issue = map(int, match2.groups())

            
            start_page, end_page = map(int, re.compile("pp[.]\s+(\d+)[-](\d+)").search(url_list.get_text(name)).groups())

            if volume == volcheck and page >= start_page and page <= end_page:
                nexturl = url_list[name]
                if not issue:
                    issue = start_issue
                break

        if not nexturl:
            raise HTMLException("Unable to find link for volume %d issue %d" % (volume, issue))

        nexturl = "http://www.sciencedirect.com%s" % nexturl
        response = fetch_url(nexturl)

        sdparser = SDParser()
        sdparser.feed(response)

        for article in sdparser:
            if article.start_page == page:
                return article.url, issue


class CPL(SDJournal):
    name = "Chemical Physics Letters"
    baseurl = "http://www.sciencedirect.com/science/journal/00092614"

class ChemPhys(SDJournal):
    name = "Chemical Physics"
    baseurl = "http://www.sciencedirect.com/science/journal/03010104"

class PhysRep(SDJournal):
    name = "Physics Reports"
    baseurl = "http://www.sciencedirect.com/science/journal/03701573"

if __name__ == "__main__":
    pass
"""
    from htmlparser import URLLister, fetch_url 
    lister = URLLister()
    response = fetch_url("http://www.sciencedirect.com/science/journal/00092614")
    lister.feed(response)
    for name in lister:
        print name, lister[name]

    data = {
        "_ob" : "QuickSearchURL",
        "_method" : "submitForm",
        "_acct" : "C000033918",
        "md5" : "4f3c1bb84b148e0df0ee45b739b18663",
        "qs_smi" : "5231",
        "qs_title" : "chemical physics letters",
        "qs_vol" : 291,
        "qs_pages" : 109,
        "qs_issue" : "",
        "qs_all" : "",
        "qs_author" : "",
    }
"""

    #params = urllib.urlencode(data)
    #url = "http://www.sciencedirect.com/science?%s" % params
    #print url
    #response = urllib.urlopen(url).read()
    #print response

