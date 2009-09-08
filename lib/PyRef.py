import pygtk
import gtk
from PyBib import *

class PyGtkTableEntry:

    def __init__(self, data):
        
        self.visible = False
        self.data = data

    def getAttribute(self, name):
        return self.data.getAttribute(name)

    def isVisible(self):
        return self.visible
        
    def setVisible(self, visible):
        self.visible = visible

class PyGtkTable:

    def __init__(self, dataset, *cols):
        self.cols = cols[:]
        self.dataset = dataset

        self.init_model()
        self.init_view()

    def window(self):
        return self.scrollwindow

    def init_model(self):
        self.listmodel = gtk.ListStore(object)
        for entry in self.dataset:
            self.listmodel.append([entry])

    def init_view(self):
        self.treeview = gtk.TreeView()
        self.treeview.get_selection().set_mode(gtk.SELECTION_MULTIPLE)
        id = 0
        for col in self.cols:
            cell = gtk.CellRendererText()
            tvcolumn = gtk.TreeViewColumn(col, cell)
            tvcolumn.pack_start(cell, False)
            tvcolumn.set_cell_data_func(cell, self.set_cell)
            tvcolumn.set_sort_column_id(id)
            self.listmodel.set_sort_func(id, self.sort_value, tvcolumn)
            id += 1
        
            self.treeview.append_column(tvcolumn)

        self.treeview.set_model(self.listmodel)

    def is_visible(self, model, iter, data=None):
        entry = model.get_value(iter, 0)
        return entry.isVisible()

    def sort_value(self, model, iter1, iter2, column):
        name = column.get_title()
        val1 = model.get_value(iter1, 0).getAttribute(name)
        val2 = model.get_value(iter2, 0).getAttribute(name)

        if val1 < val2:
            return -1
        elif val1 > val2:
            return 1
        else:
            return 0
        
    def set_cell(self, column, cell, model, iter):
        name = column.get_title()
        entry = model.get_value(iter, 0)
        value = entry.getAttribute(name)
        cell.set_property('text', value)

    def addEntries(self, entries):
        for entry in entries:
            self.listmodel.append([entry])

    def removeSelected(self):
        model, pathlist = self.treeview.get_selection().get_selected_rows()
        for path in pathlist:
            iter = model.get_iter(path)
            model.remove(iter)

    def getSelected(self):
        model, pathlist = self.treeview.get_selection().get_selected_rows()
        vals = []
        for path in pathlist:
            iter = model.get_iter(path)
            value = model.get_value(iter, 0)
            vals.append(value)
        return vals

    def getTree(self):
        return self.treeview

class PyRefTable:

    def __init__(self, bib, entries, *cols):
        self.entries = entries[:]
        self.bib = bib

        self.entrymap = {}
        entrylist = []
        for entry in self.entries:
            gtkentry = PyGtkTableEntry(bib[entry])
            self.entrymap[entry] = gtkentry
            entrylist.append(gtkentry)

        self.table = PyGtkTable(entrylist, *cols)

        self.setBibpy()

    def addReferences(self, refs):
        entrylist = []
        for entry in refs:
            label = entry.getAttribute("label")
            if label in self.entries:
                continue #already have it

            #check to see if the reference is already in the bib
            if self.bib.hasCitation(entry):
                entry = self.bib[label]
            else:
                self.bib.addCitation(entry)
                
            gtkentry = PyGtkTableEntry(entry)
            self.entrymap[entry] = gtkentry
            entrylist.append(gtkentry)
            self.entries.append(label)

        self.table.addEntries(entrylist)

    def getEntries(self):
        entries = []
        for label in self.entries:
            entries.append(self.bib[label])
        return entries

    def getTree(self):
        return self.table.getTree()

    def getSelected(self):
        gtkentries = self.table.getSelected()
        vals = []
        for entry in gtkentries:
            vals.append(entry.data)
        return vals

    def removeSelected(self):
        entries = self.getSelected()
        for entry in entries:
            label = entry.getAttribute("label")
            idx = self.entries.index(label)
            del self.entries[idx]
            del self.entrymap[label]
        self.table.removeSelected()

    def setBibpy(cls):
        set('authors', JournalArticle, delim = ',', lastname = true, finaldelim = false)
        set('volume', JournalArticle, style = 'normal', finishdelim="")
        set('pages', JournalArticle, finishdelim="") #no style modification
        set('year', JournalArticle, parentheses = false, finishdelim = "")
        set('journal', JournalArticle, finishdelim = "") #defaults are fine
        set('title', JournalArticle, finishdelim = "")
        set('label', JournalArticle, finishdelim = "")
    setBibpy = classmethod(setBibpy)


if __name__ == "__main__":
    import PySave, os.path
    file = os.path.join(os.path.expanduser("~"), "Documents", "pybib", "allrefs.pickle")
    bib = PySave.load(file)
    if not bib:
        sys.exit("Invalid bibliography %s" % file)
    table = PyRefTable(bib, None, "journal", "year", "volume", "pages", "authors", "title")

    window = gtk.Window(gtk.WINDOW_TOPLEVEL)
    window.connect("destroy", gtk.main_quit)
    window.set_title("References")
    vbox = gtk.VBox()

    hbox = gtk.HBox(False)
    entry = gtk.Entry(100)
    hbox.pack_start(entry, True)
    button = gtk.Button("Insert References")
    button.connect("clicked", insert_refs, table)
    hbox.pack_end(button, False)
    vbox.pack_start(hbox, False)

    scrollwindow = gtk.ScrolledWindow()
    scrollwindow.add(table.getTree())
    vbox.pack_start(scrollwindow)
    window.add(vbox)
    window.show_all()
    gtk.main()

