from papers.pdfget import ArticleParser, PDFArticle, Page, download_pdf
from papers.index import Library
from papers.archive import Archive, MasterArchive
from papers.utils import Cleanup
from skynet.utils.utils import save, load, clean_line, capitalize_word, traceback
from webutils.htmlexceptions import HTMLException
from webutils.htmlparser import URLLister
from papers.utils import Cleanup

import sys
import re
import os.path

from selenium import selenium

def clean_entry(x):
    return x.strip().replace("\n   ", " ")

def readable(x):
    return x.encode("ascii", "ignore")

def process_authors(entries):
    authors = []
    for entry in entries:
        last, first = entry[:2]
        #check to see if we have stupidness
        first_first = first.split()[0]
        match = re.compile("[A-Z]{2}").search(first_first)
        if match: #I fucking hate you papers
            initials = []
            for entry in first_first:
                initials.append(entry)
            first = " ".join(initials)
        else:
            first = clean_line(first)

        #capitalize last name
        last = capitalize_word(last)

        name = "%s, %s" % (last, first)
        authors.append(name)

    return authors

class ISIError(Exception):
    pass

def get_authors(x, inter_delim, intra_delim):
    try:
        #first check to see if we have parentheses
        regexp = "[\(](.*?)[\)]"
        matches = re.compile(regexp, re.DOTALL).findall(x)
        entries = []
        if matches:
            entries = map(lambda y: y.strip().split(","), matches)
        else:
            entries  = map(lambda y: y.strip().split(intra_delim), x.split(inter_delim))
        return process_authors(entries)
    except ValueError, error:
        sys.stderr.write("%s\n%s not properly split by intra='%s' inter='%s'\n" % (error, x, intra_delim, inter_delim))
        sys.stderr.write(traceback(error) + "\n")
        raise ISIError("Author list not formatted properly")

class JournalNotFoundError(Exception):
    pass

class ISIArticle: pass

class ISIParser(ArticleParser):

    def reset(self):
        ArticleParser.reset(self)

        #treat paragraph breaks as divisions
        self.start_p = self.start_div
        self.end_p = self.end_div

        self.citation = []
        self.title = []

    def citation_text(self, text):
        self.citation.append(text)

    def title_text(self, text):
        self.title.append(text)

    def start_a(self, attrs):
        if self.a_frame == "ref":
            self.text_frame = "title"
            self.a_frame = "title"

    def end_a(self):
        if self.a_frame == "title":
            title = " ".join(self.title)
            self.title = []
            self.article.set_title(title)
            self.text_frame = "citation"
            self.a_frame = None

    def _start_citedRef(self, attrs):
        self.article = ISIArticle()
        self.a_frame = "ref"
        self.text_frame = "citation"

    def _end_citedRef(self):
        citation = " ".join(self.citation) ; self.citation = []
        regexp = "([A-Z \-]+)(\d+)\s[:]\s(\d+)\s(\d+)"

        #delete the DOI part
        doi = re.compile("DOI\s.*?\s").search(citation)
        if doi:
            doitext = doi.group()
            citation = citation.replace(doitext, "")

        match = re.compile(regexp).search(citation)
        if not match:
            citation = citation.replace("\n", " ")
            sys.stderr.write("FAILURE %s\tImproper citation format\n" % citation)
            self.article = None
            self.a_frame = None
            self.text_frame = None
            return

        journal, volume, page, year = match.groups()

        from papers.utils import JournaCleanup
        name = "%s %s %s %s" % (journal, volume, page, year)
        try:
            self.article.set_journal(journal)
            self.article.set_volume(int(volume))
            self.article.set_pages(Page(page))
            self.article.set_year(int(year))
            self.articles.append(self.article)
        except JournalNotFoundError, error:
            sys.stderr.write("FAILURE %s\tJournal not found\n" % name)
        except ISIError, error:
            sys.stderr.write("FAILURE %s\tUnknown error\n" % name)

        self.text_frame = None
        self.a_frame = None
        self.article = None

class WOKObject:
    
    def die(self, msg):
        raise ISIError("%s -> %s %d %s" % (msg, self.author, self.year, self.title))

