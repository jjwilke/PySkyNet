## @package Chemistry
## contains methods and classes specific to doing chemistry calculations
import numpy
import numpy.linalg
import math
import sys
import os
import commands
from chem.molecules import *
from chem.matrixmath import *
from skynet.utils.utils import *
## Encapsulates a group of atoms that are transformed together as a group
class AtomGroup:
    ## Constructor
    #  @param molecule The molecule to build an atom group from
    #  @param atomList A numerical list of integers specifiying which atoms numbers to include in the group
    #  @param orig  Can be many different things. It can be an integer specifying a specific atom number.
    #                 It can be an string constant specifying a special part of the molecule.
    #                 It can be a vector specifying a specific point in space.
    def __init__(self, molecule, list, orig="CENTER OF MASS"):
        allAtoms = molecule.getAtoms()
        self.atomList = []
        for atomNumber in list:
            if "-" in atomNumber:
                start = eval(atomNumber.strip().split("-")[0])
                finish = eval(atomNumber.strip().split("-")[1])
                for i in range(start-1, finish):
                    self.atomList.append(allAtoms[i])
            elif "str" in "%s" % type(atomNumber):
                self.atomList.append(allAtoms[eval(atomNumber)-1])
            else:
                self.atomList.append(allAtoms[atomNumber-1])

        if "int" in "%s" % type(orig):
            #specific atom number
            self.origin = allAtoms[orig - 1]
        elif "list" in "%s" % type(orig):
            self.orgin = orig
        else:
            self.origin = orig.upper()

    def getAtoms(self):
        return self.atomList

    def getOrigin(self):
        if "Atom" in "%s" % type(self.origin):
            return self.origin.getXYZ()[:]
        elif "list" in "%s" % type(self.origin):
            return self.origin[:]
        else:
            if self.origin == "CENTER OF MASS":
                return self.getCenterOfMass()[:]

    def getCenterOfMass(self):
        xMoment = 0
        yMoment = 0
        zMoment = 0
        totalMass = 0
        for atom in self.atomList:
            mass = atom.getMass()
            totalMass += mass
            xMoment += atom.getX() * mass
            yMoment += atom.getY() * mass
            zMoment += atom.getZ() * mass
        xCenter = xMoment / totalMass
        yCenter = yMoment / totalMass
        zCenter = zMoment / totalMass

        return [xCenter, yCenter, zCenter]

## Encapsulates a rotation about a bond          
class RotateBond:
    ## Constructor.  Transformation to rotate around a given bond.
    #  @param args An array. args[0] is atom instance, args[1] is atom instance.  Rotation axis vector points
    #              from atom1 to atom2.  args[3] is rotation angle. args[4] is options, specifiyng a point
    #              other than the atom group's origin to rotate around. This point can be either another atom
    #              or a point in space.
    def __init__(self, at1, at2, ang, atomGroup, ori="DEFAULT"):
        self.atom1 = at1
        self.atom2 = at2
        self.angle = ang
        self.origin = ori
        self.atomGroup = atomGroup

    def __str__(self):
        str = "BOND ROTATION\n"
        str += self.atom1.toString()
        str += self.atom2.toString()
        str += "ANGLE=%f\n" % self.angle
        try:
            str += "ORIGIN=\n%s" % self.origin.toString()
        except AttributeError:
            str += "ORIGIN=%s\n" % self.origin.toString()

        return str
    
    def transform(self):
        axis = numpy.array(self.atom2.getXYZ()) - numpy.array(self.atom1.getXYZ())

        center = ""
        if "list" in "%s" % type(self.origin):
            center = self.origin[:]
        else:
            try:
                #see if the center is an atom or a set of xyz coordinates
                center = self.origin.getXYZ()[:]
            except AttributeError:
                if self.origin == "DEFAULT":
                    center = self.atomGroup.getOrigin()[:]

        move = -1 * numpy.array(center[:])
        moveBack = numpy.array(center)
        rotMatrix = getRotationMatrix(axis, self.angle)
        for atom in self.atomGroup.getAtoms():
            atom.translate(move)
            atom.transform(rotMatrix)
            atom.translate(moveBack)

## Encapsulates a rotation about an axis
class RotateAxis:
    ## Constructor.  Transformation to rotate around a given axis.
    #  @param args An array. args[0] is also an array, giving the rotation axis. args[1] is the rotation angle in degrees. args[2] is optional
    #              giving either a point in space or an atom to be the center of rotation.
    def __init__(self, ax, ang, atomGroup, ori="DEFAULT"):
        self.axis = ax
        self.angle = ang
        self.origin = ori
        self.atomGroup = atomGroup
            
    def transform(self):
        center = self.origin
        try:
            #see if the center is an atom or a set of xyz coordinates
            center = self.origin.getXYZ()
        except AttributeError:
            if self.origin == "DEFAULT":
                center = self.atomGroup.getOrigin()
        rotMatrix = getRotationMatrix(self.axis, self.angle)
        for atom in self.atomGroup.getAtoms():
            atom.translate(-1 * numpy.array(center))
            atom.transform(rotMatrix)
            atom.translate(center)

## Encapsulates a bond length change
class BondLengthChange:
    ## Constructor.  Transformation to change a bond length
    #  @param args An array. args[0] is atom instance, args[1] is atom instance. Bond points from atom1 to atom2. args[3] is
    #              the amount to increment the bond by.
    def __init__(self, at1, at2, atomGroup, incr):
        self.atom1 = at1
        self.atom2 = at2
        self.increment = incr
        self.atomGroup = atomGroup

    def transform(self):
        unitVector = getUnitVector(getBondVector(self.atom1, self.atom2))
        displacement = self.increment * numpy.array(unitVector)
        for atom in self.atomGroup.getAtoms():
            atom.translate(displacement)


## Encapsulates an arbitrary translation
class Translation:
    ## Constructor.
    #  @param disp An array, giving the displacement vector.
    def __init__(self, disp, atomGroup):
        self.displacement = disp
        self.atomGroup = atomGroup

    def transform(self):
        for atom in self.atomGroup.getAtoms():
            atom.translate(self.displacement)

## Encapsulates a variable
class Variable:
    ## Constructor
    #  @param dataMembers An array of the data members and their initival values necessary for the calculation
    #  @param eq The equation giving the value of the variable
    #  @param incs A list of actions that need to be performed in incremented the variable. Alternatively, it can be a string giving a command
    def __init__(self, dataMembers, eq, incs):
        for entry in dataMembers:
            name = entry[0]
            value = entry[1]
            command = "self.%s = value" % name
            exec(command)

        self.equation = eq
        self.increments = incs

    ## Increments the given variable
    def increment(self):
        for action in self.increments:
            try:
                action.act()
            except AttributeError:
                #this is a string giving an equation to execute
                exec(action)

    ## Gets the value of the given variable
    def getValue(self):
        exec("value = %s" % self.equation)
        return value

