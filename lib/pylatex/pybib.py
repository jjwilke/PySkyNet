from xml.dom import minidom
import codecs
import sys
import os.path
import os
import re
from skynet.utils.utils import framestr, traceback
from utils import unicode_to_latex

def lower_case_xml_node(node, newnode, depth):
    for child in node.childNodes:
        if child.nodeType == node.TEXT_NODE:
            newchild = newnode.ownerDocument.createTextNode(child.nodeName.lower())
            newchild.nodeValue = child.nodeValue
            newnode.appendChild(newchild)
        else:
            newchild = newnode.ownerDocument.createElement(child.nodeName.lower())
            newnode.appendChild(newchild)
            lower_case_xml_node(child, newchild, depth + 1)

def lower_case_xml(xmldoc):
    newdoc = minidom.Document()
    for child in xmldoc.childNodes:
        newchild = newdoc.createElement(child.nodeName.lower())
        try:
            newdoc.appendChild(newchild)
            lower_case_xml_node(child, newchild, 0)
        except Exception, error:
            sys.stderr.write("%s\n" % child.nodeName)
            raise error

    return newdoc

class BibPyError(Exception):
    
    def __init__(self, msg):
        Exception.__init__(self, msg)

class RecordEntryError(BibPyError):

    def __init__(self, field, msg):
        self.field = field
        BibPyError.__init__(self, msg)
    
    def getField(self):
        return self.field

class MissingDataError(BibPyError):
    def __init__(self, descr, *xargs): #all the missing data is xargs
        self.descr = descr
        self.errors = xargs[:]
        msg = "%s\nis missing the following fields:\n%s" % (descr, "\n".join(xargs))
        BibPyError.__init__(self, msg)

    def __iter__(self):
        return iter(self.errors)

    def getDescription(self):
        return self.descr

    def hasError(self, error):
        return error in self.errors

class RecordClassError(BibPyError): pass
class RecordTypeError(BibPyError): pass
class RecordAttributeError(BibPyError): pass
class BibformatUnspecifiedError(BibPyError): 
    def __init__(self, msg):
        BibPyError.__init__(self, "No format specified for %s" % msg)
class FormatOptionError(BibPyError): pass
class DuplicateLabelError(BibPyError): pass
class NoLabelError(BibPyError): pass
class RecordCountError(BibPyError): pass
class XMLRequestError(BibPyError): pass
class TexError(BibPyError): pass
class BadMatchAttribute(BibPyError): pass

#macros
true = True
false = False

def setOptions(classtype, attrname, attrclass, **kwargs):
    cmd = '%s(**kwargs)' % attrclass
    formatobj = eval(cmd)
    classtype.setBibformat(attrname, formatobj)

def set(attrname, type, **kwargs):
    formatclass = attrname[0].upper() + attrname[1:].lower() + "Format"
    setOptions(type, attrname, formatclass, **kwargs)

def order(type, *xargs):
    type.order = xargs


class MatchRequest:

    attrs = [
        'authors',
        'title',
        'volume',
        'pages',
        'year',
        'journal',
        'label',
        'keywords',
    ]

    regexp = "([a-zA-Z0-9]+)[=]([a-zA-Z0-9][a-zA-Z0-9 ]*)"

    def findEntry(self, subexpr):
        for entry in self.attrs:
            if subexpr in entry:
                return entry

        #no matches
        msg = "%s is not a valid match attribute" % subexpr
        raise BadMatchAttribute(msg)

    def __iter__(self):
        return iter(self.matches)

    def __getitem__(self, key):
        return self.matches[key]

    def __init__(self, initstring):
        self.matches = {}

        entries = map(lambda x: x.split("="), initstring.split(","))

        #entries = re.compile(self.regexp).findall(initstring)
        for name, value in entries:
            name = name.strip().lower()
            value = value.strip().lower()
            fullname = self.findEntry(name)
            if not self.matches.has_key(fullname):
                self.matches[fullname] = []
            self.matches[fullname].append(value.lower())
    
class LatexFormat:
    
    REPLACE_MAP = {
        "bold" : "\\textbf{#1}",
        "italic" : "\\textit{#1}",
        "normal" : "#1",
        "bold italic" : "\textit{\textbf{#1}}",
    }

    def format(cls, flag, text):
        try:
            text = cls.REPLACE_MAP[flag].replace("#1", text)
            return text
        except Exception, error:
            raise error
    format = classmethod(format)



class EntryFormat:
    
    style = 'normal'

    def __init__(self, **kwargs):
        self.verify(kwargs)
        for entry in kwargs:
            setattr(self, entry, kwargs[entry])

    def verify(self, attrs):
        for attr in attrs:
            if not hasattr(self, attr):
                raise FormatOptionError('%s is not a valid option for %s' % (attr, self.__class__))

    def bibitem(self, obj, simple=False):
        if simple:
            return obj.text()

        #by default, simplify does nothing
        text = LatexFormat.format(self.style, obj.text())
        return text