class WOKArticle(WOKObject):
    
    master = None

    def __init__(self, archive, block, master = None):
        self.archive = archive
        self.block = block
        self.article = self.archive.create_article()
        self.build_values()

        if master:
            self.master = master
        elif not self.master:
            self.master = MasterArchive()

    def get_papers_article(self):
        return self.article

    def set_value(self, regexp, attr, method=None, require=True):
        match = re.compile(regexp, re.DOTALL).search(self.block)
        if not match:
            if require:
                raise ISIError("Regular expression %s for attribute %s does not match block\n%s" % (regexp, attr, readable(self.block)))
            else:
                return

        value = match.groups()[0]
        if method:
            value = method(value)

        set = getattr(self.article, "set_%s" % attr)
        set(value)

    def build_values(self):
        try:
            self.set_value("Source[:]\s*(.*?)Vol", "journal", method = lambda x: x.strip())
        except ISIError: #might not have volume
            self.set_value("Source[:]\s*(.*?)Iss", "journal", method = lambda x: x.strip())
        self.set_value("Issue[:]\s*(\d+)", "issue", method=int, require=False)
        self.set_value("Volume[:]\s*(\d+)", "volume", method=int, require=False)

        try:
            self.set_value("Pages[:]\s*(\d+)[-P]", "start_page", method = Page)
            self.set_value("Pages[:]\s*\d+[-](\d+)", "end_page", method = Page, require=False)
        except ISIError: #sometimes just an article number
            self.set_value("Article\sNumber[:]\s*(\d+)\s+", "start_page", method = Page)
        #the gd monkeys at Thompson apparently decided that periods are just as good as spaces
        self.set_value("Author.*?[:](.*?)Source", "authors", method=lambda x: get_authors(x.replace(".", " "), ",", " "))
        self.set_value("Record from Web of Science.*?\s(.*?)more\soptions", "title", method=Cleanup.clean_title)
        self.set_value("Abstract[:](.*?)Addresses", "abstract", method=clean_entry, require=False)
        self.set_value("Published[:].*?\s(\d{4})", "year", method=int)
        self.set_value("DOI[:]\s+(.*?)[\n\s]", "doi", require=False)

    def add_notes(self, notes):
        self.article.set_notes(notes)

    def store(self, download = False):
        journal = self.article.get_journal()
        volume = self.article.get_volume()
        page = self.article.get_page()
        year = self.article.get_year()
        name = "%s %d %s (%d)" % (self.article.get_abbrev(), volume, page, year)

        local_match = self.archive.find_match(self.article)
        if local_match:
            sys.stdout.write("Already have article %s in local archive\n" % name)
            self.article = local_match
            return
        elif self.master.has(self.article):
            sys.stdout.write("Already have article %s in master archive\n" % name)
            return
        else:
            self.archive.add(self.article)

        if download:
            path = download_pdf(journal, volume=volume, page=page)
            if path:
                sys.stdout.write(" -> downloaded %s\n" % path)
                self.article.set_pdf(path)

        sys.stdout.write("Completed storage of %s\n" % name)


