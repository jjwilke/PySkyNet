import string, numpy, sys
import os, commands

COTTON_ORDER = {
    "d2h" : [ 'ag', 'b1g', 'b2g', 'b3g', 'au', 'b1u', 'b2u', 'b3u' ],
    "c2v" : [ 'a1', 'a2', 'b1', 'b2'],
    "c2h" : [ 'ag', 'bg', 'au', 'bu'],
    "cs" : [ 'ap', 'app'],
    "c2" : [ 'a', 'b'],
    "c1" : [ 'a' ],
    "d2" : [ 'a', 'b1', 'b2', 'b3']
    }

IRREP_SYMMETRY_ELEMENTS = {
"c2v" : {
    #4,    
    "a1" : ["xx", "yy", "zz", "z"],
    "a2" : ["xy"],
    "b1" : ["x", "xz"],
    "b2" : ["y", "yz"],
    },
"cs" : {
    # 2     
    "ap" :  ["x", "y", "xx", "yy", "zz", "xy"],
    "app" : ["z", "yz", "xz"],
    },
}

OPERATIONS = {
    "c2v" : ["e", "c2z", "sigxz", "sigyz"],
    "cs" : ["e", "sigxy"],
}

CHARACTER_TABLES = {
"d2h" : {
    #8        e  c2z c2y c2x  i  xy  xz  yz
    "ag"  : [ 1 , 1 , 1 , 1 , 1 , 1 , 1 , 1 ],       
    "b1g" : [ 1 , 1 ,-1 ,-1 , 1 , 1 ,-1 ,-1 ],
    "b2g" : [ 1 ,-1 , 1 ,-1 , 1 ,-1 , 1 ,-1 ],
    "b3g" : [ 1 ,-1 ,-1 , 1 , 1 ,-1 ,-1 , 1 ],
    "au"  : [ 1 , 1 , 1 , 1 ,-1 ,-1 ,-1 ,-1 ],
    "b1u" : [ 1 , 1 ,-1 ,-1 ,-1 ,-1 , 1 , 1 ],
    "b2u" : [ 1 ,-1 , 1 ,-1 ,-1 , 1 ,-1 , 1 ],
    "b3u" : [ 1 ,-1 ,-1 , 1 ,-1 , 1 , 1 ,-1 ]
    },
"d2" : {
    #4,    
    "a" :  [1,    1,    1,       1],
    "b1" : [1,    1,   -1,      -1],
    "b2" : [1,   -1,    1,      -1],
    "b3" : [1,   -1,   -1,       1]   
    },
"c2v" : {
    #4,    
    "a1" : [1,    1,    1,       1],
    "a2" : [1,    1,   -1,      -1],
    "b1" : [1,   -1,    1,      -1],
    "b2" : [1,   -1,   -1,       1]   
    },
"cs" : {
    # 2     e   sigh
    "ap" :  [1,    1],
    "app" : [1,   -1]
    },
"c1" : {
    "a" :  [1],
    },
"c2" : {
    # 2     e   c2
    "a" :  [1,    1],
    "b" :  [1,   -1]
    },
"ci" : {
    # 2     e   i
    "ag" :  [1,    1],
    "au" :  [1,   -1]
    },
"c2h" : {
    # 4     e  c2z  i  sigh
    "ag" : [ 1 , 1 , 1 , 1 ],
    "bg" : [ 1 ,-1 , 1 ,-1 ],
    "au" : [ 1 , 1 ,-1 ,-1 ],
    "bu" : [ 1 ,-1 ,-1 , 1 ]
    }
}

TOTALLY_SYMMETRIC_IRREPS = {
    "c2v" : "a1",
    "d2h" : "ag",
    "cs" : "ap",
    "c1" : "a",
    "c2h" : "ag",
    "c2" : "a"
    }


ACES = {
    "c2v" :
    { 1 : "a1", 2 : "b1", 3 : "b2", 4 : "a2"},
    "cs" :
    { 1 : "ap", 2 : "app" }
    }

IRREP_NUMBERS = {
    "aces" : ACES
    }

