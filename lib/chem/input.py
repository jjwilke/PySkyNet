import pickle, sys, os, commands, re
from skynet.utils.utils import *
from skynet.errors import *
from skynet.identity import *
from molecules import *
from parse import *
from data import *

PYTEMP = os.environ["PYTEMP"]
PYBASIS = os.environ["PYBASIS"]
PYCHEM = os.environ["PYCHEM"] 

## The search for a template file goes in the following order
#                os.path.join(jobtype,reference,wfn),
#                os.path.join(jobtype,reference),
#                os.path.join(jobtype,wfn),
#                jobtype,
#                wfn,

KEYWORD_ATTRIBUTES = {
    "basis" : "cc-pvdz",
    "ribasis" : "aug-cc-pvtz",
    "reference" : "rhf",
    "wavefunction" : "scf",
    "jobtype" : "singlepoint",
    "coordtype" : "default",
    "memory" : 100,
    "core" : "frozen",
    "printunits" : "angstrom",
    "optconvergence" : "normal",
    "energyconvergence" : "normal",
    "ribasis" : "aug-cc-pv5z",
    "cationguess" : False,
    "occupation" : None,
    "program" : "psi",
    "r12exponent" : 1.4,
}



#the complete attribute list is the merging of molecule and computation
ATTRIBUTE_LIST = KEYWORD_ATTRIBUTES
ATTRIBUTE_LIST.update(MOLECULE_ATTRIBUTES) 

class Keyword(object):

    allowedValues = {}
    datatype = str
    classtype = None
    allowNone = False

    def __init__(self, value):
        self.setValue(value)

    def __eq__(self, other):
        if self.datatype == str:  
            return str(self.value).lower() == other
        else:
            return self.value == other

    def __ne__(self, other):
        return not self == other

    def __req__(self, other):
        return self.__eq__(other)

    def __hash__(self):
        return hash(self.value)

    def __repr__(self):
        return str(self)

    def __str__(self):
        return str(self.value)

    def __len__(self):
        try:
            return len(self.value)
        except:
            return bool(self.value)

    def __int__(self):
        return int(self.value)

    def __float__(self):
        return float(self.value)

    def __rmod__(self):
        return self.value

    def __mod__(self):
        return self.value

    def __rmul__(self, number):
        return number * self.value

    def __mul__(self, number):
        return self.value * number

    def __sub__(self, other):
        return self.value - other

    def __rsub__(self, other):
        return other - self.value

    def __add__(self, other):
        return self.value + other

    def __radd__(self, other):
        return other + self.value

    def __bool__(self):
        return True

    def split(self, flag = " "):
        return self.value.split(flag)

    def lower(self):
        return self.value.lower()

    def upper(self):
        return self.value.upper()

    def replace(self, match, repl):
        newValue = self.value.replace(match, repl)
        return self.__class__(newValue)

    def setValue(self, value):
        try:
            #if any value can be given and the type matches, cool
            if not self.allowedValues and type(value) == self.datatype:
                self.value = canonicalize(value)
            elif self.datatype == bool:
                self.value = eval( value[0].upper() + value[1:] )
            elif self.datatype == float or self.datatype == int: #attempt to cast as a number
                self.value = eval(value)
            #if only discrete values can be given and it is in the list, cool
            elif self.allowedValues:
                if not isinstance(value, str):
                    raise KeywordError("value for keyword %s must be a string" % self.__class__)
                value = value.lower()
                length = len(value)
                #in case it is abbreviated, try to match it to the correct values
                for key in self.allowedValues:
                    if value == key[:length]: 
                        self.value = key
                        return
                #if we have gotten here, then none of the allowed values matched the keyword
                raise KeywordError("value %s does not match allowed values for keyword %s\n%s" % (value, self.__class__, self.allowedValues))
            elif value == None and self.allowNone:
                self.value = value
            else: #not cool
                #attempt to cast the value
                try:
                    self.value = self.datatype(value)
                except TypeError:
                    raise KeywordError("type of value %s does not match type of %s" %  (value, self.__class__))
        except Exception, error:
            sys.stderr.write("%s\n" % error)
            raise KeywordError("%s %s" % (self.__class__, value))

    def getValue(self):
        return self.value


