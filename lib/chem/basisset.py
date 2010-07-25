import re,sys,os,os.path 
import skynet.identity
from skynet.utils.utils import *

ANGULAR_MOMENTUM_VALUES = {"S" : 0, "P" : 1, "D" : 2,
              "F" : 3, "G" : 4, "H" : 5,
              "I" : 6, "K" : 7}

ANGULAR_MOMENTUM_LETTERS = {
    0 : "S", 1 : "P", 2 : "D", 3 : "F", 4 : "G", 5: "H", 6 : "I", 7 : "K",
    }

BASIS_NUMBERS = {
    "DZ" : 2,
    "TZ" : 3,
    "QZ" : 4,
    "5Z" : 5,
    "6Z" : 6,
    "7Z" : 7,
    "CBS" : "CBS"
    }

BASIS_LABELS = {
    2 : "DZ",
    3 : "TZ",
    4 : "QZ",
    5 : "5Z",
    6 : "6Z",
    7 : "7Z",
    "CBS" : "CBS"
    }

BASIS_LETTERS = {
    2 : "D",
    3 : "T",
    4 : "Q",
    5 : "5", 
    6 : "6",
    7 : "7",
    "CBS" : "CBS",
}

BASIS_REGEXP = "([tdq56x])z"

class Basis(skynet.identity.Identity):

    def __init__(self, basis):
        self.basis = str(basis).lower()
        percent = '%s'
        self.basisTemplate = re_replace(BASIS_REGEXP, self.basis, percent)

    def __eq__(self, val):
        #does this basis match an integer
        if isinstance(val, int): 
            selfnum = getBasisNumber(self.basis)
            return val == selfnum
        #does this basis match a generic dz, tz, qz label
        elif isinstance(val, Basis):
            return self.basis.lower() == val.basis.lower()
        else:
            try: #attempt to treat it like a string
                testval = str(val).lower()
                if len(testval) == 2 and re.compile(BASIS_REGEXP).search(testval):
                    othernum = getBasisNumber(val)
                    selfnum = getBasisNumber(self.basis)
                    return othernum == selfnum
                else:
                    return self.basis == testval
            except Exception:
                return False

    def __contains__(self, other):
        return other in self.basis

    def __getslice__(self, s, f):
        return self.basis[s:f]

    def __int__(self):
        return getBasisNumber(self)

    def __float__(self):
        return getBasisNumber(self)

    def __str__(self):
        return self.basis

    def __repr__(self):
        return self.basis

    def __hash__(self):
        return hash(self.basis)

    def __len__(self):
        return len(self.basis)

    def __mod__(self, other):
        return self.replace(other)

    def replace(self, *xargs):
        if len(xargs) == 2:
            match, repl = xargs
            return Basis(self.basis.replace(match, repl))

        val = xargs
        try:
            repl = str(val[0])
            if repl.lower() == "cbs":
                return Basis("cbs")
            elif "cc-" in repl.lower():
                return Basis(repl)
        except:
            pass

        num = getBasisNumber(val[0])
        letter = getBasisLetter(num)
        return Basis(self.basisTemplate % letter)

    def setBasisFromFolder(self, folder):
        root, last_folder = os.path.split(folder)
        if re.compile(BASIS_REGEXP).search(last_folder): #folder indicates basis
            self.basis = last_folder

    def lower(self):
        return Basis(self.basis.lower())

    def upper(self):
        return Basis(self.basis.upper())

    def __lt__(self, other):
        if self == "CBS" and other == "CBS":
            return False
        elif self == "CBS" and not other == "CBS":
            return False
        elif not self == "CBS" and other == "CBS":
            return True
        else:
            return getBasisNumber(self) < getBasisNumber(other)

    def __gt__(self, other):
        if self == "CBS" and other == "CBS":
            return False
        elif self == "CBS" and not other == "CBS":
            return True 
        elif not self == "CBS" and other == "CBS":
            return False
        return getBasisNumber(self) > getBasisNumber(other)
        