ACES_CONVERSIONS = {
    "c2v" : {
    "a1" : 1,
    "b1" : 2,
    "b2" : 3,
    "a2" : 4,
    },
    "d2h" : {
    "ag" : 1,
    "b3u" : 2,
    "b2u" : 3,
    "b1g" : 4,
    "b1u" : 5,
    "b2g" : 6,
    "b3g" : 7,
    "au" : 8
    },
    "c2h" : {
    "ag" : 1,
    "au" : 2,
    "bu" : 3,
    "bg" : 4,
    },
    "cs" :
    {
    "ap" : 1,
    "app" : 2,
    },
    "ci" :
    {
    "ag" : 1,
    "au" : 2
    },
    "c1" :
    {
    "a" : 1,   
    }
    }

MOLPRO_CONVERSIONS = {
    "c2v" : {
    "a1" : 1,
    "b1" : 2,
    "b2" : 3,
    "a2" : 4,
    "ag" : 1,
    "b3u" : 3,
    "b2u" : 2,
    "b1g" : 4,
    "b1u" : 1,
    "b2g" : 2,
    "b3g" : 3,
    "au" : 4,
    "a" : 1
    },
    "d2" : {
    "a" : 1,
    "b1" : 2,
    "b2" : 3,
    "b3" : 4,
    },
    "d2h" : {
    "ag" : 1,
    "b3u" : 2,
    "b2u" : 3,
    "b1g" : 4,
    "b1u" : 5,
    "b2g" : 6,
    "b3g" : 7,
    "au" : 8,
    "a" : 1,
    },
    "c2h" : {
    "ag" : 1,
    "au" : 2,
    "bu" : 3,
    "bg" : 4,
    "b3u" : 3,
    "b2u" : 3,
    "b1g" : 1,
    "b1u" : 2,
    "b2g" : 4,
    "b3g" : 4,
    },
    "cs" :
    {
    "ap" : 1,
    "app" : 2,
    "a1" : 1,
    "b1" : 1,
    "b2" : 2,
    "a2" : 2,
    "ag" : 1,
    "b3u" : 2,
    "b2u" : 1,
    "b1g" : 2,
    "b1u" : 1,
    "b2g" : 1,
    "b3g" : 2,
    "ag" : 1,
    "au" : 2,
    "bu" : 1,
    "bg" : 2,
    "a" : 1
    },
    "ci" :
    {
    "ag" : 1,
    "au" : 2
    },
    "c1" :
    { "a" : 1,
    "ap" : 1,
    "app" : 1,
    "a1" : 1,
    "b1" : 1,
    "b2" : 1,
    "a2" : 1,
    "ag" : 1,
    "b3u" : 1,
    "b2u" : 1,
    "b1g" : 1,
    "b1u" : 1,
    "b2g" : 1,
    "b3g" : 1,
    "ag" : 1,
    "au" : 1,
    "bu" : 1,
    "bg" : 1,   
    }
}



# the matrices for all the group operations
TRANSFORMATION_ORDER = ["e", "c2z", "c2y", "c2x", "i", "sigxy", "sigxz", "sigyz"]
transformations =  {
    "e" : 
    [
    [ 1,  0,  0],
    [ 0,  1,  0],
    [ 0,  0,  1]
    ],
    "c2z" : 
    [
    [-1,  0,  0],
    [ 0, -1,  0],
    [ 0,  0,  1]
    ],

    "c2x" :
    [
    [ 1,  0,  0],
    [ 0, -1,  0],
    [ 0,  0, -1]
    ],

    "c2y" :
    [
    [-1,  0,  0],
    [ 0,  1,  0],
    [ 0,  0, -1]
    ],

    "i" : 
    [
    [-1,  0,  0],
    [ 0, -1,  0],
    [ 0,  0, -1]
    ],

    "sigxy" :
    [
    [ 1,  0,  0],
    [ 0,  1,  0],
    [ 0,  0, -1]    
    ],

    "sigxz" :
    [
    [ 1,  0,  0],
    [ 0, -1,  0],
    [ 0,  0,  1]    
    ],
    "sigyz" :
    [
    [-1,  0,  0],
    [ 0,  1,  0],
    [ 0,  0,  1]    
    ]
}


def getEmptyDictionary(pointGroup):
    keyList = CHARACTER_TABLES[pointGroup.lower()].keys()
    newDict = {}
    for key in keyList:
        newDict[key] = 0

    return newDict

def getTotallySymmetricIrrep(pointGroup):
    return TOTALLY_SYMMETRIC_IRREPS[ pointGroup.lower() ] 

def getMolproIrrepNumber(pointGroup, irrep):
    number = MOLPRO_CONVERSIONS[pointGroup.lower()][irrep]
    return number

