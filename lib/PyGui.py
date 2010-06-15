import pygtk
import gtk
class FileSelect:
    
    def __init__(self, default, callback, main=False):
        self.selections = []
        self.filesel = gtk.FileSelection()
        self.filesel.ok_button.connect("clicked", self.ok_sel)
        self.filesel.cancel_button.connect("clicked", self.cancel_sel)
        self.filesel.hide_fileop_buttons()
        self.filesel.set_select_multiple(True)
        self.callback = callback

        if main: #we need to bring down gtk when we quit
            self.filesel.connect("destroy", gtk.main_quit)

        if default:
            self.filesel.set_filename("")

        self.filesel.show()

    def ok_sel(self, widget, data=None):
        self.selections = self.filesel.get_selections()
        self.callback(self.selections)
        self.filesel.destroy()
    
    def cancel_sel(self, widget, data=None):
        self.filesel.destroy()
    
    def getFiles(self):
        return self.selections

