from xml.dom import minidom
import codecs, sys, os.path, re


class BibPyError(Exception):
    
    def __init__(self, msg):
        Exception.__init__(self, msg)

class RecordEntryError(BibPyError): pass
class RecordTypeError(BibPyError): pass
class RecordAttributeError(BibPyError): pass
class BibformatUnspecifiedError(BibPyError): pass
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
    ]

    regexp = "([a-zA-Z0-9]+)[=]([a-zA-Z0-9]+)"

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

        entries = re.compile(self.regexp).findall(initstring)
        for name, value in entries:
            fullname = self.findEntry(name)
            self.matches[fullname] = value.lower()
    
class LatexFormat:
    
    REPLACE_MAP = {
        "bold" : "\\textbf{#1}",
        "italic" : "\\textit{#1}",
        "normal" : "#1",
        "bold italic" : "\textit{\textbf{#1}}",
    }

    def format(cls, flag, text):
        text = cls.REPLACE_MAP[flag].replace("#1", text)
        return text
    format = classmethod(format)



class EntryFormat:
    
    style = style = 'normal'
    finishdelim = ','
    parentheses = False

    def __init__(self, **kwargs):
        self.verify(kwargs)
        for entry in kwargs:
            setattr(self, entry, kwargs[entry])

    def verify(self, attrs):
        for attr in attrs:
            if not hasattr(self, attr):
                raise FormatOptionError('%s is not a valid option for %s' % (attr, self.__class__))

    def bibitem(self, obj):
        text = LatexFormat.format(self.style, obj.text())
        if self.parentheses:
            text =  "(%s)" % text
        text += self.finishdelim
        return text

class AuthorsFormat(EntryFormat):
    
    lastname = True
    style = 'normal'
    delim = ','
    finaland = False
    finaldelim = True
    finishdelim = ''


    def bibitem(self, authorList):
        formatted_list = []
        for author in authorList:
            bibentry = self.formatname(author)
            formatted_list.append(bibentry)

        frontpart = ""
        if len(formatted_list) > 1: #more than one entry
            delim = self.delim + ' ' #include extra space
            frontpart = delim.join(formatted_list[:-1])
            if self.finaldelim:
                frontpart += self.delim + ' '
            if self.finaland:
                frontpart += " and "
        bibitem = frontpart + formatted_list[-1] + self.finishdelim
        return bibitem

    def formatname(self, author):
        lastname = author.lastname()
        initials = author.initials()
        text = ''
        if self.lastname:
            text = "%s, %s" % (lastname, initials)
        else:
            text = "%s %s" % (initials, lastname)
        return LatexFormat.format(self.style, text)

class JournalFormat(EntryFormat): 
    
    def bibitem(self, obj):
        format = EntryFormat.bibitem(self, obj)
        if format[-2:] == self.finishdelim * 2: #ends in two
            format = format[:-1]
        return format

class YearFormat(EntryFormat): pass
class VolumeFormat(EntryFormat): pass
class PagesFormat(EntryFormat): pass
class TitleFormat(EntryFormat): pass
class LabelFormat(EntryFormat): pass
    
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

    def matches(self, match):
        if match in self.entry.lower():
            return True

class Label(Entry): pass
class Title(Entry): pass
class Volume(Entry): pass
class Pages(Entry): pass
class Year(Entry): pass
class Journal(Entry): pass

class Author:
    
    simplify_map = {
     r'\`{o}' : 'o',
     r'\"{a}' : 'a',
     r'\"{o}' : 'o',
     r'\o' : 'o',
     r'\"{u}' : 'u',
     r'\v{S}' : 'S',
     r'\v{z}' : 'z',
    }

    def __init__(self, author):
        try:
            self._lastname, self._initials = map( lambda x: x.strip(), author.split(",") )
        except ValueError:
            raise RecordEntryError("%s is not a valid author entry" % author)

    def __str__(self):
        return "%s, %s" % (self.lastname(), self.initials())

    def simple_entry(self):
        simple = str(self)
        for entry in self.simplify_map:
            simple = simple.replace(entry, self.simplify_map[entry])
        return simple

    def matches(self, match):
        simpleself = self.simple_entry()
        if match in simpleself.lower():
            return True

    def lastname(self):
        return self._lastname

    def initials(self):
        return self._initials