class GUSKeywordObject(Keyword):

    def __new__(cls, input):
        if not input: 
            return None

        if isinstance(input, str) and input.lower() == "none":
            return None

        return object.__new__(cls, input)


class TEMPLATE(GUSKeywordObject):
    
    def __init__(self, input):
        if isinstance(input, str):
            input = [input]

        self.templates = {}
        self.default = None
        for line in input:
            #set the startup values
            nextline = line.strip().split()
            pg = None
            file = None

            #see if we have a point group specification
            if len(nextline) > 1:
                pg, file = nextline
            else:
                file = nextline[0]

            #give it the absolute path
            if not file[0] == "/":
                import os, os.path
                cd = os.getcwd()
                file = os.path.join(cd, file)

            #if we have a point group
            if pg:
                self.templates[pg.lower()] = file
            else: #otherwise, make it the default
                self.default = file

            self.value = file

    def __str__(self):
        return self.makeGUSFile()

    def makeGUSFile(self):
        str_arr = []
        for pg in self.templates:
            file = self.templates[pg]
            str_arr.append("%s %s" % (pg, file))
        if self.default:
            str_arr.append(self.default)

        return "\n".join(str_arr)

    def __len__(self):
        return len(str(self.default))

    def getTemplateFile(self, pg=None):
        if pg and self.templates:
            try:
                return self.templates[pg.lower()]
            except KeyError:
                return None
        else:
            return self.default
        

class OCCUPATION(GUSKeywordObject):

    def __init__(self, input):
        self.occupations = {}
        regExp = r"([a-z\d]*)[\s=,]*([ds]occ)[\s=,]+.*?([\d ,]+)"
        for line in input:
            reMatch = re.compile(regExp, re.IGNORECASE).search(line.lower())
            if not reMatch:
                raise GUSInputError("Occupation not entered correctly")
            #spec is an optional specification for the occupation based on point group or symmetry elements
            #subspace refers to docc or socc
            spec, subspace, occupation = reMatch.groups()
            occList = map(eval, re.split("[ ,]+", occupation.strip()))
            if spec:
                if not self.occupations.has_key(spec):
                    self.occupations[spec] = {}
                self.occupations[spec][subspace] = occList
            else:
                self.occupations[subspace] = occList
        self.value  = "OCCUPATION"

    def __len__(self):
        return len(self.occupations)

    def __str__(self):
        return self.makeGUSFile()

    def _getFormattedLine(self, arr, subspace):
        return "\t%s = [ %s ]" % (subspace, " ".join(map(lambda x: "%d" % x, arr)))

    def makeGUSFile(self):
        occ_arr = []
        for key in self.occupations:
            if key == 'docc' or key == 'socc':
                subspace = key
                occ_arr.append(self._getFormattedLine(self.occupations[subspace], subspace))
            else: #special specification
                node = self.occupations[key]
                for subspace in node:
                    occ_arr.append("%s %s" % (key, self._getFormattedLine(node[subspace], subspace)))
        return "\n".join(occ_arr)

    def getOccupation(self, mol, subspace):
        subspace = subspace.lower()
        symmElements = mol.getSymmetryElements()
        pg = mol.getPointGroup().lower()
        symmLabel = ",".join( map(lambda x: x.lower(), symmElements) )
        occ_arr = []
        try:
            occ_arr = self.occupations[symmLabel][subspace]
        except KeyError: 
            pass

        #try again
        if not occ_arr:
            try:
                occ_arr = self.occupations[pg][subspace]
            except KeyError:
                pass

        #try again
        if not occ_arr:
            try:
                occ_arr = self.occupations[subspace]
            except KeyError: #that's it ... no other possibilites
                return None

        from grouptheory import COTTON_ORDER
        occ_dict = {}
        irrepList = COTTON_ORDER[pg]
        for i in range(len(irrepList)):
            irrep = irrepList[i]
            occ = occ_arr[i]
            occ_dict[irrep] = occ

        return occ_dict

