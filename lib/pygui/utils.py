
from StringIO import StringIO
from gtkserver import gtkout

def display(text):
    import gtk
    textview = gtk.TextView()
    buffer = textview.get_buffer()
    window = gtk.Window(gtk.WINDOW_TOPLEVEL)
    window.connect("destroy", gtk.main_quit)
    window.set_title("message")
    window.add(textview)
    window.show_all()
    window.maximize()
    buffer.set_text(text)
    gtk.main()

def input(title = "query"):
    import gtk

    class text_get:
        
        def __init__(self, buffer):
            self.buffer = buffer
        
        def get(self, widget, info = None):
            self.text = self.buffer.get_text(self.buffer.get_start_iter(), self.buffer.get_end_iter())
            gtk.main_quit(widget)

    textview = gtk.TextView()
    textview.set_editable(True)
    buffer = textview.get_buffer()
    window = gtk.Window(gtk.WINDOW_TOPLEVEL)
    info = text_get(buffer)
    window.connect("destroy", info.get)
    window.set_title(title)
    window.add(textview)
    window.show_all()
    window.maximize()
    gtk.main()

    return info.text


class gtkIO:
    
    guiprint = False

    def println(cls, line):
        if cls.guiprint:
            out = gtkout()
            out.write(line)
        else:
            print line

    def redirect_io(cls):
        cls.guiprint = True

    redirect_io = classmethod(redirect_io)
    println = classmethod(println)

def gtkprint(msg):
    gtkIO.println(msg)