## Encapsulates a dummy atom placed at an arbitrary point in space
class DummyAtom:
    ## Constructor
    #  @param dataMembers An array of the data members and their initival values necessary for the calculation
    #  @param eqArray An array giving the equations of the xyz variables
    def __init__(self, eqArray, dataMembers = []):
        for entry in dataMembers:
            name = entry[0]
            value = entry[1]
            command = "self.%s = value" % name
            exec(command)

        self.eqX = eqArray[0]
        self.eqY = eqArray[1]
        self.eqZ = eqArray[2]

    ## Gets the x coordinate
    # @return The x coordinate as a float
    def getX(self):
        exec("x = %s" % self.eqX)
        return x

    ## Gets the x coordinate
    # @return The x coordinate as a float
    def getY(self):
        exec("y = %s" % self.eqY)
        return y

    ## Gets the x coordinate
    # @return The x coordinate as a float
    def getZ(self):
        exec("z = %s" % self.eqZ)        
        return z

    ## Gets the xyz coordinates of the atom
    # @return The xyz coordinates as a list of floats
    def getXYZ(self):
        exec("x = %s" % self.eqX)
        exec("y = %s" % self.eqY)
        exec("z = %s" % self.eqZ)
        return [x,y,z]


## Encapsulates a translation where the x y z coordinates are defined by special equations
class SpecialTranslation:
    ## Constructor
    #  @param vars A dictionary of variables for the variable names that appear in the equation
    #  @param xyzArray An array giving equations for each of the x y z values
    def __init__(self, vars, xyzArray, atomGroup):
        self.variables = vars
        self.eqX = xyzArray[0]
        self.eqY = xyzArray[1]
        self.eqZ = xyzArray[2]
        self.atomGroup = atomGroup

    def transform(self):
        dispXeq = self.eqX
        dispYeq = self.eqY
        dispZeq = self.eqZ
        for variable in self.variables:
            varObject = self.variables[variable]
            dispXeq = dispXeq.replace(variable, "%14.10f" % varObject.getValue())
            dispYeq = dispYeq.replace(variable, "%14.10f" % varObject.getValue())
            dispZeq = dispZeq.replace(variable, "%14.10f" % varObject.getValue())
            
        xCommand = "dispX = %s" % dispXeq
        yCommand = "dispY = %s" % dispYeq
        zCommand = "dispZ = %s" % dispZeq
        exec(xCommand)
        exec(yCommand)
        exec(zCommand)
        dispVector = [dispX, dispY, dispZ]

        for atom in self.atomGroup.getAtoms():
            atom.translate(dispVector)

class SetAtomCoordinates:
    ## Constructor
    #  @param vars A dictionary of variables for the variable names that appear in the equation
    #  @param xyzArray An array of arrays giving equations for each of the x y z values of every atom
    #  @param atomGroup The atom group to set the coordinates of
    def __init__(self, vars, xyzArray, atomGroup):
        self.variables = vars
        self.eqXs = []
        self.eqYs = []
        self.eqZs = []
        for entry in xyzArray:
            self.eqXs.append(entry[0])
            self.eqYs.append(entry[1])
            self.eqZs.append(entry[2])        
        self.atomGroup = atomGroup

    def transform(self):
        allAtoms = self.atomGroup.getAtoms()
        for i in range(0, len(self.eqXs)):
            atom = allAtoms[i]
            Xeq = self.eqXs[i]
            Yeq = self.eqYs[i]
            Zeq = self.eqZs[i]
            for variable in self.variables:
                varObject = self.variables[variable]
                Xset = Xeq.replace(variable, "%14.10f" % varObject.getValue())
                Yset = Yeq.replace(variable, "%14.10f" % varObject.getValue())
                Zset = Zeq.replace(variable, "%14.10f" % varObject.getValue())

            xCommand = "X = %s" % Xset
            yCommand = "Y = %s" % Yset
            zCommand = "Z = %s" % Zset
            exec(xCommand)
            exec(yCommand)
            exec(zCommand)
            atom.setXYZ([X, Y, Z])


## Encapsulates a change in dihderal angle
class DihedralChange:
    ## Constructor.  Transformation to change a dihedral angle.
    # @param args An array.  args[0] is the atom whose dihedral angle should be changed. args[1] is the bond atom.
    #                        args[2] is the angle atom. args[3] is the dihedral atom. args[4] is the rotation angle.
    def __init__(self, at1, at2, at3, at4, group, ang):
        self.atom1 = at1
        self.atom2 = at2
        self.atom3 = at3
        self.atom4 = at4
        self.angle = ang
        self.atomGroup = group

    def transform(self):
        rotAxis = numpy.array(self.atom2.getXYZ() - self.atom3.getXYZ())
        rotMatrix = getRotationMatrix(rotAxis, self.angle)
        center = ( numpy.array(self.atom1.getXYZ()) + numpy.array(self.atom2.getXYZ()) ) / 2.0
        for atom in self.atomGroup.getAtoms():
            atom.translate(-1 * numpy.array(center))
            atom.transform(rotMatrix)
            atom.translate(center)

## Encapsulates a change in angle
class AngleChange:
    ## Constructor.  Transformation to change a dihedral angle.
    # @param args An array.  args[0] is the atom whose angle is changing. args[1] is the bond atom. args[2] is the angle atom. args[3] is the rotation angle.
    def __init__(self, at1, at2, at3, group, ang):
        self.atom1 = at1
        self.atom2 = at2
        self.atom3 = at3
        self.angle = ang
        self.atomGroup = group

    def transform(self):
        vector1 = numpy.array(self.atom1.getXYZ()) - numpy.array(self.atom2.getXYZ())
        vector2 = numpy.array(self.atom3.getXYZ()) - numpy.array(self.atom2.getXYZ())
        rotAxis = numpy.cross(vector2, vector1)
        rotMatrix = getRotationMatrix(rotAxis, self.angle)
        center = numpy.array(self.atom2.getXYZ())
        for atom in self.atomGroup.getAtoms():
            atom.translate(-1 * numpy.array(center))
            atom.transform(rotMatrix)
            atom.translate(center)    

## This class encapsulates a basis set
class BasisSet:
    import pickle
    ## Constructor - functions are added by method
    # @param basName An optional string identifying the basis set.  If this corresponds to a library basis set,
    ## the basis set will be read in.  If it does not exist in the library, then an empty basis with the corresponding name will be created.
    def __init__(self, basName="None"):
        self.basisName = basName
        
        ## Contains all the info, basically. This is a dictionary with the format dict[first key = atomic symbol][second key = shell (i.e. S, P, D)].
        ## The value associated to each key is a list of basis functions
        self.basisFunctions = {}

        if basName == "None":
            #just make an empty basis set
            donothing = 0
        else:
            self.basisName = basName
            try:
                basisFile = "%s/%s" % (self.BASIS_FOLDER, basName.upper())
                basis_pickle = open(basisFile, "r")
                self.basisFunctions = pickle.load(basisPickle)
                basis_pickle.close()
            except IOError:
                #must be making a new basis set - just set the name and ignore the fact that we can't find the basis set
                donothing = 0

    ## Add a given set of basis functions to a particular atom
    #  @param atomName The atomic symbol of the atom to add functions to
    #  @param basisFunctions The list of basis functions to add
    def addFunctionsToAtom(self, atomName, basisFunctions):
        symbol = atomName.upper()
        if self.basisFunctions.has_key(symbol):
            donothing = 0
        else:
            self.basisFunctions[symbol] = {}

        for func in basisFunctions:
            shell = func.getShellType
            #if the shell already exists, add this function to it
            if self.basisFunctions[symbol].has_key(shell):
                self.basisFunctions[symbol][shell].append(func)
            #if the shell does not exist, create the shell and then add the function to it
            else:
                self.basisFunctions[symbol][shell] = [func]

    ## Gets the list of basis functions associated with a given atomic shell
    #  @param atomName The atomic symbol whose basis functions you want
    #  @param shellType The atom shell you wish to get
    #  @return The list of basis functions for that atom in that shell.  List can be empty.
    def getShell(self, atomName, shellType):
        try:
            funcs = self.basisFunctions[atomName][shellType]
            return funcs
        except KeyError:
            return []

    ## Saves the basis set as a pickled class to the hard drive
    def save(self):
        basisFile = "%s/%s" % (self.BASIS_FOLDER, self.basisName)
        basis_pickle = open(basisFile, "w")
        pickle.dump(self.basisFunctions, basisFile)
        basis_pickle.close()
    

