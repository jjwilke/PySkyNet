from papers.pdfget import ArticleParser, PDFArticle, Page, download_pdf
from papers.index import Library
from papers.archive import Archive, MasterArchive
from papers.utils import Cleanup
from skynet.utils.utils import save, load, clean_line, capitalize_word, traceback
from webutils.htmlexceptions import HTMLException
from webutils.htmlparser import URLLister
from papers.utils import Cleanup
from skynet.socket.server import ServerRequest, ServerAnswer, Server
from papers.archive import ArchiveRequest

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
        if len(entry) == 1: #hmm, chinese name
            entry = map(lambda x: x.strip(), entry[0].split())
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

    def __init__(self, msg, block = ""):
        Exception.__init__(self, msg)
        self.block = readable(block)

def get_authors(x, inter_delim = ",", intra_delim = " "):
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
        sys.stderr.write("ERROR: %s\n%s not properly split by intra='%s' inter='%s'\n" % (error, x, intra_delim, inter_delim))
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

class WOKObject: pass

class WOKArticle(WOKObject):
    
    def __init__(self, archive, block):
        self.archive = archive
        self.block = block
        self.article = self.archive.create_article()
        self.build_values()

    def get_papers_article(self):
        return self.article

    def set_value(self, regexp, attr, method=None, require=True):
        match = re.compile(regexp, re.DOTALL).search(self.block)
        if not match:
            if require:
                raise ISIError("Regular expression %s for attribute %s does not match block\n" % (regexp, attr), self.block)
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
        self.set_value("Published[:].*?\s*(\d{4})", "year", method=int)
        self.set_value("DOI[:]\s+(.*?)[\n\s]", "doi", require=False)

    def add_notes(self, notes):
        self.article.set_notes(notes)

    def add_keywords(self, keywords):
        self.article.set_keywords(keywords)

    def store(self, download = False):
        journal = self.article.get_journal()
        volume = self.article.get_volume()
        page = self.article.get_page()
        year = self.article.get_year()
        name = "%s %d %s (%d)" % (self.article.get_abbrev(), volume, page, year)

        local_match = self.archive.find_match(self.article)
        if local_match:
            download = download and not local_match.has_pdf() #set to download if we don't have pdf
            self.article = local_match
            sys.stdout.write("Already have article %s in local archive\n" % name)

        
        master_match = None
        if not local_match:
            artreq = ArchiveRequest(self.article)
            master_match = artreq.run() #query master
            if master_match:
                sys.stdout.write("Already have article %s in master archive\n" % name)
                download = download and not master_match.has_pdf() #set to download if we don't have pdf
                self.article = master_match
        
        if not local_match and not master_match:
            self.archive.add(self.article)

        if download:
            path = download_pdf(journal, volume=volume, page=page)
            if path:
                sys.stdout.write(" -> downloaded %s\n" % path)
                self.article.set_pdf(path)

        sys.stdout.write("Completed storage of %s\n" % name)

class WOKArticleSearch:

    def __init__(self, title=None, source=None, volume=None, issue=None, page=None, year=None):
        self.title = title
        self.journal = source.lower()
        self.volume = volume
        self.issue = issue
        self.page = page
        self.year = year

class ISIVoid: #pseudo nonetype
    
    def __len__(self):
        return 0

class ISIAnswer(ServerAnswer):

    def __init__(self):
        ServerAnswer.__init__(self, ISIServer.ANSWER_PORT)

class ISIServerCommand:
    
    def __init__(self, method, args = None):
        self.method = method
        self.args = args