class AuthorList(Entry): 

    def __init__(self, authorList):
        self.authorList = map(lambda x: Author(x), authorList)

    def __getitem__(self, key):
        return self.authorList[key]

    def __str__(self):
        return "; ".join(map(str,self.authorList))

    def __iter__(self):
        return iter(self.authorList)

    def matches(self, match):
        for author in self:
            if author.matches(match):
                return True
        #none of the authors match
        return False

class RecordObject:

    def __str__(self):
        str_arr = ['Record:']
        for entry in self.entries:
            line = "%15s = %s" % ( '@%s' % entry, self.entries[entry])
            str_arr.append(line)
        return "\n".join(str_arr)

    def setBibformat(cls, attrname, formatobj):
        try:
            getattr(cls, attrname)
        except AttributeError:
            raise BibformatUnspecifiedError("%s is not a valid attribute to set on %s" % (attrname, cls))
        setattr(cls, attrname, formatobj)

    def matches(self, matchreq):
        for attrname in matchreq:
            match = matchreq[attrname]
            entry = self.entries[attrname]
            if not entry.matches(match):
                return False
        return True #all match

    setBibformat = classmethod(setBibformat)

    def getAttribute(self, name):
        name = name.lower()
        formatter = getattr(self, name)
        if not formatter:
            raise BibformatUnspecifiedError(name)
        text = formatter.bibitem(self.entries[name])
        return text

    def bibitem(self):
        txt_arr = []
        for flag in self.order:
            formatter = getattr(self, flag)
            if not formatter:
                raise BibformatUnspecifiedError(flag)
            text = formatter.bibitem(self.entries[flag])
            txt_arr.append(text)
        return " ".join(txt_arr)
            

class JournalArticle(RecordObject):

    authors = None
    title = None
    journal = None
    volume = None
    order = None
    pages = None
    year = None
    citekey = None
    label = None

    CLASS_MAP = {
        'authors' : AuthorList,
        'title' : Title,
        'volume' : Volume,
        'pages' : Pages,
        'year' : Year,
        'journal' : Journal,
        'label' : Label,
    }
    
    def __init__(self, **kwargs):
        self.entries = {}
        for entry in kwargs:
            try:
                classtype = self.CLASS_MAP[entry]
                classinst = classtype(kwargs[entry])
                self.entries[entry] = classinst
            except KeyError:
                raise RecordEntryError('%s does not have a class implemented' % entry)

    def citekey(self):
        return self.citekey(self)


class Record(object):
    
    CLASS_LIST = {
        "Journal Article" : JournalArticle,
    }
    
    def __new__(cls, **kwargs):
        type = None
        classtype = None
        try:
            type = kwargs['ref-type']
            del kwargs['ref-type']
        except KeyError:
            raise RecordAttributeError("no ref-type attribute for record:\n%s\n" % kwargs)

        try:
            classtype = cls.CLASS_LIST[type]
        except KeyError:
            raise RecordTypeError("%s record type is invalid or has not yet been programmed" % type)

        newrecord = classtype(**kwargs)
        return newrecord

    def setDefaults(cls):
        if not JournalArticle.order: #not yet formatted
            order(JournalArticle, 'authors', 'journal', 'volume', 'pages', 'year')
            set('authors', JournalArticle, delim = ',', lastname = false, finaldelim = true, finishdelim = ",")
            set('volume', JournalArticle, style = 'bold')
            set('pages', JournalArticle) #no style modification
            set('year', JournalArticle, parentheses = true, finishdelim = ".")
            set('journal', JournalArticle, finishdelim = ".") #defaults are fine

    setDefaults = classmethod(setDefaults)