## Encapsulates a contracted basis function
class BasisFunction:
    ## Constructor
    # @param shell A string identifying what angular momentum type (S, P, D ...)
    # @param prims A 2-d array specifiyng the primitive functions making up the basis function
    def __init__(self, shell, prims):
        self.shellType = shell.upper()
        self.primitives = prims

    ## Gets the primitive functions composing this basis function
    #  @return The 2-d array specifiying the primitive functions and the contraction coefficients
    def getPrimitives(self):
        return self.primitives

    ## Gets the shell type of the basis function
    #  @return A string identifying the angular momentum level
    def getShellType(self):
        return self.shellType

## Encapsulates an orbital.  This keeps track of at least the orbital energy.  Can also keep track of the symmetry label as well
## as the MO coefficients in a given basis set
class Orbital:    
    ## Constructor
    #  @param e The energy, a float
    #  @param symm A string identifying the irrep that this orbital belongs to
    #  @param basis A basis set name (string) or an actual basis set object
    #  @param coeffs The vector of coefficients for the orbital
    def __init__(self, e, symm = "A", basis = "CC-PVDZ", coeffs = []):
        self.symmetry = symm
        self.energy = e
        self.coefficients = coeffs
        try:
            #check to see if we have a basis set object or just a string
            basis.dir()
            self.basisSet = basis
        except AttributeError:
            #oops, we just have a string... lets go get a basis set object
            self.basisSet = BasisSet(basis)

    # Sends back the basis that was used to create this orbital
    # @return A basis set object
    def getBasis(self):
        return self.basisSet

    # Sends back the MO coefficients in the AO basis
    # @return A 2-D array of MO coefficients.  Each column corresponds to a given MO.
    def getCoefficients(self):
        return self.coefficients

    # Sends back the orbital energy
    # @return The orbital energy as a float
    def getEnergy(self):
        return self.energy

    # Sends back the irrep that the orbital belongs to
    # @return A string identifying the irrep of the orbital
    def getSymmetry(self):
        return self.symmetry

## Encapsulates a point on the potential energy surface.  This is used for keeping track of numerous calculations on the same geometry
## but with different levels of theory.
class PESPoint:
    ## Constructor
    # @param mol A molecule object
    # @param ens A dictionary containing all the possible energies to get
    # @param best A string giving which energy corresponds to the "best" result
    def __init__(self, mol, ens, best):
        self.molecule = mol
        self.energies = ens
        self.bestEnergy = best

    def getEnergyType(self):
        return self.bestEnergy

    def getEnergy(self, eType="BEST"):
        energy = 0
        try:
            energy = self.energies[eType.upper()]
            return energy
        except KeyError:
            raise Errors.InfoNotFoundError

    def getMolecule(self):
        return self.molecule

    def getXYZ(self):
        return self.molecule.getXYZ()
    
## Encapsulates all the features of a vibrational mode such as harmonic frequency, displacement vectors, etc.
class VibrationalMode:
    ## Constructor
    # @param freq The frequency of the vibration in wavenumbers, a float
    # @param disps A 2-D array giving the displacement vectors.  Rows are atoms.  Columns are x,y,z displacements
    # @param ir The IR intensity
    # @param raman The Raman intensity
    # @param redMass The reduced mass, in atomic units
    def __init__(self, freq, disps, ir=0, raman=0, redMass=0):
        ##The set of displacement vectors for each of the individual atoms.  Rows are individual atoms.  Columns are x,y,z
        self.frequency = freq
        self.dispVectors = disps
        self.IR = ir
        self.Raman = raman
        self.reducedMass = redMass

    # Sends back the frequency of the mode
    # @return The harmonic frequency in wavenumbers as a float
    def getFrequency(self):
        return self.frequency
    
    # Sends back the displacement vectors of the atoms
    # @return A 2-D array.  Each row corresponds to an atom.  The columns are the x,y,z displacements.
    def getVectors(self):
        return self.dispVectors

def gradient(method, atom):
    step = 0.001
    atom.setX( atom.getX() + step) ; x_plus = method()
    atom.setX( atom.getX() - 2*step) ; x_minus = method()
    atom.setX( atom.getX() + step) #return to old value
    grad_x = (x_plus - x_minus) / 2 / step

    atom.setY( atom.getY() + step) ; y_plus = method()
    atom.setY( atom.getY() - 2*step) ; y_minus = method()
    atom.setY( atom.getY() + step) #return to old value
    grad_y = (y_plus - y_minus) / 2 / step

    atom.setZ( atom.getZ() + step) ; z_plus = method()
    atom.setZ( atom.getZ() - 2*step) ; z_minus = method()
    atom.setZ( atom.getZ() + step) #return to old value
    grad_z = (z_plus - z_minus) / 2 / step

    return [grad_x, grad_y, grad_z]

## Encapsulates a bond length for use in z-matrices
class BondLength:

    #Constructor
    # @param at1 The first atom in the bond
    # @param at2 The second atom in the bond
    def __init__(self, at1, at2, label=None, units="ANGSTROM", molecule=None):
        if isinstance(at1, int): #we have been given integers
            atomList = molecule.getAtoms()
            self.atom1 = atomList[at1-1]
            self.atom2 = atomList[at2-1]
            self.num1 = at1
            self.num2 = at2
            self.name = "R(%d-%d)" % (at1, at2)
        elif isinstance(at1, Atom):
            self.atom1 = at1
            self.atom2 = at2
            self.num1 = None
            self.num2 = None
            self.name = label

        self.units = units

    def __str__(self):
        return "%s = %12.8f" % (self.name, self.getValue())

    def setMolecule(self, mol):
        atomList = mol.getAtoms()
        self.atom1 = atomList[self.num1-1]
        self.atom2 = atomList[self.num2-1]

    # Gets the bond length
    #  @return A float, the bond length
    def getValue(self, units=None):
        if not units: units = self.units
        value =  convertUnits(calcBondLength(self.atom1, self.atom2), self.units, units)
        return value

    def getBVectors(self):
        e12 = getUnitVector(self.atom2.getXYZ() - self.atom1.getXYZ())
        """Comment out
        print "B vectors for atom 1"
        print -e12, "analytic"
        print gradient(self.getValue, self.atom1), "numeric"
        print "B vector for atom 2"
        print e12, "analytic"
        print gradient(self.getValue, self.atom2), "numeric"
        """
        return -e12, e12

    def getAtomNumbers(self):
        return (self.num1, self.num2) 

    # Gets what should be included in the z-matrix
    # @param constantsAreValues A boolean giving whether constants should send back values or the name
    # @param useAsterisks A boolean telling whether or not to include asterisks in variable names
    # @return A string, the appropriate entry for the z-matrix
    def getEntry(self, constantsAreValues=False, useAsterisks=False, units = "ANGSTROM"):
        if constantsAreValues and self.type == "CONSTANT":
            value = convertUnits(calcBondLength(self.atom1, self.atom2), self.units, units)
            return "%14.10f" % value   
        elif self.type == "VARIABLE" and useAsterisks:
            return self.name + "*"
        else:
            return self.name
        
    ## Gets the name of the bond length
    # @return A string identifying the dihedral
    def getName(self):
        return self.name

    def isMinusPair(self): return False #never a minus pair

    ## Sets the type of coordinates, whether or not it is a variable or constant
    # @param newType A string, either "variable" or "constant"
    def setType(self, newType):
        self.type = newType.upper()

    def setUnits(self, newUnits):
        self.units = newUnits.upper()