def getBasisSetsUpTo(maxBasis, diffuse=False, core=False, secondRow=False, basisTemplate=None):
    
    if isInteger(maxBasis): basisNumber = maxBasis
    else: 
        basisNumber = getBasisNumber(maxBasis)

    template=""
    if basisTemplate: template = basisTemplate
    else:
        if diffuse: template += "AUG-"

        template += "CC-P"

        if core: template += "C"
        
        template += "V"

        if secondRow: template += '(%s+d)Z'
        else: template += '%sZ'

    basisLabels = map(getBasisLetter, range(2,basisNumber+1))
    basisList = []
    for label in basisLabels:
        basisList.append( template % label )

    return basisList

def getBasisLetter(number):
    letter = BASIS_LETTERS[number]
    return letter

def getBasisNumber(basis):
    if isinstance(basis, int):
        return basis
    #not an integer
    basis = str(basis).upper()
    if basis == "CBS":
        return "CBS"
    else:
        number = re.compile("([DTQ567]Z)").search(basis.upper())
        if number: return BASIS_NUMBERS[ number.groups()[0] ]
        else: return None

class Shell(skynet.identity.Identity):

    # @param basisDictionary The basis set dictionary that holds all the basis function
    #        Dictionary has the form key = angular momentum, value = list of basis functions
    def __init__(self, atom, angularMomentum, exponents, coefficients):
        self.atom = atom.upper()
        self.angularMomentum = angularMomentum.upper()
        self.exponents = exponents[:]
        self.coefficients = coefficients[:]

    def __repr__(self):
        return self.angularMomentum

    def __str__(self):
        str_array = [self.angularMomentum]
        for i in range(0, len(self.exponents)):
            line_arr = ["%12.8f" % self.exponents[i]]
            for func in self.coefficients:
                line_arr.append("%12.8f" % func[i])
            str_array.append("\t".join(line_arr))
        return "\n".join(str_array)

    def contains(self, other):
        for exp in other.getExponents():
            if not exp in self.exponents:
                return False
        return True

    def matches(self, other):
        if len(self.exponents) == len(other.exponents) and self.contains(other):
            return True
        return False

    def getUncontractedShells(self):
        allshells = []
        for exp in self.exponents:
            newcoeffs = [[1.0]]
            newexps = [exp]
            newshell = Shell(self.atom, self.angularMomentum, newexps, newcoeffs)
            allshells.append(newshell)
        return allshells

    def add(self, other):
        oldlength = len(self.coefficients)
        for func in other:
            self.coefficients.append( [0]*len(self.exponents) )
        for exp, coefflist in other.getCoefficientsAndExponents():
            i = 0
            while abs(exp - self.exponents[i]) > 1e-12:
                i += 1
            for j in range(0, len(coefflist)):
                self.coefficients[j + oldlength][i] = coefflist[j]
    
    def getLargestExponent(self):
        explist = self.exponents[:]
        explist.sort()
        return explist[-1]

    def getExponents(self):
        return self.exponents

    def getCoefficients(self):
        return self.coefficients

    def getAngularMomentum(self):
        return self.angularMomentum

    def getCoefficientsAndExponents(self):
        arr = []
        for i in range(0, len(self.exponents)):
            arr.append([self.exponents[i]])
            coeffs = []
            for func in self.coefficients: 
                coeffs.append( func[i] )
            arr[-1].append(coeffs)
        return arr

    def __lt__(self, other):
        selfval = ANGULAR_MOMENTUM_VALUES[self.angularMomentum]
        otherval = ANGULAR_MOMENTUM_VALUES[other.angularMomentum]
        return selfval < otherval

    def __eq__(self, other):
        selfexps = self.getExponents()
        otherexps = other.getExponents()
        if not arraysEqual(selfexps, otherexps):
            return False

        selfcoeffs = self.getCoefficients()
        othercoeffs = other.getCoefficients()

        if not len(selfcoeffs) == len(othercoeffs):
            return False

        for i in xrange(len(selfcoeffs)):
            selfarr = selfcoeffs[i]
            otherarr = othercoeffs[i]
            if not arraysEqual(selfarr, otherarr):
                return False

        return True

    def __gt__(self, other):
        if ANGULAR_MOMENTUM_VALUES[self.angularMomentum] > ANGULAR_MOMENTUM_VALUES[other.angularMomentum]:
            return True
        return False
    
    def __iter__(self):
        return iter(self.coefficients)
    
    def __len__(self):
        return len(self.coefficients)

