import threading
import time

nthread = 1

import pygtk
import gtk

gtk.gdk.threads_init()

class PyApp(gtk.Window):

    def __init__(self, threads=None):
        super(PyApp, self).__init__()
         
        self.connect("destroy", self.quit)
        self.set_title("pyGTK Threads Example")

        self.button = gtk.Button("test me")
        self.button.connect("clicked", self.ack_click)

        self.add(self.button)

        self.threads = []
        for i in range(nthread):
            self.threads.append( ListenThread(i) )

        self.show_all()

    def ack_click(self, widget, data=None):
        print "I was clicked"
     
    def quit(self, obj):
        for t in self.threads:
            t.stop()
         
        gtk.main_quit()

class ListenThread(threading.Thread):

    def __init__(self, n):
        self.n = n
        threading.Thread.__init__(self)
        self.stopthread = threading.Event()

    
    def run(self):
        while not self.stopthread.isSet():
            #gtk.gdk.threads_enter()
            print "Running thread %d" % self.n
            time.sleep(2)
            #gtk.gdk.threads_leave()

    def stop(self):
        self.stopthread.set()


if __name__ == "__main__":
    pyapp = PyApp()

    for t in pyapp.threads:
        t.start()
        
    gtk.gdk.threads_enter()
    gtk.main()
    gtk.gdk.threads_leave()
