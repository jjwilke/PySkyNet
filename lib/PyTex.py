
class PyTexGlobals:
    pass

class TableFilter:
    
    def __init__(self, table, key):
        self.table = table
        self.key = key

    def matches(self, key):
        return self.key == key

    def getTable(self):
        return self.table
    
class CiteManager:
    
    REF_LISTEN_PORT = 21567

    def __init__(self):
        import PySave, os.path, PyRef
        import pygtk
        import gtk
        import PyBib
        import PyGui

        self.bib = PyBib.Bibliography()
        self.table = PyRef.PyRefTable(self.bib, self.bib.labels(), "label", "journal", "year", "volume", "pages", "authors", "title")
        self.window = gtk.Window(gtk.WINDOW_TOPLEVEL)
        self.window.connect("destroy", self.close)
        self.window.set_title("References")

        hbox = gtk.HBox(False)

        #file buttons
        load_button = gtk.Button("Load Bibliography")
        load_button.connect("clicked", self.load)
        hbox.pack_start(load_button, False)
        upd_button = gtk.Button("Update Bibliography")
        upd_button.connect("clicked", self.update)
        hbox.pack_start(upd_button, False)

        self.entry = gtk.Entry(100)
        self.entry.connect("key-release-event", self.filter)
        self.filterstr = ''
        hbox.pack_start(self.entry, True)
        button = gtk.Button("Insert References")
        button.connect("clicked", self.insert_refs)
        hbox.pack_end(button, False)

        vbox = gtk.VBox()
        vbox.pack_start(hbox, False)

        self.scrollwindow = gtk.ScrolledWindow()
        self.scrollwindow.add(self.table.getTree())
        vbox.pack_start(self.scrollwindow)
        self.window.add(vbox)
        self.window.show_all()
        
        self.tables = [ TableFilter(self.table, self.filterstr) ]

    def filter(self, widget, data=None):
        text =  self.entry.get_text()
        cmds = text.strip().split()
        filterstrs = []
        for cmd in cmds:
            splitcmd = cmd.split("=")
            if len(splitcmd) != 2:
                continue
            attr, val = splitcmd
            if not attr or not val:
                continue #also not valid

            filterstrs.append("%s=%s" % (attr, val))

        filterstr = " ".join(filterstrs)
        if filterstr == self.filterstr:
            return #nothing to do
        else:
            self.filterstr = filterstr
            self.scrollwindow.remove(self.table.getTree())
            #check to see if the filterstr exists in the current set
            exists = False
            for table in self.tables:
                if table.matches(filterstr):
                    exists = True
                    break

            if exists: #pop back until we get the match
                match = False
                while self.tables:
                    filter = self.tables.pop()
                    if filter.matches(filterstr):
                        self.table = filter.getTable()
                        self.scrollwindow.add(self.table.getTree())
                        self.window.show_all()
                        self.tables.append(filter)
                        return
            else: #does not exist, make a new one
                import PyBib
                newtable = None
                try:
                    newtable =  self.table.filter(filterstr)
                except PyBib.BadMatchAttribute, error:
                    print error
                    #build blank table
                    newtable = self.table.subset([]) #build null table
                newfilter = TableFilter(newtable, filterstr)
                self.table = newtable
                self.tables.append(newfilter)
                self.scrollwindow.add(self.table.getTree())
                self.window.show_all()
                return

    def updateBib(self, files):
        import PyBib, os.path
        if isinstance(files, str): #single file
            files = [files]

        for file in files:
            bib = loadBibliography(file)
            if bib:
                self.table.addReferences(bib)

    def loadBib(self, files):
        pass

    def update(self, widget, data=None):
        import PyGui
        import os
        home = os.environ["HOME"]
        filesel = PyGui.FileSelect(home, self.updateBib)

    def load(self, widget, data=None):
        import PyGui
        import os
        home = os.environ["HOME"]
        filesel = PyGui.FileSelect(home, self.loadBib)

    def close(self, widget, data=None):
        import gtk
        gtk.main_quit()

    def insert_refs(self, widget, data=None):
        refs = self.table.getSelected()
        import PySock
        comm = PySock.Communicator(self.REF_LISTEN_PORT)
        nfailed = 0
        sent = False
        while not sent:
            try:
                comm.sendObject(refs)
                comm.close()
                sent = True
            except Exception, error:
                nfailed += 1

                if nfailed == 5: #too many failures
                    raise error

def walkForBibs(folder):

    def checkFolder(args, dirname, files):
        import glob, os, os.path
        topdir = os.getcwd()
        os.chdir(dirname)
        allbib = args
        xmlfiles = [elem for elem in files if elem.endswith('xml')]
        for file in xmlfiles:
            allbib.buildRecords(file)
        os.chdir(topdir)

    import os.path, PyBib
    allbib = PyBib.Bibliography()
    os.path.walk(folder, checkFolder, allbib)

    return allbib