class BasisSet(skynet.identity.Identity):

    ## Constructor
    #  @param basisDictionary The basis set dictionary that will hold all the basis functions
    #         The dictionary has the format key1 = atom, key2 = angular momentum  
    def __init__(self, basisDictionary = {}):
        self.basisDictionary = basisDictionary.copy()

    def __str__(self):
        text_array = []
        for atom in self.basisDictionary:
            text_array.append("-------- %s --------" % atom)
            for shell in self.basisDictionary[atom]:
                text_array.append( str(shell) )
        return "\n".join(text_array)

    def __iter__(self):
        return iter(self.basisDictionary)

    def __getitem__(self, key):
        return self.basisDictionary[key.upper()]

    def __setitem__(self, key, item):
        self.basisDictionary[key.upper()] = item

    def append(self, newBasis):
        for atom in newBasis:
            if not atom.upper() in self:
                self[atom] = newBasis[atom]

    def decontractAtom(self, atom):
        newbasis = self.copy()
        newbasis[atom] = [] #clear the atom
        basis = self.basisDictionary[atom]
        newshells = []
        for shell in basis:
            uncshells = shell.getUncontractedShells()
            for ush in uncshells:
                newbasis.addShell(atom, ush)
        return newbasis

    def decontract(self):
        #set up a blank basis
        newbasis = self.copy()
        for atom in self.basisDictionary:
            newbasis = newbasis.decontractAtom(atom)
        return newbasis

    def addShell(self, atom, shell):
        if not self.hasShell(atom, shell):
            self.basisDictionary[atom].append(shell)

    def hasShell(self, atom, shell):
        for selfshell in self.basisDictionary[atom]:
            if selfshell == shell:
                return True
        return False

    def getNumberOfAngMomTerms(self, atom):
        shells = self.basisDictionary[atom]
        angdict = {}
        for shell in shells:
            angmom = shell.getAngularMomentum()
            angdict[angmom] = angmom
        return len(angdict)

    def getCombinedShell(self, atom, angval):
        angmom = ANGULAR_MOMENTUM_LETTERS[angval]

        shells = self.basisDictionary[atom]
        allexps = []
        allcoeffs = []
        for shell in shells:
            if not shell.getAngularMomentum() == angmom:
                continue

            exps = shell.getExponents()
            coeffs = shell.getCoefficients()
            #the coefficients for all old functions on the next exps is zero
            for func in allcoeffs:
                newarr = [0] * len(exps)
                func.extend(newarr)
            for func in coeffs:
                #the coefficients for new functions for old exps is zero
                newcoeffs = [0] * len(allexps)
                newcoeffs.extend(func)
                allcoeffs.append(newcoeffs)
            #add in new exps
            allexps.extend(exps)

        newshell = Shell(atom, angmom, allexps, allcoeffs)

        return newshell

    def getAtoms(self):
        return self.basisDictionary.keys()

    def getAtomShells(self, atom):
        return self.basisDictionary[atom.upper()]
    
    def getNumberOfShells(self, atom):
        return len( self.basisDictionary[ atom.upper() ] )
    
                    
    def writeBasis(self, program, file="basis.dat", name="CUSTOM"):
        text = PROGRAM_LIST[program.upper()](self, name)
        open(file, "a").write(text)

    def getBasisText(self, program, name="CUSTOM", atomList=None):
        import string
        if atomList: atomList = map(string.upper, atomList)
        text = PROGRAM_LIST[program.upper()](self, name, atomList)
        return text

        
def processBasisText(basisText, atomList, program):
    basisMethods = {
        "Gaussian94" : readGaussianBasis
        }
        
    method = basisMethods[program]
    basisSet = method(basisText, atomList)
    
    return basisSet

