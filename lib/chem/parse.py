## @package ParseOuput Handles the parsing out output files
## Encapsulates a generic parser object
from skynet.errors import *
from chem.basisset import *
from data import *
from skynet.utils.utils import *
import os, sys, re, pickle, commands, numpy


ENERGY_LIST = [ "ccsdt(q)", "ccsdt", "ccsd(t)", "ccsd", "mp2", "scf", "b3lyp", "mp2r12", "dcft" ]

def getBestEnergyType(available_energies):
    #start from the best energy, and work your way through
    #figuring out the best available one
    for energy in ENERGY_LIST:
        if energy in available_energies:
            return energy

class EnergyRegExp:
    
    attributes = {}

    def __init__(self):
        #certain reg expressions need to look through a set of reg expressions
        #in this case, it should start at 1 and continue
        self.number = 1

    def __iter__(self):
        return iter([self])
    
    def getAttributes(self):
        return self.attributes.copy()

    def getNextRegexpList(self):
        try:
            reListName = "re%d" % self.number
            reList = getattr(self, reListName)
            self.number += 1 #increment for the next call
            if isinstance(reList, str): 
                reList = [
                    [re.compile(reList), 'search', {}] #make it match the format... no attributes, no flags
                ]
            return reList[:]
        except AttributeError, error:
            return None #there are no more lists

class CompoundEnergyRegExp:

    def __iter__(self):
        return iter(self.reObjList)

