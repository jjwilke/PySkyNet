PROGRAM_DICTIONARY = {
    "NWCH" : "NWChem",
    "GAUS" : "Gaussian94",
    "DALT" : "Dalton",
    "ACES" : "ACESII",
    }
import re
import sys

def getBasisSet(basis, atomList, verbatim=False):
    import urllib
    import chem.basisset

    program = "Gaussian94"
    basis_array = []
    for atom in atomList:
        text = getBasisForAtom(atom, basis, program, verbatim)
        basis_array.append(text)
   
    basisText = "\n".join(basis_array)

    basisSet = chem.basisset.processBasisText(basisText, atomList, program)

    return basisSet

def getBasisForAtom(atom, basis="STO-3G", program="Gaussian94", verbatim=False):    
    import urllib
    import chem.basisset
    
    #we want to work with atom objects, not atom names
    from chem.molecules import Atom
    if not isinstance(atom, Atom): atom = Atom(atom)

    if not verbatim: #take the name as is... don't "spell" check it
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

    prog_name = PROGRAM_DICTIONARY[ program[:4].upper() ]
    url = "http://www.emsl.pnl.gov/cgi-bin/ecce/basis_old.pl"
    urlObj = urllib.URLopener()
    query = urllib.urlencode({"BasisSets": "%s" % basis, "Atoms":atom.getSymbol(), "Codes": prog_name,
                       "Optimize" : "off", "ECP" : "off", "Email" : "jjwilke@uga.edu"})
    response = urlObj.open(url, query).read()

    #clean up the response
    regExp = "<pre>!\n!\s+REFERENCE\n(.*?)</pre>" 
    htmlCleanBasis = re.compile(regExp, re.DOTALL).search(response)
    #that reg exp may have or have not work, try again if not
    if not htmlCleanBasis: 
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