class AuthorsFormat(EntryFormat):
    
    lastname = True
    style = 'normal'
    delim = ','
    finaland = False

    simplify_map = {
     r'\`{o}':'o',
     r'\"{a}':'a',
     r'\~{A}':'A',
     r'\"{o}':'o',
     r'\"{u}':'u',
     r'\v{S}':'S',
     r'\v{z}':'z',
     r'\v{c}':'c',
     r'\{O}' :'O', 
     r'\'{I}':'I',
     r'\"{U}':'U',
     r'\ss' :'ss', 
     r'\`{a}':'a',
     r'\`{e}':'e',
     r'\`{i}':'i',
     r'\`{o}':'o',
     r'\"{a}':'a',
     r'\"{o}':'o',
     r'{\o}' :'o',
     r'\"{u}':'u',
     r'\`{o}':'o',
     r'\'{d}':'d',
     r'\'{c}':'c',
     r'\v{C}':'C',
     r'\v{c}':'c',
     r'\u{i}':'i',
     r'{\l}' :'l', 
     r'\v{r}':'r',
     r'\v{S}':'S',
     r'\v{Z}':'Z',
     r'\v{z}':'z',
     r'\"{o}':'o',
     r'\"{u}':'u',
     r'\v{c}':'c',
     r'\v{r}':'r',
     r'\v{C}':'C',
    }

    def bibitem(self, authorList, simple=False):
        if not authorList:
            return "" #nothing

        formatted_list = []
        for author in authorList:
            bibentry = self.formatname(author, simple)
            formatted_list.append(bibentry)

        frontpart = ""
        if len(formatted_list) > 1: #more than one entry
            delim = self.delim + ' ' #include extra space
            frontpart = delim.join(formatted_list[:-1])
            if self.finaland:
                frontpart += " and "
            else:
                frontpart += "%s " % delim
        bibitem = frontpart + formatted_list[-1]
        return bibitem

    def formatname(self, author, simple=False):
        lastname = author.lastname()
        initials = author.initials()
        text = ''
        if self.lastname:
            text = "%s, %s" % (lastname, initials)
        else:
            text = "%s %s" % (initials, lastname)

        if simple:
            text = self.simplify_entry(text)

        return LatexFormat.format(self.style, text)

    def simplify_entry(cls, text):
        simple = text
        for entry in cls.simplify_map:
            simple = simple.replace(entry, cls.simplify_map[entry])
        return simple

    simplify_entry = classmethod(simplify_entry)

#do editors exactly as authors
EditorsFormat = AuthorsFormat


class JournalFormat(EntryFormat): 

    def bibitem(self, obj, simple=False):
        from papers.utils import JournalCleanup
        journal = JournalCleanup.abbreviate(obj.text())
        text = LatexFormat.format(self.style, journal)
        return text

class PagesFormat(EntryFormat):
    
    lastpage = False

    def bibitem(self, obj, simple=False):
        format = EntryFormat.bibitem(self, obj, simple)
        entries = re.split("[-]+", format)
        if simple:
            return entries[0]

        if self.lastpage and len(entries) > 1:
            return "%s--%s" % (entries[0], entries[1])
        else:
            return entries[0]
        

class DoiFormat(EntryFormat): pass
class YearFormat(EntryFormat): pass
class VolumeFormat(EntryFormat): pass
class TitleFormat(EntryFormat): pass
class BooktitleFormat(EntryFormat): pass
class LabelFormat(EntryFormat): pass
class CitekeyFormat(EntryFormat): pass
class UrlFormat(EntryFormat): pass
class VersionFormat(EntryFormat): pass
class PublisherFormat(EntryFormat): pass
class CityFormat(EntryFormat): pass
class EditionFormat(EntryFormat): pass

class TitleFormat(EntryFormat):


    def bibitem(self, obj, simple=False):
        from utils import make_numbers_subscript as nsub

        title = EntryFormat.bibitem(self, obj, simple)
        return title
                
    
class CiteKey: pass

class JJWCiteKey:
    
    def __init__(self):
        pass

    def citekey(obj):
        try:
            obj['short-title']
        except RecordAttributeError, error:
            sys.stderr.write("JJW cite key requires end note entries to have a short-title.  The following entry does not have one:\n %s\n" % obj)
            raise error

class Entry:
    
    def __init__(self, text):
        self.entry = text

    def text(self):
        return self.entry

    def __str__(self):
        return self.entry

    def raw_match(cls, entry, match):
        me = entry.lower()
        if isinstance(match, basestring):
            return match in me
        else:
            for entry in match:
                if entry in me:
                    return True
            return False #no match
    raw_match = classmethod(raw_match)

    def matches(self, match):
        return self.raw_match(self.entry, match)

class Doi(Entry): pass
class Label(Entry): pass
class CiteKey(Entry): pass
class Edition(Entry): pass
class Title(Entry): pass
class Volume(Entry): pass
class Pages(Entry): pass
class Year(Entry): pass
class Journal(Entry): pass
class Url(Entry): pass
class Publisher(Entry): pass
class City(Entry): pass
class Version(Entry): pass
class FullJournalTitle(Entry): pass
class Keyword(Entry): pass
class Abstract(Entry): pass
class Notes(Entry): pass