class ISIServer(Server):

    REQUEST_PORT = 22349
    ANSWER_PORT = 22350
    
    def __init__(self):
        Server.__init__(self, self.REQUEST_PORT, self.ANSWER_PORT)
        devnull = open("/dev/null", "w")
        sys.stdout = devnull
        #start selenium running
        import os
        import time
        self.selenium = selenium("localhost", 4444, "*chrome", "http://apps.isiknowledge.com/")
        self.selenium.start()
        self.go_home()
        self.run()

    def go_home(self):
        self.selenium.open("/UA_GeneralSearch_input.do?product=UA&search_mode=GeneralSearch&SID=1CfoiNKJeadJefDa2M8&preferencesSaved=")
        text = self.selenium.get_body_text()
        if "establish a new session" in text:
            self.selenium.click("link=establish a new session")
            self.selenium.wait_for_page_to_load("30000")

    def process(self, obj):
        ret = ISIVoid() #default nothing
        try:
            method = getattr(self, obj.method)
            sys.stdout.write("Running %s\n" % obj.method)
            if obj.args:
                ret = method(obj.args)
            else:
                ret = method()
        except Exception, error:
            sys.stderr.write("ERROR: %s\n%s\n" % (traceback(error), error))

        return ret

    def add_field(self):
        pass

    def isi_search(self, search):
        fields = search.fields
        self.go_home()
        text = self.selenium.get_body_text()
        nfields = text.count("Example:")
        #count the number of occurrences of Example in text
        #we currently have 3 fields
        for i in range(nfields, len(fields) + 1): #add another field
            self.add_field()

        i = 1
        for field in fields:
            self.selenium.select("select%d" % i, "label=%s" % field.name)
            self.selenium.type("value(input%d)" % i, "%s" % field.value)
            i += 1
            
        self.selenium.click("//input[@name='' and @type='image']")
        self.selenium.wait_for_page_to_load("30000")

        self.selenium.select("pageSize", "label=Show 50 per page")
        self.selenium.wait_for_page_to_load("1000")

    def get_articles(self):
        #figure out the title
        text = self.selenium.get_body_text()
        matches = re.compile("Title[:]\s*(.*?)\n(.*?)Times\sCited", re.DOTALL).findall(text)
        if not matches:
            raise ISIError("No valid titles appear on this search page")

        def get_value(entry, name, regexp, fxn, require = True):
            match = re.compile(regexp).search(entry)
            if not match:
                if require:
                    raise ISIError("Could not find %s for entry\n%s" % (name, readable(text)))
                else:
                    return None
            try:
                val = fxn(match.groups()[0])
                return val
            except Exception, error:
                if require:
                    raise ISIError("Could not find properly formattaed %s for entry\n%s" % (name, readable(text)))
                else:
                    return None

        articles = []
        for title, entry in matches:
            try:
                volume = get_value(entry, "volume", "Volume[:]\s*(\d+)", int, require=False)
                issue = get_value(entry, "issue", "Issue[:]\s*(\d+)", int)
                if not volume:
                    volume = issue
                    issue = 0

                page = get_value(entry, "page", "Pages[:]\s*(\d+)", Page, require=False)
                if not page:
                    page = get_value(entry, "page", "Article\sNumber[:]\s*(\d+)", Page, require=True)
                year = get_value(entry, "year", "Published[:].*?\s*(\d{4})", int)

                source = get_value(entry, "source", "Source[:]\s*(.*?)Vol", lambda x: x.strip(), require=False)
                if not source:
                    source = get_value(entry, "source", "Source[:]\s*(.*?)Iss", lambda x: x.strip())

                article = WOKArticleSearch(title=title, volume=volume, issue=issue, year=year, source=source, page=page)
                articles.append(article)
            except ISIError, error:
                sys.stderr.write("ERROR: %s\n" % error)
        return articles

    def open_article(self, title):
        try:
            linktitle = title.strip()[1:-1]
            link = "link=*%s*" % linktitle
            self.lasturl = self.selenium.browserURL
            self.selenium.click(link)
            self.selenium.wait_for_page_to_load("30000")
        except Exception, error:
            sys.stderr.write("ERROR: Error on title %s:\n%s\n" % (readable(title), readable(self.selenium.get_body_text())))
            raise ISIError("%s\nCould not find title" % traceback(error))

    def open_references(self):
        text = self.selenium.get_body_text()
        match = re.compile("References[:]\s*(\d+)").search(text)
        if not match:
            self.die("Could not find references")

        nrefs = match.groups()[0]
        self.selenium.click("link=%s" % nrefs)
        self.selenium.wait_for_page_to_load("30000")
        return int(nrefs)

    def go_back(self):
        self.selenium.go_back()
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


class WOKField: 
    name = None

    def __init__(self, value):
        self.value = str(value)

    def __str__(self):
        return str(self.value)

    def get(cls, key, value):
        key = key.lower()
        if not key in cls.fields:
            return None
        
        return cls.fields[key](value)
    get = classmethod(get)

class Journal(WOKField):
    name = "Publication Name"

    def __init__(self, value):
        from papers.pdfglobals import PDFGetGlobals as globals
        self.value = globals.get_journal(value)

class Year(WOKField):
    name = "Year Published"

class Author(WOKField):
    name = "Author"

class Title(WOKField):
    name = "Title"

WOKField.fields = {
    "journal" : Journal,
    "year" : Year,
    "author" : Author,
    "title" : Title,
}

class WOKSearch(WOKObject):

    def __init__(self, **kwargs):
        self.fields = []
        for key, value in kwargs.items():
            field = WOKField.get(key, value)
            if field:
                self.fields.append(field)
                setattr(self, key, str(field))
            else:
                setattr(self, key, value)


