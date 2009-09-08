import PyTex
import os

from bibpy import *

home = os.environ["HOME"]

xmldata = home + "/Documents/Projects/R12/R12.xml"

bib = Bibliography()
bib.buildRecords(xmldata, check=False)

sub = bib.subset("au=werner")

entries = []

import pygtk
import gtk

gtk.gdk.threads_init()

cite = PyTex.Citation("test", sub, entries)

gtk.gdk.threads_enter()
gtk.main()
gtk.gdk.threads_leave()

print "hello"


