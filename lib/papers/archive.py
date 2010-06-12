from xml.dom.minidom import parse, Document
import shutil
import os.path
import os
import sys
from webutils.pdfget import Page
from utils.RM import clean_line, capitalize_word

class Article:

    journaltag = "secondary-title"
    abbrevtag = "full-title"
    volumetag = "volume"
    issuetag = "number"
    authortag = "author"
    yeartag = "year"
    pagestag = "pages"
    titletag = "title"
    pdftag = "url"
    notestag = "notes"
    abstracttag = "abstract"

    erase = [
        "and",
        "of",
        "the",
    ]

    keep = [
        "nature",
        "science",
    ]

    abbrevs = {
        "zeitsch" : "zeit",
        "account" : "acc",
        "advance" : "adv",
        "americ" : "am",
        "angewan" : "angew",
        "annual" : "ann",
        "biomol" : "biomol",
        "chem" : "chem",
        "chimica" : "chim",
        "collect" : "collect",
        "czech" : "czech",
        "comput" : "comput",
        "condensed" : "cond",
        "edition" : "ed",
        "inorg" : "inorg",
        "intern" : "int",
        "journal" : "j",
        "letter" : "lett",
        "material" : "mat",
        "math" : "math",
        "matter" : "matt",
        "molec" : "mol",
        "organ" : "org",
        "phys" : "phys",
        "proc" : "proc",
        "rep" : "rep",
        "review" : "rev",
        "royal" : "r",
        "sci" : "sci",
        "society" : "soc",
        "struct" : "struct",
        "spectros" : "spectrosc",
        "theor" : "theor",
        "topic" : "top",
    }
    
    def __init__(self, node, archive):
        self.topnode = node
        self.archive = archive

        #this needs to be here... don't know why
        text = self._fetch_text_node("ref-type")
        text.nodeValue = "17"

    def __eq__(self, other):
        try:
            if not other.__class__ == Article:
                sys.exit("Cannot compare Article to non-Article type")

            if not self._compare(other, "year"): return False
            if not self._compare(other, "volume"): return False
            if not self._compare(other, "page"): return False

            return True
        except:
            return False

    def _compare(self, other, attr):
        method = "get_%s" % attr
        m1 = getattr(self, method)
        m2 = getattr(other, method)
        return m1() == m2()

    def __str__(self):
        return self.topnode.toprettyxml()

    def _append_text_node(self, tagname, topnode = None):
        node, text = self._create_text_node(tagname)
        if topnode:
            topnode.appendChild(node)
        else:
            self.topnode.appendChild(node)

        return text

    def _create_node(self, tagname):
        node = self.topnode.ownerDocument.createElement(tagname)
        return node

    def _create_text(self, tagname):
        node = self.topnode.ownerDocument.createTextNode(tagname)
        return node

    def _create_text_node(self, tagname):
        #doesn't yet exist
        node = self._create_node(tagname)

        style = self._create_node("style")
        node.appendChild(style)
        style.setAttribute("face", "normal")
        style.setAttribute("font", "default")
        style.setAttribute("size", "100%")

        text = self._create_text("text")
        style.appendChild(text)

        return node, text

    def _fetch_text_node(self, tagname, topnode = None):
        text = self._get_text_node(tagname)
        if not text == None:
            return text

        return self._append_text_node(tagname, topnode)

    def _fetch_node(self, tagname, topnode = None):
        node = self._get_node(tagname, topnode)
        if not node:
            node = self._create_node(tagname)

        if topnode:
            topnode.appendChild(node)
        else:
            self.topnode.appendChild(node)

        return node

    def _get_node(self, tagname, topnode = None):
        nodes = None
        if topnode:
            nodes = topnode.getElementsByTagName(tagname)
        else:
            nodes = self.topnode.getElementsByTagName(tagname)

        if nodes:
            return nodes[0]
        else:
            return None

    def _get_text_node(self, tagname):
        node = self._get_node(tagname)
        if node:
            text = node.firstChild.firstChild
            return text
        else:
            return None

    def _get_entry(self, tagname, topnode = None):
        node = self._get_node(tagname, topnode)
        if not node:
            return None

        text = node.firstChild.firstChild
        return text.nodeValue

    def _set_item(self, value, tagname, topnode = None):
        text = self._fetch_text_node(tagname, topnode)
        text.nodeValue = value

    def _get_text(self, node):
        return node.firstChild.firstChild.nodeValue

    def _abbrev_word(cls, word):
        new_word = word
        for entry in cls.abbrevs:
            if entry in word:
                new_word = cls.abbrevs[entry] + "."
                break

        return capitalize_word(new_word)
    _abbrev_word = classmethod(_abbrev_word)

    def abbreviate(cls, journal):
        words = journal.lower().replace("-"," ").strip().split()

        if len(words) == 1 and words[0] in cls.keep: #keep things like science and nature
            return capitalize_word(words[0])

        str_arr = []
        for word in words:
            if word in cls.erase:
                continue

            str_arr.append(cls._abbrev_word(word))
        return " ".join(str_arr)
    abbreviate = classmethod(abbreviate)

    def get_first_author(self):
        author = self._get_entry(self.authortag)
        lastname = author.split(",")[0]
        return lastname

    def get_authors(self):
        authors = []
        nodes = self.topnode.getElementsByTagName("author")
        for node in nodes:
            text = self._get_text(node)
            authors.append(text)

    def get_issue(self):
        issue = self._get_entry(self.issuetag)
        if issue:
            return int(issue.split("-")[0])
        else:
            return 0

    def get_journal(self):
        return self._get_entry(self.journaltag)

    def get_abbrev(self):
        return self._get_entry(self.abbrevtag)

    def get_page(self):
        entry = self._get_entry(self.pagestag)
        page = Page(entry.split("-")[0])
        return page

    def get_pages(self):
        return self._get_entry(self.pagestag)

    def get_pdf(self):
        node = self._get_node("pdf-urls")
        return self._get_entry(self.pdftag, node)

    def get_pdfnode(self):
        return self._get_node(self.pdftag)

    def get_start_page(self):
        return self.get_page()

    def get_title(self):
        return self._get_entry(self.titletag)
    def get_volume(self):
        return int(self._get_entry(self.volumetag))

    def get_year(self):
        return int(self._get_entry(self.yeartag))

    def has_pdf(self):
        pdfnode = self.get_pdfnode()
        return bool(pdfnode)

    def set_abstract(self, abstract):
        self._set_item(abstract, self.abstracttag)

    def set_authors(self, authors):
        node = self._fetch_node("authors")
        for author in authors:
            text = self._append_text_node("author", node)
            text.nodeValue = author

    def set_end_page(self, page):
        pages = self.get_pages()
        if not pages:
            sys.exit("Cannot set end page before start page has been set")

        if pages and "-" in pages:
            start, end = pages.split("-")
        else:
            start = pages

        pages = start
        pages += "-%s" % page
        self.set_pages(pages)

    def set_issue(self, issue):
        self._set_item("%d" % issue, self.issuetag)

    def set_journal(self, journal):
        node = self._fetch_node("titles")
        cleanj = clean_line(journal)
        self._set_item(cleanj, self.journaltag, node)

        #and do the abbreviation
        node = self._fetch_node("periodical")
        abbrev = self.abbreviate(journal)
        self._set_item(abbrev, self.abbrevtag, node)

    def set_notes(self, notes):
        self._set_item(notes, self.notestag)

    def set_pages(self, pages):
        self._set_item(pages, self.pagestag)

    def set_pdf(self, path):
        if not os.path.isfile(path):
            sys.exit("%s is not a valid pdf file" % path)
        self.archive.add_pdf(path)

        name = os.path.split(path)[-1]

        #check to see if we already have a pdf file
        node = self.get_pdfnode()
        if node:
            style = node.firstChild
            text = style.firstChild
            text.nodeValue = name
        else:
            urlnode = self._fetch_node("urls")
            pdfnode = self._fetch_node("pdf-urls", urlnode)
            text = self._fetch_text_node("url", pdfnode)
            text.nodeValue = name

        shutil.copy(path, "Resources")

    def set_record_number(self, n):
        node = self._get_node("rec-number")
        node.firstChild.nodeValue = "%d" % n

    def set_start_page(self, page):
        pages = self.get_pages()
        start = end = None
        if pages and "-" in pages:
            start, end = pages.split("-")
        else:
            start = pages

        pages = str(page)
        if end:
            pages += "-%s" % end

        self.set_pages(pages)

    def set_title(self, title):
        node = self._fetch_node("titles")
        self._set_item(title, self.titletag, node)

    def set_volume(self, volume):
        self._set_item("%d" % volume, self.volumetag)

    def set_year(self, year):
        node = self._fetch_node("dates")
        self._set_item("%d" % year, self.yeartag, node)