## Encapsulates a bond angle for use in z-matrices
class BondAngle:

    #Constructor
    # @param at1 The first atom in the angle
    # @param at2 The second atom in the angle
    # @param at3 The third atom in the angle
    def __init__(self, at1, at2, at3, label=None, molecule=None, units="degree"):
        
        if isinstance(at1, Atom):
            self.atom1 = at1
            self.atom2 = at2
            self.atom3 = at3
            self.num1 = 0 
            self.num2 = 0
            self.num3 =0
            self.name = label
        elif isinstance(at1, int):
            atomList = molecule.getAtoms()
            self.atom1 = atomList[at1-1]
            self.atom2 = atomList[at2-1]
            self.atom3 = atomList[at3-1]
            self.num1 = at1
            self.num2 = at2
            self.num3 = at3
            self.name = "A(%d-%d-%d)" % (at1, at2, at3)
        self.units = units

    def __str__(self):
        return "%s = %12.8f" % (self.name, self.getValue())

    def setMolecule(self, mol):
        atomList = mol.getAtoms()
        self.atom1 = atomList[self.num1-1]
        self.atom2 = atomList[self.num2-1]
        self.atom3 = atomList[self.num3-1]

    ## Gets the actual numerical value associated with the angle
    #  @return A float, the bond angle
    def getValue(self, units=None):
        if not units: units = self.units
        theta = calcBondAngle(self.atom1, self.atom2, self.atom3)    
        return convertUnits(theta, "degree", units)

    # Gets what should be included in the z-matrix
    # @return A string, the appropriate entry for the z-matrix
    # @param useAsterisks A boolean telling whether or not to include asterisks in variable names
    # @param constantsAreValues A boolean giving whether constants should send back values or the name
    def getEntry(self, constantsAreValues=False, useAsterisks=False):
        if constantsAreValues and self.type == "CONSTANT":
            value = calcBondAngle(self.atom1, self.atom2, self.atom3)
            return "%12.8f" % value   
        elif self.type == "VARIABLE" and useAsterisks:
            return self.name + "*"
        else:
            return self.name

    ## Gets the name of the bond angle
    # @return A string identifying the dihedral
    def getName(self):
        return self.name

    def isMinusPair(self): return False #never a minus pair

    ## Sets the type of coordinates, whether or not it is a variable or constant
    # @param newType A string, either "variable" or "constant"
    def setType(self, newType):
        self.type = newType.upper()

    def getBVectors(self):
        ##okay this is a little weird
        #in Wilson,Decius,Cross the middle atom is atom 3
        #this is taken care of on the next line
        atom1 = self.atom1
        atom2 = self.atom3
        atom3 = self.atom2

        e31 = getUnitVector(atom1.getXYZ() - atom3.getXYZ())
        e32 = getUnitVector(atom2.getXYZ() - atom3.getXYZ())
        r31 = calcBondLength(atom1, atom3)
        r32 = calcBondLength(atom2, atom3)
        #again, middle atom is 3
        phi = convertUnits(calcBondAngle(atom1, atom3, atom2), "degree", "radian")
        cosphi = math.cos(phi)
        sinphi = math.sin(phi)

        st1 = (cosphi*e31 - e32)/(r31*sinphi)
        st2 = (cosphi*e32 - e31)/(r32*sinphi)
        st3 = ((r31 - r32*cosphi) * e31 + (r32 - r31*cosphi) * e32)/r31/r32/sinphi

        """ commented out
        print "atom 1"
        print st1, "analytic"
        print gradient(self.getValue, self.atom1), "numeric"
        print "atom 2"
        print st3, "analytic"
        print gradient(self.getValue, self.atom2), "numeric"
        print "atom 3"
        print st2, "analytic"
        print gradient(self.getValue, self.atom3), "numeric"
        """
    
        #again... st3 referes to the middle atom in decius and cross equations
        return st1, st3, st2

    def getAtomNumbers(self):
        return self.num1, self.num2, self.num3