class WOKSearch(WOKObject):

    def __init__(self, journal=None, author=None, year=None, volume=None, page=None):
        from papers.pdfglobals import PDFGetGlobals as globals

        self.selenium = None
        self.journal = ""
        self.author = ""
        self.year = ""
        self.volume = ""
        self.page = ""
        self.title = ""

        if journal: self.journal = globals.get_journal(journal)
        if author: self.author = author
        if year: self.year = year
        if volume: self.volume = volume
        if page: self.page = page

    def reset(self, journal, author, year, volume, page):
        from papers.pdfglobals import PDFGetGlobals as globals
        self.journal = globals.get_journal(journal)
        self.author = author
        self.year = year
        self.volume = volume
        self.page = page
        self.title = None

    def isi_search(self):
        text = self.selenium.get_body_text()
        if "establish a new session" in text:
            self.selenium.click("link=establish a new session")
            self.selenium.wait_for_page_to_load("30000")

        self.selenium.select("select1", "label=Author")
        self.selenium.type("value(input1)", "%s" % self.author)
        self.selenium.select("select2", "label=Year Published")
        self.selenium.type("value(input2)", "%d" % self.year)
        if self.journal:
            self.selenium.select("select3", "label=Publication Name")
            self.selenium.type("value(input3)", "%s*" % self.journal.name)

        self.selenium.click("//input[@name='' and @type='image']")
        self.selenium.wait_for_page_to_load("30000")

        self.selenium.select("pageSize", "label=Show 50 per page")
        self.selenium.wait_for_page_to_load("30000")

        #figure out the title
        text = self.selenium.get_body_text()
        matches = re.compile("Title[:]\s*(.*?)\n(.*?)Times\sCited", re.DOTALL).findall(text)
        if not matches:
            msg_arr = ["\nAuthor=%s" % self.author]
            msg_arr.append("Year=%d" % self.year)
            msg_arr.append("Journal=%s" % self.journal.name)
            msg_arr.append("Could not find list entries on page\n%s" % readable(text))
            self.die("\n".join(msg_arr))
        return matches


    def die(self, msg):
        WOKObject.die(self, msg)

    def open_article(self, title):
        try:
            linktitle = title.strip()[1:-1]
            link = "link=*%s*" % linktitle
            self.selenium.click(link)
            self.selenium.wait_for_page_to_load("30000")
        except Exception, error:
            sys.stderr.write("Error on block:\n%s\n" % self.selenium.get_body_text())
            self.stop()
            self.die("%s\nCould not find title" % traceback(error))

    def open_references(self):
        text = self.selenium.get_body_text()
        match = re.compile("References[:]\s*(\d+)").search(text)
        if not match:
            self.die("Could not find references")

        nrefs = match.groups()[0]
        self.selenium.click("link=%s" % nrefs)
        self.selenium.wait_for_page_to_load("30000")

        return int(nrefs)

    def open_isi(self):
        self.selenium.open("/UA_GeneralSearch_input.do?product=UA&search_mode=GeneralSearch&SID=1CfoiNKJeadJefDa2M8&preferencesSaved=")

    def start(self):
        self.selenium = selenium("localhost", 4444, "*chrome", "http://apps.isiknowledge.com/")
        self.selenium.start()

    def stop(self):
        if self.selenium:
            self.selenium.stop()
        self.selenium = None

    def go_back(self):
        self.selenium.click("link=<< Back to results list")
        self.selenium.wait_for_page_to_load("30000")

    def go_to_next_page(self, number):
        self.selenium.click("//input[@name='' and @type='image' and @onclick='javascript:this.form.elements.page.value=%d;']" % number)
        self.selenium.wait_for_page_to_load("30000")

    def go_to_list_entry(self, id):
        self.selenium.click("xpath=//a[contains(@href,'%s')]" % id)
        self.selenium.wait_for_page_to_load("30000")

    def get_html(self):
        return self.selenium.get_html_source()

    def get_text(self):
        return self.selenium.get_body_text()

    def open(self):
        self.open_isi()

    def get_article(self, archive):
        block = self.get_text()
        article = WOKArticle(archive, block) 
        return article

class WOKParser(WOKObject):

    def __init__(self, archive, journal=None, author=None, year=None, volume=None, page=None, notes=None, download=False):
        self.archive = Archive(archive)
        self.search  = WOKSearch(journal, author, year, volume, page)
        self.notes = notes
        self.volume = volume
        self.page = page
        self.download = download

    def run_citedrefs(self):
        try:
            import time
            self.search.start()
            self.search.open()
            matches = self.search.isi_search()
            title = self.pick_article(matches)
            self.search.open_article(title)
            self.nrefs = self.search.open_references()

            #get all possible refs on this page 
            self.walk_references()

            #if there are more pages, go through those as well
            nstart = 31 
            onclick = 2
            while nstart < self.nrefs:
                self.search.go_to_next_page(onclick)
                self.walk_references()

                break #debug

                nstart += 30
                onclick += 1
            
            self.search.stop()
            self.archive.commit()
        except KeyboardInterrupt, error:
            self.search.stop()
            raise error
        except ISIError, error:
            self.search.stop()
            raise error

    def run_allrefs(self):
        try:
            import time
            self.search.start()
            self.search.open()
            matches = self.search.isi_search()
            for title, entry in matches:
                self.search.open_article(title)
                article = self.search.get_article(self.archive)
                article.add_notes(self.notes)
                article.store(self.download)
                self.search.go_back()
            self.search.stop()
            self.archive.commit()
        except ISIError, error:
            self.search.stop()
            raise error

    def die(self, msg):
        self.search.stop()
        WOKObject.die(self, msg)

    def walk_references(self):
        import time
        url_list = URLLister()
        url_list.feed(self.search.get_html())
        for name in url_list:
            link = url_list[name]
            if "CitedFullRecord" in link:
                self.process_article(link)

    def process_article(self, link):
        id = re.compile("isickref[=]\d+").search(link).group()
        self.search.go_to_list_entry(id)

        try:
            article = self.search.get_article(self.archive)
            article.add_notes(self.notes)
            article.store()
        except ISIError, error:
            sys.stderr.write("%s\n%s\n" % (error, traceback(error)))
        except Exception, error:
            sys.stderr.write("%s\n%s\n" % (error, traceback(error)))

        self.search.go_back()

    def pick_article(self, matches):
        for title, entry in matches:
            match = re.compile("Volume[:]\s*(\d+)").search(entry)
            if not match:
                self.die("Could not find volume for entry\n%s" % readable(text))
            volume = int(match.groups()[0])

            match = re.compile("Pages[:]\s*(\d+)").search(entry)
            if not match:
                match = re.compile("Article\sNumber[:]\s*(\d+)").search(entry)
            if not match:
                self.die("Could not find page for entry\n%s" % readable(text))

            page = Page(match.groups()[0])

            if volume == self.volume and page == self.page:
                return title


