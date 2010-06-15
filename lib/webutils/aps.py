from pdfget import ArticleParser, PDFArticle, Journal, Page
from htmlexceptions import HTMLException

import sys
import re

def parse_reference(text):
    repls = {
        ".," : ".",
        " and" :  ", ",
        ".-" : ". ",
    }

    for entry in repls:
        text = text.replace(entry, repls[entry])

    #first strip off the rubbish
    match = re.compile("^.*?\d+[,]\s*\d+.*?\d{4}", re.DOTALL).search(text) #for some reason spaces are not matching here
    if not match:
        sys.stderr.write("Could not find properly formatted reference\n")
        return None
    text =  match.group()
    #get the authors
    matches = re.compile("([A-Z][.].*?)(?<!\d)[,]", re.DOTALL).findall(text)
    if not matches:
        sys.stderr.write("Could not find properly formatted authors\n")
        return None
    authors = []
    for author in matches:
        entries = map(lambda x: x.strip(), author.split("."))
        initials = "".join(entries[:-1])
        lastname = entries[-1]
        authors.append("%s, %s" % (lastname, initials))

    match = re.compile("(\d+)[,].*?(\d+).*?(\d{4})", re.DOTALL).search(text)
    if not match:
        sys.stderr.write("Could not find properly formatted volume, page, year\n")
        return None

    volume, page, year = match.groups()

    match = re.compile("[,]([a-zA-Z .]+)%s" % volume, re.DOTALL).search(text)
    if not match:
        sys.stderr.write("Could not find properly formatted journal\n")
        return None
    
    journal = match.groups()[0].strip()
    vals = {}
    vals["volume"] = int(volume)
    vals["page"] = Page(page)
    vals["year"] = int(year)
    vals["authors"] = authors
    vals["journal"] = journal

    return vals

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
            match = re.compile("(\d+.*)PDF", re.DOTALL).search(text)
            if not match: #just ignore this
                self.article = None
                self.a_frame = None
                self.text_frame = None
                ArticleParser.end_div(self)
                return

            text = match.groups()[0]
            match = map(Page, re.compile("\d+").findall(text))

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
        if self.article:
            self.articles.append(self.article)
            self.article = None
            self.text_frame = None
            self.a_frame = None


class APSJournal(Journal):

    def get_articles(self, volume, issue):
        mainurl = "%s/toc/%s/v%d/i%d" % (self.baseurl, self.abbrev, volume, issue)

        from htmlparser import fetch_url
        response = fetch_url(mainurl)
        if not response:
            return []

        parser = APSParser()
        parser.feed(response)

        return parser

    def url(self, volume, issue, page):
        from webutils.htmlparser import fetch_url 

        self.validate("baseurl", "abbrev", "volstart", "doi")

        if volume >= self.volstart: #get the issue from the page number
            issue = page.get_issue()
        else:
            import re
            url = "%s.%d.%s" % (self.doi, volume, page)
            text = fetch_url(url)
            regexp = "/toc/%s/v%d/i(\d+)" % (self.abbrev, volume)
            issue = int(re.compile(regexp).search(text).groups()[0])

        parser = self.get_articles(volume, issue) 
        for article in parser:
            if article.start_page == page:
                url = self.baseurl + article.url
                return url, issue

        raise HTMLException("No match found for %s %d %s" % (self.name, volume, page))

class PRL(APSJournal):
    
    name = "Physical Review Letters"

    #the base url
    baseurl = "http://prl.aps.org"

    #the volume start at which the journal switched over numbering system
    volstart = 87

    abbrev = "PRL"

    doi = "http://dx.doi.org/10.1103/PhysRevLett"

class PROLA(APSJournal):

    name = "Physical Review"

    #the base url
    baseurl = "http://prola.aps.org"

    #the volume start at which the journal switched over numbering system
    volstart = 10000 #never switched

    abbrev = "PR"

    doi = "http://link.aps.org/doi/10.1103/PhysRev"

class PRA(APSJournal):

    name = "Physical Review A"

    #the base url
    baseurl = "http://pra.aps.org"

    #the volume start at which the journal switched over numbering system
    volstart = 61

    abbrev = "PRA"

    doi = "http://link.aps.org/doi/10.1103/PhysRevA"

class PRB(APSJournal):

    name = "Physical Review B"

    #the base url
    baseurl = "http://prb.aps.org"

    #the volume start at which the journal switched over numbering system
    volstart = 63

    abbrev = "PRB"

    doi = "http://link.aps.org/doi/10.1103/PhysRevB"

class RMP(APSJournal):

    baseurl = "http://rmp.aps.org"

    name = "Reviews of Modern Physics"

    volstart = 10000 #none

    abbrev = "RMP"

    doi = "http://link.aps.org/doi/10.1103/RevModPhys"