def readGaussianBasis(basisText, atomList):
    regExp = r"(\D{1,2})\s+0(.*?)[*]{4}"
    basisAreas = re.compile(regExp, re.DOTALL).findall(basisText)
    basisDictionary = {}
    for atom, area in basisAreas:
        shells = []
        shellInputs = []
        shellRegExp = "(\w)\s+\d+\s+\d"
        for line in area.splitlines():
            line = line.strip()
            reobj =  re.compile(shellRegExp).search(line)
            if reobj:
                shellInputs.append([])
                angmom = reobj.groups()[0]
                shellInputs[-1].append(angmom)
            elif shellInputs and line:
                shellInputs[-1].append(line)
        for input in shellInputs:
            angmom = input[0]
            coefficients = []
            exponents = []
            for line in input[1:]:
                exp, coeff = map(eval, line.strip().split())
                coefficients.append(coeff)
                exponents.append(exp)
            newShell = Shell(atom, angmom, exponents, [coefficients])

            merged = False
            for shell in shells:
                if shell.matches(newShell):
                    shell.add(newShell)
                    merged = True
                    continue
            if not merged:
                shells.append(newShell)

        basisDictionary[atom.strip().upper()] = shells

    basis = BasisSet(basisDictionary)
    return basis


def printPsiBasis(basisSet, basisName, atomList):
    import chem.molecules
    atomList = basisSet.getAtoms()
    textArray = ["BASIS: ("]
    for atom in atomList:
        atomName = chem.molecules.getInfo("name", atom)
        textArray.append("%s : \"%s\" = (" % (atomName, basisName.upper()))
        shells = basisSet[atom]
        shells.sort()
        for shell in shells:
            angmom = shell.getAngularMomentum()
            exps = shell.getExponents()
            coeffs = shell.getCoefficients()
            for func in coeffs:
                func_text = [r"(%s   (%12.8f   %12.8f)" % (angmom, exps[0], func[0])]
                for i in xrange(1, len(exps)):
                    func_text.append(r"     (%12.8f   %12.8f)" % (exps[i], func[i]))
                func_text[-1] += r")"
                textArray.append("\n".join(func_text))
        textArray.append("  )")
    textArray.append(")")    
    return "\n".join(textArray)
    
def printMolproBasis(basisSet, basisName, atomList):
    exp_format = "%14.7E"
    coeff_format = "%14.7E"
    import chem.molecules
    atomList = basisSet.getAtoms()
    textArray = [""]
    for atom in atomList:
        for shell in basisSet[atom]:
            angular_momentum = shell.getAngularMomentum()
            currentLine = [ angular_momentum.lower(), atom ]
            exponents = shell.getExponents()
            for exponent in exponents:
                currentLine.append( exp_format % exponent )
            textArray.append( ",".join(currentLine) )
            coefficients = shell.getCoefficients()
            for basis_function in coefficients:
                coeffs_to_write = []
                for coeff in basis_function:
                    coeffs_to_write.append(coeff_format % coeff)
                currentLine = "c,%d.%d," % (1, len(exponents))
                currentLine += ",".join(coeffs_to_write)
                textArray.append( currentLine ) 

    finalText = "\n".join(textArray)
    return finalText

def printACESBasis(basisSet, basisName, atomList):
    import chem.molecules
    atomList = basisSet.getAtoms()
    textArray = []
    for atom in atomList:
        #do the header
        numangmom = basisSet.getNumberOfAngMomTerms(atom)
        textArray.append("%s:%s" % (atom.upper().strip(), basisName) )
        textArray.append("CUSTOM BASIS SET")
        textArray.append("")
        textArray.append("%3d" % numangmom)
        #tell how many shells
        currentLine = ""
        combinedShells = []
        for i in range(0, numangmom):
            currentLine += "%5d" % i
            combinedShell = basisSet.getCombinedShell(atom, i)
            combinedShells.append(combinedShell)
        textArray.append(currentLine) ; currentLine = "" 
        for shell in combinedShells:
            numfuncs = len(shell.getCoefficients())
            currentLine += "%5d" % numfuncs
        textArray.append(currentLine) ; currentLine = "" 
        for shell in combinedShells:
            numprims = len(shell.getExponents())
            currentLine += "%5d" % numprims
        textArray.append(currentLine) ; currentLine = "" 
        textArray.append("")
                
        #now go through and explicitly write out all the exponents and cofficients
        for shell in combinedShells:
            exponents = shell.getExponents()
            coefficients = shell.getCoefficients()
            #write out all the exponents
            for exponent in exponents:
                if len(currentLine) + 14  > 80: 
                    textArray.append(currentLine) ; currentLine = ""
                currentLine += "%14.6f" % exponent
            textArray.append(currentLine)
            currentLine = ""
            textArray.append("")
            for i in range(len(exponents)):
                for func in coefficients:
                    if len(currentLine) + 10  > 80: 
                        textArray.append(currentLine) ; currentLine = ""
                    currentLine += "%10.7f " % func[i]
                textArray.append(currentLine.rstrip()) ; currentLine = ""
            textArray.append("")    

    return "\n".join(textArray)    