## Encapsulates a dihedral angle for use in z-matrices
class OutOfPlaneBend:
    ## Constructor
    # @param at1 The first atom in the dihedral
    # @param at2 The second atom in the dihedral
    # @param at3 The third atom in the dihedral
    # @param at4 The fourth atom in the dihedral
    def __init__(self, at1, at2, at3, at4, label=None, molecule=None, units="degree"):
        if isinstance(at1, Atom):
            self.atom1 = at1
            self.atom2 = at2
            self.atom3 = at3
            self.atom4 = at4
            self.num1 = 0
            self.num2 = 0
            self.num3 = 0
            self.num4 = 0
            self.name = label
        elif isinstance(at1, int):
            atomList = molecule.getAtoms()
            self.atom1 = atomList[at1-1]
            self.atom2 = atomList[at2-1]
            self.atom3 = atomList[at3-1]
            self.atom4 = atomList[at4-1]
            self.num1 = at1
            self.num2 = at2
            self.num3 = at3
            self.num4 = at4
            self.name = "OOP(%d-%d-%d-%d)" % (at1, at2, at3, at4)
            self.type = "VARIABLE"
        self.minusPartner = None
        self.units = units

    def __str__(self):
        return "%s = %12.8f" % (self.name, self.getValue())

    def setMolecule(self, mol):
        atomList = mol.getAtoms()
        self.atom1 = atomList[self.num1-1]
        self.atom2 = atomList[self.num2-1]
        self.atom3 = atomList[self.num3-1]
        self.atom4 = atomList[self.num4-1]

    ## Gets the actual numerical value associated with the angle
    #  @return A float, the dihedral angle
    def getValue(self, units=None):
        if not units: units = self.units
        theta = calcOOPBend(self.atom1, self.atom2, self.atom3, self.atom4)  
        return convertUnits(theta, "degree", units)

    def getAtomNumbers(self):
        return self.num1, self.num2, self.num3, self.num4
    
    def getBVectors(self):
        e41 = getUnitVector(self.atom1.getXYZ() - self.atom4.getXYZ())
        e42 = getUnitVector(self.atom2.getXYZ() - self.atom4.getXYZ())
        e43 = getUnitVector(self.atom3.getXYZ() - self.atom4.getXYZ())
        r41 = calcBondLength(self.atom1, self.atom4)
        r42 = calcBondLength(self.atom2, self.atom4)
        r43 = calcBondLength(self.atom3, self.atom4)
        
        phi1 = convertUnits(calcBondAngle(self.atom2, self.atom4, self.atom3), "degree", "radian")
        sinphi1 = numpy.sin(phi1)
        cosphi1 = numpy.cos(phi1)
        sin2phi1 = sinphi1*sinphi1
        theta = numpy.arcsin(numpy.dot(numpy.cross(e42, e43), e41) / phi1) 
        costheta = numpy.cos(theta)
        tantheta = numpy.tan(theta)
        
        st1 = (numpy.cross(e42, e43)/costheta/sinphi1 - tantheta*e41)/r41
        st2 = (numpy.cross(e43, e41)/costheta/sinphi1 - ((tantheta/sin2phi1)*(e42 - cosphi1*e43)))/r42
        st3 = (numpy.cross(e41, e42)/costheta/sinphi1 - ((tantheta/sin2phi1)*(e43 - cosphi1*e42)))/r43
        st4 = -st1 - st2 - st3

        """ 
        print "atom 1"
        print st1, "analytic"
        print gradient(self.getValue, self.atom1), "numeric"
        print "atom 2"
        print st2, "analytic"
        print gradient(self.getValue, self.atom2), "numeric"
        print "atom 3"
        print st3, "analytic"
        print gradient(self.getValue, self.atom3), "numeric"
        print "atom 4"
        print st4, "analytic"
        print gradient(self.getValue, self.atom4), "numeric"
        """

        return st1, st2, st3, st4

    # Gets what should be included in the z-matrix
    # @param constantsAreValues A boolean giving whether constants should send back values or the name
    # @param useMinusPairs A boolean telling whether or not +/- dihedral pairs should be used in labels
    # @param useAsterisks A boolean telling whether or not to include asterisks in variable names
    # @return A string, the appropriate entry for the z-matrix
    def getEntry(self, constantsAreValues=False, useAsterisks=False):
        if constantsAreValues and self.type == "CONSTANT":
            return "%12.8f" % calcDihedralAngle(self.atom1, self.atom2, self.atom3, self.atom4)     
        elif self.type == "VARIABLE" and useAsterisks:
            return self.name + "*"
        else:
            return self.name
        
    ## Gets the name of the dihedral angle
    # @return A string identifying the dihedral
    def getName(self):
        return self.name

## Encapsulates a dihedral angle for use in z-matrices
class DihedralAngle:
    ## Constructor
    # @param at1 The first atom in the dihedral
    # @param at2 The second atom in the dihedral
    # @param at3 The third atom in the dihedral
    # @param at4 The fourth atom in the dihedral
    def __init__(self, at1, at2, at3, at4, label=None, molecule=None, units="degree", onlyPositive=False):
        if isinstance(at1, Atom):
            self.atom1 = at1
            self.atom2 = at2
            self.atom3 = at3
            self.atom4 = at4
            self.num1 = 0
            self.num2 = 0
            self.num3 = 0
            self.num4 = 0
            self.name = label
        elif isinstance(at1, int):
            atomList = molecule.getAtoms()
            self.atom1 = atomList[at1-1]
            self.atom2 = atomList[at2-1]
            self.atom3 = atomList[at3-1]
            self.atom4 = atomList[at4-1]
            self.num1 = at1
            self.num2 = at2
            self.num3 = at3
            self.num4 = at4
            self.name = "D(%d-%d-%d-%d)" % (at1, at2, at3, at4)
        self.type = "VARIABLE"
        self.minusPartner = None
        self.units = units
        self.onlyPositive = onlyPositive

    def __str__(self):
        return "%s = %12.8f" % (self.name, self.getValue())

    def setMolecule(self, mol):
        atomList = mol.getAtoms()
        self.atom1 = atomList[self.num1-1]
        self.atom2 = atomList[self.num2-1]
        self.atom3 = atomList[self.num3-1]
        self.atom4 = atomList[self.num4-1]

    ## Gets the actual numerical value associated with the angle
    #  @return A float, the dihedral angle
    def getValue(self, units=None, onlyPositive=None):
        #if not explicitly told, use our default on whether to compute dihedrals as positive values
        if onlyPositive == None: onlyPositive = self.onlyPositive
        if not units: units = self.units
        theta = calcDihedralAngle(self.atom1, self.atom2, self.atom3, self.atom4, onlyPositive)  
        return convertUnits(theta, "degree", units)
    
    # Gets what should be included in the z-matrix
    # @param constantsAreValues A boolean giving whether constants should send back values or the name
    # @param useMinusPairs A boolean telling whether or not +/- dihedral pairs should be used in labels
    # @param useAsterisks A boolean telling whether or not to include asterisks in variable names
    # @return A string, the appropriate entry for the z-matrix
    def getEntry(self, constantsAreValues=False, useAsterisks=False, useMinusPairs=False):
        if constantsAreValues and self.type == "CONSTANT":
            return "%12.8f" % calcDihedralAngle(self.atom1, self.atom2, self.atom3, self.atom4)     
        elif self.type == "VARIABLE" and useMinusPairs and self.minusPartner:
            newName = "-" + self.minusPartner.getName()
            if useAsterisks:
                newName += "*"
            return newName
        elif self.type == "VARIABLE" and useAsterisks:
            return self.name + "*"
        else:
            return self.name

    def getBVectors(self):
        e12 = getUnitVector(self.atom2.getXYZ() - self.atom1.getXYZ())
        e23 = getUnitVector(self.atom3.getXYZ() - self.atom2.getXYZ())
        e32 = getUnitVector(self.atom2.getXYZ() - self.atom3.getXYZ())
        e43 = getUnitVector(self.atom3.getXYZ() - self.atom4.getXYZ())
        r12 = calcBondLength(self.atom1, self.atom2)
        r23 = calcBondLength(self.atom2, self.atom3)
        r32 = calcBondLength(self.atom2, self.atom3)
        r43 = calcBondLength(self.atom3, self.atom4)
        
        phi3 = convertUnits(calcBondAngle(self.atom2, self.atom3, self.atom4), "degree", "radian")
        phi2 = convertUnits(calcBondAngle(self.atom1, self.atom2, self.atom3), "degree", "radian")
        sinphi2 = numpy.sin(phi2)
        cosphi2 = numpy.cos(phi2)
        sinphi3 = numpy.sin(phi3)
        cosphi3 = numpy.cos(phi3)
        sin2phi2 = sinphi2*sinphi2
        sin2phi3 = sinphi3*sinphi3
        
        st1 = -numpy.cross(e12, e23)/r12/sin2phi2
        st2 = ( ((r23 - r12*cosphi2)/(r12*r23*sinphi2))*numpy.cross(e12,e23)/sinphi2 +
                (cosphi3/r23/sinphi3)*numpy.cross(e43,e32)/sinphi3 )
        st3 = ( ((r32 - r43*cosphi3)/(r43*r32*sinphi3))*numpy.cross(e43,e32)/sinphi3 +
                (cosphi2/r32/sinphi2)*numpy.cross(e12,e23)/sinphi2 )
        st4 = -numpy.cross(e43, e32)/r43/sin2phi3

        getVal = lambda: self.getValue(units="radian", onlyPositive=True)

        """
        print "atom 1"
        print st1, "analytic"
        print gradient(getVal, self.atom1), "numeric"
        print "atom 2"
        print st2, "analytic"
        print gradient(getVal, self.atom2), "numeric"
        print "atom 3"
        print st3, "analytic"
        print gradient(getVal, self.atom3), "numeric"
        print "atom 4"
        print st4, "analytic"
        print gradient(getVal, self.atom4), "numeric"
        """

        return st1, st2, st3, st4
        
    ## Gets the name of the dihedral angle
    # @return A string identifying the dihedral
    def getName(self):
        return self.name

    def isMinusPair(self):
        return self.minusPartner

    def getAtomNumbers(self):
        return self.num1, self.num2, self.num3, self.num4
    
    ## Sets the type of coordinates, whether or not it is a variable or constant
    # @param newType A string, either "variable" or "constant"
    def setType(self, newType):
        self.type = newType.upper()

    ## Sets the "minus partner" of the dihedral angle
    # @param partner The dihedral angle that is the minus of this dihedral angle, really only useful in MolPro
    def setMinusPartner(self, partner):
        self.minusPartner = partner
        