class Parser(Item):

    def __init__(self, outputFileText, filepath, keywords = {}):
        self.fileText = outputFileText
        self.filepath = filepath
        #the parser can be "cast" to act in certain way
        self.keywords = {}
        #we don't want to rebuild a molecule object each time
        self.molecule = None
        self.values = {}

        for key in keywords:
            self.keywords[key.lower()] = keywords[key].lower()

        Item.__init__(self)

    def getKeyword(self, key):
        #try to find it in the dictionary
        try:    
            return self.keywords[key.lower()]
        #if not in the dictionary, go find it in the file text
        except KeyError:
            method = None
            #the parser may or may not be a wrapper, i.e. all calls to get the keyword
            #might have to go through parent level parser
            if hasattr(self, "get_keyword_%s" % key.upper()):
                method = getattr(self, "get_keyword_%s" % key.upper())
            else:
                method = getattr(self, "_get_keyword_%s" % key.upper())
            value = self.processValue(key, method())
            #store the value so we don't have to look it up again
            self.keywords[key.lower()] = value
            return value

    def get_keyword_BASIS(self):
        try:
            return self._get_keyword_BASIS()
        except InfoNotFoundError:
            pass

        regexp = r"\/([a-z\-]*[dtq5]z[a-z]*)[\/]?"
        basis = re.compile(regexp).search(self.filepath)
        if basis:
            basis = basis.groups()[0]
            return basis
        else:
            return "custom"

    def processValue(self, key, value):
        if key.lower() == "basis":
            return Basis(value)
        else:
            return canonicalize(value)
        
    ## Gets all the energies that can 
    def getAllEnergies(self):
        import focal
        allEnergies = focal.EnergyGroup()
        for energyType in ENERGY_LIST:
            try:
                e_list = self.getEnergy(energyType, returnAll = True)
                allEnergies.addData(e_list, wavefunction=energyType)
                if not energyType == 'scf':
                    ecorr = self.getCorrelationEnergy(energyType)
                    allEnergies.add(ecorr)
            except InfoNotFoundError, error:
                pass #not there, don't include it
        return allEnergies

    def getFrequencies(self):
        freqs = self._getHarmonicFrequencies()
        if not freqs:
            return []

        if freqs[0] < freqs[-1]: #we want to go high to low
            freqs.reverse()
        if not isinstance(freqs, DataPoint):
            freqs = DataPoint(freqs, units='wavenumber')
        return freqs

    def getFundamentals(self):
        freqs = self._getFundamentals()
        if freqs[0] < freqs[-1]: #we want to go high to low
            freqs.reverse()
        if not isinstance(freqs, DataPoint):
            freqs = DataPoint(freqs, units='wavenumber')
        return freqs

    def getIntensities(self):
        intens = self._getIntensities()
        freqs = self._getHarmonicFrequencies()

        if not freqs:
            return []

        if freqs[0] < freqs[-1]: #we want to go high to low
            intens.reverse()
        if not isinstance(intens, DataPoint):
            intens = DataPoint(intens, units='kmmol')
        return intens

    ## Determines what is the "best energy" calculated by the file.  If a wavefunction method, returns the type of wavefunction.
    ##  If a DFT job, returns the type of functional.
    #  @return A string describing the highest level used to calculate an energy
    def getBestEnergyType(self):
        bestEnergy = self.getKeyword("wavefunction")
        return bestEnergy

    def _getZMatrixXYZ(self, type):
        from geometry import getXYZFromZMatrix
        
        if type[:3] == 'opt':
            units = self._get_OPT_Units()
            [zmat, varList, constants] = self._getOptZMatrices()
            optxyz = []
            for variables in varList:
                atoms, geommatrix = getXYZFromZMatrix(zmat, variables, constants)
                xyz = DataPoint(geommatrix, units=units)
                optxyz.append(xyz)
                self._store(atoms, "%s atoms" % type)
            return optxyz
        else:
            units = self._getUnits("input")
            zmat, variables, constants = zmatrix = self._getInputZMatrix()
            atoms, xyz = getXYZFromZMatrix(zmat, variables, constants)
            xyz = DataPoint(xyz, units=units)
            self._store(atoms, "%s atoms" % type)
            return xyz

    def _get_OPTIMIZED_XYZ(self):
        return self._get_OPT_XYZ()

    def _get_OPTIMIZED_Units(self):
        return self._get_OPT_Units()

    def _getXYZ(self, type):
        methodname = "_get_%s_XYZ" % type.upper()
        if not hasattr(self, methodname):
            raise ProgrammingError("get %s xyz not yet implement for %s" % (type, self.__class__))
        method = getattr(self, methodname)
        returnval = method()
        atoms, xyzset = returnval
        finalxyz = None
        units = self._getUnits(type)
        if type[:3] == 'opt':
            finalxyz = []
            for xyz in xyzset:
                dp = DataPoint(xyz, units=units)
                finalxyz.append(dp)
        else:
            finalxyz = DataPoint(xyzset, units=units)
        self._store(atoms, "atoms")
        return finalxyz

    def _getUnits(self, type):
        methodname = "_get_%s_Units" % type.upper()
        if not hasattr(self, methodname):
            raise ProgrammingError("get %s units not yet implement for %s" % (type, self.__class__))
        method = getattr(self, methodname)
        units = method()
        return units


    def _store(self, value, name):
        self.values[name] = value

    def _fetch(self, name):
        try:
            return self.values[name]
        except KeyError:
            return None

    ## Returns the best geometry for the file. In the case single point, it just returns the xyz coordinates. 
    ## In the case of an optimization,it returns the geometry of the last step.
    ## @param xyzOnly In the case of a z-matrix file, it does not get the geometry from the z-matrix 
    ##               but instead gets it directly from xyz input
    def getXYZ(self, xyztype=None):
        jobType = self.getKeyword("jobtype")
        geomType = self.getKeyword("coordtype")

        #determine whether we are getting geometries from an optimization
        if not xyztype:
            if jobType == "optimization":
                xyztype = "optimized"
            else:
                xyztype = "initial"

        xyzset = None
        atoms = []
        if "matrix" in geomType: #z-matrix optimization
            xyzset = self._getZMatrixXYZ(xyztype)
        else:
            xyzset = self._getXYZ(xyztype)

        if not xyzset: #no xyz
            raise InfoNotFoundError("xyz")
        
        if xyztype == "optimized":
            return xyzset[-1]
        elif xyztype[:3] == "opt":
            return xyzset
        else:
            #this is not actually a list
            return xyzset

    def getAtoms(self, type = "input"):
        atoms = self._fetch("atoms")
        if not atoms:
            self.getXYZ(type)
        atoms = self._fetch("atoms")
        return atoms

    ## Gets the "best" molecule associated with the output file, and creates a computation for it.
    #  @param xyzOnly Even if the file was done with a z-matrix input, still collect it as xyz
    #               This is important for prgograms like ACES that orient the molecule
    #               You will want to collect the ACES orientation rather than the orientation
    #               generated by the Python Z-Matrix class
    def getComputation(self, weakFind=False):
        mol = self.getMolecule(weakFind)
        #check to make sure we were able to make a molecule
        if not mol:
            return None

        import input
        #build the keywords
        try: 
            keywords = self.getKeywords()
        except InfoNotFoundError, error:
            if not weakFind: 
                return None
            else:
                keywords = input.ATTRIBUTE_LIST.copy()

        ZMatrix=None
        if "matrix" in keywords["coordtype"]:
            import geometry
            units = keywords["units"]
            ZMatrix = self.getZMatrix()
            try: 
                [zmat, variables, constants] = ZMatrix
                ZMatrix = geometry.ZMatrix(atomList=mol.getAtoms(), units=units, ZMatrix=zmat, vars=variables, consts=constants)
            except (ValueError, TypeError): 
                pass #we already have the object
    
        program = input.getProgram(self.program)
        newComp = getComputationFromMolecule(mol, program=program, ZMatrix=ZMatrix, keywords=keywords, template=None)

        return newComp

    def getCorrelationEnergy(self, energyType):
        scf = self.getEnergy('scf')
        corr_points = self.getEnergy(energyType, returnAll = True)
        new_points = []
        for corr in corr_points:
            attrs = corr.getAttributes()
            newpoint = corr - scf
            #keep the attributes of the original correlated point
            newpoint.setAttributes(**attrs)
            newpoint.setAttribute('wavefunction', '%s correlation' % energyType)
            new_points.append(newpoint)
        return new_points

    def _recurseEnergyRegexps(reList, text, attributes, datapoints):
        if len(reList) == 0: #we've reached the end
            try:
                energy = eval(text)
            except Exception, error:
                sys.stderr.write("%s\n" % text)
                sys.exit()
            dp = DataPoint(energy, attributes=attributes)
            datapoints.append(dp)

        else:
            reobj, type, attrdict = reList[0]
            if isinstance(reobj, str):
                reobj = re.compile(reobj)

            #make sure the regular expression matched
            if not reobj:
                raise InfoNotFoundError("Energy for regexp %s" % regexp)

            #get the attributes associated with the given block of text
            for attrname in attrdict:
                attr_regexp = attrdict[attrname]
                if isinstance(attr_regexp, str):
                    attr_regexp = re.compile(attr_regexp)
                attr_val = attr_regexp.search(text).groups()[0]
                attributes[attrname] = attr_val
            
            if type == 'search':
                match = reobj.search(text)
                if not match:
                    raise InfoNotFoundError("energy regexp match")
                Parser._recurseEnergyRegexps(reList[1:], match.groups()[0], attributes, datapoints)
            elif type == 'findall':
                matches = reobj.findall(text)
                if not matches:
                    raise InfoNotFoundError("energy regexp match")
                for match in matches:
                    Parser._recurseEnergyRegexps(reList[1:], match, attributes.copy(), datapoints)
            else: #not a valid type
                raise ProgrammingError("%s is not a valid regular expression search directive" % type)
                    
    _recurseEnergyRegexps = staticmethod(_recurseEnergyRegexps)

    def _makeDataPoint(self, point, units='hartree', **kwargs):
        if not isinstance(point, DataPoint):
            point = DataPoint(point)

        self.assignAttributes(point)

        point.setUnits(units)
        for entry in kwargs:
            point.setAttribute(entry, kwargs[entry])

        return point

    def getGradients(self):
        #by default, not implemented
        raise InfoNotFoundError

    def getForceConstants(self):
        #by default, not implemented
        raise InfoNotFoundError

    def _fetchEnergy(self, type):
        attrname = "get_energy_%s" % type.upper().replace("(", "_").replace(")", "")
        energy = None
        try:
            method = getattr(self, attrname)
            return [ method() ]
        except AttributeError, error:
            pass

        if energy == None:
            attrname = "Singlepoint%s" % type.upper().replace("(", "_").replace(")", "")
            energyReObj = None
            try:
                energyReObj = getattr(self, attrname)
            except AttributeError:  
                raise InfoNotFoundError("%s energy.  Not supported for this program" % type)

        energies = []
        reInstance = energyReObj()
        for entry in reInstance:
            attrs = entry.getAttributes()
            reList = entry.getNextRegexpList()
            while reList:
                try:
                    Parser._recurseEnergyRegexps(reList, self.fileText, attrs, energies)
                    #if success, set reList to none
                    reList = None
                except InfoNotFoundError:
                    #hmm, that didn't seem to work
                    #maybe the regexp has a backup plan
                    reList = entry.getNextRegexpList()

        return energies

    
    def _checkConvergence(self, type):
        TYPES_TO_CHECK = {
            'ccsd(t)' : ['scf', 'ccsd'],
            'scf' : ['scf'],
            'mp2' : ['scf'],
            'dcft' : ['scf'],
            'mp2r12' : ['scf'],
            'ccsd' : ['scf', 'ccsd'],
            'ccsdt' : ['scf', 'ccsdt'],
            'ccsdt(q)' : ['scf', 'ccsdt'],
            'b3lyp' : ['b3lyp'],
        }

        checkList = TYPES_TO_CHECK[type.lower()]
        for check in checkList:
            methodName = "_check_convergence_%s" % check.upper()
            try:
                method = getattr(self, methodName)
                converged = method()
                if not converged:
                    raise ConvergenceError("%s convergence error on file %s" % (type, self.filepath))
            except AttributeError, error:
                raise InfoNotFoundError("%s convergence info error on file %s" % (check, self.filepath))

    ## Gets a specific energy from a file
    #  @param energyType A string specifying the energy type.  Allowed values are SCF, MP2, CCSD, CCSD(T), etc.
    #  @return The value of the energy in hartrees.  If energy is not found, returns None.
    #  @throws ConvergenceError If SCF, CCSD, or DFT is requested, but iterations did not converge, exception thrown.
    def getEnergy(self, energyType="best", returnAll = False):
        energyType = energyType.lower()

        #if we have generically been given 'best', determine the best energy type
        type = energyType
        if energyType == "best":
            type = self.getBestEnergyType().upper()

        #first things first! check convergence on the energy
        self._checkConvergence(type)

        #get the job type.  If we did an optimization, we have to fetch a lot of energies
        jobType = self.getKeyword("jobtype")
        energies = []
        if jobType[0:3] == "opt":
            energies = self._getOptEnergies()
        else:
            energies = self._fetchEnergy(type)

        if not energies: #no energies were found
            raise InfoNotFoundError("%s energy on file %s" % (type, self.filepath))
            
        #make sure that we are sending back data points
        func = lambda x: self._makeDataPoint(x, units='hartree')
        energies = map(func, energies)

        #if we only want the "best" value, not all possible values
        if energyType == "best" or not returnAll: 
            return energies[-1]
        else: #we want all possible energies
            return energies

    def assignAttributes(self, dp):
        keywords = self.getKeywords()
        for key in keywords:
            dp.setAttribute(key, keywords[key])

    def getFieldGradients(self):
        raise ProgrammingError("not yet implemented")

    ## Determines all the keywords used in the input file
    #  @param outputFile The text of the output file
    #  @return A dictionary of keywords and values
    def getKeywords(self):
        import input
        keywords = input.ATTRIBUTE_LIST.copy() #start from defaults
        for keyword in keywords:
            try: keywords[keyword] = self.getKeyword(keyword)
            except AttributeError, error: 
                pass #oops, not a real method
        return keywords

    ## Gets the "best" molecule associated with the output file.  If an optimization, a
    ## a molecule with the geometry of the last step. Otherwise, just the input geometry.
    def getMolecule(self, weakFind = False):
        #store the molecule so we don't have to do all the work over again
        if self.molecule: 
            return self.molecule

        from molecules import Molecule, Atom, getAtomListFromXYZ
        import globalvals
        
        try:
            xyz = self.getXYZ()
            atoms = self.getAtoms()
            atomList = getAtomListFromXYZ(atoms, xyz)
        except InfoNotFoundError, error:
            if globalvals.Debug.debug:
                sys.stderr.write("%s\n%s\n" % (traceback(error), error))
            return None #absolutely necessary

        charge = 0
        mult = 1
        stateSymm = 'a'
        title = 'default'
        energy = 0
        
        try: charge = self.get_keyword_CHARGE()
        except InfoNotFoundError, error: #depending on the 'strictness' we may return a none or just use a fill-in value
            if globalvals.Debug.debug:
                sys.stderr.write("%s\n%s\n" % (traceback(error), error))
            if not weakFind: 
                return None
        try: mult = self.get_keyword_MULTIPLICITY()
        except InfoNotFoundError, error: #depending on the 'strictness' we may return a none or just use a fill-in value
            if globalvals.Debug.debug:
                sys.stderr.write("%s\n%s\n" % (traceback(error), error))
            if not weakFind: 
                return None
        try: stateSymm = self.get_keyword_STATESYMMETRY()
        except InfoNotFoundError, error: #depending on the 'strictness' we may return a none or just use a fill-in value
            if globalvals.Debug.debug:
                sys.stderr.write("%s\n%s\n" % (traceback(error), error))
            if not weakFind: 
                return None
        try: title = self.get_keyword_TITLE()
        except InfoNotFoundError, error: #depending on the 'strictness' we may return a none or just use a fill-in value
            if globalvals.Debug.debug:
                sys.stderr.write("%s\n%s\n" % (traceback(error), error))
            if not weakFind: 
                return None
        try: energy = self.getEnergy()
        except InfoNotFoundError, error: #depending on the 'strictness' we may return a none or just use a fill-in value
            if globalvals.Debug.debug:
                sys.stderr.write("%s\n%s\n" % (traceback(error), error))
            if not weakFind: 
                return None

        mol = Molecule(atomList, charge, mult, stateSymm, title, energy, False, False)

        #optional things that may or may not be there
        try:
            grads = self.getGradients()
            mol.setGradients(grads)
        except (AttributeError, InfoNotFoundError), error: 
            pass
        try:
            fc = self.getForceConstants()
            mol.setForceConstants(fc)
        except (AttributeError, InfoNotFoundError): pass
        try:
            frequencies = self.getFrequencies()
            mol.setFrequencies(frequencies)
        except (AttributeError, InfoNotFoundError): pass
        try:
            intensities = self.getIntensities()
            mol.setIntensities(intensities)
        except (AttributeError, InfoNotFoundError): pass
        try:
            dipole = self.getDipole()
            mol.setDipole(dipole)
        except (AttributeError, InfoNotFoundError): pass
        
        return mol

    ## Gets a list of molecules associated with an optimization.
    def getOptMolecules(self):
        from molecule import Molecule, Atom, getAtomListFromXYZ
        molList = []
        allXYZ = self.getOptXYZ()
        units = self.getUnits()
        charge = self.get_keyword_CHARGE()
        mult = self.get_keyword_MULTIPLICITY()
        stateSymm = self.get_keyword_STATESYMMETRY()
        title = self.get_keyword_TITLE()

        for entry in allXYZ:
            atomList = getAtomListFromXYZ(entry)
            mol = Molecule(atomList, charge, mult, stateSymm, title, units, 0, False, False)
            molList.append(mol)

        return molList

    def getAtomList(self):
        xyz = self.getInitialXYZ()
        atomList = []
        for entry in xyz:
            atomList.append(entry[0])
        return atomList
    
    def getZMatrix(self, zmatType=-1):
        jobType = self.get_keyword_JOBTYPE()
        if jobType == "OPTIMIZATION":
            return self._getOptZMatrices()[-1]
        else:
            return self.getInputZMatrix()

    def storeXYZ(self, xyzType):
        try:
            typename = xyzType[0].upper() + xyzType[1:].lower()
            methodName = "_get%sXYZ" % typename
            method = getattr(self, methodName)
            atoms, xyz = method()
            methodName = "get%sUnits" % typename
            method = getattr(self, methodName)
            units = method()
            storedxyz = []
            self.setAttribute("%s atoms" % xyzType.lower(), atoms)
            if isinstance(xyz[0][0], list): #a set of xyz, as in an optimization
                for i in xrange(len(xyz)):
                    dp = DataPoint(numpy.array(xyz[i]), units=units)
                    storedxyz.append(dp)
            else:
                dp = DataPoint(numpy.array(xyz), units=units) #a single xyz
                storedxyz = dp
            self.setAttribute("%s xyz" % xyzType.lower(), storedxyz)
        except AttributeError, error:
            sys.stderr.write("%s\n%s\n" % (traceback(error), error))
            raise ProgrammingError("%s methodName not yet implemented for %s" % (methodName, self.__class__))
        except IndexError, error:
            raise InfoNotFoundError("xyz")