CLASS_ATTRIBUTES = {
    'occupation' : OCCUPATION,
    'template' : TEMPLATE,
}
ALL_ATTRIBUTES = ATTRIBUTE_LIST.copy(); ALL_ATTRIBUTES.update(CLASS_ATTRIBUTES)


def getProgram(program):
    import writer
    program_list = {
        "MOLPRO" : writer.Molpro,
        "MOLPRO2002" : writer.Molpro,
        "PSI" : writer.Psi,
        "ACES" : writer.Aces,
        "MPQC" : writer.MPQC,
        "GAMESS" : writer.Gamess,
        "MRCC" : writer.MRCC,
        "GAUSSIAN" : writer.Gaussian,
        "QCHEM" : writer.QChem,
        "ORCA" : writer.Orca,
        }
    
    try: 
        prog_obj = program_list[program.upper()]
    except AttributeError: 
        return program

    if prog_obj: 
        return prog_obj()
    else: 
        return None #this program hasn't been implemented yet, which isn't a huge problem

def getKeyword(attribute, value):
    matches = [] 
    length = len(attribute)
    for attr in ALL_ATTRIBUTES:
        if attr[:length] == canonicalize(attribute): 
            matches.append(attr)

    if len(matches) != 1: 
        #ambiguous or no matches at all
        return None, attribute
    
    attribute_name = matches[0]  #exact
    if isinstance(value, Keyword):
        return value, attribute_name
    
    import input
    item = getattr(input, attribute_name.upper())
    keyinst = item(value)
    #return instance of keyword
    return keyinst, attribute_name

class BASIS(Keyword): datatype = str ; import basisset ; classtype = basisset.Basis
class RIBASIS(Keyword): datatype = str ; import basisset ; classtype = basisset.Basis
class REFERENCE(Keyword): pass
class WAVEFUNCTION(Keyword):
    allowedValues = [
    "scf", "mp2", "mp2r12", "ccsd", "ccsd(t)", "ccsdt", "ccsdt(q)", "ccsdtq", "b3lyp", "zapt2r12",
    ]
class JOBTYPE(Keyword): 
    allowedValues = [
    'singlepoint', 'frequency', 'optimization', 'dboc', 'relativity', 'handoptimization', 'handfrequency', 'gradient',
    'oeprop',
    ]
class CHARGE(Keyword): datatype = int
class MULTIPLICITY(Keyword): datatype = int
class POINTGROUP(Keyword): datatype = str
class STATESYMMETRY(Keyword): pass
class TITLE(Keyword): pass
class PROGRAM(Keyword): datatype = str ; import writer ; classtype = writer.Writer
class UNITS(Keyword): allowedValues = ["bohr", "angstrom"]
class MEMORY(Keyword): datatype = int
class COORDTYPE(Keyword): allowedValues = ["xyz", "zmatrix", 'default']
class CORE(Keyword): allowedValues = ["frozen", "correlated"]
class PRINTUNITS(Keyword): allowedValues = ["bohr", "angstrom"]
class OPTCONVERGENCE(Keyword): allowedValues = ["tight", "normal", "loose"]
class ENERGYCONVERGENCE(Keyword): allowedValues = ["tight", "normal", "loose"]
class RIBASIS(Keyword): pass
class CORRELATIONFACTOR(Keyword): allowedValues = ["f12", "r12"]
class CATIONGUESS(Keyword): datatype = bool
class R12EXPONENT(Keyword): datatype = float