class ZMatrix:
    ## Constructor
    # @param ZMatrix A zmatrix array
    # @param units 
    # @param atomList An atom list - this is necessary since the z-matrix must be linked to individual atoms
    # @param variables A dictionary with keys the variable names and values the z-matrix values
    # @param constants A dictionary with keys the constant names and values the z-matrix values    
    def __init__(self, atomList, units, ZMatrix, vars, consts):
        #store the original values for use in creating copies of this z-matrix
        self.startVars = vars
        self.startConsts = consts
        self.startZMat = ZMatrix

        #create a copy of the z-matrix so we don't overwrite anything
        from copy import deepcopy
        self.zmatrix = deepcopy(ZMatrix)
        self.variables = {}
        self.constants = {}
        self.units = units
        valuesWritten = {}
        allAtoms = atomList  

        atomNumber = 1
        for atom in self.zmatrix:
            atomName = atom[0]
            anchorAtom = allAtoms[atomNumber-1]

            bondAtom = ""
            angleAtom = ""
            dihedralAtom = ""
            
            if len(atom) > 1:
                bondAtom = allAtoms[atom[1]-1]
                bondName = atom[2]
                bondLength = ""
                if bondName in self.variables and self.variables[bondName].__class__ == "BondLength":
                    bondLength = self.variables[bondName]
                elif bondName in self.constants and self.constants[bondName].__class__ == "BondLength":
                    bondLength = self.constants[bondName]
                else:
                    bondLength = BondLength(anchorAtom, bondAtom, bondName, self.units)
                    if bondName in vars:
                        self.variables[bondName] = bondLength
                        bondLength.setType("VARIABLE")
                    else:
                        self.constants[bondName] = bondLength
                        bondLength.setType("CONSTANT")
                atom[2] = bondLength

            if len(atom) > 3:
                angleAtom = allAtoms[atom[3]-1]
                angleName = atom[4]
                angle = ""
                if angleName in self.variables and self.variables[angleName].__class__ == "BondAngle":
                    angle = self.variables[angleName]
                elif angleName in self.constants and self.constants[angleName].__class__ == "BondAngle":
                    angle = self.constants[angleName]
                else:
                    angle = BondAngle(anchorAtom, bondAtom, angleAtom, angleName)
                    if angleName in vars:
                        self.variables[angleName] = angle
                        angle.setType("VARIABLE")
                    else:
                        self.constants[angleName] = angle
                        angle.setType("CONSTANT")
                atom[4] = angle
          
            if len(atom) > 5:
                dihAtom = allAtoms[atom[5]-1]
                dihName = atom[6]
                dihedral = ""
                if dihName in self.variables and self.variables[dihName].__class__ == "DihedralAngle":
                    dihedral = self.variables[dihName]
                elif dihName in self.constants and self.constants[dihName].__class__ == "DihedralAngle":
                    dihedral = self.constants[dihName]
                else:
                    dihedral = DihedralAngle(anchorAtom, bondAtom, angleAtom, dihAtom, dihName)
                    value = 0
                    if dihName in vars:
                        self.variables[dihName] = dihedral
                        dihedral.setType("VARIABLE")
                        value = ("%f" % dihedral.getValue())[:7] 
                    else:
                        self.constants[dihName] = dihedral
                        dihedral.setType("CONSTANT")
                        value = ("%f" % dihedral.getValue())[:7]
                    valuesWritten[value] = dihedral

                    #special handling of minus variables
                    if ("-%s" % value)[:7] in valuesWritten:
                        oldDihedral = valuesWritten[("-%s" % value)[:7]]
                        dihedral.setMinusPartner(oldDihedral)
                    elif value[1:8] in valuesWritten:
                        oldDihedral = valuesWritten[value[1:8]]
                        dihedral.setMinusPartner(oldDihedral)

                atom[6] = dihedral

            atomNumber += 1

    def __str__(self):
        return "%s\n%s" % (self.getZMatrix(units=self.units), self.getVariablesAndConstants(units=self.units, headers=True))

    ## Creates a copy of the z-matrix
    #  @param newMol An optional molecule object. Sometimes you may wish to make the z-matrix copy with
    #                respect to a given molecule to preserve atom references.  Otherwise, a molecule copy is generated.
    def copy(self, newMol=None):
        zMat = self.startZMat[:]
        newVars = self.startVars.copy()
        newConsts = self.startConsts.copy()
        if not newMol:
            newMol = self.molecule.copy()
        units = newMol.getUnits()
        newZMatrix = ZMatrix(newMol.getAtoms(), units, zMat, newVars, newConsts)
        return newZMatrix

    ## Gets a formatted z-matrix to be used in printing output files
    #  @param delim The delimiter between z-matrix entries
    #  @param lineCloser The character at the end of the line
    #  @param constantsAreValues A boolean, whether or not constants should just be listed values or be given a name
    #  @param asterisks A boolean, whether to put asterisks on variables
    #  @param minusPairs A boolean, whether to print dihedral labels as negative pairs as in molpro
    #  @return A formatted z-matrix as a string
    def getZMatrix(self, delim = " ", lineCloser = "", constantsAreValues=False, asterisks=False, minusPairs = False, dummyLabel = "Q", units="ANGSTROM"):
        formattedMatrix = "%s%s\n" % (self.zmatrix[0][0], lineCloser)

        for i in range(1, len(self.zmatrix)):
            currentAtom = self.zmatrix[i]
            if currentAtom == "Q":
                #dummy atom
                currentAtom = dummyLabel
                
            formattedMatrix += currentAtom[0]
            j = 1
            while j < len(currentAtom):
                formattedMatrix += delim
                atom = currentAtom[j]
                value = ""
                if j == 5:
                    value = currentAtom[j+1].getEntry(constantsAreValues, asterisks, minusPairs)
                elif j ==1:
                    value = currentAtom[j+1].getEntry(constantsAreValues, asterisks, units)
                else:
                    value = currentAtom[j+1].getEntry(constantsAreValues, asterisks)
                    
                formattedMatrix += "%d" % atom
                formattedMatrix += delim
                formattedMatrix += value
                j += 2

            formattedMatrix += lineCloser + "\n"

        #get rid of the last new line
        formattedMatrix = formattedMatrix[:-1]

        return formattedMatrix
        
    ## Gets a formatted list of z-matrix parameters to be used in printing output files
    #  @param delim The delimiter between z-matrix entries
    #  @param lineCloser The character at the end of the line
    #  @param constantsAreValues A boolean, whether or not constants should just be listed values or be given a name
    def getVariablesAndConstants(self, delim = "=", useMinusPairs=False, lineCloser = "", constantsAreValues=False, 
                                units="ANGSTROM", headers=False):
        str_array = []
        if headers: str_array.append("Variables")
        for variable in self.variables:
            if isinstance(self.variables[variable], BondLength):
                str_array.append("%s%s%14.10f%s" % (variable, delim, self.variables[variable].getValue(units), lineCloser))
            elif useMinusPairs and self.variables[variable].isMinusPair(): pass    
            else:
                str_array.append("%s%s%14.10f%s" % (variable, delim, self.variables[variable].getValue(), lineCloser))
        if constantsAreValues: return "\n".join(str_array) #go no further
        #if we got here, we must include constants

        if headers: str_array.append("Constants")
        for constant in self.constants:
            if isinstance(self.constants[constant], BondLength):
                str_array.append("%s%s%14.10f%s" % (constant, delim, self.constants[constant].getValue(units), lineCloser))
            elif useMinusPairs and self.variables[variable].isMinusPair(): pass    
            else:
                str_array.append("%s%s%14.10f%s" % (constant, delim, self.constants[constant].getValue(), lineCloser))

        return "\n".join(str_array)

    def getDummyAtoms(self):
        return []

    def getXYZ(self):
        #build a toned down z-matrix
        zmat_array = []
        for line in self.zmatrix:
            zmat_array.append([])
            for entry in line:
                try: zmat_array[-1].append(entry.getValue())
                except AttributeError: zmat_array[-1].append(entry)
        xyz = getXYZFromZMatrix(zmat_array, {}, {})
        return xyz

    def getUnits(self):
        return self.units

    def setUnits(self, newUnits):
        self.units = newUnits.upper()
        for variable in self.variables:
            value = self.variables[variable]
            if isinstance(value, BondLength): value.setUnits(newUnits)
        for constant in self.constants:
            value = self.constants[constant]
            if isinstance(value, BondLength): value.setUnits(newUnits)