class SavedRecordParser:
    
    def __init__(self, name):
        self.archive = Archive(name)
        self.master = MasterArchive()
        self.lib = Library()

    def __iter__(self):
        return iter(self.archive)

    def __getitem__(self, index):
        return self.archive.__getitem__(index)

    def add_pdf(self, path):
        self.archive.add_pdf(path)

    def get_text(self, text, start, stop):
        regexp = "\n%s (.*?)\n%s " % (start.upper(), stop.upper())
        match = re.compile(regexp, re.DOTALL).search(text)
        if not match:
            return None

        return match.groups()[0].strip()

    def exclude_entry(self, entry, exclude):
        for exc in exclude:
            if exc in entry:
                return True
        return False

    def get_entry(self, attr, method=None, default=None, require=True, exclude=(), entries=()):
        set = getattr(self.article, "set_%s" % attr)
        str_arr = []
        for start, stop in entries:
            str_arr.append("%s->%s" % (start, stop))
            entry = self.get_text(self.block, start, stop)
            if entry and not self.exclude_entry(entry, exclude):
                if method:
                    entry = method(entry)

                set(entry)
                return

        if not default == None:
            set(default)
            return

        if require:
            sys.stderr.write("%s\n" % self.block)
            msg = "no %s for tags\n" % attr
            msg += "\n".join(str_arr)
            raise ISIError(msg)
            
    def feed(self, text, notes):
        journals = {}
        blocks = re.compile("PT\sJ(.*?)\nER", re.DOTALL).findall(text)
        for block in blocks:
            try:
                self.block = block
                self.article = self.archive.create_article()

                get_number = lambda x: re.compile("(\d+)").search(x).groups()[0] 
                get_page = lambda x: Page(get_number(x))
                #clean_title = lambda x: clean_line(clean_entry(x))
                clean_title = Cleanup.clean_title

                self.get_entry("journal", entries=(("so", "la"), ("so", "ab"), ("so", "sn")) )
                self.get_entry("volume", method=int, entries=(("vl", "is"), ("vl", "bp")) )
                self.get_entry("issue", method=lambda x: int(get_number(x)), require=False, entries=(("is", "bp"),) )
                self.get_entry("start_page", method=get_page, exclude=("art. no.",), entries=(("bp", "ep"), ("bp", "ut"), ("ar", "di"), ("ar", "ut")) )
                self.get_entry("end_page", method=get_page, require=False, entries=(("ep", "di"), ("ep", "ut")) )


                self.get_entry("authors", method=lambda x: get_authors(x, "\n", ","), entries=(("af", "ti"), ("au", "ti"), ("au", "so")))

                self.get_entry("title", method=clean_title, entries=(("ti", "so"),) )
                self.get_entry("abstract", method=clean_entry, require=False, entries=(("ab", "sn"),) )
                self.get_entry("year", method=int, entries=(("py", "vl"), ("py", "tc") ) )

                self.get_entry("doi", require=False, entries=(("di", "pg"), ("di", "ut"),("di", "er")) )

                self.article.set_notes(notes)
                
                journal = ISIArticle.get_journal(self.article.get_journal())
                volume = self.article.get_volume()
                page = self.article.get_page()
                name = "%s %d %s" % (journal, volume, page)
                if not self.master.has(self.article):
                    self.archive.test_and_add(self.article)
                else:
                    sys.stdout.write("%s exists in archive\n" % name)
                    continue
            except Exception, error:
                sys.stderr.write("%s\n%s\n" % (error, block))

def walkISI(files, archive, notes):
    from papers.pdfget import download_pdf

    parser = SavedRecordParser(archive)

    for file in files:
        text = open(file).read()
        parser.feed(text, notes)
        sys.stdout.write("%d new articles\n" % len(parser.archive))

        for article in parser:
            journal = article.get_journal()
            abbrev = article.get_abbrev()
            volume = article.get_volume()
            start = article.get_start_page() 
            name = "%s %d %s" % (abbrev, volume, start)
            sys.stdout.write("Downloading %s" % name)

            path = name + ".pdf"
            if os.path.isfile(path):
                sys.stdout.write(" -> exists %s" % path)
                article.set_pdf(path)
                continue

            #check to see if we already have it
            path = download_pdf(ISIArticle.get_journal(journal), volume, 0, start) #don't require issue
            if path:
                sys.stdout.write(" -> %s" % path)
                article.set_pdf(path)
            else:
                sys.stdout.write(" -> FAILED")
    parser.archive.commit()
                

    


