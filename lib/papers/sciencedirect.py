from papers.pdfget import ArticleParser, PDFArticle, Journal, Page
from webutils.htmlexceptions import HTMLException
from webutils.htmlparser import URLLister, fetch_url

import sys
import re

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
        text = text.strip()
        match1 = re.compile("\d+[.]").search(text)
        match2 = ("articles" in text) #second boolean check
        if not match1 and not match2:
            return

        if match1:
            match = match1.group()
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

            start_page, end_page = map(Page, match.groups())
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

    def url(self, selenium):
        volume = self.volume
        page = self.page
        issue = self.issue
        
        self.validate("baseurl")

        
        response = fetch_url(self.baseurl)
        url_list = URLLister()
        url_list.feed(response)

        #check to see if we are already on the top page
        match = re.compile("Volume\s%d[,]\sIssue" % volume).search(response)
        nexturl = None
        if not match:
            for name in url_list:
                match1  = re.compile("Volumes\s(\d+)\s*[-]\s*(\d+)").search(name)
                match2  = re.compile("Volume\s(\d+)").search(name)
                if not match1 and not match2:
                    continue

                start = finish = 0
                if match1:
                    start, finish = map(int, match1.groups())
                elif match2:
                    start = finish = int(match2.groups()[0])

                if volume >= start and volume <= finish:
                    nexturl = url_list[name]
                    break

            if not nexturl:
                raise HTMLException("Unable to find link for volume %d" % volume)

            nexturl = "http://www.sciencedirect.com%s" % nexturl
            response = fetch_url(nexturl)
            url_list.reset()
            url_list.feed(response)


        baseurl = nexturl
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


            page_text = url_list.get_text(name)
            
            start_page, end_page = map(Page, re.compile("pp[.]\s+(\d+)[-](\d+)").search(page_text).groups())

            if volume == volcheck and page >= start_page and page <= end_page:
                nexturl = url_list[name]
                if not issue:
                    issue = start_issue
                break

        if not nexturl: #all is not lost... we might already be on the correct page
            regexp = "Volume\s%d[,]\sIssue[s]?\s(\d+)[-]?\d*[,]\sPages\s(\d+)[-](\d+)" % volume
            match = re.compile(regexp).search(response)
            if match:
                number, start, end = map(int, match.groups())
                if start <= page and end >= page:
                    nexturl = baseurl
                    issue = number

        else:
            nexturl = "http://www.sciencedirect.com%s" % nexturl

        if not nexturl:
            raise HTMLException("Unable to find link for volume %d issue %d" % (volume, issue))

        response = fetch_url(nexturl)

        sdparser = SDParser()
        sdparser.feed(response)

        for article in sdparser:
            if article.start_page == page:
                return article.url, issue

        raise HTMLException("No match found for %s %d %s" % (self.name, volume, page))


class CPL(SDJournal):
    name = "Chemical Physics Letters"
    baseurl = "http://www.sciencedirect.com/science/journal/00092614"

class ChemPhys(SDJournal):
    name = "Chemical Physics"
    baseurl = "http://www.sciencedirect.com/science/journal/03010104"

class PhysRep(SDJournal):
    name = "Physics Reports"
    baseurl = "http://www.sciencedirect.com/science/journal/03701573"

class THEOCHEM(SDJournal):
    name = "Journal of Molecular Structure: THEOCHEM"
    baseurl = "http://www.sciencedirect.com/science/journal/01661280"

class CompChem(SDJournal):
    name = "Computers and Chemistry"
    baseurl = "http://www.sciencedirect.com/science/journal/00978485"

class JMS(SDJournal):
    name = "Journal of Molecular Spectroscopy"
    baseurl = "http://www.sciencedirect.com/science/journal/00222852"

class JCompPhys(SDJournal):
    name = "Journal of Computational Physics"
    baseurl = "http://www.sciencedirect.com/science/journal/00219991"

class CMS(SDJournal):
    name = "Computational Materials Science"
    baseurl = "http://www.sciencedirect.com/science/journal/09270256"

class CPC(SDJournal):
    name = "Computer Physics Communications"
    baseurl = "http://www.sciencedirect.com/science/journal/00104655"

class JMB(SDJournal):
    name = "Journal of Molecular Biology"
    baseurl = "http://www.sciencedirect.com/science/journal/00222836"

class CCR(SDJournal):
    name = "Coordination Chemistry Reviews"
    baseurl = "http://www.sciencedirect.com/science/journal/00108545"

if __name__ == "__main__":
    pass