## Figures out the file format and sends back the appropriate parsing module
#  @param outputFile Either the path of the file to be parsed or the text of the outputFile
#  @return The parsing module appropriate to the file
def getParser(outputFile, keywords = {}):
    import Aces
    import Molpro
    import Gamess
    import Psi
    import QChem
    import MPQC
    import YETI
    import Gaussian
    import MRCC

    #determine which parser to use
    fileText = ""
    try:
        file = open(outputFile)
        fileText = file.read()
        file.close()
    except (IOError, OSError):
        return None
    
    molproCheck = re.compile("PROGRAM SYSTEM MOLPRO").search(fileText)
    mrccCheck = re.compile("Executing xmrcc").search(fileText)
    acesCheck = re.compile("ACES2: Advanced Concepts in Electronic Structure II").search(fileText)
    cfourCheck = re.compile("CFOUR Coupled-Cluster").search(fileText)
    gamessCheck = re.compile("EXECUTION OF GAMESS BEGUN").search(fileText)
    qchemCheck = re.compile("Q-Chem").search(fileText)
    psiCheck1 = re.compile("PSI3").search(fileText)
    psiCheck2 = re.compile("tstart called on").search(fileText)
    mpqcCheck = re.compile("MPQC: Massively Parallel Quantum Chemistry").search(fileText)
    yetiCheck = re.compile("Running YETI").search(fileText)
    gaussianCheck = re.compile("Entering Gaussian System").search(fileText)

    parser = None
    if mrccCheck:
        if molproCheck:
            parser = MRCC.MRCCMolproParser
        elif acesCheck:
            parser = MRCC.MRCCAcesParser
        else:
            parser = MRCC.MRCCParser
            
    elif molproCheck:
        parser = Molpro.MolproParser
    elif cfourCheck:
        parser = Aces.AcesParser
    elif acesCheck:
        parser = Aces.AcesParser
    elif gamessCheck:
        parser = Gamess.GamessParser
    elif psiCheck1 and psiCheck2:
        parser = Psi.PsiParser
    elif qchemCheck:
        parser = QChem.QChemParser
    elif mpqcCheck:
        parser = MPQC.MPQCParser
    elif gaussianCheck:
        parser = Gaussian.GaussianParser
    elif yetiCheck:
        parser = YETI.YETIParser
    else:
        return None #no parser
    
    return parser(fileText, outputFile, keywords)




