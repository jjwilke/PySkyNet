import re
import numpy
import commands
import grouptheory
import sys
import os
import os.path
from skynet.errors import *
from skynet.utils.utils import *
from chem.data import *


from parse import Parser, EnergyRegExp
class AcesParser(Parser):

    program = "ACES"

    class SinglepointSCF(EnergyRegExp):
        import re
        re1 = r"E\(SCF\)\s*=\s*([-]?\d+[.]\d+)\sa[.]u[.]"
        re2 = [[re.compile('SCF has converged[.].*?([-]\d+[.]\d+)\s+', re.DOTALL), 'search', {}]]
        re3 = r"E\(SCF\)\s*=\s*([-]?\d+[.]\d+)"

    class SinglepointMP2(EnergyRegExp):
        re1 = r'Total MBPT\(2\) energy\s+=\s+(.*?)\s'

    class SinglepointCCSD(EnergyRegExp):
        re1 = r"CCSD\s+=\s+(.*?)\n"
        re2 = "[-]?\d+[.]\d+\s+([-]?\d+[.]\d+).*?\n.*?\n\s*A\smiracle"

    class SinglepointCCSD_T(EnergyRegExp):
        re1 = r'CCSD\(T\)\s+=\s+(.*?)\n'
        re2 = r'E\(CCSD\(T\)\)\s+=\s+(.*?)\n'
        re3 = r'CCSD\(T\) energy\s+([-]?\d+[.]\d+)\n'

    def getProgram(self):
        return "ACES"

    def getRotationMatrix(self):
        try:
            regexp = "rotation matrix(.*?)[-]{5}"
            text = re.compile(regexp, re.DOTALL).search(self.fileText).groups()[0]
            values = map(eval, re.compile("[-]?\d+[.]\d+").findall(text))
            dp = DataPoint(values)
            natoms = self.getNumAtoms()
            dp.toMatrix(3, 3)
            return dp
        except Exception, error:
            raise InfoNotFoundError("rotation matrix")

    ## Reads in the highest level diagonal born oppenheimer correction from the file
    #  @param inputFile The path of the file to read in
    #  @return The diagaonal born-oppenheimer correction in hartrees
    #  @throws InfoNotFoundError
    def getDBOCCorrection(self):
        try:
            dbocInWN = eval(re.compile("diagonal Born-Oppenheimer correction.*?is:\s+(.*?)\s").search(self.fileText).groups()[0])
            dbocInHartree = convertUnits(dbocInWN, "WAVENUMBER", "HARTREE")
            return dbocInHartree
        except (TypeError, AttributeError):
            raise InfoNotFoundError("DBOC CORRECTION")

    def getEOMEnergy(self, irrep, root):
        try:
            irrep = eval(irrep)
        except TypeError:
            import grouptheory
            irrep = grouptheory.ACES_CONVERSIONS[irrep.upper()]
        regExp = "Beginning symmetry block\\s+?%d.*?Solution of\\s+?\d roots required" % irrep
        matchstr = re.compile(regExp, re.DOTALL)
        rootArea = matchstr.findall(self.fileText)[0]
        regExp = r"""Total EOMEE-.*?electronic energy.*?a[.]u[.]"""
        matchstr = re.compile(regExp)
        matches = matchstr.findall(rootArea)
        desiredLine = matches[root-1]
        energy = eval(desiredLine.split()[4])
        return energy

    def _get_keyword_BASIS(self):
        try:
            basis = re.compile("IBASIS\s+(.*?)\s").search(self.fileText).groups()[0]
            if basis[0] == "P":
                basis = "CC-" + basis
            elif basis[:3] == "AUG":
                basis = "AUG-CC-" + basis[4:]
            else:
                raise AttributeError
            return basis
        except AttributeError:
            raise InfoNotFoundError("BASIS")

    def getFieldGradients(self):
        try:
            grads = DataSet()
            atoms = self.getAtoms()
            numatoms = len(atoms)
            regexp = "Electric field gradient at atomic centers(.*?)Elec"
            section = re.compile(regexp, re.DOTALL).findall(self.fileText)[-1]
            comps = 'XX', 'YY', 'ZZ'
            for comp in comps:
                regexp = r'%s\s+=\s+([-]?\d+[.]\d+)' % comp
                vals = re.compile(regexp).findall(section)
                for i in xrange(numatoms):
                    label = "%s%s" % (atoms[i], i+1)
                    dp = DataPoint(eval(vals[i]), attributes=self.getKeywords(), units="hartree/bohr^2", component=comp, atom=label)
                    grads.add(dp)
            return grads
        except Exception, error:
            raise InfoNotFoundError("electric field gradients")

    def get_keyword_CHARGE(self):
        try:
            keyword = re.compile("ICHRGE\s+(.*?)\s").search(self.fileText).groups()[0]
            return eval(keyword)
        except AttributeError:
            raise InfoNotFoundError("CHARGE")        

    def get_keyword_CORE(self):
        try:
            keyword = re.compile("IDRPMO\s+(.*?)\s").search(self.fileText).groups()[0]
            if keyword == "NONE":
                return "CORRELATED"
            else:
                return "FROZEN"
        except AttributeError:
            raise InfoNotFoundError("CORE")  

    def get_keyword_COORDTYPE(self):
        try:
            keyword = re.compile("ICOORD\s+(.*?)\s").search(self.fileText).groups()[0]
            if keyword == "INTERNAL":
                return "ZMATRIX"
            else:
                return "XYZ"
        except AttributeError:
            raise InfoNotFoundError("GEOMETRY TYPE")  

    def get_keyword_JOBTYPE(self):
        checkRel = re.compile("IPROPS\s+(.*?)\s").search(self.fileText).groups()[0]
        if checkRel == "FIRST_ORDER":
            return "RELATIVITY"

        checkDBOC = re.compile("IDBOC\s+(.*?)\s").search(self.fileText).groups()[0]
        if checkDBOC == "ON":
            return "DBOC"

        checkFreq = re.compile("IVIB\s+(.*?)\s").search(self.fileText).groups()[0]
        if not checkFreq == "NO":
            return "FREQUENCY"

        if self.get_keyword_COORDTYPE() == "XYZ":
            return "SINGLEPOINT"

        checkOpt = eval(re.compile("Of these,\s+(.*?)\s").search(self.fileText).groups()[0])
        if checkOpt > 0:
            return "OPTIMIZATION"

        #okay, nothing special
        return "SINGLEPOINT"

    def get_keyword_MEMORY(self):
        try:
            keyword = re.compile("IMEMSZ\s+(.*?)\s").search(self.fileText).groups()[0]
            try:
                mem = eval(keyword)
                return int(mem/1E6)
            except (TypeError, SyntaxError):
                return 1900 #for Opt06 machines, too big to fit
        except AttributeError:
            raise InfoNotFoundError("MEMORY") 

    def get_keyword_MRCC(self):
        mrcc = re.compile("ICCPRO\s+(.*?)\s").search(self.fileText).groups()[0]
        if mrcc == "MRCC":
            return "TRUE"
        else:
            return "FALSE"       

    def get_keyword_MULTIPLICITY(self):
        try:
            keyword = re.compile("IMULTP\s+(.*?)\s").search(self.fileText).groups()[0]
            return eval(keyword)
        except AttributeError:
            raise InfoNotFoundError("MULTIPLICITY")   

    def get_keyword_OCCUPATION(self):
        occupation = self.getOccupation()
        alpha = occupation["ALPHA"]
        beta = occupation["BETA"]

        pg = self.get_keyword_POINTGROUP().lower()
        import grouptheory

        str_arr = []
        line_arr = ["docc = "]
        for irrep in grouptheory.COTTON_ORDER[pg]:
            line_arr.append("%d" % beta[irrep])
        str_arr.append(" ".join(line_arr))

        line_arr = ["socc = "]
        for irrep in grouptheory.COTTON_ORDER[pg]:
            line_arr.append("%d" % (alpha[irrep] - beta[irrep]))
        str_arr.append(" ".join(line_arr))

        return str_arr

    def get_keyword_SPHERICAL(self):
        keyword = re.compile("IDFGHI\s+(.*?)\s").search(self.fileText).groups()[0]
        if keyword == "ON":
            return "TRUE"
        else:
            return "FALSE" 

    ## An ACES specific method.  Figures out the numbering scheme ACES used for numbering the irreps
    #  @param inputFile The path of the file to parse
    #  @return A dictionary object.  Keys are the irreps.  Values are the integer number of the irrep.
    def getIrrepNumbers(self):
        irrepNumbers = {}
        pg = self.get_keyword_POINTGROUP()
        standardIrreps = grouptheory.getIrreps(pg)
        for irrep in standardIrreps:
            irrep = irrep.upper()
            acesIrrep = irrep.replace("P", "'").replace("G", "g").replace("U", "u")
            regExp = r"""MO # .*? E\(hartree\) .*? """ + acesIrrep + r"""\s* \([0-9]+\)"""
            matchStr = re.compile(regExp, re.DOTALL)
            try:
                occMatch = matchStr.findall(self.fileText)[0]
                number = eval(occMatch.strip().split()[-1].strip("()"))
                irrepNumbers[irrep.lower()] = number    
            except IndexError:
                #one of the irreps doesn't actually have any mo's
                irrepNumbers[irrep.lower()] = 0
        return irrepNumbers

    def getOccupation(self):
            
        occupation = {
            "ALPHA" : {},
            "BETA" : {}
            }

        pg = self.get_keyword_POINTGROUP()
        if pg == "C1": 
            num_electrons = self.getNumElectrons()
            num_alpha = num_electrons/2 + num_electrons%2
            num_beta = num_electrons/2
            occupation["ALPHA"]["A"] = num_alpha
            occupation["BETA"]["A"] = num_beta

        try:
            regExp = r"""current occupation vector [0-9\s]+ SCF has"""
            matchstr = re.compile(regExp)
            matches = matchstr.findall(self.fileText)
            occupancyLines = matches[-1].splitlines()[1:3]
            
            alpha = occupancyLines[0].strip().split()
            beta = occupancyLines[1].strip().split()

            irrepNumbers = self.getIrrepNumbers()

            for irrep in irrepNumbers:
                number = irrepNumbers[irrep]
                numAlpha = eval(alpha[number-1])
                numBeta = eval(beta[number-1])
                occupation["ALPHA"][irrep] = numAlpha
                occupation["BETA"][irrep] = numBeta

            return occupation
        except IndexError:
            raise ParseError

    def get_keyword_POINTGROUP(self):
        try:
            pg = re.compile("Computational point group:\s*(.*?)\n").search(self.fileText).groups()[0]
            return pg.upper().replace(" ","")
        except AttributeError:
            pass

        try:
            pg = re.compile("computational point group is (.*?)\s[.]").search(self.fileText).groups()[0]
            return pg.upper().replace(" ","")
        except AttributeError:
            raise InfoNotFoundError("POINTGROUP")

    def get_keyword_REFERENCE(self):
        reference = re.compile("IREFNC\s+(.*?)\s").search(self.fileText).groups()[0]
        return reference

    def _getFrequencies(self):
        regExp = r"""Cartesian force constants:.*?Zero-point vibrational energy"""
        matchStr = re.compile(regExp, re.DOTALL)
        frequencies = []
        try:
            freqLines = matchStr.findall(self.fileText)[0].splitlines()[1:-1]
        except IndexError:
            raise InfoNotFoundError
        for line in freqLines:
            freq = line.strip().split()[1]

            #turn i's into negative numbers
            newFreq = 0
            if "i" in freq:
                newFreq = -1 * eval(freq[:-1])
            else:
                newFreq = eval(freq)

            #throw out zero's
            if abs(newFreq) < 1E-4:
                pass
            else:
                frequencies.append(newFreq)

        return frequencies
                
    def get_keyword_STATESYMMETRY(self):
        pointGroup = self.get_keyword_POINTGROUP()
        if pointGroup == "C1":
            return "A"
        
        occupation = self.getOccupation()
        excessAlphaArray = {}
        for irrep in occupation["ALPHA"]:
            excessAlpha = occupation["ALPHA"][irrep] - occupation["BETA"][irrep]
            excessAlphaArray[irrep.lower()] = excessAlpha


        stateSymmetry = grouptheory.getStateSymmetry(pointGroup, excessAlphaArray)

        return stateSymmetry

    def get_keyword_TITLE(self):
        try:
            title = re.compile(r"Job Title : (.*?)\n").search(self.fileText).groups()[0].strip()
            return title
        except AttributeError:
            return "NONE"

    def get_keyword_PRINTUNITS(self):
        return self.getUnits("input")

    def _get_INPUT_Units(self):
        try:
            units = re.compile("IUNITS\s+(.*?)\s").search(self.fileText).groups()[0]
            return units
        except AttributeError:
            raise InfoNotFoundError("input units")

    def get_keyword_WAVEFUNCTION(self):
        wfn = re.compile("ICLLVL\s+(.*?)\s").search(self.fileText).groups()[0].replace("[", "(").replace("]",")")
        if "MBPT" in wfn:
            numMP = wfn.strip(")").split("(")[1]
            wfn = "MP%s" % numMP
        return wfn

    def getRelativityCorrection(self):
        try:
            rel = eval(re.compile("Relativistic correction to the energy.*?Total\s+=\s+(.*?)\n", re.DOTALL).findall(self.fileText)[-1])
            return rel
        except (TypeError, IndexError):
            raise InfoNotFoundError("Relativity Correction")

    def _get_INITIAL_Units(self):
        if 'matrix' in self.getKeyword('coordtype'):
            return self._get_INPUT_Units()
        else:
            return "bohr"

    def getDipole(self):
        indexmap = { 'x' : 0, 'y' : 1, 'z' : 2 }
        dipolevec = numpy.array( [0.0, 0.0, 0.0] )
        try:
            dipoleText = re.compile('Total dipole moment\n(.*?)Conversion factor', re.DOTALL).search(self.fileText).groups()[0]
            components = re.compile('([xyz])\s+[-]?\d+[.]\d+\s+([-]?\d+[.]\d+)').findall(dipoleText)
            for comp, val in components:
                index = indexmap[comp]
                dipolevec[index] = eval(val)
            return dipolevec
        except:
            raise InfoNotFoundError('dipole')

    def _get_OPT_Units(self):
        return self._get_OPTIMIZED_Units()

    def _get_OPTIMIZED_Units(self):
        return "bohr"