## Converts a z-matrix into xyz coordinates
# @param ZMatrix A zmatrix array
# @param variables A dictionary with keys the variable names and values the z-matrix values
# @param constants A dictionary with keys the constant names and values the z-matrix values
def getXYZFromZMatrix(ZMatrix, variables, constants):
    atoms = [ZMatrix[0][0]]
    coordinates = [ [0, 0, 0] ]

    if len(ZMatrix) > 1:
        atom2 = ZMatrix[1][0]
        bondLength = 0
        try:
            bondLength = ZMatrix[1][2] * 1.0
        except TypeError:
            try:
                bondLength = variables[ZMatrix[1][2]]
            except KeyError:
                bondLength = constants[ZMatrix[1][2]]                
        coordinates.append([0, 0, bondLength])
        atoms.append(atom2)

    if len(ZMatrix) > 2:
        currentAtom = ZMatrix[2]
        atom3 = currentAtom[0]

        bondLength = 0
        try:
            bondLength = ZMatrix[2][2] * 1.0
        except TypeError:
            try:
                bondLength = variables[ZMatrix[2][2]]
            except KeyError:
                bondLength = constants[ZMatrix[2][2]]

        bondAngle = 0
        try:
            bondAngle = ZMatrix[2][4] * 1.0
        except TypeError:
            try:
                bondAngle = variables[ZMatrix[2][4]]
            except KeyError:
                bondAngle = constants[ZMatrix[2][4]]

        bondAtomLine = coordinates[currentAtom[1]-1]
        bondAtom = atoms[currentAtom[1]-1]
        bondAtom = Atom(bondAtom, bondAtomLine)

        angleAtomLine = coordinates[currentAtom[3]-1]
        angleAtom = atoms[currentAtom[3]-1]
        angleAtom = Atom(angleAtom, angleAtomLine)

        newAtom = Atom(currentAtom[0], bondAtomLine)
        startVector = getUnitVector( getBondVector(bondAtom, angleAtom) ) * numpy.float64(bondLength)
        newAtom.translate(startVector)
        axis1 = [0,1,0]
        origin = bondAtom.getXYZ()
        newAtom.rotate(axis1, bondAngle, origin)
        [newX, newY, newZ] = newAtom.getXYZ()
        coordinates.append([newX, newY, newZ])
        atoms.append(atom3)

    for i in range(3, len(ZMatrix)):
        currentAtom = ZMatrix[i]
        atomi = currentAtom[0]
        bondLength = 0
        try:
            bondLength = currentAtom[2] * 1.0
        except TypeError:
            try:
                bondLength = variables[currentAtom[2]]
            except KeyError:
                bondLength = constants[currentAtom[2]]

        bondAngle = 0
        try:
            bondAngle = currentAtom[4] * 1.0
        except TypeError:
            try:
                bondAngle = variables[currentAtom[4]]
            except KeyError:
                bondAngle = constants[currentAtom[4]]     

        dihedral = 0
        try:
            dihedral = currentAtom[6] * 1.0
        except TypeError:
            try:
                dihedral = variables[currentAtom[6]]
            except KeyError:
                dihedral = constants[currentAtom[6]]

        bondAtomLine = coordinates[currentAtom[1]-1]
        bondAtom = atoms[currentAtom[1]-1]
        bondAtom = Atom(bondAtom, bondAtomLine)

        angleAtomLine = coordinates[currentAtom[3]-1]
        angleAtom = atoms[currentAtom[3]-1]
        angleAtom = Atom(angleAtom, angleAtomLine)
        
        dihAtomLine = coordinates[currentAtom[5]-1]
        dihAtom = atoms[currentAtom[5]-1]
        dihAtom = Atom(dihAtom, dihAtomLine)
        #start by placing the atom directly on top of the bond connecting atom
        newAtom = Atom(currentAtom[0], bondAtomLine)
        #then move the atom along the bond vector the bond length distance
        startVector = numpy.array(getUnitVector(getBondVector(bondAtom, angleAtom))) * bondLength
        newAtom.translate(startVector)
        #rotate the atom about an axis perpendicual to the bond vector to make the correct angle
        axis1 = numpy.cross( getBondVector(angleAtom, dihAtom), getBondVector(angleAtom, bondAtom) )
        origin = bondAtom.getXYZ()
        newAtom.rotate(axis1, bondAngle, origin)
        #finally, rotate about the bond axis to make the correct dihedral angle
        axis2 = getBondVector(angleAtom, bondAtom)
        newAtom.rotate(axis2, dihedral, origin)

        [newX, newY, newZ] = newAtom.getXYZ()
        coordinates.append([newX, newY, newZ])
        atoms.append(atomi)

    return atoms, coordinates