## Auxilliary method the process the XYZ coordinates in a given file
#  @param geometryLines A string containing all the lines (with new line characters) that have xyz coordinates on them
#  @return A 2-D array.  Each row is a new atom.  1st column is atom label, 2nd column is x, 3rd y, 4th z
def readXYZ(geomLines, units):
    coordinates = []

    from molecules import Atom, canonicalizeAtomLabel

    def processAtom(label, xyz, atomNumber=1):
        newLabel = canonicalizeAtomLabel(label)
        xyz = DataPoint(xyz, units=units)
        newAtom = Atom(label, xyz, number=atomNumber)
        return newAtom
        
    regExp = r"([\da-zA-Z.]+)[\s,]+([-]?\d+[.]\d+)[\s,]+([-]?\d+[.]\d+)[\s,]+([-]?\d+[.]\d+)"
    atomNumber = 1
    atomList = []
    for line in geomLines:
        match = re.compile(regExp).search(line)
        if not match:
            raise Exception("Input line %s not formatted properly" % line)
        label, x, y, z = match.groups()
        label = label.upper()
        coords = map(eval, [x,y,z])
        newAtom = processAtom(label, coords, atomNumber)
        atomList.append(newAtom)
        atomNumber += 1

    return atomList

## Auxilliary method to process the Z-Matrix coordinates in a given file
#  @param geometryLines A string containing all the lines that have z-matrix info on them
#  @param coordinates An optional argument to send a set of xyz coordinates.  As the script reads through the z-matrix, if it finds a
#                     z-matrix value that has not been given a value, it will calculate the value and fill in the gaps
#  @return A 3-tuple with a z-matrix array, a variables dictionary, and a constants dictionary.
def readZMatrix(geometryLines, units):
    geometryText = "\n".join(geometryLines)

    import string
    from molecules import canonicalizeAtomLabel, Atom
    #hack to keep the regexp working
    geometryText = "\n" + geometryText.upper()
    variables = {}
    constants = {}
    atom_labels = {}
    ZMatrix = []

    #first, search for XYZ coordinates
    regExp = r"\n\s*([0-9a-zA-Z.]+)[\s,]+([-]?\d+[.]\d+)[\s,]+([-]?\d+[.]\d+)[\s,]+([-]?\d+[.]\d+)"
    geomLines = re.compile(regExp).findall(geometryText)
    atomNumber = 1
    atomList = []
    for label, x, y, z in geomLines:
        #whatever is given, convert it to atomic symbol
        label = canonicalizeAtomLabel(label)
        coords = map(eval, [x,y,z])
        newAtom = Atom(label, coords, units, atomNumber)
        atomList.append(newAtom)
        atomNumber += 1
    #at this point, if xyz coordinates were given for a general z-matrix, they are contained in the atom list variable


    #get the text defining the variables
    varText = re.compile("[Vv][Aa][Rr][Ii](.*?)[Cc][Oo][Nn][Ss][Tt]", re.DOTALL).search(geometryText)
    if not varText: #try again
        varText = re.compile("[Vv][Aa][Rr][Ii](.*)", re.DOTALL).search(geometryText)
    if varText: varText = varText.groups()[0]
    else: varText = "" #no variables
    #get the text defining the constants
    constText =  re.compile("[Cc][Oo][Nn][Ss][Tt](.*?)[Vv][Aa][Rr][Ii]", re.DOTALL).search(geometryText)
    if not constText: #try again
        constText = re.compile("[Cc][Oo][Nn][Ss][Tt](.*)", re.DOTALL).search(geometryText)
    if constText: constText = constText.groups()[0]
    else: constText = "" #no constants

    #now, go through the variable and constants text and fish out all variable and constant values
    regExp = r"\n\s*([A-Z\d]+)[=\s]+([-]?\d+[.]?\d*)"
    vars = re.compile(regExp).findall(varText)
    consts = re.compile(regExp).findall(constText)
    for varname, value in vars:
        variables[varname] = eval(value) 
    for const_name, value in consts:
        constants[const_name] =  eval(value)

    #these are symbols in the z-matrix that were never given values
    unset_values = []

    def getNewName(value, varType):
        startLetter = ""
        if varType == 1: startLetter = "R"
        elif varType == 2: startLetter = "A"
        elif varType == 3: startLetter = "D"

        #if the value already exists
        for entry in variables:
            if variables[entry] == value: return entry
        for entry in constants:
            if constants[entry] == value: return entry

        number = 1
        newSymbol = "%s%d" % (startLetter, number)
        while newSymbol in variables or newSymbol in constants:
            number += 1
            newSymbol = "%s%d" % (startLetter, number)

        return newSymbol

    def computeValue(name, atom, preceedingAtoms):
        import molecules
        if len(preceedingAtoms) == 1:
            return molecules.calcBondLength(atom, preceedingAtoms[0])
        elif len(preceedingAtoms) == 2:
            return molecules.calcBondAngle(atom, preceedingAtoms[0], preceedingAtoms[1])
        elif len(preceedingAtoms) == 3:
            return molecules.calcDihedralAngle(atom, preceedingAtoms[0], preceedingAtoms[1], preceedingAtoms[2])

    def processConnectValuePair(connecting_atom, connecting_number_label, value, line, atom_number, preceeding_atoms, varType):
        connecting_number = eval(connecting_number_label)
        #ah, but the connecting atom might be given be a label, so check for it
        if connecting_atom:
            connecting_number = atom_labels[connecting_atom + connecting_number_label]
        #the value might be a variable or constant... or it might be an actual number
        if isNumber(value): #this is a constant... and we must give the constant a name
            constName = getNewName(eval(value), varType)
            constants[constName] = eval(value)
            line.append(connecting_number)
            line.append(constName)
        else:
            #we may or may not have a value, but it won't actually matter in the end
            line.append(connecting_number)
            line.append(value)
        if atomList:
            #aha, we were given xyz coordinates so we better keep track of this atom
            #in case we need to compute some values in the z-matrix
            preceeding_atoms.append( atomList[connecting_number-1] )
            #also, since this is not a constant, we must keep track of the name
            if not isNumber(value): unset_values.append(value)

    def processLine(groups, lineNumber):
        atom = groups[0]
        atom_number_label = groups[1]
        if atom_number_label:
            atom_labels[atom + atom_number_label] = len(atom_labels) + 1
        line = [atom] #this will contain all the info on the line
        #now go through and process the rest of the line
        i = 2
        preceeding_atoms = []
        while i + 3 <= len(groups):
            (connecting_atom, connecting_number_label, value) = groups[i:i+3]
            processConnectValuePair(connecting_atom, connecting_number_label, value, line, lineNumber, preceeding_atoms, i/3+1)
            #the i%3+1 is so that the method knows what type of value is being processed, i.e. 1 for bond, 2 for angle, 3 for dih
            i += 3

        return line

    #try to process the first z-matrix lines
    regExp = r"""\s*([A-Za-z]+) #initial atom name
    (\d)* #a number label for the atom, potentially
    """
    lineNumber = 1
    firstGroups = re.compile(regExp, re.VERBOSE).search(geometryText).groups()
    ZMatrix.append( processLine(firstGroups, lineNumber) )
    
    #try to process the second z-matrix line
    extra = """[ ]+([A-Za-z]+)* #an atom label for the connecting atom, potentially
    (\d+) #the number label for the connecting atom
    [ ]+([-]?[a-zA-Z.\d*]+) #the value of the parameter, which may be a variable name or a specific value 
    """
    lineNumber = 2
    #try to process the second z-matrix line
    regExp += extra
    secondGroups = re.compile(regExp, re.VERBOSE).search(geometryText)
    if secondGroups: #if we have a second line
        ZMatrix.append( processLine(secondGroups.groups(), lineNumber) )    

    #try to process the third z-matrix line
    regExp += extra
    thirdGroups = re.compile(regExp, re.VERBOSE).search(geometryText)
    if thirdGroups: #if we have a second line
        ZMatrix.append( processLine(thirdGroups.groups(), lineNumber) )

    #try to process all remaining z-matrix lines
    dihExtra = """[ ]+([A-Za-z]+)* #an atom label for the connecting atom, potentially
    (\d+) #the number label for the connecting atom
    [ ]+([-]?[a-zA-z.\d*]+) #the value of the parameter, which may be a variable name or a specific value 
    """
    regExp += dihExtra
    allGroupList = re.compile(regExp, re.VERBOSE).findall(geometryText)
    for line in allGroupList:
        ZMatrix.append( processLine(line, lineNumber) )    

    #okay, at this point all constants have been given a name
    #however, there is the possibility that variables have been specified but not given values
    #since they are to be computed from xyz coordinates. Set these to none.  The zmatrix object
    #doesn't care what they are set to.  It will overwrrite them if they aren't numbers
    for name in unset_values:
        if not name in constants: variables[name] = None

    import chem.geometry
    if atomList:
        zmatObject = chem.geometry.ZMatrix(atomList, "angstrom", ZMatrix, variables, constants)
        #for now we set the units to angstroms... but that will probably be changed later
        return (atomList, zmatObject)
    else:
        atoms, xyz = chem.geometry.getXYZFromZMatrix(ZMatrix, variables, constants)
        xyz = DataPoint(xyz, units=units)
        import chem.molecules
        atomList = chem.molecules.getAtomListFromXYZ(atoms, xyz)
        zmatObject = chem.geometry.ZMatrix(atomList, "angstrom", ZMatrix, variables, constants)
        return (atomList, zmatObject)