# Gets the name of an irrep in a given point group corresponding to a certain vector
def getIrrepName(pointGroup, vector):
    irrep_dict = CHARACTER_TABLES[pointGroup]
    for irrep in irrep_dict:
        if vector == irrep_dict[irrep]:
            return irrep

class Irrep:
    def __init__(self, pointGroup, irrepName):
        self.pointGroup = pointGroup.lower()
        self.irrepName = irrepName.lower()
        self.vector = CHARACTER_TABLES[self.pointGroup][self.irrepName]

    def __mul__(self, otherIrrep):
        newVector = []
        for i in range(0, len(self.vector)):
            newVector.append(self.vector[i] * otherIrrep.vector[i])

        newIrrepName = getIrrepName(self.pointGroup, newVector)
        newIrrep = Irrep(self.pointGroup, newIrrepName)
        return newIrrep

    def getPointGroup(self):
        return self.pointGroup

    def getName(self):
        return self.irrepName

    def __eq__(self, other):
        if not self.getPointGroup() == other.getPointGroup():
            return False
        if not self.getName() == other.getName():
            return False

        return True

## Gets the irreps for a given point group
#  @param pointGroup A string identifier for the point group
#  @return A list containing the names of the irreps for a point group (in no particular order)
def getIrreps(pointGroup):
    irreps = []
    cTable = CHARACTER_TABLES[pointGroup.lower()]

    return cTable.keys()


def reduceOccupation(currentGroup, currentOccupation, newGroup, symmetryElements):
    x = [1,0,0]
    y = [0,1,0]
    z = [0,0,1]

    newOccupation = {}
    for irrep in CHARACTER_TABLES[newGroup]: newOccupation[irrep] = 0

   
    char_table = {}
    for element in symmetryElements:
        matrix = transformations[element]
        X = numpy.dot(x, numpy.dot(matrix,x)) 
        Y = numpy.dot(y, numpy.dot(matrix,y)) 
        Z = numpy.dot(z, numpy.dot(matrix,z)) 
        XX = X*X
        YY = Y*Y
        ZZ = Z*Z
        XY = X*Y
        XZ = X*Z
        YZ = Y*Z 
        for irrep in currentOccupation:
            symm_element = IRREP_SYMMETRY_ELEMENTS[currentGroup][irrep][0]
            character = eval(symm_element)
            if not char_table.has_key(irrep): char_table[irrep] = []
            char_table[irrep].append(character)

        
    sys.exit()


def getPointGroupFromSymmetryElements(symmElements):
    numSymmPlanes = 0; numAxes = 0; invertible = 0; 
    for elem in symmElements:
        symmElem = elem.lower()
        if   "SIG" in symmElem: numSymmPlanes += 1
        elif "C2" in symmElem: numAxes += 1
        elif "I" in symmElem: invertible = 1

    if numSymmPlanes == 0 and numAxes == 0 and invertible == 0:
        pg = "c1"
    elif numSymmPlanes == 1 and numAxes == 1 and invertible == 1:
        pg = "c2h"
    elif numSymmPlanes == 2 and numAxes == 1 and invertible == 0:
        pg = "c2v"
    elif numSymmPlanes == 3 and numAxes == 3 and invertible == 1:
        pg = "d2h"    
    elif numSymmPlanes == 1 and numAxes == 0 and invertible == 0:
        pg = "cs"
    elif numSymmPlanes == 0 and numAxes == 1 and invertible == 0:
        pg = "c2"
    elif numSymmPlanes == 0 and numAxes == 0 and invertible == 1:
        pg = "ci"
    elif numSymmPlanes == 0 and numAxes == 3 and invertible == 0:
        pg = "d2"

    return pg

def getSymmetryElements(mol):
    from chem.molecules import Atom
    testmol = mol.copy()
    testmol.recenter()
    testmol.reorient()
    if isinstance(mol, list): 
        #oops, xyz, better make a molecule object
        from Molecules import Molecule, getAtomListFromXYZ
        atomList = getAtomListFromXYZ(mol)
        testmol = Molecule(atomList)
        
    def testTransformation(trans, atoms):
        for atom in atoms:
            newAtom = atom.copy()
            newAtom.transform(trans)
            test = testmol.testAtomEquivalence(newAtom)
            if not test:
                #this is not a symmetry element
                return False
        return True

    symmElements = []
    allAtoms = testmol.getAtoms()
    for trans in TRANSFORMATION_ORDER:
        matrix = transformations[trans]
        isSymmOp = testTransformation(matrix, allAtoms)
        if isSymmOp:
            symmElements.append(trans)

    return symmElements