class Archive:
    
    def __init__(self, file):
        self.articles = []

        topdir = os.getcwd()
        self.folder = "%s.archive" % file
        if not os.path.isdir(self.folder):
            os.mkdir(self.folder)
        os.chdir(self.folder)
        if not os.path.isdir("Contents"):
            os.mkdir("Contents")
        os.chdir("Contents")

        if not os.path.isdir("Resources"):
            os.mkdir("Resources")

        if os.path.isfile("Info.xml"):
            self.parser = parse("Info.xml")
            self.records = self.parser.getElementsByTagName("records")[0]
            nodes = self.parser.getElementsByTagName("record")
            for node in nodes:
                article = Article(node, self)
                self.articles.append(article)
        else:
            self.parser = Document()
            xmlnode = self.parser.createElement("xml")
            self.parser.appendChild(xmlnode)
            self.records = self.parser.createElement("records")
            xmlnode.appendChild(self.records)

        os.chdir(topdir)

    def __getitem__(self, index):
        return self.articles.__getitem__(index)

    def __iter__(self):
        return iter(self.articles)

    def __len__(self):
        return len(self.articles)

    def __str__(self):
        str_arr = []
        for article in self.articles:
            str_arr.append(str(article))
        return "\n".join(str_arr)

    def add_pdf(self, path):
        dst = os.path.join(self.folder, "Contents", "Resources")
        import shutil
        shutil.copy(path, dst)

    def commit(self):
        import codecs
        path = os.path.join(self.folder, "Contents", "Info.xml")
        fileobj = codecs.open(path, "w", "utf-8")
        fileobj.write(self.toxml())
        fileobj.close()

    def get_pdfs(self):
        folder = os.path.join(self.folder, "Contents", "Resources")
        pdfs = [elem for elem in os.listdir(folder) if elem.endswith("pdf")]
        return pdfs

    def has(self, article):
        for test in self.articles:
            if article == test:
                return True
        return False

    def test_and_add(self, article):
        if not self.has(article):
            self.add_article(article)

    def add_article(self, article):
        self.records.appendChild(article.topnode)
        self.articles.append(article)

    def create_article(self):
        node = self.parser.createElement("record")
        article = Article(node, self)
        return article


    def toxml(self):
        if not self.articles:
            return ""

        return self.articles[0].topnode.ownerDocument.toxml()

    
class MasterArchive(Archive):
    
    masterfile = "/Users/jjwilke/Documents/backup"
    
    def __init__(self):
        Archive.__init__(self, self.masterfile)