def readOptions(fileText):
    keywordLines = []
    classEntries = {}

    lineIter = iter(fileText.splitlines())
    def getNextLine():
        nextLine = lineIter.next().strip().strip(":")
        while not nextLine: 
            nextLine = lineIter.next().strip().strip(":")
        return nextLine

    def isFrameChange(nextLine):
        if nextLine in directives or nextLine.replace("=", " ").strip().split()[0] in ATTRIBUTE_LIST:
            return True
        else:  
            return False

    sections = []
    
    line = lineIter.next().strip()
    #do the keyword lines
    try:
        while not ":" in line:
            keywordLines.append(line)
            line = lineIter.next().strip()
    except StopIteration:
        pass

    #do the class attribute lines
    name = None
    try:
        while 1:
            if ":" in line:
                name = line.strip(":")
                classEntries[name] = []
            elif line:
                classEntries[name].append(line.strip())
            line = lineIter.next().strip()
    except StopIteration:
        pass

    #get xyz coordinates, maybe
    xyzLines = []
    if classEntries.has_key("geometry"):
        xyzLines = classEntries['geometry']
        del classEntries['geometry']
    elif classEntries.has_key("xyz"):
        xyzLines = classEntries['xyz']
        del classEntries['xyz']

    #get the zmatrix, maybe
    zmatLines = []
    if classEntries.has_key("zmatrix"):
        zmatLines = classEntries['zmatrix']
        del classEntries['zmatrix']


    #if we have both xyz and zmatrix, add the lines
    if xyzLines and zmatLines:
        zmatLines.extend(xyzLines)

    keywords={}
    for line in keywordLines:
        splitline = re.split("[= ]+", line.strip())
        if len(splitline) != 2:
            continue
        key, value = splitline
        keywords[key] = value

    for key in classEntries:
        inputLines = classEntries[key]
        classType = CLASS_ATTRIBUTES[key]
        classVal = classType(inputLines)
        keywords[key] = classVal


    zmat = None
    atomList = None
    units = ATTRIBUTE_LIST['units']
    if "units" in keywords:
        units = keywords['units']
    if zmatLines: #this takes precedence
        atomList, zmat = readZMatrix(zmatLines, units)
    elif xyzLines: #secondary to zmat
        atomList = readXYZ(xyzLines, units)

    return keywords, atomList, zmat