class Author:
    
    def __init__(self, author):
        try:
            self._lastname, firstname = map( lambda x: x.strip(), author.split(",") )

            firstnames = map( lambda x: x.strip(), firstname.split() )
            str_arr = []
            for entry in firstnames:
                entry = entry.replace(".","") #get rid of any periods. I'll put these in
                #split on -
                initial = "-".join(map(lambda x: "%s." % self.get_initial(x), entry.split("-")))
                if initial:
                    str_arr.append(initial)
            self._initials = " ".join(str_arr)

            #fix capitalization
            #self.capitalize()

            return

        except ValueError:
            pass #try again

        try:
            split = author.strip().split()
            self._lastname = split[-1]
            firstname = split[0]
            initials = [self.get_initial(firstname)]
            for entry in split[1:-1]:
                initials.append(self.get_initial(entry))
            self._initials = ". ".join(initials) + '.'
            #fix capitalization
            #self.capitalize()
        except IndexError:
            raise RecordEntryError("author", "%s is not a valid author entry" % author)

    def get_initial(self, name):
        if not name:
            return None

        if name[0] == "{":
            return name[:4].upper()
        else:
            return name[0].upper()


    def capitalize(self):
        #find the first letter
        firstletter = ''
        if self._lastname[0] != "\\":
            self._lastname = self._lastname[0].upper() + self._lastname[1:].lower()
        elif "{" in self._lastname: #complicated
            firstletter = re.compile("([{][a-zA-Z][}])").search(self._lastname).groups()[0]
            self._lastname = self._lastname.replace(firstletter, firstletter.upper())
            pos = 0
            while self._lastname[pos] != '}':
                pos += 1
            self._lastname = self._lastname[:pos + 1] + self._lastname[pos + 1:].lower()
        else:
            firstletter = re.compile("([a-zA-Z])").search(self._lastname).groups()[0] 
            pos = 0
            while self._lastname[pos] != '}':
                pos += 1
            self._lastname = self._lastname[:pos + 1].upper() + self._lastname[pos + 1:].lower()

        #check last name for dashes
        matches = re.compile("[-][a-zA-Z]").findall(self._lastname)
        for match in matches:
            old = match
            new = match.upper()
            self._lastname = self._lastname.replace(old, new)

        #check last name for Mc
        for prefix in "Mc", "De":
            if self._lastname[:2] == prefix:
                old = self._lastname[:3]
                new = self._lastname[:2] + old[-1].upper()
                self._lastname = self._lastname.replace(old, new)

    def __str__(self):
        return "%s, %s" % (self.lastname(), self.initials())

    def matches(self, match):
        simpleself = AuthorsFormat.simplify_entry(str(self))
        return Entry.raw_match(simpleself, match)

    def bibtex(self):
        firstname = self._initials.replace(".","")
        return "%s %s" % (firstname, self._lastname)

    def lastname(self):
        return self._lastname

    def initials(self):
        str_arr = []
        for entry in self._initials.split():
            if entry[-1] == ".":
                str_arr.append(entry)
            else:
                str_arr.append(entry + ".")
        return " ".join(str_arr)

class RecordList(Entry):
    
    def __init__(self, method, entries):
        self.entries = map(method, entries)

    def __getitem__(self, key):
        return self.entries[key]

    def __len__(self):
        return len(self.entries)

    def __str__(self):
        return "; ".join(map(str,self.entries))

    def __iter__(self):
        return iter(self.entries)

    def raw_match(self, match):
        for entry in self:
            if entry.matches(match):
                return True
        #none of the authors match
        return False

    def matches(self, match):
        if isinstance(match, basestring):
            return self.raw_match(match)
        else:
            for entry in match:
                if not self.raw_match(entry):
                    return False
            return True #all pass

class KeywordList(RecordList):
    
    def __init__(self, keywords):
        RecordList.__init__(self, lambda x: Keyword(x.encode('ascii', 'ignore').strip().lower()), keywords)

class AuthorList(RecordList):

    def __init__(self, authorList):
        self.authorList = RecordList.__init__(self, lambda x: Author(x), authorList)

