from papers.pdfget import ArticleParser, PDFArticle, Journal, Page
from webutils.htmlparser import URLLister
from webutils.htmlexceptions import HTMLException
from webutils.htmlparser import fetch_url
from selenium import selenium

import sys
import os.path
import re

def parse_reference(text):
    from papers.pdfglobals import PDFGetGlobals as pdfglobals

    repls = {
        ".," : ".",
        " and" :  ", ",
        ".-" : ". ",
    }

    for entry in repls:
        text = text.replace(entry, repls[entry])

    match = re.compile("^(.*?)\n\s*[\(]\d+[\)]", re.DOTALL).search(text)
    if match:
        text = match.groups()[0]

    journal = pdfglobals.find_journal_in_entry(text)
    if not journal:
        sys.stderr.write("Could not find properly formatted journal\n")
        return None 

    match = re.compile("^.*?(\d{4}[,]\s*\d+[,]\s*\d+[.]?)", re.DOTALL).search(text) #for some reason spaces are not matching here
    if not match:
        sys.stderr.write("Could not find properly formatted volume, page, year\n")
        return None

    numbers = match.groups()[0]
    match = re.compile("(\d{4})[,].*?(\d+)[,].*?(\d+)", re.DOTALL).search(numbers)
    if not match:
        sys.stderr.write("Could not find properly formatted volume, page, year\n")
        return None
    year, volume, page = match.groups()


    #throw out the journal
    new_text = text.replace(journal, "").replace(numbers, "")
    match = re.compile("[\(]\d+[\)](.*)", re.DOTALL).search(new_text)
    if match:
        new_text = match.groups()[0]

    #get the authors
    matches = new_text.split(";")
    if not matches:
        sys.stderr.write("Could not find properly formatted authors\n")
        return None

    authors = []
    for author in matches:
        lastname, initials = author.split(",")
        initials = map(lambda x: x.strip().strip("."), initials)
        initials = "".join(initials)
        authors.append("%s, %s" % (lastname, initials))

    vals = {}
    vals["volume"] = int(volume)
    vals["page"] = Page(page)
    vals["year"] = int(year)
    vals["authors"] = authors
    vals["journal"] = journal

    return vals

class ACSQuery:
    
    def __init__(self, id, volume, page, selenium):
        self.id = id
        self.volume = volume
        self.page = page
        self.selenium = selenium

    def run(self):
        self.selenium.open("http://pubs.acs.org/loi/%s" % self.id);
        self.selenium.click("qsTabCitation");
        self.selenium.type("qsCitVol", "%d" % self.volume);
        self.selenium.type("qsCitPage", "%s" % self.page);
        self.selenium.click("qsCitSubmit");
        self.selenium.wait_for_page_to_load("30000");
        self.html = self.selenium.get_html_source()

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

            start = Page("%d" % start_page)
            end = Page("%d" % end_page)
            self.article.set_pages(start, end)
        
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

    def url(self, selenium):
        volume = self.volume
        page = self.page
        issue = self.issue

        self.validate("id")

        if not self.issue:
            query = ACSQuery(self.id, self.volume, self.page, selenium)
            query.run()
            url_list = URLLister("Abstract","Tools")
            url_list.feed(query.html)
            pdfurl = None

            try:
                pdfurl = "http://pubs.acs.org" + url_list["PDF w/ Links"]
            except KeyError:
                pass

            if not pdfurl:
                pdfurl = "http://pubs.acs.org" + url_list["Hi-Res PDF"]
                

            tocurl = url_list["Table of Contents"]
            self.issue = int(os.path.split(tocurl)[-1])
            return pdfurl, self.issue

        else:
            mainurl = "http://pubs.acs.org/toc/%s/%d/%d" % (self.id, self.volume, self.issue)

            response = fetch_url(mainurl)
            parser = ACSParser()
            parser.feed(response)
            for article in parser:
                if article.start_page == page:
                    return article.url, self.issue

        raise HTMLException("No match found for %s %d %s" % (self.name, self.volume, self.page))

class JACS(ACSJournal):
    name = "Journal of the American Chemical Society"
    id = "jacsat"

class JCTC(ACSJournal):
    name = "Journal of Chemical Theory and Computation"
    id = "jctcce"

class JPC(ACSJournal):
    name = "Journal of Physical Chemistry"
    id = "jpchax"

class JPCL(ACSJournal):
    name = "Journal of Physical Chemistry Letters"
    id = "jpclcd"

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
    
class OrgLett(ACSJournal):
    name = "Organic Letters"
    id = "orlef7"

class ChemRev(ACSJournal):
    name = "Chemical Reviews"
    id = "chreay"

class ACR(ACSJournal):
    name = "Accounts of Chemical Research"
    id = "achre4"