##         try:
##             units = re.compile(r"""Parameter values are in(.*?)[\s\n]""").search(self.fileText).groups()[0]
##             print units
##             sys.exit()
##             if units == "Angstroms":
##                 return "ANGSTROM"
##             else:
##                 return "BOHR"
##         except AttributeError:
##             raise InfoNotFoundError("OPTIMIZATION", "Could not find any units for the optimization")

    def _get_OPT_XYZ(self):
        coordinates = []
        coordinateSet = re.compile(r"Coordinates.*?in bohr.*?Z(.*?)Interatomic", re.DOTALL).findall(self.fileText)
        atoms = []
        for geomsection in coordinateSet:
            atoms = []
            xyzlines = re.compile("([a-zA-Z]+)\s+\d+\s+([-]?\d+[.]\d+)\s+([-]?\d+[.]\d+)\s+([-]?\d+[.]\d+)").findall(geomsection)
            coordinates.append([])
            for label, x, y, z in xyzlines:
                atoms.append(label)
                x = eval(x)
                y = eval(y)
                z = eval(z)                 
                coordinates[-1].append([x,y,z])
        return atoms, coordinates      

    def _get_start_xyz(self):
        coordinates = []
        atoms = []
        coordinateSet = re.compile(r"Coordinates.*?in bohr.*?Z(.*?)Interatomic", re.DOTALL).findall(self.fileText)[0].strip().splitlines()[1:-1]
        for entry in coordinateSet:
            splitLine = entry.strip().split()
            atoms.append(splitLine[0])
            x = eval(splitLine[2])
            y = eval(splitLine[3])
            z = eval(splitLine[4])                 
            coordinates.append([x,y,z])
        return atoms, coordinates  

    def _get_end_xyz(self):
        coordinates = []
        atoms = []
        coordinateSet = re.compile(r"Cartesian Coordinates.*?[-]{5}.*?Total number of coordinates[:]\s*\d+\n\n(.*?)(Symm|Trans)", re.DOTALL)
        coordtext = coordinateSet.search(self.fileText).groups()[0]
        
        vals = map(eval, re.compile("[-]?\d+[.]\d+").findall(coordtext))
        atomlist = re.compile("[A-Z]+").findall(coordtext)
        natoms = len(vals) / 3
        coordinates = []
        atoms = []
        for i in range(natoms):
            xyz = vals[3*i : 3*i+3]
            coordinates.append(xyz)
            atoms.append(atomlist[i])

        return atoms, coordinates  

    def _get_permutation_matrix(self):
        import numpy
        atoms, startxyz = self._get_start_xyz();
        startxyz = numpy.array(startxyz)
        atoms, endxyz = self._get_end_xyz()
        endxyz = numpy.array(endxyz)
    
        natoms = len(atoms)

        #loop through start xyz and find out what row it now corresponds to
        perm = []
        for i in range(natoms):
            row = [0] * natoms
            thisxyz = startxyz[i]
            for j in range(natoms):
                testxyz = endxyz[j]
                diff = 0
                diff += abs(testxyz[0] - thisxyz[0]) 
                diff += abs(testxyz[1] - thisxyz[1]) 
                diff += abs(testxyz[2] - thisxyz[2]) 
                if (diff < 1e-5):
                    row[j] = 1
                    break
            perm.append(row)

        return numpy.array(perm)

    def _get_INITIAL_XYZ(self):
        import numpy

        try:
            atoms, endxyz = self._get_end_xyz()

            permMatrix = self._get_permutation_matrix()

            endxyz = numpy.array(endxyz)
            xyz = numpy.dot(permMatrix,endxyz)

            return atoms, xyz
        except Exception, error:
            atoms, startxyz = self._get_start_xyz()

            return atoms, startxyz



    def _get_INPUT_XYZ(self):
        return self._get_INITIAL_XYZ()

    def _getInputZMatrix(self):
        ZMatrix = []
        variables = {}
        constants = {}
        zMatrixLines = re.compile("User supplied.*?WRT.*?WRT.*?DEG\)(.*?)\*Initial", re.DOTALL).search(self.fileText).groups()[0].replace("-","").strip().splitlines()
        for line in zMatrixLines:
            splitLine = line.strip().split()
            ZMatrix.append(splitLine)
        for atom in ZMatrix: #convert atom numbers to integers
            j = 1
            while j < len(atom):
                atom[j] = eval(atom[j])
                j += 2

        regExp = r"""Initial values for internal coordinates.*?---"""
        matchStr = re.compile(regExp, re.DOTALL)
        variableLines = matchStr.findall(self.fileText)[0]
        variableArray = variableLines.splitlines()[2:-1]
        for line in variableArray:
            [name, value] = line.strip().split()
            constants[name] = eval(value)

        return [ZMatrix, variables, constants]

    def _getOptZMatrices(self):
        try:
            [inputZMat, variables, constants] = self._getInputZMatrix()
            regExp = r"""Parameter\s+dV/dR\s+Step\s+Rold.*?Minimum force"""
            matchStr = re.compile(regExp, re.DOTALL)
            parameterLines = matchStr.findall(self.fileText)
            allVariables = []
            for parameterSet in parameterLines:
                parameterLinesArray = parameterSet.splitlines()[2:-2]
                for line in parameterLinesArray:
                    splitLine = line.strip().split()
                    name = splitLine[0]
                    value = eval(splitLine[-1])
                    variables[name] = value
                allVariables.append(variables.copy())

            return [inputZMat, allVariables, constants]
        except (AttributeError, IndexError):
            raise InfoNotFoundError("Optimization Z-Matrices")

    ## Methods specific to optimizations
    def _getOptEnergies(self):
        energies = [] #array to hold all of the energies

        #aces is tricky...we have to determine what the highest energy level is

        wfn = self.get_keyword_WAVEFUNCTION()
        return [0]

        regExps = {
            "CCSD(T)" : "CCSD\(T\)\s+=\s+(.*?)\n",
            "CCSD" : "CCSD\s+=\s+(.*?)\n",
            "MP2" : "Total MBPT\(2\) energy\s+=\s+(.*?)\s",
            "SCF" : "E\(SCF\)\s*=\s*(.*?)[\s\n]"
            }
        regExp = regExps[wfn]
        
        try:
            energies = map(eval, re.compile(regExp).findall(self.fileText))
            return energies
        except AttributeError:
            raise InfoNotFoundError("Optimization Energies")

    def getNumAtoms(self):
        return len(self.getXYZ())

    def getGradients(self):
        regExp = "Molecular gradient(.*?)Molecular gradient norm"  
        gradText = re.compile(regExp, re.DOTALL).search(self.fileText)

        #check that gradients were found
        if not gradText:   
            raise InfoNotFoundError("gradients")

        #okay, gradients were found
        gradText = gradText.groups()[0]
        regExp = "([a-zA-Z]+).*?([-]?\d+[.]\d+)\s+([-]?\d+[.]\d+)\s+([-]?\d+[.]\d+)"
        gradientList = re.compile(regExp).findall(gradText)

        #loop through and store gradients
        gradientmap = {}
        gradients = []
        for xyzGrad in gradientList:
            atom, gradient = xyzGrad[0], map(eval, xyzGrad[1:])
            gradients.append(gradient)
            """
            if gradientmap.has_key(atom):
                gradientmap[atom].append(gradient)
            else:
                gradientmap[atom] = [gradient]

        for atom in self.getAtoms():
            print atom
            nextGrad = gradientmap[atom].pop(0)
            gradients.append(nextGrad)

        print gradients
        sys.exit("aces getGradient")
        """

        permMatrix = self._get_permutation_matrix()
        gradients = numpy.array(gradients)
        gradients = numpy.dot(permMatrix, gradients)

        #return it as a numpy matrix
        dp = DataPoint(gradients, units="hartree/bohr")
        return dp

    def getForceConstants(self):
        try:
            folder, file = os.path.split(self.filepath)
            fcmfile = open(os.path.join(folder, "fcmfinal")).read()
            numAtoms = eval(re.compile("(\d+)").search(fcmfile).groups()[0])
            numCoords = 3 * numAtoms
            allFC = map(eval, re.compile("[-]?\d+[.]\d+").findall(fcmfile))

            num = 0
            fcm = []
            for fc in allFC:
                if num % numCoords == 0:
                    fcm.append([])
                fcm[-1].append(fc)
                num += 1

            fc_matrix = numpy.array(fcm)
            dp = DataPoint(fc_matrix, units="hartree/bohr^2")
            return dp
        except (OSError, IOError):
            raise InfoNotFoundError("force constants")

    def _check_convergence_CCSD(self):
        return True

    def _check_convergence_SCF(self):
        regexp = "SCF failed to convergence"
        failmatch = re.compile(regexp).search(self.fileText)

        regexp = "SCF has converged"
        convmatch = re.compile(regexp).search(self.fileText)

        if failmatch:
            return False
        elif convmatch:
            return True
        else: #there's no SCF here...
            raise InfoNotFoundError("scf convergence")

            
        

