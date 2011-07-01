# @module Molecules Contains the atom and molecule objects along with miscellaneous methods for geometry manipulation and calculation

from skynet.utils.utils import *
import numpy
import chem.data
import skynet.identity

MOLECULE_ATTRIBUTES = {
    "charge" : 0,
    "multiplicity" : 1,
    "statesymmetry" : "a",
    "title" : 'default',
    "units" : "angstrom",
    "pointgroup" : "c1",
}


NO_BOND=1E6 #very large number indicates never bonded
BOND_THRESHOLDS = {
    "N-N" : 1.8,
    "C-C" : 1.8,
    "O-O" : 1.8,
    "C-H" : 1.3,
    "H-C" : 1.3,
    "N-C" : 1.6,
    "C-N" : 1.6,
    "N-H" : 1.3,
    "H-N" : 1.3,
    "C-CL" : 2.5,
    "CL-C" : 2.5,
    "C-F" : 2.5,
    "F-C" : 2.5,
    "H-H" : 1.0,
    "CL-H" : 1.8,
    "H-CL" : 1.8,
    "CL-CL" : 2.0,
    "H-F" : 1.2,
    "F-H" : 1.2,
    "H-O" : 1.2,
    "O-H" : 1.2,
    "H-SI" : 1.5,
    "SI-H" : 1.5,
    "H-S" : 1.5,
    "S-H" : 1.5,
    "F-F" : 1.8,
    "C-SI" : 2.0,
    "SI-C" : 2.0,
    "C-S" : 2.0,
    "S-C" : 2.0,
    "S-O" : 1.8,
    "O-S" : 1.8,
    "S-N" : 1.8,
    "N-S" : 1.8,
    "O-N" : 1.8,
    "N-O" : 1.8,
    "O-C" : 1.8,
    "C-O" : 1.8,
    "S-S" : 3.6,
}
def getBondThreshold(atom1, atom2, units):
    key = "%s-%s" % (atom1.getSymbol(), atom2.getSymbol())
    value_in_ang = BOND_THRESHOLDS[key]
    return convertUnits(value_in_ang, "angstrom", units)

## Calculates the bond length between two atoms
# @param atom1 An atom instance
# @param atom2 An atom instance
# @return A float, the bond length
def calcBondLength(atom1, atom2):
    bondVector = getBondVector(atom1, atom2)
    bondSq = numpy.dot(bondVector, bondVector)
    bond = numpy.sqrt(bondSq)
    return bond

## Calculates the bond angle of the connectivity 1-2-3
# @param atom1 An atom instance
# @param atom2 An atom instance
# @param atom3 An atom instance
# @return A float, the bond angle
def calcBondAngle(atom1, atom2, atom3):
    bondVector1 = getBondVector(atom2, atom1)
    bondVector2 = getBondVector(atom2, atom3)
    bondLength1 = numpy.sqrt(numpy.dot(bondVector1, bondVector1))
    bondLength2 = numpy.sqrt(numpy.dot(bondVector2, bondVector2))
    dotProd = numpy.dot(bondVector1, bondVector2)
    cosTheta = dotProd / (bondLength1 * bondLength2)
    
    theta = numpy.arccos(cosTheta) * 180 / numpy.pi
    return theta

## Calculates the dihedral angle of the connectivity 1-2-3-4
# @param atom1 A an atom instance.
# @param atom2 A an atom instance.
# @param atom3 A an atom instance.
# @param atom4 A an atom instance.
# @return A float, the dihedral angle
def calcDihedralAngle(atom1, atom2, atom3, atom4, discontinuity=-90):
    bondVector1 = getUnitVector(getBondVector(atom2, atom1))
    bondVector2 = getUnitVector(getBondVector(atom2, atom3))
    bondVector3 = getUnitVector(getBondVector(atom3, atom2))
    bondVector4 = getUnitVector(getBondVector(atom3, atom4))

    #point the z-axis along the middle bond and the x-axis straight up
    newY = numpy.cross(bondVector2, bondVector1)
    newZ = bondVector2
    newX = numpy.cross(newY, newZ)

    x = numpy.dot(bondVector4, newX)
    y = numpy.dot(bondVector4, newY)
    dihedral = numpy.arctan2(y,x) * 180 / numpy.pi
    if dihedral < discontinuity:
        dihedral += 360
    elif dihedral > 360 + discontinuity:
        dihedral -= 360
    return dihedral

def getNormalVector(atom1, atom2, atom3):
    bv1 = getUnitVector(getBondVector(atom2, atom1))
    bv2 = getUnitVector(getBondVector(atom2, atom3))
    nvec = getUnitVector( numpy.cross(bv1, bv2) )
    return nvec

def getAngleBetweenVectors(vec1, vec2):
    dotProd = numpy.dot(vec1, vec2)
    length1 = numpy.sqrt(numpy.dot(vec1, vec1))
    length2 = numpy.sqrt(numpy.dot(vec2, vec2))
    costheta = dotProd / length1 / length2
    theta = numpy.arccos(costheta) * 180 / numpy.pi
    return theta

def calcLinX(atom1, atom2, atom3, atom4):
    bondVector2_to_1 = getUnitVector(getBondVector(atom2, atom1))
    bondVector2_to_3 = getUnitVector(getBondVector(atom2, atom3))
    bondVector3_to_2 = getUnitVector(getBondVector(atom3, atom2))
    bondVector3_to_4 = getUnitVector(getBondVector(atom3, atom4))

    inter1 = getUnitVector( numpy.cross(bondVector2_to_1, bondVector2_to_3) )
    inter2 = numpy.cross(bondVector3_to_4, bondVector2_to_3) 

    return numpy.dot(inter1, inter2)

def calcLinY(atom1, atom2, atom3, atom4):
    bondVector2_to_1 = getUnitVector(getBondVector(atom2, atom1))
    bondVector2_to_3 = getUnitVector(getBondVector(atom2, atom3))
    bondVector3_to_2 = getUnitVector(getBondVector(atom3, atom2))
    bondVector3_to_4 = getUnitVector(getBondVector(atom3, atom4))

    numer = numpy.dot(bondVector2_to_1, numpy.cross(bondVector3_to_4, bondVector2_to_3))
    denom = magnitude( numpy.cross(bondVector2_to_1, bondVector2_to_3) )

    return numer/denom

def calcOOPBend(atom1, atom2, atom3, atom4):
    phi = convertUnits(calcBondAngle(atom2, atom4, atom3), "degree", "radian")
    sinphi = numpy.sin(phi)

    e41 = getUnitVector(getBondVector(atom4, atom1))
    e42 = getUnitVector(getBondVector(atom4, atom2))
    e43 = getUnitVector(getBondVector(atom4, atom3))

    sintheta = numpy.dot(numpy.cross(e42, e43), e41) / sinphi
    theta = numpy.arcsin(sintheta)

    return theta


## Takes an array of xyz coordinates (with labels) and returns an atom list
#  @param xyzArray
#  @return A list of atom objects
def getAtomListFromXYZ(atoms, xyz):
    if not isinstance(xyz, DataPoint):
        raise ProgrammingError("getAtomListFromXYZ requires a DataPoint object")

    number = 1
    atomList = []
    for i in xrange(len(xyz)):
        label = atoms[i]
        coords = xyz[i]
        newAtom = Atom(label, coords, number)
        atomList.append(newAtom)
        number += 1

    return atomList