## Tests the point group of the molecule... assuming it has been reoriented so that the x,y,z axes are the principal axes
def getPointGroup(molToTest):
    # whether or not the molecule has the given operations, same as D2h
    # E  C2z C2y C2x  i  xy  xz  yz

    #don't actually test the sent molecule...create a copy, recenter, reorient, and then test
    molecule = molToTest.copy()
    if molecule.allowRecenter(): molecule.recenter()
    if molecule.allowReorient(): molecule.reorient()

    symmElements = getSymmetryElements(molToTest)

    orientedMol = molToTest.copy()
    orientedMol.recenter(); orientedMol.reorient()

    symmOps = {}
    orientedSymmElements = getSymmetryElements(orientedMol)
    for key in transformations:
        if key in orientedSymmElements:
            symmOps[key] = 1
        else:
            symmOps[key] = 0

    numSymmPlanes = symmOps["sigxy"] + symmOps["sigxz"] + symmOps["sigyz"]
    numAxes = symmOps["c2x"] + symmOps["c2y"] + symmOps["c2z"]
    invertible = symmOps["i"]

    pg = None
    if numSymmPlanes == 0 and numAxes == 0 and invertible == 0:
        pg = "c1"
    elif numSymmPlanes == 1 and numAxes == 1 and invertible == 1:
        pg = "c2h"
    elif numSymmPlanes == 2 and numAxes == 1 and invertible == 0:
        pg = "c2v"
    elif numSymmPlanes == 3 and numAxes == 3 and invertible == 1:
        pg = "d2h"    
    elif numSymmPlanes == 1 and numAxes == 0 and invertible == 0:
        pg = "cs"
    elif numSymmPlanes == 0 and numAxes == 1 and invertible == 0:
        pg = "c2"
    elif numSymmPlanes == 0 and numAxes == 0 and invertible == 1:
        pg = "ci"
    elif numSymmPlanes == 0 and numAxes == 3 and invertible == 0:
        pg = "d2"

    return pg, symmElements

## Figures out the irrep symbol for the given state
#  @param pointGroup A string identifier for the point group
#  @param excessAlphaArray A dictionary identifying the number of excess alpha electrons in each irrep.  The reason for only the alpha
#                          is that most programs only do high spin.  The dictionary has the format dict[first key = irrep symbol] = integer
#  @return A string identifying the irrep
def getStateSymmetry(pointGroup, excessAlphaArray):
    cTable = CHARACTER_TABLES[pointGroup.lower()]
    irrepsToMultiply = []
    for irrepName in excessAlphaArray:
        power = excessAlphaArray[irrepName]
        irrepArray = cTable[irrepName]
        irrepToAdd = irrepToPower(irrepArray, power)
        irrepsToMultiply.append(irrepToAdd)
    finalIrrep = multIrrepSet(irrepsToMultiply)

    for irrepName in cTable:
        if finalIrrep == cTable[irrepName]:
            return irrepName

## Takes an irrep to a power, i.e. dots a given irrep with itself a certain number of times
#  @param irrepArray A list object containg the characters of the irrep in order
#  @param power An integer identifying how many times to do the irrep with itself
#  @return A new irrep list containing the characters of the irrep that results
def irrepToPower(irrepArray, power):
    if power == 0:
        return [1] * len(irrepArray)

    finalAnswer = irrepArray
    for i in range(1, power):
        finalAnswer = multIrrep(finalAnswer, irrepArray)

    return finalAnswer

## Multiplies a set of irreps
#  @param arraySet A list of irrep arrays.  Each irrep array is a list containing the characters of the irrep
#  @return A new irrep list containing the characters of the irrep that results
def multIrrepSet(arraySet):
    finalAnswer = arraySet[0]
    for i in range(1, len(arraySet)):
        finalAnswer = multIrrep(finalAnswer, arraySet[i])

    return finalAnswer
        
## Multiplies two irreps
#  @param irrep1 The irrep array is a list containing the characters of the irrep
#  @param irrep2 The irrep array is a list containing the characters of the irrep
#  @return A new irrep list containing the characters of the irrep that results
def multIrrep(irrep1, irrep2):
    newIrrep = []
    for i in range(0, len(irrep1)):
        newEntry = irrep1[i] * irrep2[i]
        newIrrep.append(newEntry)

    return newIrrep