def readInputFile(filepath, reorient=False, recenter=False):
    #make sure we have a real file
    if not os.path.isfile(filepath):
        return None

    fileText = open(filepath).read().lower() #let's work in lower case

    #split the file based on the *** separator
    inputs = fileText.split("***")
    if not inputs: #file was empty
        return None

    compList = []

    #do the first input
    firstInput = inputs[0]
    newkeys, atomList, zmat = readOptions(firstInput)
    if not atomList: #something went wrong
        return None
    comp = Computation(atomList, ZMatrix=zmat, keywords=newkeys, recenter=recenter, reorient=reorient)
    compList.append(comp)


    #now, read the rest of the inputs
    for input in inputs[1:]:
        if not newatoms:
            newatoms = atomList
        if not newzmat:
            newzmat = zmat
        comp = Computation(atomList, ZMatrix=zmat, keywords=newkeys, recenter=recenter, reorient=reorient)
        #and set the new attributes
        #we need to do things this way because it can happen that in one part of the input file you say multiplicity = 1
        #but in the second you say mult = 2, in which case the second DOES NOT override the first
        for key in keychanges:
            comp.setAttribute(key, keychanges[key])
        compList.append(comp)

    if len(compList) == 1: #only return the comp, not as a list
        return compList[0]
    else:
        return compList
        