## Returns a bond vector pointing from atom1 to atom2
# @param atom1 An instance of an atom. 
# @param atom2 An instance of an atom.
# @return The bond vector from atom1 to atom2
def getBondVector(atom1, atom2):
    deltaX = atom2.getX() - atom1.getX()
    deltaY = atom2.getY() - atom1.getY()
    deltaZ = atom2.getZ() - atom1.getZ()
    return [deltaX, deltaY, deltaZ]

## Methods to get information about individual atoms
ATOM_INFO = {
    "H" : { "ATOMIC WEIGHT" : 1.00782503207, "ATOMIC NUMBER" : 1, "CORE ELECTRONS" : 0, "VALENCE ELECTRONS" : 1, "NAME" : "HYDROGEN" , "CHARGE" : 1.00 },
    "HE" : { "ATOMIC WEIGHT" : 4.002602, "ATOMIC NUMBER" : 2, "CORE ELECTRONS" : 0, "VALENCE ELECTRONS" : 2, "NAME" : "HELIUM" , "CHARGE" : 2.00 },
    "LI" : { "ATOMIC WEIGHT" : 6.941, "ATOMIC NUMBER" : 3, "CORE ELECTRONS" : 2, "VALENCE ELECTRONS" : 1, "NAME" : "LITHIUM", "CHARGE" : 3.00 },
    "BE" : { "ATOMIC WEIGHT" : 9.012182, "ATOMIC NUMBER" : 4, "CORE ELECTRONS" : 2, "VALENCE ELECTRONS" : 2, "NAME" : "BERYLLIUM", "CHARGE" : 4.00 },
    "B" : { "ATOMIC WEIGHT" : 10.812, "ATOMIC NUMBER" : 5, "CORE ELECTRONS" : 2, "VALENCE ELECTRONS" : 3, "NAME" : "BORON", "CHARGE" : 5.00 },
    "C" : { "ATOMIC WEIGHT" : 12.00000, "ATOMIC NUMBER" : 6, "CORE ELECTRONS" : 2, "VALENCE ELECTRONS" : 4, "NAME" : "CARBON", "CHARGE" : 6.00 },  
    "N" : { "ATOMIC WEIGHT" : 14.00307400478, "ATOMIC NUMBER" : 7, "CORE ELECTRONS" : 2, "VALENCE ELECTRONS" : 5, "NAME" : "NITROGEN", "CHARGE" : 7.00 },
    "O" : { "ATOMIC WEIGHT" : 15.99491461956, "ATOMIC NUMBER" : 8, "CORE ELECTRONS" : 2, "VALENCE ELECTRONS" : 6, "NAME" : "OXYGEN", "CHARGE" : 8.00 },
    "F" : { "ATOMIC WEIGHT" : 18.9984, "ATOMIC NUMBER" : 9, "CORE ELECTRONS" : 2, "VALENCE ELECTRONS" : 7, "NAME" : "FLUORINE", "CHARGE" : 9.00 },
    "NE" : { "ATOMIC WEIGHT" : 20.1797, "ATOMIC NUMBER" : 10, "CORE ELECTRONS" : 2, "VALENCE ELECTRONS" : 8, "NAME" : "NEON", "CHARGE" : 10.00 },
    "S" : { "ATOMIC WEIGHT" : 31.972070999, "ATOMIC NUMBER" : 16, "CORE ELECTRONS" : 10, "VALENCE ELECTRONS" : 6, "NAME" : "SULFUR", "CHARGE" : 16.00 },
    "X" : { "ATOMIC WEIGHT" : 0.0, "ATOMIC NUMBER" : 0, "CORE ELECTRONS" : 0, "VALENCE ELECTRONS" : 0, "NAME" : "DUMMY", "CHARGE" : 0.00 },
    "P" : { "ATOMIC WEIGHT" : 30.973762, "ATOMIC NUMBER" : 15, "CORE ELECTRONS" : 10, "VALENCE ELECTRONS" : 5, "NAME" : "PHOSPHORUS", "CHARGE" : 15.00 }, 
    "CL" : { "ATOMIC WEIGHT" : 35.5, "ATOMIC NUMBER" : 17, "CORE ELECTRONS" : 10, "VALENCE ELECTRONS" : 7, "NAME" : "CHLORINE", "CHARGE" : 17.00 }, 
    "SI" : { "ATOMIC WEIGHT" : 28, "ATOMIC NUMBER" : 14, "CORE ELECTRONS" : 10, "VALENCE ELECTRONS" : 4, "NAME" : "SILICON", "CHARGE" : 14.00 },   
    "AR" : { "ATOMIC WEIGHT" : 39.948, "ATOMIC NUMBER" : 18, "CORE ELECTRONS" : 10, "VALENCE ELECTRONS" : 8, "NAME" : "ARGON", "CHARGE" : 18.00 },   
    "AL" : { "ATOMIC WEIGHT" : 26.9815386, "ATOMIC NUMBER" : 13, "CORE ELECTRONS" : 10, "VALENCE ELECTRONS" : 3, "NAME" : "ALUMINUM", "CHARGE" : 13.00 },   
    }

## Figures out which atoms has a specified atom property, i.e. charge, mass, etc.
#  @param infoType The type of info being suppled, i.e. charge, mass
#  @param infoValue The value of the info being supplied
#  @return The atomic symbol of the atom that has the specified property
def getAtomFromInfo(infoType, infoValue):
    for atom in ATOM_INFO:
        try:
            testInfo = ATOM_INFO[atom][infoType.upper()]
            if testInfo == infoValue:
                return atom
        except KeyError:
            return None
    return None

def getInfo(infoType, atom):
    return ATOM_INFO[atom.upper()][infoType.upper()]

## Figures out whether a string corresponds to an atomic symbol
#  @param atom The string to test
#  @return A boolean.  True if the string is an atomic symbol. False if not.
def isAtom(atom):
    if atom.upper() in ATOM_INFO:
        return True
    else:
        return False

class GeometryValueObject:

    THRESHOLDS = {
        'bond' : 0.001,
        'angle' : 1,
        'dih' : 2,
    }

    def __init__(self, type, name, value):
        self.type = type
        self.name = name
        self.value = value
        
        if self.type == 'dih' and self.value < 0:
            self.value += 360

    def __eq__(self, other):
        if self.type != other.type:
            return False

        if self.name != other.name:
            return False

        diff = 0
        if self.type == "dih":
            diff = min( abs(self.value - other.value), abs(self.value + 360 - other.value), abs(self.value - 360 - other.value) )
        else:
            diff = abs(self.value - other.value)
        if diff > self.THRESHOLDS[self.type]:
            return False

        return True

    def __lt__(self, other):
        if self.type < other.type:
            return True
        elif self.type > other.type:
            return False

        if self.name < other.name:
            return True
        elif self.name > other.name:
            return False

        if self.value < other.value:
            return True
        else:
            return False

    def __repr__(self):
        return "%s %s %s" % (self.type, self.name, self.value)

    def getData(self):
        return self.type, self.name, self.value

def canonicalizeGeometryLabel(label):
    allchars = re.compile('\D').findall(label)
    charlist = []
    for char in allchars:
        charlist.append(char)
    
    straight = "".join(charlist)
    charlist.reverse()
    reversed = "".join(charlist)

    if (reversed < straight):
        return reversed
    else:
        return straight

