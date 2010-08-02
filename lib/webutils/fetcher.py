PROGRAM_DICTIONARY = {
    "NWCH" : "NWChem",
    "GAUS" : "Gaussian94",
    "DALT" : "Dalton",
    "ACES" : "ACESII",
    }
import re
import sys
import time
from selenium import selenium

def getBasisSet(basis, atomList, verbatim=False):
    import urllib
    import chem.basisset

    program = "Gaussian94"
    atoms = []
    #we want to work with atom objects, not atom names
    from chem.molecules import Atom
    for atom in atomList:
        if not isinstance(atom, Atom): 
            atom = Atom(atom)
        atoms.append(atom)
    basisText = getBasis(atoms, basis, program, verbatim)
    print basisText
    basisSet = chem.basisset.processBasisText(basisText, atomList, program)
    return basisSet

def getBasis(atomList, basis="STO-3G", program="Gaussian94", verbatim=False):    
    import urllib
    import chem.basisset
    

    def fix_basis(basis):
        if verbatim:
            return basis

        basis=basis.upper()

        def checkPlusD(basis):
            reTest = re.compile(r"\(([DTQ56])\+D\)").search(basis)
            if reTest:
                replacement = reTest.groups()[0]
                basis = basis.replace(r"(%s+D)" % replacement, replacement)
            return basis    
       
        if atom.isHydrogenic():
            basis = basis.replace("CC-PC", "CC-P").replace("CC-PWC", "CC-P")
            basis = checkPlusD(basis)
        elif atom.isFirstRow():
            basis = checkPlusD(basis)
        basis = basis.upper().replace("W", "w").replace("CC-P", "cc-p").replace("AUG", "aug").replace("+D", "+d")
        return basis

    prog_name = PROGRAM_DICTIONARY[ program[:4].upper() ]

    print "Fetching", basis
    text_arr = ["****"]
    sel = selenium("localhost", 4444, "*chrome", "https://bse.pnl.gov/")
    sel.start()
    sel.open("/bse/portal")
    sel.select_frame("Main11535052407933")
    sel.select("outputcode", "label=Gaussian94")
    sel.click("contraction") #turn off optimize general contractions
    for atom in atomList:
        submit_basis = fix_basis(basis)
        sel.select("blist", "label=%s" % submit_basis)
        number = "%d" % atom.getAtomicNumber()
        sel.type("searchstr", submit_basis)
        sel.click(number)
        sel.click("getBasisSet")
        sel.wait_for_pop_up("", "30000")
        main, popup = sel.get_all_window_titles()
        sel.select_window(popup)
        response = sel.get_body_text()
        sel.close()
        sel.select_window(main)
        sel.click(number) #deselect atom
        text = re.compile("[*]{4}\n(.*)", re.DOTALL).search(response).groups()[0]
        text_arr.append(text)
    sel.click("getBasisSet")
    sel.stop()

    return "\n".join(text_arr)

def getPetersonBasis(atom, basis, program, ri = False):    
    import urllib
    import chem.basisset
    
    #we want to work with atom objects, not atom names
    from chem.molecules import Atom
    if not isinstance(atom, Atom):
        atom = Atom(atom)

    url = 'http://tyr0.chem.wsu.edu/~kipeters/basissets/basisformf12.php'
    if ri:
        url = 'http://tyr0.chem.wsu.edu/~kipeters/basissets/basisform_optri1.php'
    urlObj = urllib.URLopener()
    query = urllib.urlencode({"element":atom.getSymbol(nice=True), "basis": "%s" % basis,  "program": program})
    response = urlObj.open(url, query).read()

    import html2text
    response = html2text.html2text(response)
    htmlCleanBasis = re.compile("BASIS.*?\n(.*[*]{4})", re.DOTALL).search(response)

    #okay, we should have found a reg expression that works by now
    htmlCleanBasis = htmlCleanBasis.groups()[0]
    clean_basis = []
    for line in htmlCleanBasis.splitlines():
        #if a comment line, don't include
        if len(line) > 0 and line[0] == "!": pass
        else: clean_basis.append(line)    
    
    #return both the basis text and the name of the basis because it may have changed
    return "\n".join(clean_basis)