def openBibFile(file):
    bibobj = None
    if file.endswith("xml"):
        import PyBib
        bibobj = PyBib.Bibliography()
        bibobj.buildRecords(file)
    else:
        import PySave
        try:
            bibobj = PySave.load(file)
        except Exception, error:
            pass

    return bibobj

def loadBibliography(bibpath):
    
    import os.path
    bibobj = None
    if os.path.isdir(bibpath):
        bibobj = walkForBibs(bibpath)
    else:
        bibobj = openBibFile(bibpath)

    return bibobj

def setBiblography(bibpath):
    bibobj = loadBibliography(bibpath)
    if not bibobj:
        return #nothing to do

    if hasattr(PyTexGlobals, "bib"):
        oldbib = getattr(PyTexGlobals, "bib")
        oldbib.update(bibobj)
        setattr(PyTexGlobals, "bib", oldbib)
    else:
        setattr(PyTexGlobals, "bib", bibobj)

def startLatex():
    import gtk
    cite = CiteManager()
    cite.updateBib("/Users/jjwilke/Documents/Projects")
    gtk.main()

import threading
class CiteThread(threading.Thread):

    def __init__(self, citation):
        
        import PySock
        self.citation = citation
        self.stopthread = threading.Event()
        self.server = PySock.Communicator(CiteManager.REF_LISTEN_PORT)
        self.server.bind()

        threading.Thread.__init__(self)

    def run(self):
        while not self.stopthread.isSet():
            try:
                objlist = self.server.acceptObject()
                if objlist: #if we got a list of objects
                    self.citation.addReferences(objlist)
                    
            except Exception, exc:
                print exc

        self.server.close()

    def stop(self):
        import PySock
        self.stopthread.set()
        comm = PySock.Communicator(CiteManager.REF_LISTEN_PORT)
        comm.sendObject([]) #send blank array to bring down thread

class Citation:

    def __init__(self, title, bib, entries):
        import PyRef
        import pygtk
        import gtk
        self.table = PyRef.PyRefTable(bib, entries, "journal", "year", "volume", "pages", "authors", "title")
        self.window = gtk.Window(gtk.WINDOW_TOPLEVEL)
        self.window.set_title(title)
        self.vbox = gtk.VBox()
        self.erase_button = gtk.Button("Delete selected")
        self.erase_button.connect("clicked", self.delete_refs)
        self.vbox.pack_start(self.erase_button, False)
        self.scrollwindow = gtk.ScrolledWindow()
        self.scrollwindow.add(self.table.getTree())
        self.vbox.pack_end(self.scrollwindow, True)
        self.window.add(self.vbox)
        self.window.show_all()

        #self.window.connect("focus-in-event", self.start_listening)
        #self.window.connect("focus-out-event", self.stop_listening)
        self.window.connect("destroy", self.close)

        self.thread = CiteThread(self)
        self.thread.start()

    def addReferences(self, refs):
        self.table.addReferences(refs)

    def delete_refs(self, widget, data=None):
        self.table.removeSelected()

    def close(self, widget, data=None):
        import pygtk
        import gtk
        self.thread.stop()
        gtk.main_quit()

    def getEntries(self):
        return self.table.getEntries()

def processInitFlag(flag):
    opts = flag.lower().strip().split()
    name = opts[0]
    options = opts[1:]

    if name == "bibliography":
        if not options:
            return #nothing there
        loadBibliography(options[0])
    

def init(flags):
    for flag in flags:
        processInitFlag(flag)

def loadCitation():
    import PyVim, re
    import pygtk
    import gtk
    cword = PyVim.getCurrentWord()
    entries = []
    if '\cite{' in cword: #we are currently on a citation
        #get the entries within the citation
        innards = re.compile(r'cite[{](.*?)[}]').search(cword).groups()[0].strip()
        if innards:
            entries = map(lambda x: x.strip(), innards.split(","))
        else:
            entries = []
    else: #no citation, but put one in
        PyVim.appendAtWord("\cite{}")
        cword = "\cite{}"

    #build the citation
    bib = getattr(PyTexGlobals, "bib")
    title = "Reference at line %d" % PyVim.line
    citeobj = Citation(title, bib, entries)

    gtk.gdk.threads_init()
    gtk.gdk.threads_enter()
    gtk.main()
    gtk.gdk.threads_leave()

    #use the citation object to generate the new reference
    entries = citeobj.getEntries()
    labels = []
    for entry in entries:
        labels.append(str(entry.getAttribute("label")))
    newtext = "\cite{%s}" % ",".join(labels)
    PyVim.replace(cword, newtext)

if __name__ == "__main__":
    startLatex()