## This class encapsulates a molecule
class Molecule(chem.data.Item):

    discontinuity = -90

    ## Constructor for the molecule
    # @param coords The xyz coordinates of the molecule.  The first column should be a list of atom names or atomic symbols.  The next 3 columns
    #               should be the x,y, and z coordinates
    # @param chrg An integer giving the charge on the molecule
    # @param mult An integer giving the multiplicity of the spin
    # @param stateSymm A string identifying the irrep of the electronic state
    # @param molName The name of the molecule.  Defaults to the molecular formula.
    # @param units The units the geometry are specified in
    # @param ener The energy of the molecule, given as a float
    # @param recenter A boolean, whether or not to center the molecule on its center of mass
    # @param reorient A boolean, whehter or not to reorient the molecule 
    def __init__(self, atomList, chrg = 0, mult = 1, stateSymm = "A", molName = None, ener=0, recenter = False, reorient = False):        
        if isinstance(atomList[0], Atom):
            self.atoms = atomList
        else:
            self.atoms = getAtomListFromXYZ(atomList)

        chem.data.Item.__init__(self)
        #check if state symmetry and molecule name should be given defaults
        title = molName
        if not molName: #no molname given
            title = self.getMolecularFormula()
        #set the things that definitely need to be set
        self.setAttributes(charge=chrg,multiplicity=mult,stateSymmetry=stateSymm,title=title)

        #if desired, reorient and recenter molecule
        if recenter: 
            self.recenter()
        #allow recentering and reorienting unless specficially told not to later on
        self.okRecenter = True

        if reorient: 
            self.reorient()
        self.okReorient = True 

        self.ZPVE = None
        self.frequencies = []
        self.gradients = []
        self.intensities = []
        self.dipole = []
        self.energy = ener


    def __str__(self):
        desc = []
        desc.append("%20s=%16.12f" % ('energy', self.getEnergy()))
        formatter = Formatter()
        for attribute in self.getAttributes():
            desc.append("%20s=%16s" % (attribute, formatter(Molecule.getAttribute(self, attribute))))
        desc.append("xyz (%s)" % self.getUnits())
        desc.append(self.getXYZTable(units = self.getUnits()))
        return "\n".join(desc)

    def __len__(self):
        return len(self.atoms)

    def __iter__(self):
        return iter(self.atoms)


    def __repr__(self):
        return str(self)

    def getAtom(self, atomNumber):
        atom = self.atoms[atomNumber-1]
        return atom

    def isSame(self, other):
        if self.getNumAtoms() != other.getNumAtoms():
            return False

        mol1 = self.copy()
        mol2 = other.copy()
        #make sure to reorient to recenter
        mol1.recenter(); mol1.reorient()
        mol2.recenter(); mol2.reorient()

        atomset1 = mol1.getAtoms()
        atomset2 = mol2.getAtoms()

        atomset1.sort()
        atomset2.sort()

        for i in range( self.getNumAtoms() ):
            if not atomset1[i] == atomset2[i]:
                return False
        #they all check out
        return True

    ##Gets all the atoms in the molecule
    # @return A list of atom instances
    def getAtoms(self, includeDummies = False):
        return self.atoms

    ## Gets a specific set of geometry values for the molecule
    # @param A 2D array.  Each entry is a list containing atom numbers defining the geom value.
    #                     Two values means a bond, three an angle, etc.
    # @return A list of geometry values in the same order as the speficiation list.
    def getGeomValues(self, valueList):
        getAtom = lambda x: self.atoms[ x - 1 ]
        getSymbol = lambda x: x.getSymbol()
        values = []
        for entry in valueList:
            if len(entry) == 2:
                [num1, num2] = entry
                [atom1, atom2] = map(getAtom, entry)
                [label1, label2] = map(getSymbol, [atom1, atom2])
                bondLength = calcBondLength(atom1, atom2)
                if self.getUnits() == "bohr":
                    bondLength = convertUnits(bondLength, "bohr", "angstrom")
                values.append(bondLength)

            if len(entry) == 3:
                [num1, num2, num3] = entry
                [atom1, atom2, atom3] = map(getAtom, entry)
                [label1, label2, label3] = map(getSymbol, [atom1, atom2])
                angle = calcBondAngle(atom1, atom2, atom3)
                values.append(angle)
                
            if len(entry) == 4:
                [num1, num2, num3, num4] = entry
                [atom1, atom2, atom3, atom4] = map(getAtom, entry)
                [label1, label2, label3, label4] = map(getSymbol, [atom1, atom2, atom3, atom4])
                dihedral = calcDihedralAngle(atom1, atom2, atom3, atom4)
                values.append(dihedral)
                
        return values

    def getXYZFile(self):
        str_arr = []
        str_arr.append("%d" % self.getNumAtoms())
        str_arr.append("%s" % self.getAttribute("title"))
        str_arr.append(self.getXYZTable())
        return "\n".join(str_arr)

    def getGeometryFeatures(self):
        bondLengths = []
        connectivity = [] #stores which atoms are "connected" to each other

        bonds = []
        angles = []
        dihedrals = []

        #fill out the bondLengths and connectivity arrays
        for i in range(0, len(self.atoms)):
            connectivity.append([])
            bondLengths.append([])

        #first store all the bond lengths - this will be used in determining which values to print
        for i in range(0, len(self.atoms)):
            for j in range(0, i):
                atom1 = self.atoms[i]
                atom2 = self.atoms[j]
                bondLength = calcBondLength(atom1, atom2)
                bondThreshold = getBondThreshold(atom1, atom2, self.getUnits())
                if bondLength < bondThreshold: #the atoms are bonded
                    connectivity[i].append(j)
                    connectivity[j].append(i)

        #print out all the bond lengths of atoms that are connected to each other
        for i in range(0, len(connectivity)):
            connectedAtoms = connectivity[i]
            for atom in connectedAtoms:
                if atom < i:
                    bonds.append( [i, atom] )
                        
        for i in range(0, len(connectivity)):
            connectedMiddleAtoms = connectivity[i]
            for middleAtom in connectedMiddleAtoms:
                connectedEndAtoms = connectivity[middleAtom]
                for endAtom in connectedEndAtoms:
                    if endAtom < i:
                        angles.append([i, middleAtom, endAtom])
                            
        for i in range(0, len(connectivity)):
            firstMiddleAtoms = connectivity[i]
            for firstMiddleAtom in firstMiddleAtoms:
                secondMiddleAtoms = connectivity[firstMiddleAtom]
                for secondMiddleAtom in secondMiddleAtoms:
                        if not secondMiddleAtom == i:
                            connectedEndAtoms = connectivity[secondMiddleAtom]
                            for endAtom in connectedEndAtoms:
                                if not endAtom == firstMiddleAtom and endAtom < i:
                                    dihedrals.append([i, firstMiddleAtom, secondMiddleAtom, endAtom])

        return bonds, angles, dihedrals

    def getGeomValues(self):
        bonds = []
        angles = []
        dihedrals = []
    
        bondLengths = []
        connectivity = [] #stores which atoms are "connected" to each other

        bond_indices, ang_indices, dih_indices = self.getGeometryFeatures()

        for i, atom in bond_indices:
            atom1 = self.atoms[i] 
            atom2 = self.atoms[atom]
            bondValue = calcBondLength(atom1, atom2)
            bondLength = bondValue
            name1 = "%s%d" % (atom1.getSymbol(), i+1)
            name2 = "%s%d" % (atom2.getSymbol(), atom+1)
            label = "%s-%s" % (name1, name2)
            bonds.append([label, bondLength])

                        
        for i, middle, end in ang_indices: 
            atom1 = self.atoms[i]
            atom2 = self.atoms[middle]
            atom3 = self.atoms[end]
            bondAngle = calcBondAngle(atom1, atom2, atom3)
            name1 = "%s%d" % (atom1.getSymbol(), i+1)
            name2 = "%s%d" % (atom2.getSymbol(), middle+1)
            name3 = "%s%d" % (atom3.getSymbol(), end+1)
            label = "%s-%s-%s" % (name1, name2, name3)
            angles.append([label, bondAngle])

        for i, middle1, middle2, end in dih_indices:
            atom1 = self.atoms[i]
            atom2 = self.atoms[middle1]
            atom3 = self.atoms[middle2]
            atom4 = self.atoms[end]
            dihedral = calcDihedralAngle(atom1, atom2, atom3, atom4)
            name1 = "%s%d" % (atom1.getSymbol(), i+1)
            name2 = "%s%d" % (atom2.getSymbol(), middle1+1)
            name3 = "%s%d" % (atom3.getSymbol(), middle2+1)
            name4 = "%s%d" % (atom4.getSymbol(), end+1)                                    
            label = "%s-%s-%s-%s" % (name1, name2, name3, name4)
            dihedrals.append([label, dihedral])

        return bonds, angles, dihedrals

    # Creates a human readable description of the geometry, displaying all geometry variables defined by bond connectivities
    # @param includeBonds a boolean, whether to includeBonds
    # @param includeAngles a boolean, whether to includeAngles
    # @param includeDihedrals a boolean, whether to includeDihedrals
    def getGeomDescription(self, includeBonds = True, includeAngles = True, includeDihedrals = True, bondPrecision=4, 
                           anglePrecision=2, dihPrecision=1, units="ANGSTROM", angleUnits="DEGREE"):
        bondThreshold = 0

        units=units.upper()

        percent = '%'
        bondString = "%s13.%df" % (percent, bondPrecision)
        angleString = "%s13.%df" % (percent, anglePrecision)
        dihString = "%s13.%df" % (percent, dihPrecision)

        bonds, angles, dihedrals = self.getGeomValues()
        descriptions = []

        if includeBonds:
            for label, bondLength in bonds:
                descriptions.append(label.ljust(12) + "\t" + bondString % convertUnits(bondLength, self.getUnits(), units))
                        
        if includeAngles:
            for label, bondAngle in angles:
                descriptions.append(label.ljust(12) + "\t" + angleString % convertUnits(bondAngle, "DEGREE", angleUnits))
                            
        if includeDihedrals:
            for label, dihedral in dihedrals:
                descriptions.append(label.ljust(12) + "\t" + dihString % convertUnits(dihedral, "DEGREE", angleUnits))

        return "\n".join(descriptions)

    def getGeomDifference(self, other, units="ANGSTROM"):
        self_values = self.getGeomValues()
        other_values = other.getGeomValues()

        difference_array = []
        
        BOND=0
    
        #do bonds  
        for value_type in range(0, len(self_values)):
            for value_num in range(0, len(self_values[value_type])): 
                self_label, self_value = self_values[value_type][value_num]
                other_label, other_value = other_values[value_type][value_num]
                if self_label == other_label:
                    if value_type == BOND:
                        self_value = convertUnits(self_value, self.units, units)
                        other_value = convertUnits(other_value, other.units, units)
                    diff = self_value - other_value  
                    difference_array.append( "%s %12.8f %12.8f %12.8f" % (self_label.ljust(12), self_value, other_value, diff) )

        return "\n".join(difference_array)

    ## Makes a string suitable as a unique identifier for the molecule, a molecule "hash".  The identifier is a list of bond lengths
    #  and bond angles.
    #  @return A string identifier
    def getHash(self):
        if len(self.atoms) == 1: #only a single atom
            return str(self.atoms[0])

        return self.getGeomDescription(True, True, False, 3, 1)

    def getFullHash(self):
        return self.getGeomDescription(True, True, True, 3, 1, 1)

    def getWeakHash(self):
        vallist = getConformerValues(self.getFullHash())
        text_arr = []
        for val in vallist:
            text_arr.append("%s" % val)
        return "\n".join(text_arr)

    def hasSameValues(self, other, printDetail=False):
        selfvals = Molecule.getValueListFromHash( self.getFullHash() )
        othervals = Molecule.getValueListFromHash( other.getFullHash() )

        if len(selfvals) != len(othervals):
            return False

        same = True
        for i in range(len(selfvals)):
            if not selfvals[i] == othervals[i]:
                if printDetail:
                    sys.stdout.write("%s is different from %s\n"  % (selfvals[i], othervals[i]))
                same = False
            else:
                if printDetail:
                    sys.stdout.write("%s is the same as %s\n"  % (selfvals[i], othervals[i]))

        return same

    def getValueListFromHash(hash):
        typedict = {
            2 : 'bond',
            3 : 'angle',
            4 : 'dih',
        }
        arr = []
        for line in hash.splitlines():
            label, value = line.split()
            type = typedict[len(label.split("-"))]
            cleanLabel = canonicalizeGeometryLabel(label)
            arr.append( GeometryValueObject(type, cleanLabel, eval(value)) )
        arr.sort()
        return arr
    getValueListFromHash = staticmethod(getValueListFromHash)

    def getConformerValues(self):
        return self.getValueListFromHash(self.getFullHash())
        
    ##Gets a bond angle
    #  @param args A list of three integers corresponding to the numbers of the three atoms (in order of connectivity for the angle)
    #  @return The bond angle as a float
    def getBondAngle(self, *args):
        angle = calcBondAngle(self.atoms[args[0]-1], self.atoms[args[1]-1], self.atoms[args[2]-1])
        return angle

    ## Gets a bond length
    #  @param args A list of two integers corresponding to the numbers of the two atoms
    #  @return The bond length as a float
    def getBondLength(self, *args):
        bond = calcBondLength(self.atoms[args[0]-1], self.atoms[args[1]-1])
        return bond

    ## Gets a bond length
    #  @param args A list of two integers corresponding to the numbers of the two atoms
    #  @return The bond length as a float
    def getOutOfPlaneBend(self, args):
        bond = calcOOPBend(self.atoms[args[0]-1], self.atoms[args[1]-1], self.atoms[args[2]-1], self.atoms[args[3]-1])
        return bond

    def getLinX(self, args):
        getAtom = lambda x: self.atoms[x-1]
        atom1, atom2, atom3, atom4 = map(getAtom, args)
        linx = calcLinX(atom1, atom2, atom3, atom4)
        return linx

    def getLinY(self, args):
        getAtom = lambda x: self.atoms[x-1]
        atom1, atom2, atom3, atom4 = map(getAtom, args)
        liny = calcLinY(atom1, atom2, atom3, atom4)
        return liny

    ## Gets the center of mass
    # @return A position vector for the center of mass
    def getCenterOfMass(self):
        xMoment = 0
        yMoment = 0
        zMoment = 0
        totalMass = 0
        for atom in self.atoms:
            mass = atom.getMass()
            totalMass += mass
            xMoment += atom.getX() * mass
            yMoment += atom.getY() * mass
            zMoment += atom.getZ() * mass
        xCenter = xMoment / totalMass
        yCenter = yMoment / totalMass
        zCenter = zMoment / totalMass

        return [xCenter, yCenter, zCenter]    

    ##Gets the charge associated with this molecule
    # @return An integer, the charge
    def getCharge(self):
        charge = Molecule.getAttribute(self, 'charge')
        return Molecule.getAttribute(self, 'charge')
    
    ##Gets a conformation label from a list of dihedral angles
    #  @param dihedrals A 2-D array specifying a list of dihedral angles.  Each array element is an array
    #                   of atom numbers specifying the dihedral
    def getConformerLabel(self, dihedrals = None):
        disc = self.discontinuity
        self.discontinuity = -180
        valueList = []
        if not dihedrals:
            throw_away_bonds, throw_away_angles, valueList = self.getGeomValues()
        else:
            if isinstance(dihedrals, str):
                dihlist = []
                for line in dihedrals.strip().splitlines():
                    dihlist.append( map(eval, line.strip().split()) )
            elif isinstance(dihedrals, list):
                dihlist = dihedrals
            for entry in dihlist:
                dih = self.getDihedralAngle(entry)
                valueList.append([str(entry), dih])
        
        dihLabels = []
        for label, value in valueList:
            dihLabel = Molecule.getDihLabel(value)
            dihLabels.append(dihLabel)

        #return the discontinuity
        self.discontinuity = disc

        name = "_".join(dihLabels)
        return name

    def getDihLabel(dih):
        if dih >= -30 and dih < 30:
            return "C"
        elif dih >= 30 and dih < 90:
            return "G+"
        elif dih >= 90 and dih < 150:
            return "A+"
        elif dih >= 150 or dih < -150:
            return "T"
        elif dih >= -150  and dih < -90:
            return "A-"
        elif dih >= -90 and dih < -30:
            return "G-"
        elif dih >= 210 and dih < 270:
            return "G-"

    getDihLabel = staticmethod(getDihLabel)

    ##Gets a dihedral angle
    #  @param args A list of four integers corresponding to the numbers of the four atoms (in order of connectivity for the angle)
    #  @return The dihedral angle as a float
    def getDihedralAngle(self, *xargs):
        args = None
        if isinstance(xargs[0], list) or isinstance(xargs[0], tuple): #arguments given as list object
            args = xargs[0]
        else:
            args = xargs
        atom1 = self.atoms[args[0]-1]
        atom2 = self.atoms[args[1]-1]
        atom3 = self.atoms[args[2]-1]
        atom4 = self.atoms[args[3]-1]
        angle = calcDihedralAngle(atom1, atom2, atom3, atom4, self.discontinuity)
        return angle

    ## Gets the energy
    # @return A float, the energy
    def getEnergy(self):
        return self.getValue()

    ## Gets the force constants
    # @return A 2-D array of floats containing the force constants
    def getForceConstants(self):
        return forceConstants

    ## Gets the gradients
    # @return A 2-D array. The first column are the x-gradients, second column the y-gradients, third column the z-gradients
    def getGradients(self):
        return self.gradients

    def setGradients(self, grads):
        self.gradients = grads

    def getForceConstants(self):
        return self.fc

    def setForceConstants(self, fc):
        self.fc = fc

    def getFormulaDict(self):
        formula = {}
        for atom in self.atoms:
            lbl = atom.getSymbol()
            if lbl in formula:
                formula[lbl] += 1
            else:
                formula[lbl] = 1
        return formula

    def getMolecularFormula(self):
        formula = {}
        for atom in self.atoms:
            label = atom.getSymbol()
            if formula.has_key(label):
                formula[label] += 1
            else:
                formula[label] = 1
                
        name = ""
        for entry in formula:
            name += entry
            if formula[entry] == 1:
                pass
            else:
                name += "%d" % formula[entry]
                
        return name

    def getSymmetryElements(self):
        if not hasattr(self, 'symmetryElements') or not self.symmetryElements: #not yet initialized
            from grouptheory import getPointGroup
            self.pointGroup, self.symmetryElements = getPointGroup(self)
        return self.symmetryElements

    ## Gets the inertial tensor for the molecule
    #  @return A 2x2 array, giving the inertia tensor
    def getMomentOfInertiaTensor(self):
        [xCenter, yCenter, zCenter] = self.getCenterOfMass()
        xx = 0
        xy = 0
        xz = 0
        yz = 0
        yy = 0
        zz = 0
        for atom in self.atoms:
            [x,y,z] = atom.getXYZ().getValue("angstrom")
            #move to the center of mass
            x -= xCenter
            y -= yCenter
            z -= zCenter
            mass = atom.getMass()
            xx += mass * (y*y + z*z)
            yy += mass * (x*x + z*z)
            zz += mass * (x*x + y*y)
            xy += -1 * mass * (x*y)
            xz += -1 * mass * (x*z)
            yz += -1 * mass * (y*z)

        tensor = [
            [xx, xy, xz],
            [xy, yy, yz],
            [xz, yz, zz]
            ]

        return tensor

    ##Gets the multiplicity of the molecule
    # @return An integer, the multiplicity
    def getMultiplicity(self):
        return skynet.identity.Identity.getAttribute(self,'multiplicity')

    def isOpenShell(self):
        if self.multiplicity == 1:
            return False
        return True

    ##Gets the name of the molecule
    # @return A string identifier for the molecule
    def getTitle(self):
        return Molecule.getAttribute(self, 'title')

    ## Gets the normal modes
    # @return A list of VibrationalMode objects sorted by energy ordering
    def getNormalModes(self):
        return self.normalModes

    ##Gets the number of atoms in the molecule
    # @return The number of atoms (not including dummies)
    def getNumAtoms(self):
        return len(self.atoms)

    def getNumberOfElectrons(self):
        num_electrons = 0
        for atom in self.atoms:
            num_electrons += atom.getCharge()
        ch = self.getCharge()
        num_electrons -= self.getCharge()
        return num_electrons

    def getNumberOfOrbitals(self):
        num_electrons = self.getNumberOfElectrons()
        num_orbitals = num_electrons/2 + num_electrons%2
        return num_orbitals

    def getNumberOfCoreElectrons(self):
        num_electrons = 0
        for atom in self.atoms:
            num_electrons += atom.getNumCoreOrbitals()
        return num_electrons

    def getNumberOfUnpairedElectrons(self):
        return self.getMultiplicity() - 1

    ## Returns all the molecular orbitals
    #  @return A list of orbital objects sorted by energy ordering
    def getOrbitals(self):
        return self.orbitals

    ##Gets the point group of the molecule
    # @return A string identifying the point group of the molecule
    def getPointGroup(self):
        if not hasattr(self, 'symmetryElements'): #never initialized
            from grouptheory import getPointGroup
            self.pointGroup, self.symmetryElements = getPointGroup(self)
        return self.pointGroup

    def allowRecenter(self):
        return self.okRecenter

    def allowReorient(self):
        return self.okReorient

    ## Gets the moments of inertia
    # @return The array of inertia moments
    def getPrincipalMoments(self):
        if not hasattr(self, 'moments'):
            pAxes = self.getPrincipalRotationAxes()

        return self.moments

    def getPrincipalRotationAxes(self):
        import numpy
        I = numpy.array(self.getMomentOfInertiaTensor()).astype(numpy.float64)
        self.moments, axisSet = numpy.linalg.eig(I)
        return axisSet

    def getRotationalConstants(self):
        conversion = 1E-20 * 1.66053886E-27
        moments = self.getPrincipalMoments() * conversion
        import math
        h = 6.626068e-34
        ItoA = lambda x: h/8/math.pi/math.pi/x/1e6
        return map(ItoA, moments)
        
    
    ##Gets the state symmetry of the electronic state associated with this molecule
    # @return A string identifier for the electronic state
    def getStateSymmetry(self):
        return Molecule.getAttribute(self, 'statesymmetry')

    ## Gets the units
    #  @return The units the molecular geometry is specified in
    def getUnits(self):
        val = self.atoms[0].getXYZ().getUnits()
        return val

    ##Gets the XYZ coordinates as a 2-D array, with optional arguments to include extra labels in the coordinates
    # @param includeLabels A boolean, whether or not to include the atom label in the coordinates
    # @param includeCharges A boolean, whether or not to include the atom charge in the coordinates  
    # @return The XYZ coordinates as a 2-D array.  The last 3 columns are the x,y,z coordinates.  Optional columns may be
    #         the atom labels, charges, and numbers
    def getXYZMatrix(self, units = "angstrom", includeLabels=True, includeCharges=False):
        coords = []
        selfunits = self.getAttribute('units')
        for atom in self.atoms:
            if atom.getName() == "DUMMY":
                donothing = 0
            else:
                currentAtom = []
                if includeLabels:
                    currentAtom.append(atom.getSymbol())
                if includeCharges:
                    currentAtom.append(atom.getCharge())
                xyz = atom.getXYZ().getValue(units)
                currentAtom.extend(xyz)
                coords.append(currentAtom)
        return coords

    def getXYZ(self):
        units = self.getUnits()
        coords = []
        for atom in self.atoms:
            if atom.getName() == "DUMMY":
                pass
            else:
                currentAtom = atom.getXYZ().getValue(units)
                coords.append(currentAtom)
        newXYZ = DataPoint(numpy.array(coords), units=units)
        return newXYZ

    def writeXYZFile(self, file):
        str_array = ["%d" % self.getNumAtoms()] 
        str_array.append( self.getMolecularFormula() )
        xyz = self.getXYZTable(units="ANGSTROM")
        str_array.append( xyz )
        str_array.append( "" )
        text = "\n".join(str_array)
        fileObj = open(file, "w")
        fileObj.write(text)
        fileObj.close()

    ## Gets a set of formatted xyz coordinates for printing
    # @param includeLabels A boolean, whether or not to include the atom label in the coordinates
    # @param includeNumbers A boolean, whether or not to include the atom number in the coordinates    
    # @param includeCharges A boolean, whether or not to include the atom charge in the coordinates
    # @param delim The delimiter between entries in the xyz coordinates
    # @param closeLine A closer for the line
    def getXYZTable(self, units="angstrom", includeLabels=True, includeNumbers=False, includeCharges=False, delim = " ", closeLine = "", align=False, xyzformat = "%14.8f"):
        formattedXYZ = []
        atomNumber = 1
        format = lambda x: xyzformat % x
        for atom in self.atoms:
            if atom.getName() == "DUMMY":
                donothing = 0
            else:
                label = ""
                xyz = atom.getXYZ()
                if includeLabels:
                    label += "%s%s" % (atom.getSymbol(), delim)
                if includeNumbers:
                    label += "%d%s" % (atomNumber, delim)
                    atomNumber += 1 
                if includeCharges:
                    label += "%4.2f%s" % (atom.getCharge(), delim)

                nextline = []
                if includeLabels: nextline.append( ("%s" % label).ljust(3) )
                nextline.extend( map(format, xyz.getValue(units)) )
                nextline = delim.join(nextline)
                nextline += closeLine
                formattedXYZ.append(nextline)

        return "\n".join(formattedXYZ)

    ## Returns the zero-point vibrational energy of the molecule in kcal/mol
    def getZPVE(self):
        if not hasattr(self, 'frequencies'):
            return 0 #this may not be a good thing to do... perhaps an exception should be thrown

        if len(self.frequencies) == 0:
            return 0 
        
        if not self.ZPVE:
                ZPVEinCMx2 = 0
                for freq in self.frequencies:
                    if freq > 0:
                        ZPVEinCMx2 += freq

        self.ZPVE = 0.5 * convertUnits(ZPVEinCMx2, "wavenumber", "kcal")
        return self.ZPVE
            
    ## Recenters the molecule on the center of mass
    def recenter(self):
        comMove = numpy.array(self.getCenterOfMass()) * -1
        self.translate(comMove)

    ## Reorients the molecule to line up with the principal axes
    def reorient(self):
        import numpy
        selfunits = self.getUnits()
        I = numpy.array(self.getMomentOfInertiaTensor()).astype(numpy.float64)
        self.moments, axisSet = numpy.linalg.eig(I)
        [xAxis, yAxis, zAxis] = axisSet
        self.rotateAxes(xAxis, yAxis, zAxis)

    ## Sets the coordinates of the molecule
    # @param coords The coordinates of the molecule in either z-matrix or xyz format
    # @param vars An optional argument for z-matrices to give the variable values.  This should be a dictionary where the keys are the variable names
    #             and the values are the variable values
    # @param conts An optional argument for z-matrices to give the constant values.  This should be a dictionary where the keys are the constant names
    #             and the values are the constant
    def resetCoordinates(self, coords = [], vars = {}, consts = {}):
        self.atoms = []
        for atom in coords:
            xyz = atom[1:]
            name = atom[0]
            newAtom = Atom(name, xyz)
            self.atoms.append(newAtom)

    ## Rotates the entire molecule in the coordinate frame
    # @param axis A vector giving the rotation axis
    # @param angle The rotation angle in degrees
    # @param origin The origin to rotate around, defaults to [0,0,0]
    def rotate(self, axis, angle, origin = [0,0,0]):
        self.translate(-1 * numpy.array(origin))
        rotMatrix = getRotationMatrix(axis, angle)
        for atom in self.atoms:
            atom.transform(matrix)
        self.translate(origin)

    ## Rotate the molecule around a bond vector pointing from atom1 to atom2
    #  @param angle The angle to rotate by in degrees
    #  @param at1 The number of the first atom
    #  @param at2 The number of the second atom
    #  @param atomsToRotate A list of atoms to include in the rotation
    def rotateAroundBond(self, angle, at1, at2, atomsToRotate):
        atom1 = self.atoms[at1-1]
        atom2 = self.atoms[at2-1]
        xCenter = ( atom1.getX() + atom2.getX() ) / 2.0
        yCenter = ( atom1.getY() + atom2.getY() ) / 2.0
        zCenter = ( atom1.getZ() + atom2.getZ() ) / 2.0
        origin = [xCenter, yCenter, zCenter]
        axis = getBondVector(atom1, atom2)
        self.rotateAtoms(atomsToRotate, axis, angle, origin)

    ##Rotates only a subset of the atoms
    #@param atomsToRotate A vector giving the numbers of the atoms to rotate
    #@param axis A vector giving the rotation axis
    #@param angle The rotation angle in degrees
    #@param origin The origin to rotate around, defaults to [0,0,0]        
    def rotateAtoms(self, atomsToRotate, axis, angle, origin = [0,0,0]):

        self.translateAtoms(atomsToRotate, -1 * numpy.array(origin))
        rotMatrix = getRotationMatrix(axis, angle)
        for atomNumber in atomsToRotate:
            atom = self.atoms[atomNumber-1]
            atom.transform(rotMatrix)
        self.translateAtoms(atomsToRotate, origin)

    ## Rotates the coordinate frame (by modifying a set of coordinates).  Note, a set of vectors is given.
    ## If these vectors are not mutually orthogonal, then a gram-schmidt orthonormalization is performed to
    ## ensure the coordinate axes are well defined.  The gram-schmidt procedure begins with the z-axis, goes
    ## to the y-axis, and finishes with the x-axis
    #  @param xAxis A vector definining the desired new x axis
    #  @param yAxis A vector definining the desired new y axis
    #  @param zAxis A vector definining the desired new z axis
    #  @param coordinates The set of coordinates to transform
    #  @param origin 
    def rotateAxes(self, xAxis, yAxis, zAxis):
        import numpy
        import matrixmath

        from numpy import dot
        if abs( dot(xAxis, yAxis) ) > 1E-10 or abs( dot(xAxis, zAxis) ) > 1E-10 or abs( dot(zAxis, yAxis) ) > 1E-10:
            #first, we must perform a gram-schmidt to ensure that as closely as possible
            #the given basis resembles the old one, but ensure orthogonality
            [xAxis, yAxis, zAxis] = matrixmath.getGramSchmidtBasis(xAxis, yAxis, zAxis)
        rotMatrix = self.getAxisRotationMatrix(xAxis, yAxis, zAxis)

        for atom in self.atoms:
            atom.transform(rotMatrix)

    def getAxisRotationMatrix(self, xAxis, yAxis, zAxis):
        rotMatrix = [xAxis, yAxis, zAxis]
        rotMatrix = numpy.transpose(numpy.array(rotMatrix))
        return rotMatrix

    ## Sets the charge on the molecule
    # @param newCharge An integer giving the new charge on the molecule
    def setCharge(self, newCharge):
        self.setAttributes(charge=newCharge)

    def setDipole(self, dipole):
        self.dipole = dipole

    def setEnergy(self, energy):
        self.energy = energy

    def getEnergy(self):
        return self.energy

    def getDipole(self):
        return self.dipole

    def getPrincipalDipole(self):
        pAxes = self.getPrincipalRotationAxes()

        comps = []
        for x in pAxes:
            proj = numpy.dot(x, self.dipole)
            comps.append(proj)

        return numpy.array(comps)
        

    def getDipoleMoment(self):
        if len(self.dipole) == 0:
            return None
        import math
        import numpy
        return math.sqrt( numpy.dot(self.dipole, self.dipole) )

    def setFrequencies(self, freqs):
        self.frequencies = freqs[:]

    def getFrequencies(self):
        return self.frequencies

    def setIntensities(self, intens):
        self.intensities = intens[:]

    def getIntensities(self):
        return self.intensities

    ## Sets the moltiplicity on the molecule
    # @param newMult An integer giving the new multiplicity on the molecule
    def setMultiplicity(self, newMult):
        self.setAttributes(multiplicity=newMult)

    def setTitle(self, title):
        self.setAttributes(title=title)

    def setStateSymmetry(self, newSymm):
        self.setAttributes(stateSymmetry=newSymm)

    def setUnits(self, units):
        for atom in self.atoms:
            atom.setUnits(units)

    def setPointGroup(self, newpg):
        self.setAttributes(pointgroup=newpg)

    ## Sets the xyz coordinates of the molecule
    # @param xyz An array of xyz coordinates
    def setXYZ(self, xyz):
        if len(xyz) == len(self.atoms):
            for i in xrange(len(xyz)):
                currentAtom = self.atoms[i]
                newCoords = xyz[i]
                currentAtom.setXYZ(newCoords)


    ## Tests to see if the molecule has an atom matching the coordinates and atomic symbol
    #  @param testAtom The atom you are testing equivalence for - this can be either an atom or an array
    def testAtomEquivalence(self, testAtom):
        testXYZ = []
        testSymbol = ""
        try:
            testXYZ = testAtom.getXYZ()
            testSymbol = testAtom.getSymbol()
        except AttributeError:
            testXYZ = testAtom[1:]
            testSymbol = testAtom[0]
            
        for atom in self.atoms:
            xyz = atom.getXYZ()
            symbol = atom.getSymbol()

            import numpy
            delta = numpy.array(testXYZ) - numpy.array(xyz)
            dist = numpy.dot(delta, delta)

            if symbol == testSymbol and dist < 1E-8:
                return True

        return False

    ## Translates the molecule by the given amount
    #  @param amount A vector giving the x,y,z displacements 
    def translate(self, amount):
        for atom in self.atoms:
            atom.translate(amount)

    def displace(self, amount):
        for i in xrange(len(self.atoms)):
            self.atoms[i].translate(amount[i])

    def displaceXYZ(self, allXYZVector):
        for i in range(0, len(allXYZVector)/3):
            currentAtom = self.atoms[i]
            dispVector = allXYZVector[3*i:3*i + 3]
            currentAtom.translate(dispVector)

    ## Translates only a subset of the atoms
    # @param atomsToTranslate A vector giving the numbers of the atoms to translate
    # @param amount A vector giving the x,y,z displacements
    def translateAtoms(self, atomsToTranslate, amount):
        for atomNumber in atomsToTranslate:
            atom = self.atoms[atomNumber-1]
            atom.translate(amount)

    def getMathematicaXYZTable(self):
        
        def formatX(x):
            ret_str = ""
            if x < 0: ret_str = '\(%14.10f\)' % x        
            else: ret_str = '%14.10f' % x
            #get rid of whitespace
            return ret_str.replace(" " , "")

        xyz_array = []
        for atom in self.atoms:
            xyz_part = ",".join( map(formatX, atom.getXYZ()) )
            line = "\[IndentingNewLine]{%s}" % xyz_part
            xyz_array.append(line)

        return ",\n".join(xyz_array)

    def addXML(self, node):
        document = node.ownerDocument
        #add the xyz coordinates
        units = self.getUnits()
        xyzNode = document.createElement('xyz')
        xyzNode.setAttribute('units', str(units))
        xyzText = document.createTextNode('coordinates')
        xyzText.nodeValue = self.getXYZTable(units=units)
        xyzNode.appendChild(xyzText)
        node.appendChild(xyzNode)

        #add an energy node
        if abs(self.getEnergy()) > 1e-12: #only include if the energy is non-zero
            eNode = document.createElement('energy')
            eNode.setAttribute('type', 'molecular')
            eNode.setAttribute('value', "%14.10f" % self.getEnergy())
            node.appendChild(eNode)

    def getLonePairDihedral(self, *xargs):
        atom1, atom2, atom3, lpatom1, lpatom2 = map(self.getAtom, xargs)

        midxyz = 0.5 * (lpatom1.getXYZ() + lpatom2.getXYZ())

        a3midbond = midxyz - atom3.getXYZ()
        lonepair_xyz = atom3.getXYZ() - a3midbond
        lonepair_atom = Atom("H", lonepair_xyz) #just assign it as a hydrogen
        lpdih = calcDihedralAngle(atom1, atom2, atom3, lonepair_atom, self.discontinuity)
        return lpdih

    def getConfiguration(self, *xargs):
        center, A1, A2, A3, A4 = map(self.getAtom, xargs)
        vec1, vec2, vec3, vec4 = map(lambda x: x.getXYZ() - center.getXYZ(), (A1, A2, A3, A4))
        #take the cross product of 1 and 4 vectors
        testvec = vec1.cross(vec2)
        projection = testvec.dot(vec4)
        
        #if this is greater than 0, the 1-2-3-4 rotation is in a clockwise sense
        if projection > 0:
            return "D"

        else: #if less than 0, the 1-2-3-4 rotation in in a counter-clockwise sense
            return "L"

