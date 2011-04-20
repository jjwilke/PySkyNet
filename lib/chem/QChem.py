## @package QChem
#  A script called by other modules to process QChem files. The
#  documented methods are those specific to QChem and are not part of the
#  generic parser interface.
import commands
import os 
import os.path 
import re 
import numpy 
import sys
from skynet.errors import *
from skynet.utils.utils import *
from chem.data import *

from parse import Parser, EnergyRegExp
class QChemParser(Parser):
    ALLOWED_ENERGIES = ["DFT", "MP2", "B3LYP", "SCF"]
    
    class SinglepointB3LYP(EnergyRegExp):
        re1 = "([-]?\d+[.]\d+).*?Convergence"

    program = "QCHEM"

    def getUnits(self):
        regExp = r"Standard Nuclear Orientation\s+\(([a-zA-Z]+)\)"
        matchStr = re.compile(regExp, re.DOTALL)
        units = matchStr.search(self.fileText).groups()[0]
        if units == "Angstroms": return "ANGSTROM"
        else: return "BOHR"

    def _get_INPUT_Units(self):
        return "angstrom" #I don't know how to do bohr

    def _get_INITIAL_Units(self):
        return "angstrom"

    def _get_INITIAL_XYZ(self):
        return self._get_INPUT_XYZ()
        raise ProgrammingError("_getInitialXYZ not yet implemented")
        geomregexp = "[$]end(.*?)Mol"
        geomsection = re.compile(geomregexp, re.DOTALL | re.IGNORECASE).findall(self.fileText)[-1]
        print geomsection
        sys.exit()
        molArea = self.getMoleculeSection()
        print molArea
        return self._getInitialXYZ()

    def _get_INPUT_XYZ(self):
        molArea = self.getMoleculeSection()
        regExp = r"([a-zA-Z]+)\s+([-]?\d+[.]\d+)\s+([-]?\d+[.]\d+)\s+([-]?\d+[.]\d+)"
        xyzMatches = re.compile(regExp).findall(molArea)
        atoms = []
        xyz = []
        for match in xyzMatches:
            symbol, x, y, z = match
            atomxyz = map(eval, (x, y, z))
            xyz.append(atomxyz)
            atoms.append(symbol)
        return atoms, xyz

    def _get_OPT_XYZ(self):
        regexp = "Optimization Cycle:.*?Coordinates(.*?)Point Group" 
        geoms = re.compile(regexp, re.DOTALL).findall(self.fileText)
        all_geoms = []
        atoms = []
        xyz_regexp = "\d+\s+([a-zA-Z]+)\s+([-]?\d+[.]\d+)\s+([-]?\d+[.]\d+)\s+([-]?\d+[.]\d+)"
        xyz_re = re.compile(xyz_regexp)
        for geomtext in geoms:
            current_geom = []
            atoms = []
            xyzlines = xyz_re.findall(geomtext)
            for line in xyzlines:
                symbol = line[0]
                xyz = map(eval, line[1:])
                current_geom.append(xyz)
                atoms.append(symbol)
            all_geoms.append(current_geom)
        return atoms, all_geoms

    def _get_OPT_Units(self):
        return self.getUnits()

    def _getOptEnergies(self):
        regexp = 'Energy is\s+([-]?\d+[.]\d+)'
        energies = map(eval, re.compile(regexp).findall(self.fileText))
        return energies

    def get_keyword_REFERENCE(self):
        remSection = self.getRemSection()
        unr = re.compile("unrestricted\s+([a-zA-Z\d]+)", re.IGNORECASE).search(remSection).groups()[0].upper()
        if unr == "TRUE":
            return "UHF"
        else:
            mult = self.get_keyword_MULTIPLICITY()
            if mult == 1:
                return "RHF"
            else:
                return "ROHF"
        

    def get_keyword_CHARGE(self):
        try:
            molArea = self.getMoleculeSection()
            #the top line contains the charge and multiplicity
            topLine = molArea.splitlines()[0].strip()
            charge = eval(topLine.split()[0])
            return charge
        except:
            raise InfoNotFoundError("charge")

    def get_keyword_MULTIPLICITY(self):
        molArea = self.getMoleculeSection()
        #the top line contains the charge and multiplicity
        topLine = molArea.splitlines()[0].strip()
        mult = eval(topLine.split()[1])
        return mult

    def get_keyword_WAVEFUNCTION(self):
        remSection = self.getRemSection()
        #get the exchange keyword... this should always be specified
        exch = re.compile("exchange\s+([a-zA-Z\d]+)", re.IGNORECASE).search(remSection).groups()[0].upper()
        #attempt to get the correlation keyword
        corrMatch = re.compile("correlation\s+([a-zA-Z\d]+)", re.IGNORECASE).search(remSection)
        if corrMatch:
            corr = corrMatch.groups()[0].upper()
            if exch == "HF": #don't include in the wf return
                return corr
            else: #must be dft.. in which case you should return the combination of exch and corr
                return exch + corr
        else: #just return the exchange thing
            return exch

    def get_keyword_TITLE(self):
        regExp = r"\$comment(.*?)\$end"
        matchStr = re.compile(regExp, re.DOTALL | re.IGNORECASE)
        titleArea = matchStr.search(self.fileText).groups()[0].strip()
        return titleArea

    def get_keyword_COORDTYPE(self):
        return "XYZ"

    def get_keyword_STATESYMMETRY(self):
        return "A"

    def get_keyword_JOBTYPE(self):
        try:
            jobType = re.compile("jobtyp[e]?[=\s]+([a-zA-Z]+)", re.IGNORECASE).findall(self.fileText)[-1].upper();
            if   jobType == "SP": return "SINGLEPOINT"
            elif jobType == "OPT": return "OPTIMIZATION"
            elif jobType == "FREQ": return "FREQUENCY"
        except (IndexError):
            raise InfoNotFoundError('jobtype')

    def getNumAtoms(self):
        molArea = self.getMoleculeSection()
        numAtoms = len(molArea.splitlines()) - 1 #the minus one is because of the charge and mult line
        return numAtoms

    def getRemSection(self):
        regExp = r"\$rem(.*?)\$end"
        matchStr = re.compile(regExp, re.DOTALL | re.IGNORECASE)
        molArea = matchStr.findall(self.fileText)[-1].strip()
        return molArea

    def getMoleculeSection(self):
        regExp = r"\$molecule(.*?)\$end"
        matchStr = re.compile(regExp, re.DOTALL | re.IGNORECASE)
        #usually this would be a search, but because in qchem it's very common to converge the 
        #double cation and then run the actualy computation, so grab the last molecule section
        molArea = matchStr.findall(self.fileText)[-1].strip()
        return molArea
    
    def getNumberOfInputs(self):
        try:
            regexp = 'User input:'
            match = re.compile(regexp).findall(self.fileText)
            return len(match)
        except Exception, error:
            raise InfoNotFoundError("Number of user inputs")

    def _getHarmonicFrequencies(self):
        try:
            freqlines = re.compile("Frequency:(.*?)\n").findall(self.fileText)
            frequencies = []
            for line in freqlines:
                freqlist = re.compile("(\d+[.]\d+[i]?)").findall(line)
                for freq in freqlist:
                    if 'i' in freq:
                        frequencies.append(-1 * eval(freq[:-1]))
                    else:
                        frequencies.append(eval(freq))
            return frequencies
        except (IndexError):
            raise InfoNotFoundError("Frequencies")

    def _getIntensities(self):   
        try:
            freqlines = re.compile("IR Intens:(.*?)\n").findall(self.fileText)
            intensities = []
            for line in freqlines:
                freqlist = map(eval, re.compile("(\d+[.]\d+[i]?)").findall(line))
                intensities.extend(freqlist)
            return intensities
        except (IndexError):
            raise InfoNotFoundError("Intensities")

    def _check_convergence_B3LYP(self):
        try:
            regexp = "Convergence criterion met"
            match = re.compile(regexp).findall(self.fileText)
            if match:
                return True
            else:
                return False
        except Exception:
            return False

    def getDipole(self):
        try:
            regexp = r"Dipole Moment \(Debye\)\n(.*?)\n"
            dipoletext = re.compile(regexp).findall(self.fileText)[-1]
            dipole_xyz = map(eval, re.compile("([-]?\d+[.]\d+)").findall(dipoletext))
            return numpy.array(dipole_xyz)
        except (IndexError):
            raise InfoNotFoundError('dipole')
        


