import sys
import commands
import os.path
import pygtk
import gtk

class KeyState:
    On = "On"
    Off = "Off"

    command = Off

dirname = os.path.join(os.path.expanduser("~"), "Python")

def is_visible(model, iter, data=None):
    return True

def filter(widget, data):
    entry, filtermodel = data
    print "filtered!"

def sort_val(val1, val2):
    if val1 < val2:
        return -1
    elif val1 > val2:
        return 1
    else:
        return 0
    
def sort_name(model, iter1, iter2, col=None):
    file1 = model.get_value(iter1, 0)
    file2 = model.get_value(iter2, 0)
    return sort_val(file1, file2)

def sort_size(model, iter1, iter2, col=None):
    size1 = os.stat(os.path.join(dirname, model.get_value(iter1, 0))).st_size
    size2 = os.stat(os.path.join(dirname, model.get_value(iter2, 0))).st_size
    return sort_val(size1, size2)

def display_stats(treeview, path, column):
    model = treeview.get_model()
    iter = model.get_iter(path)
    filename = os.path.join(dirname, model.get_value(iter,0))
    ls = commands.getoutput("ls -l %s" % filename)
    print ls

def file_name(column, cell, model, iter):
    cell.set_property('text', model.get_value(iter,0))

def file_size(column, cell, model, iter):
    filename = os.path.join(dirname, model.get_value(iter,0))
    filestat = os.stat(filename)
    cell.set_property('text', filestat.st_size)

window = gtk.Window(gtk.WINDOW_TOPLEVEL)
window.connect("destroy", gtk.main_quit)
window.set_title(dirname)
files = os.listdir(dirname)
listmodel = gtk.ListStore(object)
for f in files:
    listmodel.append([f])

treeview = gtk.TreeView()

select = treeview.get_selection().set_mode(gtk.SELECTION_MULTIPLE)
filtermodel = listmodel.filter_new()
filtermodel.set_visible_func(is_visible)

column_names = ['Name', 'Size']
cell_data_funcs = [None, file_size]
sort_funcs = [sort_name, sort_size]
tvcolumn = [None] * len(column_names)
cell = gtk.CellRendererText()
tvcolumn[0] = gtk.TreeViewColumn(column_names[0], cell)
tvcolumn[0].pack_start(cell, False)
tvcolumn[0].set_cell_data_func(cell, file_name)
tvcolumn[0].set_sort_column_id(0)
filtermodel.set_sort_func(0, sort_name)
treeview.append_column(tvcolumn[0])
for n in range(1, len(column_names)):
    cell = gtk.CellRendererText()
    tvcolumn[n] = gtk.TreeViewColumn(column_names[n], cell)
    tvcolumn[n].set_cell_data_func(cell, cell_data_funcs[n])
    tvcolumn[n].set_sort_column_id(n)
    treeview.append_column(tvcolumn[n])
    filtermodel.set_sort_func(n, sort_funcs[n])



scrolledwindow = gtk.ScrolledWindow()
scrolledwindow.add(treeview)

vbox = gtk.VBox()

#entry = gtk.Entry(10)
#vbox.pack_start(entry)
#button = gtk.Button("Filter")
#button.connect("clicked", filter, (entry, filtermodel))
#vbox.pack_start(button)

vbox.pack_start(scrolledwindow)

treeview.connect('row-activated', display_stats)
treeview.set_model(filtermodel)

window.add(vbox)

window.show_all()

gtk.main()