class XMLRequest:

    LOOKUP_TABLE = {
        u'\xe1' : r'\`{o}',
        u'\xe4' : r'\"{a}',
        u'\xf6' : r'\"{o}',
        u'\xf8' : r'\o',
        u'\xfc' : r'\"{u}',
        u'\u0160' : r'\v{S}',
        u'\u017e' : r'\v{z}',
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
            try:
                text = entry.firstChild.firstChild.data
                cleanEntry = self.cleanEntry(text)
                data.append(cleanEntry)
            except:
                pass #character not yet added
        return data

    def nrecords(cls, xmldoc, flag):
        nodes = xmldoc.getElementsByTagName(flag)
        return len(nodes)
    nrecords = classmethod(nrecords)

class Bibliography:

    attrlist = [
        'title',
        ['authors', 'author'],
        'volume',
        'year',
        'pages',
        'short-title',
        'abbr-1', #the abbreviated journal title
        XMLRequest(topname = 'ref-type', attrname = 'name'),
    ]

    mapnames = {
        'abbr-1' : 'journal',
        'short-title' : 'label',
    }

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
            str_arr.append("%d. %s" % (n, rec.bibitem()))
            n += 1
        return "\n".join(str_arr)

    def hasCitation(self, entry):
        label = entry.getAttribute("label")
        return label in self.records

    def addCitation(self, entry):
        label = entry.getAttribute("label")
        self.records[label] = entry

    def labels(self):
        return self.records.keys()

    def subset(self, initstring):
        matchreq = MatchRequest(initstring)

        newrecs = {}
        for entry in self.records:
            if self.records[entry].matches(matchreq):
                newrecs[entry] = self.records[entry]

        bib = Bibliography()
        bib.records = newrecs

        return bib

    def write(self, file="bibliography.tex"):
        if not self.bibicites:
            sys.stderr.write("Warning: no entries for bibliography.  Did you build the entry?")
            
        str_arr = []
        for entry in self.bibcites:
            record = self.records[entry]
            str_arr.append('\\bibitem{%s}%s\n' % (entry, record.bibitem()))
        fileobj = open(file, "w")
        fileobj.write("\n".join(str_arr))
        fileobj.close()

    def buildBibliography(self, texfile):
        auxfile = open(texfile + ".aux").read()
        regexp = "\citation[{](.*?)[}]"
        entries = re.compile(regexp).findall(auxfile)
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

    def buildRecords(self, bibfile, check=false):
        xmldoc = None
        try:
            xmldoc = minidom.parse(bibfile)
        except Exception, error: #not a valid xmldoc
            return -1

        xmlrecords = xmldoc.getElementsByTagName('record')
        for rec in xmlrecords:
            try:
                self.addRecord(rec)
            except RecordEntryError, error:
                if check: #if we are doing a full check, print the errors
                    sys.stderr.write("record error\n%s\n" % error)

    def addRecord(self, xmlrec):
        kwargs = {}
        errors = []
        for attr in self.attrlist:
            try:
                self.addEntry(attr, xmlrec, kwargs)
            except RecordEntryError, error:
                errors.append(str(error))

        if errors:
            raise RecordEntryError("records\n%s\n is not valid\n%s" % (kwargs, "\n".join(errors))) 

        #get the label
        label = kwargs['label']

        if label in self.records:
            raise DuplicateLabelError("duplicate labels for\n%s\nand\n%s" % (rec, self.records[label]))

        try:
            rec = Record(**kwargs)
            #everything good, add the record
            self.records[label] = rec
        except RecordTypeError, error:
            sys.stderr.write("%s\nfor record\n%s\n" % (error, kwargs))

    def addEntry(self, attr, recnode, kwargs):
        req = self.getXMLRequest(attr)
        mapname = topname = req.topname
        if self.mapnames.has_key(topname):
            mapname = self.mapnames[topname]

        try:
            data = req.getData(recnode)
            kwargs[mapname] = data
        except XMLRequestError, error:
            raise RecordEntryError("entry does not have attribute %s" % req.topname)
            





