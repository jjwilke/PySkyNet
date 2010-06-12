from pdfget import ArticleParser, PDFArticle, Page
from papers.index import Library
from papers.archive import Archive, MasterArchive
from htmlexceptions import HTMLException
from utils.RM import save, load, clean_line, capitalize_word
from webutils.htmlparser import URLLister
import sys
import re
import os.path

from selenium import selenium

def find_in_library(library, volume, page):
    for year in library:
        path = library.find(year, volume, page)
        if path:
            return path
    return None

def clean_entry(x):
    return x.strip().replace("\n   ", " ")

def process_authors(entries):
    authors = []
    for last, first in entries:
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

def get_authors(x, inter_delim, intra_delim):
    entries  = map(lambda y: y.strip().split(intra_delim), x.split(inter_delim))
    return process_authors(entries)

class ISIError(Exception):
    pass

class JournalNotFoundError(Exception):
    pass

class ISIArticle:

    journal_map = {
        "angewandte chemie-international edition" : "ange",
        "chemical physics" : "chemphys",
        "physics reports" : "physrep",
        "physics reports-review section of physics letters" : "physrep",
        "molecular physics" : "molphys",
        "journal of computational physics" : "jcompphys",
    }

    def get_journal(cls, journal):
        try:
            journal = cls.journal_map[journal.lower()]
            return journal
        except KeyError:
            name = journal.lower().replace("of","").replace("the","").replace("and", "").replace("-"," ")
            initials = map(lambda x: x[0], name.strip().split())
            return "".join(initials)
    get_journal = classmethod(get_journal)

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
        import re
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
        name = "%s %s %s %s" % (journal, volume, page, year)
        try:
            self.article.set_journal(journal.strip())
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