if __name__ == "__main__":
    archive = Archive("test") 
    block = u"""
Sign In     My EndNote Web      My ResearcherID     My Citation Alerts      My Saved Searches       Log Out      Help   
    
     
                                    
                                         Search      Search History      Marked List (0)    


                                         ALL DATABASES
                                          
                                            
                                            << Back to results list     
                                                     Record 1  of  2        
                                                     Record from Web of Science®


                                                        
                                                        Unique homonuclear multiple bonding in main group compounds
                                                            
                                                                    more options
                                                                    Author(s): Wang YZ (Wang, Yuzhong)1, Robinson GH (Robinson, Gregory H.)1
                                                                    Source: CHEMICAL COMMUNICATIONS    Issue: 35    Pages: 5201-5213    Published: 2009  
                                                                    Times Cited: 8     References: 152     Citation Map     
                                                                    Abstract: Significant progress in the chemistry of main group compounds (group 13, 14, and 15) containing homonuclear multiple bonds has been made over the past three decades. This feature article addresses the unique structural and bonding motifs of these compounds, with a particular emphasis on both iconic molecules and recent novel discoveries.
                                                                    Document Type: Review
                                                                    Language: English
                                                                    KeyWords Plus: SI=SI DOUBLE-BOND; ELECTRON PI-BOND; DENSITY-FUNCTIONAL THEORY; RAY CRYSTAL-STRUCTURE; GALLIUM TRIPLE BOND; B=B DOUBLE-BOND; GROUP ELEMENTS; MOLECULAR-STRUCTURE; TERPHENYL LIGANDS; STABLE COMPOUND
                                                                    Reprint Address: Robinson, GH (reprint author), Univ Georgia, Dept Chem, Athens, GA 30602 USA
                                                                    Addresses: 
                                                                    1. Univ Georgia, Dept Chem, Athens, GA 30602 USA
                                                                    E-mail Addresses: robinson@chem.uga.edu
                                                                    Funding Acknowledgement:
                                                                    Funding Agency  Grant Number
                                                                    National Science Foundation      
                                                                    [Show funding text]   
                                                                    Publisher: ROYAL SOC CHEMISTRY, THOMAS GRAHAM HOUSE, SCIENCE PARK, MILTON RD, CAMBRIDGE CB4 0WF, CAMBS, ENGLAND
                                                                    IDS Number: 488CO
                                                                    ISSN: 1359-7345
                                                                    DOI: 10.1039/b908048a

                                                                    Cited by: 8
                                                                    This article has been cited 8 times (from Web of Science).
                                                                    Fischer RC, Power PP  pi-Bonding and the Lone Pair Effect in Multiple Bonds Involving Heavier Main Group Elements: Developments in the New Millennium  CHEMICAL REVIEWS  110  7  3877-3923  JUL 2010
                                                                    Gerdes C, Muller T  News from Silicon: An Isomer of Hexasilabenzene and A Metal-Silicon Triple Bond  ANGEWANDTE CHEMIE-INTERNATIONAL EDITION  49  29  4860-4862  2010
                                                                    Wehmschulte RJ  At Last: A Stable Univalent Gallium Cation  ANGEWANDTE CHEMIE-INTERNATIONAL EDITION  49  28  4708-4709  2010
                                                                    [  view all 8 citing articles  ]


                                                                    Related Records:
                                                                    Find similar records based on shared references (from Web of Science).
                                                                    [ view related records ]

                                                                    References: 152
                                                                    View the bibliography of this record (from Web of Science).

                                                                    Additional information
                                                                    View the journal's impact factor (in Journal Citation Reports)
                                                                    View the journal's Table of Contents (in Current Contents Connect)
                                                                    View this record in other databases:
                                                                    View citation data (in Web of Science)
                                                                        

                                                                            


                                                                            << Back to results list     
                                                                                     Record 1  of  2        
                                                                                     Record from Web of Science®


                                                                                     Output Record
                                                                                        
                                                                                        Step 1:
                                                                                          Authors, Title, Source
                                                                                                  plus Abstract
                                                                                                   Full Record
                                                                                                           plus Cited Reference     
                                                                                                           Step 2: [How do I export to bibliographic management software?]
                                                                                                                     
                                                                                                                      

    """
    master = Archive("nullmaster")
    article = WOKArticle(archive, readable(block), master)
    article.store()