class XMLRequest:

    LOOKUP_TABLE = {
        u'\xb0' : r'$\degree$',
        u'\xb7' : r'$\cdot$',
        u'\xd8' : r'{\O}',
        u'\xc3' : r'\~{A}',
        u'\xcd' : r'\'{I}',
        u'\xdc' : r'\"{U}',
        u'\xd0' : 'D',
        u'\xdf' : r'\ss',
        u'\xe1' : r'\`{a}',
        u'\xe9' : r'\`{e}',
        u'\xed' : r'\`{i}',
        u'\xf3' : r'\`{o}',
        u'\xe4' : r'\"{a}',
        u'\xf6' : r'\"{o}',
        u'\xf8' : r'{\o}',
        u'\xfc' : r'\"{u}',
        u'\xf3' : r'\`{o}',
        u'\xfd' : r'\'{y}',
        u'\u0107' :  r'\'{c}',
        u'\u010c' : r'\v{C}',
        u'\u010d' : r'\v{c}',
        u'\u012d' :  r'\u{i}',
        u'\u0142' :  r'{\l}',
        u'\u0159' : r'\v{r}',
        u'\u0160' : r'\v{S}',
        u'\u017d' : r'\v{Z}',
        u'\u017e' : r'\v{z}',
        u'i\u0308' : r'\"{i}', #this is not right... not sure where it is coming from
        u'a\u0308' : r'\"{a}', #this is not right... not sure where it is coming from
        u'o\u0308' : r'\"{o}', #this is not right... not sure where it is coming from
        u'u\u0308' : r'\"{u}', #this is not right... not sure where it is coming from
        u'c\u030c' : r'\v{c}', #this is not right... not sure where it is coming from
        u'r\u030c' : r'\v{r}', #this is not right... not sure where it is coming from
        u'C\u030c' : r'\v{C}', #this is not right... not sure where it is coming from
        u'\u0338' : r'\\',
        u'\u0393' : r'$\Gamma$',
        u'\u0396' : r'$\Zeta$',
        u'\u03b1' : r'$\alpha$',
        u'\u03b2' : r'$\beta$',
        u'\u03b6' : r'$\zeta$',
        u'\u03c0' : r'$\pi$',
        u'\u03c9' : r'$\omega$',
        u'\u2019' : r"'",
        u'\u201c' : r"``",
        u'\u201d' : r"''",
        u'\u201f' : r"''",
        u'\u2026' : r'...',
        u'\u2020' : r'$^{\dagger}$',
        u'\u2014' : r'-',
        u'\u2013' : r'-',
        u'\u2012' : r'-',
        u'\u2010' : r'-',
        u'\u2190' : r'$\leftarrow$',
        u'\u2191' : r'$\uparrow$',
        u'\u2192' : r'$\rightarrow$',
        u'\u2193' : r'$\downarrow$',
        u'\u2194' : r'$\leftrightarrow$',
        u'\u2212' : r'-',
        u'\ufb01' : "",
    }

    def __init__(self, topname, dataname = None, attrname = None):
        self.dataname = dataname
        self.topname = topname
        self.attrname = attrname

    def getData(self, xmldoc):
        nodes = xmldoc.getElementsByTagName(self.topname)
        data = None
        try: 
            if self.dataname: #second level
                childnodes = nodes[0].getElementsByTagName(self.dataname)
                data = self.getDataFromNodes(childnodes)
            elif self.attrname:
                data = self.getAttributesFromNodes(nodes, self.attrname)[0] 
            else:
                data = self.getDataFromNodes(nodes)[0]
        except MissingDataError:
            raise XMLRequestError("could not find data for %s" % self.topname)
        except IndexError:
            raise XMLRequestError("could not find data for %s" % self.topname)

        return data

    def getList(self, xmldoc):
        topnodes = xmldoc.getElementsByTagName(self.topname)
        data = []
        if self.dataname: #second level
            for node in topnodes:
                childnodes = node.getElementsByTagName(self.dataname)
                data.append(self.getDataFromNodes(childnodes))
            return data
        elif self.attrname:
            data = self.getAttributesFromNodes(topnodes, self.attrname)
        else: #only one level
            data = self.getDataFromNodes(topnodes)

        return data

    def cleanEntry(self, text):
        for repl in self.LOOKUP_TABLE:
            text = text.replace(repl, self.LOOKUP_TABLE[repl])
        
        try:
            text.encode()
        except UnicodeEncodeError, error:
            sys.stderr.write("%s\n" % text.encode("utf-8"))
            raise error

        return text

    def getAttributesFromNodes(self, nodes, attrname):
        data = []
        for node in nodes:
            attr = node.getAttribute(attrname)
            data.append(attr)
        return data

    def getDataFromNodes(self, nodes):
        data = []
        for entry in nodes:
            text = ""
            if not entry.firstChild: #nothing here... hmmm
                raise MissingDataError("No data")
            if entry.firstChild.firstChild:
                text = entry.firstChild.firstChild.data
            else:
                text = entry.firstChild.data

            try:
                text = self.cleanEntry(text)
            except BibPyError:
                continue

            data.append(text)

        return data

    def nrecords(cls, xmldoc, flag):
        nodes = xmldoc.getElementsByTagName(flag)
        return len(nodes)
    nrecords = classmethod(nrecords)

class RecordObject:
    
    mandatoryfields = ['label']
    patchlist = {}
    sort_criterion = None
    reverse_sort = False


    def __str__(self):
        str_arr = ['Record:']
        for entry in self.entries:
            line = "%15s = %s" % ( '@%s' % entry, self.entries[entry])
            str_arr.append(line)
        return "\n".join(str_arr)

    def __lt__(self, other):
        if not self.sort_criterion:
            return True

        my_attr = self.getAttribute(self.sort_criterion)
        other_attr = other.getAttribute(self.sort_criterion)

        return my_attr < other_attr

    def setBibformat(cls, attrname, formatobj):
        try:
            getattr(cls, attrname)
        except AttributeError:
            raise BibformatUnspecifiedError("%s is not a valid attribute to set on %s" % (attrname, cls))
        setattr(cls, attrname, formatobj)

    def get_summary(self):
        return "No summary"

    def getText(self, attr):
        attr = attr.lower()
        if not attr in self.entries:
            return ""
        else:
            return str(self.entries[attr])

    def getBibtex_authors(self):
        alist = self.entries["authors"] 
        str_arr = []
        for author in alist:
            str_arr.append(author.bibtex())
        return " and ".join(str_arr)

    def getBibtexValue(self, attr):
        return self.getAttribute(attr)

    def getBibtexEntry(self):
        #set the necessary formatting
        for tag in self.bibtex:
            set(tag, self.__class__) #no formatting
        set("pages", self.__class__, lastpage = True)

        str_arr = ["@%s{%s" % (self.bibtype, self.getBibkey())]
        for attr in self.bibtex:
            tag = self.bibtex[attr]
            method = None
            name = "getBibtex_%s" % attr
            if hasattr(self, name):
                method = getattr(self, name)
            else:
                method = lambda x=attr : self.getBibtexValue(x)
            value = method()
            str_arr.append("%s = {%s}" % (tag, value))
        entry = ",\n".join(str_arr)
        entry += "\n}" #append final
        return entry

    def getBibkey(self):
        pages = self.getAttribute("pages", simple = True)
        year = self.getAttribute("year", simple = True)
        authors = self.getAttribute("authors", simple = True)

        if not pages:
            return None

        firstpage = pages.split("-")[0].strip()
        firstauthor = AuthorsFormat.simplify_entry(authors.split(",")[0].split(".")[-1].strip().replace(" ", "").replace("-",""))

        citekey = "%s:%sp%s" % (firstauthor, year, firstpage)
        return citekey

    def matches(self, matchreq):
        for attrname in matchreq:
            match = matchreq[attrname]
            try:
                entry = self.entries[attrname]
                if not entry.matches(match):
                    return False
            except KeyError, error:
                sys.stderr.write("%s for class %s\n" % (error, self.__class__))
                return False

        return True #all match

    setBibformat = classmethod(setBibformat)

    def getAttribute(self, name, simple=False):
        method = "get_%s" % name.lower()
        if hasattr(self, method):
            method = getattr(self, method)
            return method()

        name = name.lower()
        try:
            formatter = getattr(self, name)
            if not formatter:
                raise BibformatUnspecifiedError(name)
            text = formatter.bibitem(self.entries[name], simple)
            return text
        except AttributeError:
            return None

    def addAttribute(self, key, value):
        pass

    def get(self, attr):
        try:
            return self.entries[attr]
        except KeyError:
            return None

    def __getitem__(self, name, simple=False):
        try:
            formatter = getattr(self, name)
            if not formatter:
                raise BibformatUnspecifiedError(name)
            text = formatter.bibitem(self.entries[name], simple)
            return text
        except Exception, error:
            sys.stderr.write("error in getitem for %s\n" % name)
            raise error