def canonicalizeAtomLabel(label):
    if isNumber(label):
        label = eval(label)
        label = getAtomFromInfo("CHARGE", label)
        return label

    #okay, not an integer
    label = removeNumberSuffix(label)
    newAtom = ""
    if label.upper() == "DUMMY" or label.upper() == "Q" or label.upper() == "X":
        return "Q"
    else:
        atomName = removeNumberSuffix(label)
        #check to see if we have an atomic symbol or an atom name
        symbol = getAtomFromInfo("NAME", atomName)
        if not symbol:
            return label
        else:
            return symbol

## This class encapsulates an atom
class Atom(skynet.identity.Identity):
    ## Constructor
    # @param atomName Either the atomic symbol or the name of the atom
    # @param coords The xyz coordinates of the atom.  This should be a list of 3 floats
    # @param num The number of this atom in a z-mat
    def __init__(self, label, coordinates = [0,0,0], units="angstrom", number=1):        
        if isinstance(coordinates, chem.data.DataPoint):
            self.coordinates = coordinates
        else:
            self.coordinates = chem.data.DataPoint(coordinates, units=units)

        skynet.identity.Identity.__init__(self)

        #and set some attributes
        atomicSymbol = label.upper()
        number = number
        self.info = ATOM_INFO[atomicSymbol]
        mass = self.info["ATOMIC WEIGHT"]

        self.setAttributes(mass=mass,atomicsymbol=atomicSymbol,number=number)

    ## Sends back a string representation, i.e. info description, of this class
    # @return A string name
    def __str__(self):
        coordinates = self.getCoordinates()
        desc = "%s %12.8f %12.8f %12.8f" % (self.getSymbol(), coordinates[0], coordinates[1], coordinates[2]) 
        return desc

    def __lt__(self, other):
        #sort first by atomic symbol
        if self.getSymbol() < other.getSymbol():
            return True
        elif self.getSymbol() > other.getSymbol():
            return False

        selfx = abs(self.getX())
        otherx = abs(other.getX())
        if (selfx < otherx):
            return True
        elif (selfx > otherx):
            return False

        selfy = abs(self.getY())
        othery = abs(other.getY())
        if (selfy < othery):
            return True
        elif (selfy > othery):
            return False

        selfz = abs(self.getz())
        otherz = abs(other.getZ())
        if (selfz < otherz):
            return True
        elif (selfz > otherz):
            return False

        #must be equal if we got here, in which case
        return False

    def __eq__(self, other):
        def finddiff(x1, x2):
            return min( abs(x1-x2), abs(x1+x2) )

        xdiff = finddiff(self.getX(), other.getX())
        ydiff = finddiff(self.getY(), other.getY())
        zdiff = finddiff(self.getZ(), other.getZ())

        maxdiff = max(xdiff, ydiff, zdiff)
        if maxdiff > 1e-2:
            return False
        else:
            return True

    def __repr__(self):
        return str(self)

    ## Gets the atomic number
    # @return The atomic number as a float
    def getAtomicNumber(self):
        return self.info["ATOMIC NUMBER"]

    ## Get the atom charge
    # @return The atomic charge as a float
    def getCharge(self):
        return self.info["ATOMIC NUMBER"]

    ## Gets the atom mass
    # @return The mass of the atom
    def getMass(self):
        return Atom.getAttribute(self, 'mass')

    ## Gets the name of the atom, i.e. oxygen, carbon, etc.
    # @return The name of the atom as a string
    def getName(self):
        return self.info["NAME"]

    ## Gets the number of the atom in the molecule
    # @return The integer number
    def getNumber(self):
        return self.getAttribute('number')

    def getNumCore(self):
        return self.info["CORE ELECTRONS"]

    def getNumCoreOrbitals(self):
        return self.getNumCore() / 2

    def getNumValence(self):
        return self.info["VALENCE ELECTRONS"]

    ## Gets the atomic symbol
    # @return The atomic symbol as a string
    def getSymbol(self, nice = False):
        symbol = self.getAttribute('atomicsymbol').upper()
        return self.getAttribute('atomicsymbol')
        if nice:
            symbol = symbol[0] + symbol[1:].lower()
        return symbol

    ## Gets the atomic weight
    #  @return The atomic weight as a float
    def getWeight(self):
        return self.info["ATOMIC WEIGHT"]

    ## Gets the xyz coordinates of the atom
    # @return The xyz coordinates as a list of floats
    def getXYZ(self):
        return self.coordinates
    
    ## Gets the x coordinate
    # @return The x coordinate as a float
    def getX(self):
        return self.getCoordinates()[0]

    ## Gets the x coordinate
    # @return The x coordinate as a float
    def getY(self):
        return self.getCoordinates()[1]

    ## Gets the x coordinate
    # @return The x coordinate as a float
    def getZ(self):
        return self.getCoordinates()[2]

    def isHydrogenic(self):
        atomicNumber = self.getAtomicNumber()
        if atomicNumber <= 2: return True
        return False
    
    def isFirstRow(self):
        atomicNumber = self.getAtomicNumber()
        if atomicNumber > 2 and atomicNumber <= 10: return True 
        return False

    ## Translate the x coordinate by a given amount
    # @param xAmount The amount to translate x by
    def moveX(self, xAmount):
        self.getCoordinates[0] += xAmount

    ## Translate the y coordinate by a given amount
    # @param yAmount The amount to translate y by
    def moveY(self, yAmount):
        self.getCoordinates()[0] += yAmount

    ## Translate the z coordinate by a given amount
    # @param zAmount The amount to translate z by
    def moveZ(self, zAmount):
        self.getCoordinates()[0] += zAmount

    def setMass(self, newMass):
        self.setAttributes(mass=newMass)
        
    ## Sets the xyz coordinates of the atom
    # @param newXYZ The xyz coordinates as a list of floats
    def setXYZ(self, newXYZ):
        self.coordinates.setValue(newXYZ)
    
    ## Sets the x coordinate
    # @return newX The x coordinate as a float
    def setX(self, newX):
        self.getCoordinates()[0] = newX

    ## Sets the y coordinate
    # @param newY The y coordinate as a float
    def setY(self, newY):
        self.getCoordinates()[1] = newY

    ## Sets the z coordinate
    # @param newX The z coordinate as a float
    def setZ(self, newZ):
        self.getCoordinates()[2] = newZ

    ## Rotate the atom about a given axis and origin
    # @param axis A vector giving the rotatin axis
    # @param angle The rotation angle in degrees
    # @param origin The point to rotate around, defaults to [0,0,0]
    def rotate(self, axis, angle, origin):
        self.translate( -1 * numpy.array(origin).astype(numpy.float64) )
        matrix = getRotationMatrix(axis, angle)        
        coordinates = self.getCoordinates()
        newCoordinates = numpy.dot(matrix, coordinates)
        self.setCoordinates(newCoordinates)
        self.translate(origin)

    ## Transform the coordinates with some linear operator
    # @param matrix The linear operator to transform coordinates with
    def transform(self, matrix):
        newCoords = numpy.dot(matrix, self.getCoordinates())
        self.setCoordinates(newCoords)

    ## Operates with an affine transform on the atom
    # @param matrix The linear operator part of the affine transform
    # @param translation The translation part of the affine transform
    def affineTransform(self, matrix, translation):
        self.transform(matrix)
        self.translate(translation)

    ## Translate the coordinates by a given amount
    # @param translate A vector giving the x,y,z displacements
    def translate(self, amount):
        if not isinstance(amount, chem.data.DataPoint):
            amount = numpy.array(amount)
        self.coordinates = self.coordinates + amount

    def getCoordinates(self, units=None):
        return self.coordinates.getValue(units)

    def setCoordinates(self, coords):
        self.coordinates.setValue(coords)

    def getBondLength(self, other):
        disp = self - other
        return disp.magnitude()
        