def readInternals(file, mol, bondUnits="bohr", angleUnits="radian"):
    fileText = ""
    if os.path.isfile(file):
        fileText = open(file).read()
    else: 
        fileText = file
    internalList = []
    #casts a string as a integer and reindexes it to a zero based counting
    for line in fileText.splitlines():
        splitLine = line.strip().lower().split()
        #nothing on this line
        if len(splitLine) == 0: pass
        else:
            coordType = splitLine[0]
            internalCoord = None
            atoms = map(eval, splitLine[1:])
            if coordType == "bond":
                internalCoord = BondLength(atoms[0], atoms[1], molecule=mol, units=bondUnits)
            elif coordType == "bend" or coordType == "angle":
                internalCoord = BondAngle(atoms[0], atoms[1], atoms[2], molecule=mol, units=angleUnits)
            elif coordType == "out":
                internalCoord = OutOfPlaneBend(atoms[0], atoms[1], atoms[2], atoms[3], molecule=mol, units=angleUnits)
            elif coordType[:4] == "tors":
                internalCoord = DihedralAngle(atoms[0], atoms[1], atoms[2], atoms[3], molecule=mol, units=angleUnits, onlyPositive=True)
            internalList.append(internalCoord)

    return internalList

def buildB(internalList, mol):
    Bmatrix = []
    atomList = mol.getAtoms()
    for coord in internalList:
        currentVec = []
        for atom in atomList:
            currentVec.extend([0,0,0])
        bvecs = coord.getBVectors()
        nums = coord.getAtomNumbers()
        #fill in the nonzero components
        for i in range(0, len(nums)):
            atomNum = nums[i] - 1
            vec = bvecs[i]
            currentVec[atomNum*3] = vec[0]
            currentVec[atomNum*3+1] = vec[1]
            currentVec[atomNum*3+2] = vec[2]
        Bmatrix.append(currentVec)
    Bmatrix = numpy.array(Bmatrix)
    return Bmatrix

def printInternals(internalList, mol):
    for internal in internalList:
        internal.setMolecule(mol)
        print internal

def getNewMoleculeFromInternals(internalValues, internalList, mol, units="bohr"):
    allXYZ = []
    for atom in mol.getAtoms():
        allXYZ.extend(atom.getXYZ())

    #compute everything on a copy of the molecule
    #so as to not alter the given molecule
    molcopy = mol.copy()
    for internal in internalList:
        internal.setMolecule(molcopy)

    total_error = 0
    num_cycles = 0
    max_cycles = 1000
    for coordNum in range(0, len(internalValues)):
        desiredValue = internalValues[coordNum]
        actualValue = internalList[coordNum].getValue()
        error = abs(desiredValue - actualValue)
        total_error += error

    while total_error > 1e-14 and num_cycles < max_cycles:  
        total_error = 0
        for coordNum in range(0, len(internalValues)):
            desiredValue = internalValues[coordNum]
            actualValue = internalList[coordNum].getValue()
            error = abs(desiredValue - actualValue)
            total_error += error
        Bmatrix = buildB(internalList, molcopy)
    
        for i in range(0, len(internalValues)):
            internal_bvec = Bmatrix[i]
            coord = internalList[i]
            desired_value = internalValues[i]
            diff = desired_value - coord.getValue("bohr-rad-au")
            #displacing by this vector produces the following change in the internal coordinate
            #i.e. the magnitude squared of this vector gives the change in the internal coordinate
            #after displacing the coordinates by the vector
            unit_step = numpy.dot(internal_bvec, internal_bvec)
            #the amount by which we should scale the bvector to produced the desired internal coordinate change
            scale_factor = diff / unit_step
            disp_vector = internal_bvec * scale_factor
            molcopy.displaceXYZ(disp_vector)

        """ an experiment using singular value decomposition... that doesn't work
        U, SVec, V = numpy.linalg.svd(Bmatrix)
        VT = numpy.transpose(V)
        nonSingValues = len(SVec)
        Sigma = numpy.identity(nonSingValues)
        for i in range(0, nonSingValues):
            Sigma[i][i] = SVec[i]
        projB = numpy.dot(U, Sigma)
        rot_trans_xyz = numpy.dot(V, allXYZ)[-6:]
        new_trans_xyz = numpy.dot(numpy.linalg.inv(projB), internalValues).tolist()
        new_trans_xyz.extend(rot_trans_xyz)
        allXYZ = numpy.dot(VT, new_trans_xyz)
        mol.setXYZ(allXYZ)
        print numpy.dot(Bmatrix, allXYZ)
        """
        
        num_cycles += 1

    if num_cycles >= max_cycles:
        print "GEOMETRY NOT CONVERGED"
    
    #set the internals back to the original molecule
    for internal in internalList:
        internal.setMolecule(mol)

    return molcopy

class DispIter:

    def __init__(self, displacement):
        self.currentStep = 0
        self.displacement = displacement

    def __iter__(self):
        return self

    def next(self):
        if self.currentStep == len(self.displacement):
            raise StopIteration

        internals = self.displacement.getInternals()
        values = self.displacement.getValues(step=self.currentStep)
        self.currentStep += 1
    
        return internals, values

class Displacement:

    def __init__(self, *xargs):
        self.internals = []
        self.values = []
        if os.path.isfile(xargs[0]): #this is a "molecule merge" scan
            internals = xargs[2:-1]
            numsteps = xargs[-1]
            mol1 = getComputation(xargs[0])
            mol2 = getComputation(xargs[1])
            for internal in internals:
                internal.setMolecule(mol1)
                startValue = internal.getValue()
                internal.setMolecule(mol2)
                endValue = internal.getValue()
                stepsize = (endValue - startValue) / numsteps
                displacements = []
                for j in range(0, numsteps+1):
                    value = startValue + j * stepsize
                    displacements.append(value)
                #go back to the original molecule
                internal.setMolecule(mol1)
                self.internals.append(internal)
                self.values.append(displacements)
        else:
            i = 0
            numsteps = xargs[-1]
            while i < len(xargs) - 3:
                internal = xargs[i]
                i += 1
                if isinstance(xargs[i], list):
                    displacements = xargs[i]
                    i += 1    
                else:
                    start = xargs[i]
                    i += 1
                    end = xargs[i]
                    stepsize = (end - start) / numsteps
                    i += 1    

                if isinstance(internal, Geometry.BondLength): #convert units to bohr   
                    pass #don't bother to convert - here we make the assumption that the scan units match the input units
                else: #an "angle" unit, convert to radian
                    convert = lambda x: convertUnits(x, "degree", "radian")
                    displacements = map(convert, displacements)
                self.internals.append(internal)        
                self.values.append(displacements)

    def __len__(self):
        return len(self.values[0])
    
    def getInternals(self):
        return self.internals
        
    def getValues(self, step):
        step_values = [] 
        for internal in self.values:
            step_values.append(internal[step])
        return step_values
    
    def __iter__(self):
        return DispIter(self)
    
    def __str__(self):
        str_arr = []
        for internal in self.internals:
            str_arr.append(str(internal))
        for value in self.values:
            str_arr.append(",".join(map(toString, self.values)))
        return "\n".join(str_arr)    