class ComputerProgram(RecordObject):

    authors = None
    title = None
    order = None
    year = None
    publisher = None
    label = None
    url = None
    bibitem = None

    attrlist = [
        'title',
        ['authors', 'author'],
        'year',
        'short-title',
        "accession_number",
        'url',
        #'edition',
        'publisher',
        XMLRequest(topname = 'ref-type', attrname = 'name'),
    ]

    mapnames = {
        'short-title' : 'label',
        'accession_number' : 'label',
        #'edition' : 'version',
    }

    CLASS_MAP = {
        'authors' : AuthorList,
        'keywords' : KeywordList,
        'title' : Title,
        'year' : Year,
        'label' : Label,
        'url' : Url,
        #'version' : Version,
        'publisher' : Publisher,
    }
    
    def __init__(self, **kwargs):
        self.entries = {}
        for entry in kwargs:
            try:
                classtype = self.CLASS_MAP[entry]
                classinst = classtype(kwargs[entry])
                self.entries[entry] = classinst
            except KeyError:
                raise RecordClassError('%s does not have a class implemented' % entry)
            

class Book(RecordObject):

    authors = None
    title = None
    booktitle = None
    edition = None
    year = None
    pages = None
    city = None
    publisher = None
    bibitem = None
    editors = None
    label = None
    bibtype = "book"

    attrlist = [
        'title',
        ['authors', 'author'],
        ['secondary-authors', 'author'],
        'volume',
        'year',
        'pages',
        'short-title',
        'secondary-title',
        'accession_number',
        'edition',
        'publisher',
        'pub-location',
        XMLRequest(topname = 'ref-type', attrname = 'name'),
    ]

    mapnames = {
        'short-title' : 'label',
        'secondary-title' : 'booktitle',
        'accession_number' : 'label',
        'secondary-authors' : 'editors',
        'pub-location' : 'city',
    }

    patchlist = {
    }

    bibtex = {
        "title" : "title",
        "year" : "year",
        "authors" : "author",
        "publisher" : "publisher",
        "city" : "address",
    }


    CLASS_MAP = {
        'authors' : AuthorList,
        'title' : Title,
        'booktitle' : Title,
        'volume' : Volume,
        'pages' : Pages,
        'year' : Year,
        'full-title' : FullJournalTitle,
        'label' : Label,
        'editors' : AuthorList,
        'edition' : Edition,
        'publisher' : Publisher,
        'city' : City,
    }

    bibtype = "book"

    def __init__(self, **kwargs):
        self.entries = {}
        for entry in kwargs:
            try:
                classtype = self.CLASS_MAP[entry]
                classinst = classtype(kwargs[entry])
                self.entries[entry] = classinst
            except KeyError:
                raise RecordClassError('%s does not have a class implemented' % entry)

    def getBibkey(self):
        return self.getAttribute("label")


class BookSection(RecordObject):
    authors = None
    title = None
    booktitle = None
    edition = None
    year = None
    pages = None
    city = None
    publisher = None
    bibitem = None
    editors = None
    label = None
    bibtype = "booksection"

    attrlist = [
        'title',
        ['authors', 'author'],
        ['secondary-authors', 'author'],
        'volume',
        'year',
        'pages',
        'short-title',
        'secondary-title',
        'accession_number',
        'edition',
        'publisher',
        'pub-location',
        XMLRequest(topname = 'ref-type', attrname = 'name'),
    ]

    mapnames = {
        'short-title' : 'label',
        'secondary-title' : 'booktitle',
        'accession_number' : 'label',
        'secondary-authors' : 'editors',
        'pub-location' : 'city',
    }

    patchlist = {
    }

    bibtex = {
        "title" : "title",
        "year" : "year",
        "authors" : "author",
        "publisher" : "publisher",
        "city" : "address",
    }


    CLASS_MAP = {
        'authors' : AuthorList,
        'title' : Title,
        'booktitle' : Title,
        'volume' : Volume,
        'pages' : Pages,
        'year' : Year,
        'full-title' : FullJournalTitle,
        'label' : Label,
        'editors' : AuthorList,
        'edition' : Edition,
        'publisher' : Publisher,
        'city' : City,
    }

    def __init__(self, **kwargs):
        self.entries = {}
        for entry in kwargs:
            try:
                classtype = self.CLASS_MAP[entry]
                classinst = classtype(kwargs[entry])
                self.entries[entry] = classinst
            except KeyError:
                raise RecordClassError('%s does not have a class implemented' % entry)

    def getBibkey(self):
        return self.getAttribute("label")