def printMPQCBasis(basisSet, basisName, atomList = None):
    import chem.molecules
    if not atomList: atomList = basisSet.getAtoms()
    textArray = []
    for atom in atomList:
        textArray.append( "%s : \"%s\" : [" % (chem.molecules.getInfo("name", atom).lower(), basisName) )  
        numShells = basisSet.getNumberOfShells(atom)
        for shell in basisSet.getAtomShells(atom):
            topLine = '(type: ['
            primLine = "{ exp"
            numFunctions = len(shell)
            angType = shell.getAngularMomentum()
            i = ANGULAR_MOMENTUM_VALUES[angType]
            for j in range(0, numFunctions):
                if i <= 1: #no need to specify spherical for s,p functions
                    topLine += " am = %s " % angType.lower()
                else:
                    topLine += " (am = %s puream=1) " % angType.lower()
                primLine += " coef:%d " % j
            topLine += "]" ; textArray.append(topLine)
            primLine += "} = {" ; textArray.append(primLine)
            exponents = shell.getExponents()
            functions = shell.getCoefficients()
            #on each line write the exponent and all the contraction coefficients
            current_line = []
            for expnum in range(0, len(exponents)):
                current_line.append("%16.8f" % exponents[expnum])
                for function in functions:
                    coeff = function[expnum]
                    if coeff < 0:
                        current_line.append("%9.6E" % coeff)
                    else:
                        current_line.append(" %8.6E" % coeff)
                textArray.append( " ".join(current_line) )
                current_line = []
            textArray.append("})")
        textArray.append("]")

    return "\n".join(textArray)
                
def printMPQCRIBasis(basisSet, basisName, atomList = None):
    import chem.molecules
    if not atomList: atomList = basisSet.getAtoms()
    textArray = []
    for atom in atomList:
        textArray.append("basis:%s:\"%s\": [" % ( chem.molecules.getInfo("name", atom).lower(), basisName) )
        for shell in basisSet[atom]:
            exponents = shell.getExponents()
            angType = shell.getAngularMomentum()
            for exp in exponents:
                topLine = '(type: [ (am = %s puream=1) ]' % angType
                primLine = "{ exp coef:0 } = {"
                textArray.append(topLine)
                textArray.append(primLine)
                textArray.append("%16.8f %8.6E" % (exp, 1.0))
                textArray.append("})")
        textArray.append("]")
    return "\n".join(textArray)

def printGaussianBasis(basisSet, basisName, atomList = None):
    import chem.molecules
    textArray = []
    if not atomList:   
        atomList = basisSet.getAtoms()
    for atom in atomList:
        textArray.append("%s 0" % atom)
        for shell in basisSet[atom]:
            angmom = shell.getAngularMomentum()
            exps = shell.getExponents()
            for func in shell.getCoefficients():
                textArray.append("%s    %d 1.0" % (angmom, len(exps)))
                for i in xrange(len(func)):
                    textArray.append("    %16.10f %16.10f" % (exps[i], func[i]))
        textArray.append("****")
                    
    return "\n".join(textArray)
            
    

def cleanBasisName(basis):
    return basis.replace(")","").replace("(","").replace("+", "-")

PROGRAM_LIST = {
        "PSI" : printPsiBasis,
        "ACES" : printACESBasis,
        "MPQC" : printMPQCBasis,
        "MPQCRI" : printMPQCRIBasis,
        "MOLPRO" : printMolproBasis,
        "GAUSSIAN" : printGaussianBasis,
        "QCHEM" : printGaussianBasis, #qchem and gaussian currently have same format
        }