class WOKParser:

    def __init__(self, archive, journal, author, year, title):
        self.author = author
        self.journal = journal
        self.year = year
        self.title = title
        self.archive = Archive(archive)
        self.master = MasterArchive()
        self.lib = Library()

    def test(self):
        self.block = u"Sign In My EndNote Web My ResearcherID My Citation Alerts My Saved Searches Log Out Help    Search Search History Marked List ALL DATABASES << Back to results list Record 1  of  1 Record from Web of Science Gaussian-3 theory using reduced Moller-Plesset order more options Author(s): Curtiss LA, Redfern PC, Raghavachari K, Rassolov V, Pople JA Source: JOURNAL OF CHEMICAL PHYSICS    Volume: 110    Issue: 10    Pages: 4703-4709    Published: MAR 8 1999   Times Cited: 589     References: 15     Citation Map      Abstract: A variation of Gaussian-3 (G3) theory is presented in which the basis set extensions are obtained at the second-order Moller-Plesset level. This method, referred to as G3(MP2) theory, is assessed on 299 energies from the G2/97 test set [J. Chem. Phys. 109, 42 (1998)]. The average absolute deviation from experiment of G3(MP2) theory for the 299 energies is 1.30 kcal/mol and for the subset of 148 neutral enthalpies it is 1.18 kcal/mol. This is a significant improvement over the related G2(MP2) theory [J. Chem. Phys. 98, 1293 (1993)], which has an average absolute deviation of 1.89 kcal/mol for all 299 energies and 2.03 kcal/mol for the 148 neutral enthalpies. The corresponding average absolute deviations for full G3 theory are 1.01 and 0.94 kcal/mol, respectively. The new method provides significant savings in computational time compared to G3 theory and, also, G2(MP2) theory. (C) 1999 American Institute of Physics. [S0021-9606(99)30309-3]. Document Type: Article Language: English KeyWords Plus: ENERGIES Reprint Address: Curtiss, LA (reprint author), Argonne Natl Lab, Div Chem, 9700 S Cass Ave, Argonne, IL 60439 USA Addresses: 1. Argonne Natl Lab, Div Chem, Argonne, IL 60439 USA 2. Argonne Natl Lab, Div Sci Mat, Argonne, IL 60439 USA 3. AT&T Bell Labs, Lucent Technol, Murray Hill, NJ 07974 USA 4. Northwestern Univ, Dept Chem, Evanston, IL 60208 USA Publisher: AMER INST PHYSICS, CIRCULATION FULFILLMENT DIV, 500 SUNNYSIDE BLVD, WOODBURY, NY 11797-2999 USA Subject Category: Physics, Atomic, Molecular & Chemical IDS Number: 170XG ISSN: 0021-9606 Cited by: 589 This article has been cited 589 times (from Web of Science). Ali MA, Rajakumar B  Kinetics of OH radical reaction with CF3CHFCH2F (HFC-245eb) between 200 and 400 K: G3MP2, G3B3 and transition state theory calculations  JOURNAL OF MOLECULAR STRUCTURE-THEOCHEM  949  1-3  73-81  JUN 15 2010 Verevkin SP, Emel'yanenko VN, Hopmann E, et al.  Thermochemistry of ionic liquid-catalysed reactions. Isomerisation and transalkylation of tert-alkyl-benzenes. Are these systems ideal?  JOURNAL OF CHEMICAL THERMODYNAMICS  42  6  719-725  JUN 2010 Zhang IY, Wu JM, Luo Y, et al.  Trends in R-X Bond Dissociation Energies (R-center dot = Me, Et, i-Pr, t-Bu, X-center dot = H, Me, Cl, OH)  JOURNAL OF CHEMICAL THEORY AND COMPUTATION  6  5  1462-1469  MAY 2010 [  view all 589 citing articles  ] Related Records: Find similar records based on shared references (from Web of Science). [ view related records ] References: 15 View the bibliography of this record (from Web of Science). Additional information View author biographies (in ISI HighlyCited.com) View the journal's impact factor (in Journal Citation Reports) View the journal's Table of Contents (in Current Contents Connect)   << Back to results list Record 1  of  1 Record from Web of Science Output Record Step 1: Authors, Title, Source plus Abstract Full Record Step 2: [How do I export to bibliographic management software?] Save to other Reference Software Save to BibTeX Save to HTML Save to Plain Text Save to Tab-delimited (Win) Save to Tab-delimited (Mac)"
        self.article = self.archive.create_article()
        self.build_values()
        print self.article

    def open_isi(self):
        self.selenium = selenium("localhost", 4444, "*chrome", "http://apps.isiknowledge.com/")
        self.selenium.start()
        self.selenium.open("/UA_GeneralSearch_input.do?product=UA&search_mode=GeneralSearch&SID=1CfoiNKJeadJefDa2M8&preferencesSaved=")

    def run(self):
        self.open_isi()
        self.find_article()
        self.open_article()
        self.walk_references()

    def find_article(self):
        self.selenium.select("select1", "label=Author")
        self.selenium.type("value(input1)", "%s" % self.author)
        self.selenium.select("select2", "label=Year Published")
        self.selenium.type("value(input2)", "%d" % self.year)
        self.selenium.select("select3", "label=Publication Name")
        self.selenium.type("value(input3)", "%s*" % self.journal)
        self.selenium.click("//input[@name='' and @type='image']")
        self.selenium.wait_for_page_to_load("30000")

    def die(self, msg):
        self.selenium.stop()
        sys.exit("%s -> %s %d %s" % (msg, self.author, self.year, self.title))

    def open_article(self):
        try:
            self.selenium.click("link=*%s*" % self.title)
            self.selenium.wait_for_page_to_load("30000")
        except Exception, error:
            self.die("Could not find title")

        text = self.selenium.get_body_text()
        match = re.compile("References[:]\s*(\d+)").search(text)
        if not match:
            self.die("Could not find references")

        nrefs = match.groups()[0]
        self.selenium.click("link=%s" % nrefs)
        self.selenium.wait_for_page_to_load("30000")

    def walk_references(self):
        url_list = URLLister()
        url_list.feed(self.selenium.get_html_source())
        for name in url_list:
            link = url_list[name]
            if "CitedFullRecord" in link:
                self.process_article(link)
            return

    def set_value(self, regexp, attr, method=None, require=True):
        match = re.compile(regexp, re.DOTALL).search(self.block)
        if not match:
            if require:
                raise ISIError
            else:
                return

        value = match.groups()[0]
        if method:
            value = method(value)

        set = getattr(self.article, "set_%s" % attr)
        set(value)

    def build_values(self):
        self.set_value("Source[:]\s*(.*?)Vol", "journal", method = lambda x: x.strip())
        self.set_value("Volume[:]\s*(\d+)", "volume", method=int)
        self.set_value("Issue[:]\s*(\d+)", "issue", method=int, require=False)
        self.set_value("Pages[:]\s*(\d+)[-P]", "start_page", method = Page)
        self.set_value("Pages[:]\s*\d+[-](\d+)", "end_page", method = Page, require=False)
        self.set_value("Author.*?[:](.*?)Source", "authors", method=lambda x: get_authors(x, ",", " "))
        self.set_value("Record from Web of Science.*?\s(.*?)more\soptions", "title", method=clean_line)
        self.set_value("Abstract[:](.*?)Addresses", "abstract", method=clean_entry)
        self.set_value("Published[:]\s*[A-Z]+\s*\d+\s*(\d+)", "year", method=int)

    def go_back(self):
        self.selenium.click("link=<< Back to results list")
        self.selenium.wait_for_page_to_load("30000")

    def process_article(self, link):
        id = re.compile("isickref[=]\d+").search(link).group()
        self.selenium.click("xpath=//a[contains(@href,'%s')]" % id)
        self.selenium.wait_for_page_to_load("30000")

        self.article = self.archive.create_article()
        self.block = self.selenium.get_body_text()

        try:
            self.build_values()
        except ISIError:
            self.article = None
            self.go_back()
            return
        
        if not self.master.has(self.article):
            self.archive.test_and_add(self.article)
        else:
            print "Already have article %s" % path
            self.article = None
            self.go_back()
            return

        path = download_pdf(journal, volume=volume, page=page)
        if path:
            self.article.set_pdf(path)

        self.article = None
        self.go_back()


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
            sys.exit(msg)
            
    def feed(self, text, notes):
        journals = {}
        blocks = re.compile("PT\sJ(.*?)\nER", re.DOTALL).findall(text)
        for block in blocks:
            self.block = block
            self.article = self.archive.create_article()

            get_number = lambda x: re.compile("(\d+)").search(x).groups()[0] 
            get_page = lambda x: Page(get_number(x))
            clean_title = lambda x: clean_line(clean_entry(x))

            self.get_entry("journal", entries=(("so", "ab"), ("so", "sn")) )
            self.get_entry("volume", method=int, entries=(("vl", "is"), ("vl", "bp")) )
            self.get_entry("issue", method=lambda x: int(get_number(x)), require=False, entries=(("is", "bp"),) )
            self.get_entry("start_page", method=get_page, exclude=("art. no.",), entries=(("bp", "ep"), ("bp", "ut"), ("ar", "di"), ("ar", "ut")) )
            self.get_entry("end_page", method=get_page, require=False, entries=(("ep", "di"), ("ep", "ut")) )


            self.get_entry("authors", method=lambda x: get_authors(x, "\n", ","), entries=(("af", "ti"), ("au", "ti")) )

            self.get_entry("title", method=clean_title, entries=(("ti", "so"),) )
            self.get_entry("abstract", method=clean_entry, require=False, entries=(("ab", "sn"),) )
            self.get_entry("year", method=int, entries=(("py", "vl"),) )

            self.article.set_notes(notes)
            
            volume = self.article.get_volume()
            page = self.article.get_page()
            path = find_in_library(self.lib, volume, page)
            if path: #already in library
                print "%s exists in archive" % path
                continue
        
            journal = ISIArticle.get_journal(self.article.get_journal())
            if not self.master.has(self.article):
                self.archive.test_and_add(self.article)

        """
            journal = self.get_text(block, "so", "ab")
            if not journal: journal = self.get_text(block, "so", "sn")
            if not journal:
                print block
                sys.exit("no journal")
            article.set_journal(journal)

            volume = self.get_text(block, "vl", "is")
            if not volume: volume = self.get_text(block, "vl", "bp")
            if not volume:
                print block
                sys.exit("no volume")
            volume = int(volume)
            article.set_volume(volume)

            issue = self.get_text(block, "is", "bp")
            if not issue:
                issue = 0
            else:
                issue = int(re.compile("(\d+)").search(issue).groups()[0])
            article.set_issue(issue)

            page = self.get_text(block, "bp", "ep")
            if not page: page = self.get_text(block, "bp", "ut")
            if not page or "art. no." in page: page = self.get_text(block, "ar", "di")
            if not page: page = self.get_text(block, "ar", "ut")
            if not page:
                print block
                sys.exit("no page")
            page = Page(page)
            article.set_pages(page)

            journals[journal] = 1
            
        journals = journals.keys()
        journals.sort()
        print "\n".join(journals)
        sys.exit()
        """

