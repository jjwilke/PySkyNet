
class PyTexGlobals:
    pass
    
class CiteManager:
    
    REF_LISTEN_PORT = 21567

    def __init__(self):
        import PySave, os.path, PyRef
        import pygtk
        import gtk

        bib = getattr(PyTexGlobals, "bib")
        if not bib:
            sys.exit("Invalid bibliography %s" % file)
        self.table = PyRef.PyRefTable(bib, bib.labels(), "label", "journal", "year", "volume", "pages", "authors", "title")

        self.window = gtk.Window(gtk.WINDOW_TOPLEVEL)
        self.window.connect("destroy", self.close)
        self.window.set_title("References")

        hbox = gtk.HBox(False)
        entry = gtk.Entry(100)
        hbox.pack_start(entry, True)
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

def loadBibliography():
    if hasattr(PyTexGlobals, "bib"):
        return #already loaded

    import os.path, PySave
    file = os.path.join(os.path.expanduser("~"), "Documents", "pybib", "allrefs.pickle")
    bib = PySave.load(file)
    setattr(PyTexGlobals, "bib", bib)

def startLatex():
    import gtk
    loadBibliography()
    cite = CiteManager()
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
        print "listening"
        while not self.stopthread.isSet():
            try:
                objlist = self.server.acceptObject()
                print "Received %d objects" % len(objlist)
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
    print entries
    labels = []
    for entry in entries:
        labels.append(str(entry.getAttribute("label")))
    newtext = "\cite{%s}" % ",".join(labels)
    print newtext, str(newtext.__class__)
    PyVim.replace(cword, newtext)

if __name__ == "__main__":
    startLatex()