class WOKParser(WOKObject, ServerRequest):

    def __init__(self, archive, journal=None, author=None, year=None, volume=None, page=None, notes=None, download=False, keywords=None):
        ServerRequest.__init__(self, ISIServer.REQUEST_PORT, ISIAnswer)
        self.archive = Archive(archive)
        self.download = download
        self.notes = notes
        self.keywords = keywords
        self.kwargs = {}
        if journal: self.kwargs["journal"] = journal
        if author: self.kwargs["author"] = author
        if year: self.kwargs["year"] = year
        if volume: self.kwargs["volume"] = volume
        if page: self.kwargs["page"] = page
        self.search = WOKSearch(**self.kwargs)

    def run(self, method, args=None):
        cmd = ISIServerCommand(method, args)
        response = ServerRequest.run(self, cmd)
        return response

    def pick_article(self, articles):
        for article in articles:
            foundmatch = True
            for key, value in self.kwargs.items():
                if not hasattr(article, key): #don't use this for matching
                    continue

                match = getattr(article, key)
                if str(value).lower() != str(match).lower():
                    foundmatch = False
                    break;
            
            if foundmatch:
                return article

    def store_article(self):
        block = self.run("get_text")
        article = WOKArticle(self.archive, block) 
        if article:
            article.add_notes(self.notes)
            article.add_keywords(self.keywords)
            article.store(self.download)
        return article
                
    def run_citedrefs(self):
        try:
            import time
            void = self.run("isi_search", self.search)
            articles = self.run("get_articles")

            title = ""
            article = self.pick_article(articles)
            if not article:
                raise ISIError("Could not find article with given specifications");

            self.run("open_article", article.title)
            nrefs = self.run("open_references")

            #get all possible refs on this page 
            self.walk_references()

            #if there are more pages, go through those as well
            nstart = 31 
            onclick = 2
            while nstart < nrefs:
                self.run("go_to_next_page", onclick)
                self.walk_references()

                nstart += 30
                onclick += 1
            
            self.archive.commit()
        except KeyboardInterrupt, error:
            raise error
        except ISIError, error:
            sys.stderr.write("ERROR: %s\nFailed on block:\n%s\n" % (error, error.block))
            raise error

    def run_getref(self):
        try:
            void = self.run("isi_search", self.search)
            articles = self.run("get_articles")

            if not articles:
                raise ISIError("Could not find article with given specifications");


            title = ""
            article = self.pick_article(articles)
            if not article:
                raise ISIError("Could not find article with given specifications");

            self.run("open_article", article.title)
            article = self.store_article()
            if not article:
                raise ISIError("No article found")
            self.archive.commit()
        except KeyboardInterrupt, error:
            self.archive.commit()
            raise error
        except ISIError, error:
            self.archive.commit()
            sys.stderr.write("ERROR: %s\nFailed on block:\n%s\n" % (error, error.block))
            raise error

    def run_allrefs(self):
        try:
            void = self.run("isi_search", self.search)
            articles = self.run("get_articles")
            if not articles:
                raise ISIError("no articles found")
            for article in articles:
                try:
                    self.run("open_article", article.title)
                    article = self.store_article()
                    if not article:
                        continue
                except ISIError, error: #don't stop because of one error
                    sys.stderr.write("ERROR: %s\nFailed on block:\n%s\n" % (error, error.block))
                except Exception, error:
                    sys.stderr.write("Unknown error:\n%s\n%s\n" % (traceback(error), error))
                self.run("go_back")
        except Exception, error:
            self.archive.commit()
            sys.stderr.write("ERROR: %s\n%s\n" % (traceback(error), error))
            raise error

    def walk_references(self):
        import time
        url_list = URLLister()
        text = self.run("get_html")
        url_list.feed(text)
        for name in url_list:
            link = url_list[name]
            if "CitedFullRecord" in link:
                self.process_article(link)

    def process_article(self, link):
        id = re.compile("isickref[=]\d+").search(link).group()
        self.run("go_to_list_entry", id)

        try:
            article = self.store_article()
        except ISIError, error:
            sys.stderr.write("ERROR: %s\n%s\n" % (error, traceback(error)))
        except Exception, error:
            sys.stderr.write("ERROR: %s\n%s\n" % (error, traceback(error)))

        self.run("go_back")

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
            sys.stderr.write("ERROR: %s\n" % self.block)
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
                sys.stderr.write("ERROR: %s\n%s\n" % (error, block))

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
    article = WOKArticle(archive, readable(block))
    article.store()
    article = WOKArticle(archive, readable(block))
    article.store()
    #x = "Wang HY (Wang Hong-Yan), Li XB (Li Xi-Bo), Tang YJ (Tang Yong-Jian), King RB (King, R. Bruce), Schaefer HF (Schaefer, Henry F., III)"
    #print get_authors(x, intra_delim=" ", inter_delim=",")