def find_in_folder(pdfs, journal, volume, page):
    abbrev = ISIArticle.get_journal(journal)
    for pdf in pdfs:
        if abbrev in pdf and "%d" % volume in pdf and str(page) in pdf:
            return pdf
    return None
        
def walkISI(files, archive, notes):
    from webutils.pdfget import download_pdf

    lib = Library()
    parser = SavedRecordParser(archive)
    pdfs = [elem for elem in os.listdir(".") if elem.endswith("pdf")]

    for file in files:
        text = open(file).read()
        parser.feed(text, notes)
        print "%d new articles" % len(parser.archive)

        for article in parser:
            journal = article.get_journal()
            abbrev = article.get_abbrev()
            volume = article.get_volume()
            start = article.get_start_page() 
            name = "%s %d %s" % (abbrev, volume, start)
            print "Downloading %s" % name,

            path = find_in_folder(pdfs, journal, volume, start)
            if path:
                print " -> exists %s" % path
                article.set_pdf(path)
                continue

            path = name + ".pdf"
            if os.path.isfile(path):
                print " -> exists %s" % path
                article.set_pdf(path)
                continue

            #check to see if we already have it
            path = download_pdf(ISIArticle.get_journal(journal), volume, 0, start) #don't require issue
            if path:
                print " -> %s" % path
                article.set_pdf(path)
            else:
                print " -> FAILED"
    parser.archive.commit()
                

    