class JournalArticle(RecordObject):

    authors = None
    title = None
    journal = None
    volume = None
    pages = None
    year = None
    citekey = None
    label = None
    bibitem = None
    doi = None

    mandatoryfields = []

    attrlist = [
        'title',
        'abstract',
        'notes',
        ['authors', 'author'],
        ['keywords', 'keyword'],
        'volume',
        'year',
        'pages',
        'short-title',
        'accession_number',
        'abbr-1', #the abbreviated journal title
        'secondary_title',
        'electronic_resource_number',
        XMLRequest(topname = 'ref-type', attrname = 'name'),
    ]

    mapnames = {
        'abbr-1' : 'journal',
        'short-title' : 'label',
        'secondary_title' : 'journal',
        'accession_number' : 'label',
        'electronic_resource_number' : 'doi'
    }

    #get attr key and write bibtex value
    bibtex = {
        "title" : "title",
        "journal" : "journal",
        "pages" : "pages",
        "volume" : "volume",
        "year" : "year",
        "authors" : "author",
    }
    bibtype = "article"

    patchlist = {
        'journal' : ['full-title'],
    }

    CLASS_MAP = {
        'keywords' : KeywordList,
        'authors' : AuthorList,
        'title' : Title,
        'abstract' : Abstract,
        'notes' : Notes,
        'volume' : Volume,
        'pages' : Pages,
        'year' : Year,
        'journal' : Journal,
        'full-title' : FullJournalTitle,
        'label' : Label,
        'doi' : Doi,
        'citekey' : CiteKey,
    }
    
    def __init__(self, **kwargs):
        self.entries = {}
        for entry in kwargs:
            self.addAttribute(entry, kwargs[entry])
    
    def addAttribute(self, key, value):
            try:
                classtype = self.CLASS_MAP[key]
                classinst = classtype(value)
                self.entries[key] = classinst
            except KeyError:
                raise RecordClassError('%s does not have a class implemented' % key)

    #def citekey(self):
    #    return self.citekey(self)

    def get_summary(self):
        str_arr = []
        notes = self.getText("notes")
        if notes:
            str_arr.append("Notes:")
            str_arr.append(notes)

        abstract = self.getText("abstract")
        if abstract:
            str_arr.append("Abstract:")
            str_arr.append(abstract)

        return "\n".join(str_arr)


class Record(object):
    
    CLASS_LIST = {
        "Journal Article" : JournalArticle,
        "17" : JournalArticle, #fuck papers, seriously
        "13" : JournalArticle, #fuck papers, seriously
        "0" : JournalArticle, #fuck papers, seriously
        "9" : ComputerProgram,
        "27" : ComputerProgram,
        "5" : BookSection,
        "6" : Book,
        "Computer Program" : ComputerProgram,
    }

    formatted = False
    
    def __new__(cls, **kwargs):
        type = None
        try:
            type = kwargs['ref-type']
            del kwargs['ref-type']
        except KeyError:
            raise RecordAttributeError("no ref-type attribute for record:\n%s\n" % kwargs)

        classtype = cls.getClassType(type)

        newrecord = classtype(**kwargs)
        return newrecord

    def getClassType(cls, reftype):
        try:
            classtype = cls.CLASS_LIST[reftype]
        except KeyError:
            raise RecordTypeError("%s record type is invalid or has not yet been programmed" % reftype)
        return classtype
    getClassType = classmethod(getClassType)

    def setFormat(cls, format):
        format = format.lower()
        try:
            cmd = "from pylatex.%s import set_%s_format as set_format" % (format, format)
            exec(cmd)
        except ImportError:
            sys.stderr.write("invalid format %s" % format)
            return
        set_format()
        cls.formatted = True
    setFormat = classmethod(setFormat)

    
    def unsetFormat(cls):
        cls.formatted = False
        JournalArticle.bibitem = None
        Book.bibitem = None
    unsetFormat = classmethod(unsetFormat)

    def setDefaults(cls):
        if cls.formatted:
            return #format already done

        if not JournalArticle.bibitem: #not yet formatted

            def journal_bibitem(r):
                format = "%s, %s %s, %s, (%s)." % (r['authors'], r['journal'], r['volume'], r['pages'], r['year'])
                return format

            JournalArticle.bibitem = journal_bibitem
            set('authors', JournalArticle, delim = ',', lastname = false)
            set('volume', JournalArticle, style = 'bold')
            set('pages', JournalArticle, lastpage = false) #no style modification
            set('year', JournalArticle)
            set('journal', JournalArticle)
            set('label', JournalArticle)
            set('citekey', JournalArticle)
            set('title', JournalArticle)
            set('doi', JournalArticle)

            set('authors', ComputerProgram, delim = ',', lastname = false)
            set('year',    ComputerProgram)
            set('title',   ComputerProgram) #defaults are fine
            set('label',   ComputerProgram) #defaults are fine

            def book_bibitem(r):
                format = "%s, %s." % (r['authors'], r['title'])

                editors = r['editors']
                if editors:
                    format += " edited by %s." % editors

                format += " (%s, %s, %s)." % (r['publisher'], r['city'], r['year'])

                return format
            set('authors', Book, delim = ',', lastname = false)
            set('editors', Book, delim = ',', lastname = false)
            set('year',    Book)
            set('title',   Book) #defaults are fine
            set('label',   Book) #defaults are fine
            set('publisher',   Book) #defaults are fine
            set('city',   Book) #defaults are fine
            Book.bibitem = book_bibitem

            def book_section_bibitem(r):
                format = "%s, %s in %s" % (r['authors'], r['title'], r['booktitle'])

                editors = r['editors']
                if editors:
                    format += " edited by %s." % editors

                format += " (%s, %s, %s)." % (r['publisher'], r['city'], r['year'])
                return format

            set('authors', BookSection, delim = ',', lastname = false)
            set('editors', BookSection, delim = ',', lastname = false)
            set('year',    BookSection)
            set('title',   BookSection) #defaults are fine
            set('booktitle',   BookSection) #defaults are fine
            set('label',   BookSection) #defaults are fine
            set('publisher',   BookSection) #defaults are fine
            set('city',   BookSection) #defaults are fine
            BookSection.bibitem = book_section_bibitem

        cls.formatted = True

    setDefaults = classmethod(setDefaults)



