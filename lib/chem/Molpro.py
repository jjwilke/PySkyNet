## @package MolPro
#  A script called by other modules to process MolPro2006 and MolPro2002 files. The
#  documented methods are those specific to the MolProParser and are not part of the
#  generic parser interface.
import commands
import os
import os.path
import re
from skynet.errors import *
from skynet.utils.utils import *

IRREP_CONVERSIONS = {
    "C2" : {
    "A" : 1,
    "B" : 2
    },
    "C2V" : {
    "A1" : 1,
    "B1" : 2,
    "B2" : 3,
    "A2" : 4
    },
    "D2H" : {
    "AG" : 1,
    "B3U" : 2,
    "B2U" : 3,
    "B1G" : 4,
    "B1U" : 5,
    "B2G" : 6,
    "B3G" : 7,
    "AU" : 8
    },
    "C2H" : {
    "AG" : 1,
    "AU" : 2,
    "BU" : 3,
    "BG" : 4,
    },
    "CS" :
    {
    "AP" : 1,
    "APP" : 2,   
    },
    "CI" :
    {
    "AG" : 1,
    "AU" : 2
    },
}

from parse import Parser, EnergyRegExp
class MolproParser(Parser):

    program = "MOLPRO"

    class SinglepointSCF(EnergyRegExp):
        re1 = r"""![UR]HF [A-Z\s]* [0-9]*[.][0-9]* ENERGY(.*?)\n"""

    class SinglepointMP2(EnergyRegExp):
        re1 = r"""!.*?MP2 [A-Z\s]* [0-9]*[.][0-9]* ENERGY(.*?)\n"""
        re2 = "MP2 total energy:(.*?)\n"

    class SinglepointCCSD(EnergyRegExp):
        re1 = "!.*?CCSD.*?ENERGY\s+(.*?)[\s\n]"

    class SinglepointCCSD_T(EnergyRegExp):
        re1 = "!.*?CCSD\(T\).*?ENERGY\s+(.*?)[\s\n]"
    
    def getProgram(self):
        return "MOLPRO"

    def get_keyword_CHARGE(self):
        inputArea = self.getInputArea().upper()
        inputArray = inputArea.splitlines()
        try:
            charge = re.compile(r"WF,\d+,\d+,\d+,([-]?\d+)").search(inputArea).groups()[0]
            return eval(charge)
        except AttributeError:
            #no charge, give the default
            return 0

    def getGradients(self):
        try:
            #figure out the last step
            regExp = "Optimization point\s+\d+(.*?)Conver"
            steps = re.compile(regExp, re.DOTALL).findall(self.fileText)
            gradMatrix = []
            optunits = self.getOptUnits()
            units = "hartree/%s" % optunits.lower()
            #now build a regexp for the last step
            regExp = "%s(.*?)Conver" % len(steps)
            coordRegExp = """[XYZ]\d+.*?%s #the initial coordinate label
                             \s+[-]?\d+[.]\d+ #previous x,y,z
                             \s+[-]?\d+[.]\d+ #current x,y,z
                             \s+[-]?\d+[.]\d+ #x,y,z on next step
                             \s+([-]?\d+[.]\d+) #the gradient)""" % optunits.upper()
            grads = map(eval, re.compile(coordRegExp, re.VERBOSE).findall(steps[-1]))

            import data
            dp = data.DataPoint(grads, units=units).toXYZ()
        
            #send back the geometries of all steps in the optimization
            return dp

        except (IndexError, AttributeError), error:
            raise InfoNotFoundError("gradients")

    def getNumberOfBasisFunctions(self):
        regExp = "NUMBER OF CONTRACTIONS:\s+(\d+)"
        num_basis = re.compile(regExp).findall(self.fileText)[-1]
        return eval(num_basis)

    def _get_keyword_BASIS(self):
        try:
            basis = re.compile("Library entry [a-zA-Z]+\s+[A-Z] ([a-z\-A-Z]+)\s+selected").search(self.fileText).groups()[0].strip()
            return basis
        except AttributeError:
            pass

        try:
            basis = re.compile("SETTING BASIS\s+[=]\s+(.*?)\n").search(self.fileText).groups()[0].strip()
            return basis   
        except AttributeError:
            pass

        try:
            inputArea = self.getInputArea()
            basis = re.compile("BASIS\s*[=]\s*(.*?)\n").search(inputArea).groups()[0].strip()
            return basis
        except AttributeError:
            raise InfoNotFoundError("basis")


    def get_keyword_CORE(self):
        inputArea = self.getInputArea().upper()
        coreCheck = re.compile("CORE").search(inputArea)
        if coreCheck: #the core keyword was found
            return "CORRELATED"
        else:
            return "FROZEN"

    def get_keyword_COORDTYPE(self):
        inputArea = self.getInputArea().upper()
        try:
            geomType = re.compile("[gG][eE][oO][mM][tT][yY][pP]\s*=\s*(.*?)\n").search(inputArea).groups()[0]
            if geomType == "XYZ":
                return "XYZ"
            else:
                commaTest = re.compile("[gG][eE][oO][mM][eE][tT][rR][yY].*?[{](.*?)[}]", re.DOTALL).search(inputArea).groups()[0].strip().splitlines()[-1]
                if ",," in commaTest:
                    return "XYZ"
                else:
                    return "ZMATRIX"
        except AttributeError: #default to zmat
            return "ZMATRIX"

    def get_keyword_JOBTYPE(self):
        inputArea = self.getInputArea().upper()
        if "OPTG" in inputArea and not "OPTGRAD" in inputArea:
            return "OPTIMIZATION"
        elif "FREQUENCIES" in inputArea:
            return "FREQUENCY"
        else:
            return "SINGLEPOINT"

    def get_keyword_MRCC(self):
        inputArea = self.getInputArea().upper()
        if "MRCC" in inputArea:
            return "TRUE"
        else:
            return "FALSE"

    def get_keyword_MULTIPLICITY(self):
        inputArea = self.getInputArea().upper()
        inputArray = inputArea.splitlines()
        try:
            mult = re.compile("WF,\d+,\d+,(\d+)").search(inputArea).groups()[0]
            return eval(mult) + 1
        except AttributeError:
            #no multiplicity, use default based on the charge
            num_electrons = self.getNumberOfElectrons()
            num_unpaired = num_electrons % 2
            return num_unpaired + 1

    def get_keyword_POINTGROUP(self):
        try:
            pointGroup = re.compile("Point group\s+(.*?)\n").search(self.fileText).groups()[0]
            return pointGroup.upper().strip()
        except AttributeError:
            raise InfoNotFoundError("POINT GROUP")

    def get_keyword_REFERENCE(self):
        inputArea = self.getInputArea().upper()
        if "UHF" in inputArea:
            return "UHF"

        mult = self.get_keyword_MULTIPLICITY()
        if mult > 1:
            return "ROHF"
        else:
            return "RHF"

    def get_keyword_STATESYMMETRY(self):
        import grouptheory
        inputArea = self.getInputArea().upper()
        pointGroup = self.get_keyword_POINTGROUP()
        stateNumber = None
        if pointGroup == "C1":
            return "A"
        try:
            stateExp = re.compile("WF,\d+,(\d+)").search(inputArea).groups()[0]
            stateNumber = eval(stateExp)
        except AttributeError:
            pass #the person may have just omitted the line

        #in this case, no wf line was specified... nor does it have to be
        if not stateNumber: stateNumber = 1

        currentGroup = IRREP_CONVERSIONS[pointGroup]
        for irrep in currentGroup:
            if stateNumber == currentGroup[irrep]:
                return irrep

    def get_keyword_TITLE(self):
        try:
            title=re.compile("\*\*\*,(.*?)\n").search(self.fileText).groups()[0].strip()
            return title
        except AttributeError:
            raise InfoNotFoundError("TITLE")

    def _get_INPUT_Units(self):
        inputArea = self.getInputArea().upper()
        geomArea = re.compile("GEOMETRY\s*=\s*{(.*?)}", re.DOTALL).search(inputArea).groups()[0]
        geomType = self.getKeyword("coordtype")
        if geomType == "xyz":
            if ",," in geomArea: #zmat xyz input
                if "ANGSTROM" in geomArea.upper(): return "ANGSTROM"
                else: return "BOHR"
            else: return "ANGSTROM" #standard xyz only gives angstrom
        else: #zmatrix
            if "ANGSTROM" in geomArea:
                return "ANGSTROM"
            else:
                return "BOHR"

    def get_keyword_WAVEFUNCTION(self):
        inputArea = self.getInputArea().upper()

        if "CCSDT(Q)" in inputArea:
            return "CCSDT(Q)"
        elif "CCSDT" in inputArea:
            return "CCSDT"
        elif "CCSD(T)" in inputArea:
            return "CCSD(T)"
        elif "CCSD" in inputArea:
            return "CCSD"
        elif "MP2" in inputArea:
            return "MP2"
        elif "UHF" in inputArea or "RHF" in inputArea:
            return "SCF"
        else:
            raise InfoNotFoundError("WAVEFUNCTION")

    def getNumberOfElectrons(self):
        try:
            regExp = "NUMBER OF ELECTRONS:\s+(\d+)[+]\s+(\d+)[-]"
            alpha, beta = map(eval, re.compile(regExp).search(self.fileText).groups())
            return alpha + beta
        except AttributeError:
            raise InfoNotFoundError("NUMBER OF ELECTRONS")

    def _get_INITIAL_Units(self):
        geomType = self.getKeyword("coordtype")
        if geomType == "xyz":
            return "bohr"
        else: #we want the units from the initial input for z-matrix
            return self._Units("input")

    def getOptUnits(self):
        return self._getUnits("input")

    def _get_INPUT_XYZ(self):
        inputArea = self.getInputArea().upper()
        atomRegExp = "([A-Z]+)[ ,]+([-]?\d+[.]\d+)[ ,]+([-]?\d+[.]\d+)[ ,]+([-]?\d+[.]\d+)"
        geomInput = re.compile(atomRegExp).findall(inputArea)
        coords = []
        atoms = []
        for atom in geomInput:
            label = atom[0]
            xyz = map(eval, atom[1:])
            atoms.append(label)
            coords.append(xyz)
        return atoms, coords

    def _get_INITIAL_XYZ(self):
        try:
            geomre = re.compile("ATOMIC COORDINATES.*?Z(.*?)(Bond lengths|NUCLEAR CHARGE)", re.DOTALL)
            geomArea = geomre.search(self.fileText).groups()[0].strip()
        except AttributeError:
            raise InfoNotFoundError("XYZ COORDINATES")            
       
        coordinates = []
        atoms = []
        coordinateArray = geomArea.splitlines()
        for line in coordinateArray:
            coordinates.append([])

        for line in coordinateArray:
            splitLine = line.strip().split()
            label = removeNumberSuffix(splitLine[1])
            number = getNumberSuffix(splitLine[1])
            if not number: 
                number = eval(splitLine[0])
            x, y, z = map(eval, splitLine[3:])
            coordinates[number-1] = [x, y, z]
            atoms.append(label)

        return atoms, coordinates

    def _getOptXYZ(self):
        try:
            #figure out the last step
            regExp = "Optimization point\s+\d+" 
            steps = re.compile(regExp).findall(self.fileText)
    
            coordinates = []
            units = self.getOptUnits()
            atomList = self.getAtoms("input")
            for step in steps:
                currentXYZ = []
                #now build a regexp for the last step
                regExp = "%s(.*?)Conver" % step
                xyzBlock = re.compile(regExp, re.DOTALL).search(self.fileText).groups()[0]
                coordRegExp = "[XYZ]\d+.*?%s\s+[-]?\d+[.]\d+\s+([-]?\d+[.]\d+)" % units
                allXYZ = re.compile(coordRegExp).findall(xyzBlock)

                atomNumber = 0
                for i in range(0, len(allXYZ)):
                    if i % 3 == 0: 
                        atomNumber += 1
                        currentXYZ.append([])
                    currentCoord = eval(allXYZ[i])
                    currentXYZ[-1].append(currentCoord) 
                
                coordinates.append(currentXYZ)

            #send back the geometries of all steps in the optimization
            return atomList, coordinates

        except (IndexError, AttributeError), error:
            sys.stderr.write("%s\n" % error)
            raise InfoNotFoundError("optimized XYZ")

    def cleanZMatrix(self, ZMatrix, variables, constants):
        #now, we have to go through and process all the negative dihedral variables
        try:
            negativeVars = {}
            for i in range(3, len(ZMatrix)):
                atom = ZMatrix[i]
                currentValue = atom[6]
                if currentValue[0] == "-":
                    if currentValue in negativeVars:
                        newVarName = negativeVars[currentValue]
                        atom[6] = newVarName
                    else:
                        varNumber = 1
                        newVarName = "D%d" % varNumber
                        while variables.has_key(newVarName) or constants.has_key(newVarName):
                            varNumber += 1
                            newVarName = "D%d" % varNumber
                        variables[newVarName] = variables[currentValue]
                        negativeVars[currentValue] = newVarName
                        atom[6] = newVarName
                        del variables[currentValue]
        except (IndexError, KeyError):
            raise InfoNotFoundError("Z-MATRIX")

        return [ZMatrix, variables, constants]

    def getForceConstants(self):
        raise InfoNotFoundError

    def getNumDummyAtoms(self):
        inputArea = self.getInputArea()
        numDummy = 0
        read = False
        for line in inputArea.splitlines():
            stripLine = line.strip().upper()
            if "{" in stripLine:
                read = True
            elif "}" in stripLine:
                read = False
            elif read and len(stripLine) > 0 and (stripLine[0] == "DUMMY" or stripLine[0] == "Q" or stripLine[0] == "X"):
                numDummy += 1

        return numDummy

    ##### AUXILLIARY METHODS #####

    ## Gets the input area where the user defines the geometry and keywords
    # @param self.fileText A string telling the file to be parsed
    # @returns A string of the input area.  This will contain new line characters!
    # @throws FileTypeError If no input area is found, assumes you don't have a MolPro file
    def getInputArea(self):
        regExp = r"""default implementation .*? Variables initialized"""
        matchStr = re.compile(regExp, re.DOTALL)
        try:
            inputArea = matchStr.findall(self.fileText)[0]
            return inputArea
        except IndexError:
            raise InfoNotFoundError


    def getInputZMatrix(self):
        #determine the size of the z-matrix
        try:
            inputArea = self.getInputArea().upper().replace("ANGSTROM","")
            geomArea = re.compile("GEOMETRY\s*=\s*{(.*?)}", re.DOTALL).search(inputArea).groups()[0].strip()                        
            zMatrixArray = geomArea.splitlines()
            variables = {}
            constantNames = {}
            constantValues = {}
            specialVarValues = {}
            atomLabels = {}
            numNewVariables = {"BOND" : 0, "ANGLE" : 0, "DIHEDRAL" : 0}
            newVariables = { "R" : {}, "A" : {}, "D" : {}}
            #clean up the zmatrix and store all the values in an array
            for i in range(0, len(zMatrixArray)):
                line = zMatrixArray[i].replace(";","").replace(",", " ").strip().split()
                zMatrixArray[i] = line

            for i in range(0, len(zMatrixArray)):
                atom = zMatrixArray[i]
                j = 2
                while j < len(atom):
                    currentValue = atom[j]
                    if isNumber(currentValue): #we have a constant
                        currentValue = eval(currentValue) 
                        if constantValues.has_key(currentValue): #we have already stored this constant
                            atom[j] = constantValues[currentValue]
                        else:
                            constantNumber = 1
                            newName = ""
                            if j == 2: 
                                numNewVariables["BOND"] += 1
                                newName = "Rnew%d" % numNewVariables["BOND"]
                                newVariables["R"][newName] = currentValue 
                            elif j == 4:
                                numNewVariables["ANGLE"] += 1
                                newName = "Anew%d" % numNewVariables["ANGLE"]
                                newVariables["A"][newName] = currentValue 
                            elif j == 6:
                                numNewVariables["DIHEDRAL"] += 1
                                newName = "Dnew%d" % numNewVariables["DIHEDRAL"]
                                newVariables["D"][newName] = currentValue  
                            #replace the number in the z-matrix
                            atom[j] = newName

                    else: #this is a variable
                        if variables.has_key(currentValue.upper()): #we have already stored this variable
                            atom[j] = atom[j].upper()                        
                        else:
                            #some variables are minus variables, and must be searched for the base values
                            if currentValue[0] == "-":
                                regExp = "%s\s*=\s+(.*?)\s" % currentValue.strip("-")
                                varValue = -1 * eval(re.compile(regExp).findall(self.fileText)[-1])
                                variables[currentValue.upper()] = varValue      
                            else:
                                regExp = "%s\s*=\s?(.*?)\n" % currentValue
                                varValue = eval(re.compile(regExp).findall(self.fileText)[-1])
                                variables[currentValue.upper()] = varValue
                            atom[j] = currentValue.upper()
                    j += 2
            #process all the new variables that must be named       
            for varType in newVariables:
                for name in newVariables[varType]:
                    constantNumber = 1
                    currentValue = newVariables[varType][name]
                    newConstant = "%s%d" % (varType, constantNumber)
                    while variables.has_key(newConstant) or constantNames.has_key(newConstant):
                        constantNumber += 1
                        newConstant = "%s%d" % (varType, constantNumber)
                    constantValues[currentValue] = newConstant
                    constantNames[newConstant] = currentValue
                    for line in zMatrixArray:
                        for j in (2, 4, 6):
                            if j < len(line) and line[j] == name: line[j] = newConstant
                        

            atomLabels = {}
            #process all special atom labels
            atomNumber = 1
            for i in range(0, len(zMatrixArray)):
                atom = zMatrixArray[i]
                atomLabel = atom[0]
                atomLabels[atomLabel] = atomNumber
                atomName = removeNumberSuffix(atomLabel)
                atom[0] = atomName
                atomNumber += 1

                #now go through and make any necssary replacements
                j = 1
                while j < len(atom):
                    currentValue = atom[j]
                    if atom[j] in atomLabels:
                        atom[j] = atomLabels[atom[j]]
                    elif isinstance(atom[j],str):
                        atom[j] = eval(atom[j])
                    j += 2

            return self.cleanZMatrix(zMatrixArray, variables, constantNames)


        except OSError:#(IndexError, KeyError, AttributeError):
            raise InfoNotFoundError("INPUT Z-MATRIX")

    def getNumAtoms(self):
        return len(self.getXYZ())

    def getOptEnergies(self):
        try:
            energies = map(eval, re.compile("Optimization point.*?Hartree\s+"
                                            "[-]?\d+[.]\d+\s+([-]\d+[.]\d+)", re.DOTALL).findall(self.fileText))
            return energies
        except AttributeError:
            raise InfoNotFoundError("Optimization Energies") 

    def getOptimizedZMatrix(self):
        varLines = ""
        [ZMatrix, variables, constants] = self.getInputZMatrix()
        regExp = r"""Optimization point .*? Variable \s+ Last \s+ .*? Convergence:"""
        matchStr = re.compile(regExp, re.DOTALL)
        try:
            varLines = matchStr.findall(self.fileText)[-1]
        except IndexError:
            jobType = self.get_keyword_JOBTYPE()
            if not jobType == "OPTIMIZATION":
                raise FileTypeError("OPTIMIZATION")
            else:
                raise InfoNotFoundError("Optimized Z-Matrix")

        varArray = varLines.splitlines()
        for line in varArray:
            splitLine = line.strip().split("/")
            varName = splitLine[0].strip()
            if varName in variables:
                varValue = splitLine[1].split()[2]
                variables[varName] = eval(varValue)
                if "-%s" % varName in variables: #also a negative variable
                    varValue = splitLine[1].split()[2]
                    variables["-%s" % varName] = eval("-%s" % varValue)

                    
        return self.cleanZMatrix(ZMatrix, variables, constants)

    def getOptZMatrices(self):
        varLines = ""
        [ZMatrix, variables, constants] = self.getInputZMatrix()
        regExp = r"""Optimization point.*? Variable \s+ Last \s+ .*? Convergence:"""
        matchStr = re.compile(regExp, re.DOTALL)
        allVariables = matchStr.findall(self.fileText)
        allVars = []
        for varLines in allVariables:
            varArray = varLines.splitlines()
            for line in varArray:
                splitLine = line.strip().split("/")
                varName = splitLine[0].strip()
                if varName in variables:
                    varValue = splitLine[1].split()[2]
                    variables[varName] = eval(varValue)
                    if "-%s" % varName in variables: #also a negative variable
                        varValue = splitLine[1].split()[2]
                        variables["-%s" % varName] = eval("-%s" % varValue)
            allVars.append(variables.copy())

        finalVars = []
        finalConstants = {}
        finalZMat = []
        for variables in allVars:
            [finalZMat, vars, finalConstants] = self.cleanZMatrix(ZMatrix, variables, constants)
            finalVars.append(vars)

        return [finalZMat, finalVars, finalConstants]
                        
    def _check_convergence_CCSD(self):
        check = re.compile("CONVERGENCE NOT REACHED AFTER MAX. ITERATIONS").search(self.fileText)
        if check: #did not convergence
            return False
        else:
            return True

    def getSingleCCSDEnergy(self):
        #check convergence
        self.checkSingleSCFConvergence()
        self.checkSingleCCSDConvergence()

        try:
            energy = re.compile("!.*?CCSD.*?ENERGY\s+(.*?)[\s\n]").search(self.fileText).groups()[0]
            return eval(energy)
        except (IndexError, AttributeError):
            raise InfoNotFoundError("CCSD Energy")


    def getSingleCCSD_TEnergy(self):
        #check convergence
        self.checkSingleSCFConvergence()
        self.checkSingleCCSDConvergence()    

        try:
            energy = re.compile("!.*?CCSD\(T\).*?ENERGY\s+(.*?)[\s\n]").search(self.fileText).groups()[0]
            return eval(energy)
        except (IndexError, AttributeError):
            raise InfoNotFoundError("CCSD(T) Energy")

    def getSingleMP2Energy(self):
        #check convergence
        self.checkSingleSCFConvergence()

        #two different ways of getting MP2, check both
        regExp = r"""!.*?MP2 [A-Z\s]* [0-9]*[.][0-9]* ENERGY(.*?)\n"""
        matchStr = re.compile(regExp, re.DOTALL)
        try:
            energyLine = matchStr.findall(self.fileText)[-1]
            energy = energyLine.strip().split()[-1]
            return eval(energy)
        except IndexError:
            pass

        #okay... the first one failed... let's try again
        try:
            energy = re.compile("MP2 total energy:(.*?)\n").search(self.fileText).groups()[0]
            return eval(energy)
        except (IndexError, AttributeError):
            raise InfoNotFoundError("MP2 Energy")


    def _check_convergence_SCF(self):
        try:
            maxIterations = eval(re.compile("MAX. NUMBER OF ITERATIONS:\s+(.*?)\n").search(self.fileText).groups()[0])
            numIterations = eval(re.compile("ITERATION\s+DDIFF(.*?)Final.*?occupancy", re.DOTALL).search(self.fileText).groups()[0].strip().splitlines()[-1].strip().split()[0])
            if maxIterations <= numIterations:
                return False
            else:
                return True
        except AttributeError:
            raise InfoNotFoundError("Couldn't find SCF iterations and convergence")            

    def getStateEnergy(self, stateLabel, mult):
        symm = stateLabel.split(".")[1]
        try:
            regExp = "Spin symmetry=%s\s+Space symmetry=%s(.*?)DATASETS" % (mult, symm)
            multText = re.compile(regExp, re.DOTALL).search(self.fileText).groups()[0]
        except AttributeError: #not a casscf, a ci
            regExp = "Reference symmetry:\s+%s\s+%s(.*?)DATASETS" % (symm, mult)
            multText = re.compile(regExp, re.DOTALL).search(self.fileText).groups()[0]

        regExp = "STATE %s ENERGY(.*?)\n" % stateLabel
        energy = eval( re.compile(regExp).findall(multText)[-1] )

        return energy

    def getSOCElements(self, bra_record, ket_record, component):
        clean = lambda x: eval(x.replace("i", "j"))
        try:
            regExp = "Ket wavefunction restored from record\s+%s.*?Bra wavefunction restored from record\s+%s(.*?)DATASETS" % (ket_record, bra_record)
            soc_area = re.compile(regExp, re.DOTALL).search(self.fileText).groups()[0]        

            #regExp = r"full Breit-Pauli(.*?)[*]"
            regExp = r"mean field operator(.*?)Spin-orbit"
            soc_area = re.compile(regExp, re.DOTALL).search(soc_area).groups()[0]

            regExp = r"MRCI trans.*?<.*?LS%s.*?>\s+[\-]?(.*?)au"
            mat_elements = re.compile(regExp % component).findall(soc_area)

            if len(mat_elements) == 0:
                return None
            else:
                return map(clean, mat_elements)
        except AttributeError:
            return None #we want to return a value of false so the program knows that nothing was returned
    


