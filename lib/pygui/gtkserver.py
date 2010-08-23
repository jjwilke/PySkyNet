
from StringIO import StringIO

from skynet.socket.server import Server, ServerRequest, ServerAnswer
from skynet.socket.pysock import Communicator

import sys

class gtkanswer(ServerAnswer):
    
    def __init__(self):
        ServerAnswer.__init__(self, gtkserver.ANSWER_PORT)

class gtkrequest(ServerRequest):
    
    def __init__(self):
        ServerRequest.__init__(self, gtkserver.REQUEST_PORT, gtkanswer)

class gtkout(StringIO):

    def __init__(self):
        StringIO.__init__(self)

    def write(self, text):
        try:
            comm = Communicator(gtkserver.REQUEST_PORT)
            comm.open()
            comm.sendObject(text)
            comm.close()
        except:
            pass

class gtkstatuswindow(Server):

    port = None

    def __init__(self, port, name):
        import gtk
        import pygtk
        import sys
        Server.__init__(self, port, None)
        self.textview = gtk.TextView()
        self.port = port
        gtkstatuswindow.port = port
        #self.textview.set_editable(False)
        self.buffer = self.textview.get_buffer()
        self.window = gtk.Window(gtk.WINDOW_TOPLEVEL)
        self.buffer.set_text("Status Window")
        self.viewport = gtk.Viewport()
        self.viewport.add(self.textview)
        self.sw = gtk.ScrolledWindow()
        self.window.connect("destroy", gtk.main_quit)
        self.window.set_title(name)
        self.sw.set_policy(gtk.POLICY_AUTOMATIC, gtk.POLICY_AUTOMATIC)
        self.sw.add(self.viewport)
        self.window.add(self.sw)
        self.window.show_all()

    def report(self):
        pass

    def process(self, obj):
        iter = self.buffer.get_end_iter()
        self.buffer.set_text(obj)
        return ""

    def stop(self):
        pass

    def display_report(cls):
        try:
            import inspect
            frame = inspect.currentframe().f_back.f_back.f_back
            info = inspect.getframeinfo(frame)
            framestr = "%s" % str(info)
            comm = Communicator(cls.port)
            comm.open()
            comm.sendObject(framestr)
            comm.close()
        except Exception, error:
            sys.stderr.write("%s\n" % error)
    display_report = classmethod(display_report)

class gtkserver(Server):

    REQUEST_PORT = 22361
    ANSWER_PORT = None

    def __init__(self):
        Server.__init__(self, self.REQUEST_PORT, self.ANSWER_PORT)
        import gtk
        import pygtk
        import sys
        self.textview = gtk.TextView()
        #self.textview.set_editable(False)
        self.buffer = self.textview.get_buffer()
        self.window = gtk.Window(gtk.WINDOW_TOPLEVEL)
        self.viewport = gtk.Viewport()
        self.viewport.add(self.textview)
        self.sw = gtk.ScrolledWindow()
        self.window.connect("destroy", gtk.main_quit)
        self.window.set_title("stdout and stderr")
        self.sw.set_policy(gtk.POLICY_AUTOMATIC, gtk.POLICY_AUTOMATIC)
        self.sw.add(self.viewport)
        self.window.add(self.sw)
        self.window.show_all()
        self.window.maximize()

    def process(self, obj):
        iter = self.buffer.get_start_iter()
        self.buffer.insert(iter, obj)

    def report(self):
        pass

    def stop(self):
        pass


def report():
    return
    gtkstatuswindow.display_report()

