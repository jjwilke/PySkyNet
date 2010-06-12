from pdfget import ArticleParser, PDFArticle, Page
from papers.index import Library
from papers.archive import Archive
from htmlexceptions import HTMLException
from utils.RM import save, load, clean_line, capitalize_word
import sys
import re
import os.path

from selenium import selenium

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

    def open_isi(self):
        self.selenium = selenium("localhost", 4444, "*chrome", "http://apps.isiknowledge.com/")
        self.selenium.start()
        self.selenium.open("/UA_GeneralSearch_input.do?product=UA&search_mode=GeneralSearch&SID=1CfoiNKJeadJefDa2M8&preferencesSaved=")

        print self.selenium.get_body_text()
        self.selenium.stop()
        sys.exit()

    def run(self):
        self.open_isi()
        self.find_article()
        self.open_article()

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
        url_list.feed(self.get_html_source())
        for name in url_list:
            link = url_list[name]
            if "CitedFullRecord" in link:

    def process_article(self, link):
        id = re.compile("isickref[=]\d+").search(link).group()
        self.selenium.click("xpath=//a[contains(@href,'%s')]" % id
        self.selenium.wait_for_page_to_load("30000")
        print self.selenium.get_body_text()
        self.die("")
            
        

def find_in_library(library, volume, page):
    for year in library:
        path = library.find(year, volume, page)
        if path:
            return path
    return None

class SavedRecordParser:
    
    def __init__(self, name):
        self.archive = Archive(name)
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
            clean_entry = lambda x: x.strip().replace("\n   ", " ")
            clean_title = lambda x: clean_line(clean_entry(x))

            self.get_entry("journal", entries=(("so", "ab"), ("so", "sn")) )
            self.get_entry("volume", method=int, entries=(("vl", "is"), ("vl", "bp")) )
            self.get_entry("issue", method=lambda x: int(get_number(x)), require=False, entries=(("is", "bp"),) )
            self.get_entry("start_page", method=get_page, exclude=("art. no.",), entries=(("bp", "ep"), ("bp", "ut"), ("ar", "di"), ("ar", "ut")) )
            self.get_entry("end_page", method=get_page, require=False, entries=(("ep", "di"), ("ep", "ut")) )

            def get_authors(x):
                entries  = map(lambda y: y.strip(), x.split("\n"))

                authors = []
                for entry in entries:
                    last, first = entry.split(",")
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
                    print first_first, name
                    authors.append(name)

                return authors

            self.get_entry("authors", method=get_authors, entries=(("af", "ti"), ("au", "ti")) )

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
                

    


