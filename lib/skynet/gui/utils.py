
class gtkout(StringIO):
    
    def __init__(self, name):
        StringIO.__init__(self)
        self.textview = gtk.TextView(buffer)
        self.buffer = self.textview.get_buffer()
        window = gtk.Window(gtk.WINDOW_TOPLEVEL)
        window.connect("destroy", gtk.main_quit)
        window.set_title(name)
        gtk.main()

    def write(self, text):
        iter = self.buffer.get_end_iter()
        self.buffer.insert(iter, text)