## Encapsulates a computation.  This is abstracted to the level where the computation knows nothing about the program or machine that will run it.
## It doesn't even know its own keyword. It just holds the keywords without any awareness of them. It also holds the parent molecule and
## potentially the basis set. Specific tasks such as SinglePoint or Optimization will hold information specific to a calculation type.
class Computation(Molecule):

    GET_METHODS = {
        "pointgroup" : "getPointGroup",
        "multiplicity" : "getMultiplicity",
        "charge" : "getCharge",
        "statesymmetry" : "getStateSymmetry",
        "title" : "getTitle",
        "template" : "getTemplate",
        "geometry" : "getGeometry",
        "numelectrons" : "getNumberOfElectrons",
        "numunpaired" : "getNumberOfUnpairedElectrons",
        "program" : "getProgram",
        }

    SET_METHODS = {
        "pointgroup" : "setPointGroup",
        "program" : "setProgram",
        "template" : "setTemplate",
        "statesymmetry" : "setStateSymmetry",
        "title" : "setTitle",
        "charge" : "setCharge",
        "multiplicity" : "setMultiplicity",
        }

    def __init__(self, atomList, program="psi", keywords={},
                 ZMatrix = None, charge = 0, multiplicity = 1, stateSymmetry = "A",
                 moleculeName = None, energy=0, recenter = False, reorient = False):

        Molecule.__init__(self, atomList, charge, multiplicity, stateSymmetry, moleculeName, energy, recenter, reorient)

        self.program = program #a program object
        self.ZMatrix = ZMatrix
        #we have to do things this way otherwise certain keywords may not be overwritten properly
        for key in ATTRIBUTE_LIST:
            self.setAttribute(key, ATTRIBUTE_LIST[key])
        for key in keywords:
            self.setAttribute(key, keywords[key])

        #the computation may potentially need to copy files to its directory
        self.filesToCopy = {}

    ## Sends back a string representation, i.e. info description, of this class
    # @return A string name
    def __str__(self):
        str_array = [( Molecule.__str__(self) )]
        #if self.getAttribute("coordtype") == "zmatrix":
            #str_array.append("zmatrix (%s)" % self.ZMatrix.getUnits())
            #str_array.append("%s" % self.ZMatrix) 
        return "\n".join(str_array)

    def findTemplate(self, program=None):
        import os.path
        import os
        jobtype = str(self.getAttribute("jobtype"))
        reference = str(self.getAttribute("reference"))
        wfn = str(self.getAttribute("wavefunction"))
        if not program: program = self.program.getName()

        folders_to_test = [
            os.path.join(jobtype,reference,wfn),
            os.path.join(jobtype,reference),
            os.path.join(jobtype,wfn),
            jobtype,
            wfn,
            "", #maybe no specifics
            ]

        for folder in folders_to_test:
            testname = folder.lower()
            folderpath = os.path.join(os.environ["PYCHEM"],program.lower(),testname)
            template_file = os.path.join(folderpath, "template")
            if os.path.isfile(template_file):
                return template_file
                
    ## Adds a file that the computation will need to put somewhere before running  
    #  @param name The name of the file to copy
    #  @param nameToCopy Optional argument specifying a name to copy the file to 
    def addFileToCopy(self, name, nameToCopy=None):
        if nameToCopy: 
            self.filesToCopy[name] = nameToCopy
        else: 
            self.filesToCopy[name] = file

    def getFilesToCopy(self):
        return self.filesToCopy

    def getKeyword(self, keyword):
        return Item.getAttribute(self, keyword)

    def getAttribute(self, attribute):
        try:
            method_name = self.GET_METHODS[canonicalize(attribute)]
            method = getattr(self, method_name)
            return method()
        except KeyError: #oops, perhaps a keyword
            pass
    
        #perhaps it is a keyword
        value = Item.getAttribute(self, attribute)
        return value

    def getGeometry(self):
        geom_type = self.getAttribute('coordtype')

        if geom_type == 'default':
            if self.ZMatrix:
                geom_type = 'zmatrix'
            else:
                geom_type = 'xyz'

        geom_text= ""
        if geom_type == "xyz":
            geom_text = self.program.getXYZ(self)
        else:
            geom_text = self.program.getZMatrix(self)
        return geom_text

    def getGeometryType(self):
        if self.ZMatrix:
            return "zmatrix"
        else:
            return "xyz"
        
    def getProgram(self):
        return self.program

    def getTemplate(self):
        template = Item.getAttribute(self, 'template')
        if not template: 
            return None
        elif isinstance(template, GUSKeywordObject):
            file = template.getTemplateFile(self.getPointGroup())
            return open(file).read()
        elif os.path.isfile(template): 
            return open(template).read()
        else:
            return template

    def getZMatrix(self):
        return self.ZMatrix 

    def hasTemplate(self):
        return self.template

    def makeFile(self):
        fileText = self.program.makeFile(self)
        return fileText

    def setOptions(self, input):
        for line in input.splitlines():
            line = line.strip().replace("=", " ")
            if line:
                attr, val = line.split()
                self.setAttribute(attr, val)

    def setAttribute(self, attribute_name, attribute_value):
        #first, attempt to build a keyword object for the name and value
        keyObj, fullName = getKeyword(attribute_name, attribute_value)
        if not keyObj == None: #if in fact this is a keyword object
            attribute_name = fullName
            attribute_value = keyObj
       
        try: #maybe a special set method
            method_name = self.SET_METHODS[ attribute_name.lower() ]
            method = getattr(self, method_name)
            method(attribute_value)
            return
        except KeyError: #put in a generic slot
            Item.setAttribute(self, attribute_name, attribute_value)
                
    def setProgram(self, program):
        self.program = getProgram(program)

    def setTemplate(self, template):
        if not template: #given a none type, which means to get the template from the library
            Item.setAttribute(self, 'template', None)
        elif not isinstance(template, TEMPLATE):
            template = TEMPLATE(template)
        Item.setAttribute(self, 'template', template)

    def setUnits(self, units):
        if hasattr(self, 'ZMatrix') and self.ZMatrix: #if we have a zmat and it is not a null  
            self.ZMatrix.setUnits(units)
        #do any molecule unit stuff
        Molecule.setUnits(self, units)

    def makeGUSFile(self):
        desc = []
        formatter = Formatter()
        stringList = []
        objList = []
        for attribute in self.getAttributes():
            val = Item.getAttribute(self, attribute)
            if isinstance(val, GUSKeywordObject):
                objList.append([attribute, val])
            else:
                stringList.append([attribute, val])
        for name, val in stringList:
            desc.append("%20s=%16s" % (name, val))
        for name, val in objList:
            desc.append("%s:\n%s" % (name, val.makeGUSFile()))
        desc.append("xyz:")
        desc.append(self.getXYZTable(units = self.getUnits()))
        if self.getAttribute("coordtype") == "zmatrix":
            desc.append("zmatrix:")
            desc.append("%s" % self.ZMatrix) 
        return "\n".join(desc)
        