class Bibliography:
    
    ENDNOTE_XML_LIB = os.environ["ENDNOTE_XML_LIB"]
    

    def __init__(self):
        self.records = {}
        self.init()

    def init(self):
        Record.setDefaults()

    def __iter__(self):
        return iter(self.records.values())

    def __getitem__(self, key):
        return self.records[key]

    def __str__(self):
        str_arr = []
        n = 1
        for label in self.records:
            rec = self.records[label]
            if not rec.bibitem:
                continue
            str_arr.append("%d. %s" % (n, rec.bibitem()))
            n += 1
        textstr =  "\n".join(str_arr)
        return textstr

    def bibitem(self, label):
        return "\\bibitem{%s}" % label

    def update(self, bib):
        for entry in bib:
            self.records[entry.getAttribute("label")] = entry

    def hasCitation(self, entry):
        label = entry.getAttribute("label")
        return label in self.records

    def addCitation(self, entry):
        label = entry.getAttribute("label")
        self.records[label] = entry

    def labels(self):
        return self.records.keys()


    def subset(self, labels):
        newbib = Bibliography()
        newrecs = {}
        for label in labels:
            try:
                newrecs[label] = self.records[label]
            except KeyError:
                pass #don't include
        newbib.records = newrecs
        return newbib

    def filter(self, initstring):
        matchreq = MatchRequest(initstring)

        newrecs = {}
        for entry in self.records:
            if self.records[entry].matches(matchreq):
                newrecs[entry] = self.records[entry]

        bib = Bibliography()
        bib.records = newrecs

        return bib

    def write(self, file="bibliography.tex"):
        if not self.bibcites:
            sys.stderr.write("Warning: no entries for bibliography.  Did you build the entry?\n")

        records = []
        for entry in self.bibcites:
            records.append((self.records[entry], entry))

        if RecordObject.sort_criterion:
            records.sort()
            if RecordObject.reverse_sort:
                records.reverse()
            
        str_arr = []
        for record, label in records:
            str_arr.append('%s%s\n' % (self.bibitem(label), record.bibitem()))
        fileobj = open(file, "w")
        fileobj.write("\n".join(str_arr))
        fileobj.close()

    def buildBibAll(self):
        self.bibcites = self.records.keys()

    def cleanTex(self, texfile):
        text = open(texfile).read()
        for entry in self.records:
            rec = self.records[entry] 
            citekey = rec.getAttribute("citekey")
            label = rec.getAttribute("label")
            if not label or not citekey:
                continue
            if label != citekey:
                text = text.replace(label,citekey)
        fileobj = open("new.tex","w")
        fileobj.write(text)
        fileobj.close()


    def buildBibliography(self, file, sort_criterion = None):
        entries = []
        if file == "all":
            entries = self.records.keys()

        else:
            filetext = open(file).read()
            regexp = ""
            if "aux" in file:
                regexp = "\citation[{](.*?)[}]"
            else:
                regexp = "\cite[n]?[u]?[m]?[{](.*?)[}]"
            entries = re.compile(regexp).findall(filetext)
        self.bibcites = []
        missing = []

        for entry in entries:
            citations = map(lambda x: x.strip(), entry.split(","))
            for cite in citations:
                if cite in self.bibcites: #we already have it
                    continue

                if not cite in self.records: #we don't have this
                    missing.append(cite)
                else:
                    self.bibcites.append(cite)


        if missing: #some records are not in the bib file
            sys.stderr.write("Warning: the following records do not have bibliography entries.  I recommend running a full check to see if the entries are in the bibliography but just misformatted.\n%s\n" % "\n".join(missing))

    def getXMLRequest(self, entry):
        data = None
        if isinstance(entry, str): #only one flag
            return XMLRequest(topname = entry)
        elif isinstance(entry, list): #must be a list
            topname, dataname = entry
            return XMLRequest(topname = topname, dataname = dataname)
        elif isinstance(entry, XMLRequest):
            return entry
        else:
            raise XMLRequestError("invalid xml request input %s" % entry)

    def buildRecords(self, bibfile, check=False, xargerrors=[]):
        xmldoc = None
        try:
            xmldoc = minidom.parse(bibfile)
        except BibPyError, error: #not a valid xmldoc
            return -1

        #lower case-ify the xml file
        try:
            xmldoc = lower_case_xml(xmldoc)
        except Exception, error:
            sys.exit("%s\n%s bibfile failed" % (error, bibfile))

        xmlrecords = xmldoc.getElementsByTagName('record')


        for rec in xmlrecords:
            try:
                self.addRecord(rec)
            except MissingDataError, error:
                pass
                #for field in error:
                #    sys.stderr.write("invalid field %s\n" % field)
                #sys.stderr.write("%s\n" % error.getDescription())
            except RecordTypeError, error:
                sys.stderr.write("%s\n" % error)
                #sys.stderr.write("%s\n" % unicode_to_latex(rec.toxml()))
            except DuplicateLabelError, error:
                sys.stderr.write("%s\n" % error)
                #sys.stderr.write("%s\n" % unicode_to_latex(rec.toxml()))


    def clear(self):
        self.records = {}
        self.bibcites = []

    def findEntry(self, journal, volume, page):
        from papers.pdfglobals import PDFGetGlobals
        for label in self.records:
            try:
                record = self.records[label]
                volcheck = str(record.get("volume"))
                if not volume == volcheck:
                    continue

                pagecheck = str(record.get("pages")).split("-")[0].strip()
                if not page == pagecheck:
                    continue

                jobj = PDFGetGlobals.get_journal(journal)
                jrec = PDFGetGlobals.get_journal(str(record.get("journal")))
                if jobj and jobj.name != jrec.name:
                    continue

                return record
            except Exception, error:
                continue

    def addRecord(self, xmlrec):
        kwargs = {}
        errors = []
        #figure out the reference type
        reftype = None
        try:
            req = XMLRequest(topname = 'ref-type', attrname = 'name')
            reftype = req.getData(xmlrec)
        except XMLRequestError,error:
            pass

        #try again
        if not reftype:
            try:
                req = XMLRequest(topname = 'ref-type')
                reftype = req.getData(xmlrec)
            except XMLRequestError,error:
                pass

        #try again
        if not reftype:
            try:
                req = XMLRequest(topname = 'reference_type')
                reftype = req.getData(xmlrec)
            except XMLRequestError,error:
                raise error

        kwargs['ref-type'] = reftype
        reftype = Record.getClassType(reftype)
        
        errors = []
        for attr in reftype.attrlist:
            try:
                self.addEntry(reftype, attr, xmlrec, kwargs)
            except RecordEntryError, error:
                errors.append(error.getField())

        
        for field in reftype.patchlist:
            if kwargs.has_key(field) and kwargs[field]: #we are either missing a field, or the field has no value
                continue

            for patch in reftype.patchlist[field]:
                if kwargs.has_key(patch):
                    kwargs[field] = kwargs[patch]
                    break #done, move on

        fatal_errors = []
        optional_errors = []
        for field in errors:
            if kwargs.has_key(field) and kwargs[field]: #this got patched
                continue

            if field in reftype.mandatoryfields:
                fatal_errors.append(field)
            else:
                optional_errors.append(field)

        if fatal_errors:
            fatal_errors.extend(optional_errors)
            raise MissingDataError(str(kwargs), *fatal_errors)


        try:
            rec = Record(**kwargs)
            label = kwargs["label"]
            citekey = rec.getBibkey()
            if not label:
                label = citekey
            if not citekey:
                citekey = label
            rec.addAttribute("label", label)
            rec.addAttribute("citekey", citekey)
            if label in self.records:
                raise DuplicateLabelError("duplicate label %s\n%s" % (label,kwargs))
            title = kwargs["title"]
            if not citekey and not label:
                sys.stderr.write("no citekey or label for %s\n" % kwargs)
            elif rec.__class__ == JournalArticle and not re.compile("\d+").search(citekey):
                sys.stderr.write("Journal article cite key %s does not contain numbers\n%s\n" % (kwargs, citekey))
            else: #all good
                self.records[citekey] = rec
        except RecordTypeError, error:
            sys.stderr.write("%s\nfor record\n%s\n" % (error, kwargs))
        except BibformatUnspecifiedError, error:
            sys.stderr.write("error building record for\n%s\n" % kwargs)
            raise error
        except Exception, error:
            #sys.stderr.write("%s\n" % error)
            sys.stderr.write("%s\n" % traceback(error))
            raise error

        #if optional_errors:
        #    raise MissingDataError(str(kwargs), *optional_errors)

    def addEntry(self, reftype, attr, recnode, kwargs):
        req = self.getXMLRequest(attr)
        mapname = topname = req.topname
        if reftype.mapnames.has_key(topname):
            mapname = reftype.mapnames[topname]

        if kwargs.has_key(mapname) and kwargs[mapname]:
            return #already have this from different field

        try:
            data = req.getData(recnode)
            kwargs[mapname] = data
        except XMLRequestError, error:
            #if not a mandatory field and there is not previous entry, write nothing
            if not mapname in reftype.mandatoryfields:
                kwargs[mapname] = '' #store nothing
            raise RecordEntryError(mapname, "entry does not have attribute %s" % req.topname)

            

if __name__ == "__main__":
    bib = Bibliography()
    #bib.buildRecords(sys.argv[1], check=True)
    bib.buildRecords(Bibliography.ENDNOTE_XML_LIB)





