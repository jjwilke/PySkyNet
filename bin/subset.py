import os
from PyBib import *

home = os.environ["HOME"]

xmldata = home + "/Documents/Projects/R12/R12.xml"

bib = Bibliography()
bib.buildRecords(xmldata, check=True)

print bib

sub = bib.subset("au=werner")

import PySave, os.path
path = os.path.join(os.path.expanduser("~"), "Documents", "pybib", "allrefs.pickle")
PySave.save(sub, path)

print sub

