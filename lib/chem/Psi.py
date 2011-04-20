import commands
import sys
import os
import os.path
import re
from skynet.errors import *
from skynet.utils.utils import *
from chem.data import *

from chem.parse import Parser, EnergyRegExp

class PsiParser(Parser):
    
    class SinglepointSCF(EnergyRegExp):
        re1 = "SCF total energy\s+=\s+(.*?)\n"

    class SinglepointCCSD(EnergyRegExp):
        re1 = "CCSD total energy\s+=\s+(.*?)\n"

    class SinglepointCCSD_T(EnergyRegExp):
        re1 = r"CCSD\(T\) total energy\s+=\s+(.*?)\n"


    program = "PSI"
    
    def getProgram(self):
        return "PSI"
    
    def checkOptimizationCompleted(self):
        check = commands.getoutput("grep 'MAX force' %s | grep 'Optimization is complete'" % self.fileText)
        if not check == "":
            return True
        else:
            return False

    def get_keyword_COORDTYPE(self):
        return "XYZ"

    def get_keyword_BASIS(self):
        firstAtom = re.compile( "Geometry before Center.*?\n\s+Center.*?\n.*?\n\s+([A-Z]+)").search( self.fileText ).groups()[0]
        basisArea = re.compile( r"Basis set on unique center 1(.*?)B[Aa][Ss][iI][sS]", re.DOTALL).findall(self.fileText)[0]
        newFunctions = re.compile( r"[SPDFGHIK]").findall(basisArea)        
        num_functions_on_first_atom = len(newFunctions)
        if firstAtom == "HYDROGEN":
            correspondence_list = {
                1 : "STO-3G",
                3 : "cc-pVDZ",
                5 : "aug-cc-pVDZ",
                6 : "cc-pVTZ",
                9 : "aug-cc-pVTZ",
                10 : "cc-pVQZ",
                11 : "aug-TZUC",
                14 : "aug-cc-pVQZ",
                15 : "cc-pV5Z",
                16 : "aug-QZUC",
                20 : "aug-cc-pV5Z",
                21 : "cc-pV6Z",
                23 : "aug-5ZUC",
                27 : "aug-cc-pV6Z",
                }
        elif firstAtom in ( "SULFUR", "CHLORINE"):
            correspondence_list = {
                5 : "STO-3G"
                }
            
        else:
            correspondence_list = {
                3 : "STO-3G",
                6 : "cc-pVDZ",
                9: "aug-cc-pVDZ",
                10 : "cc-pVTZ",
                14 : "aug-cc-pVTZ",
                15 : "cc-pVQZ",
                20 : "aug-cc-pVQZ",
                21 : "cc-pV5Z",
                27 : "aug-cc-pV5Z",
                28 : "cc-pV6Z",
                35 : "aug-cc-pV6Z",
                22 : "aug-TZUC",
                29 : "aug-QZUC",
                36 : "cc-pV7Z",
                38 : "aug-5ZUC",
                }

        try: return correspondence_list[num_functions_on_first_atom].upper()
        except KeyError: return "unknown"   

    def get_keyword_CHARGE(self):
        try:
            charge = re.compile("charge\s+=\s+(\d+)").search(self.fileText).groups()[0]
            return eval(charge)
        except AttributeError:
            raise InfoNotFoundError("Charge")

    def get_keyword_OCCUPATION(self):
        return None
        regExp = "determine occupations\s+Symmetry block:(.*?)\n(.*?)\n(.*?)\n"
        irreps, docc, socc = re.compile(regExp).search(self.fileText).groups()
        irreps = irreps.strip().split()
        docc = docc.strip().split()[1:] #throw away DOCC: at beginning
        socc = socc.strip().split()[1:] #throw away SOCC: at beginning
        occ = { "DOCC" : {}, "SOCC" : {} }
        for i in range(0, len(irreps)):
            irrep = irreps[i].upper() ; docc_i = docc[i] ; socc_i = socc[i]
            occ["DOCC"][irrep] = docc_i
            occ["SOCC"][irrep] = socc_i
        from input import Occupation
        pg = self.getKeyword("pointgroup")
        occ = Occupation(occ)
        return occ

    def getFrequencies(self):
        try:
            frequencies = []
            regExp = r"""Harmonic Vibrational Frequencies .*? OPTKING execution"""
            matchStr = re.compile(regExp, re.DOTALL)
            freqLines = matchStr.findall(self.fileText)[0].splitlines()[2:-3]
            for line in freqLines:
                freq = line.strip().split()[1]
                newFreq = 0
                if "i" in freq:
                    newFreq = -1 * eval(freq[:-1])
                else:
                    newFreq = eval(freq)

                if abs(newFreq) < 1E-4:
                    pass
                else:
                    frequencies.append(newFreq)
            return frequencies
        except (AttributeError, IndexError):
            raise InfoNotFoundError

    def getOptGradients(self):
        gradientSet = re.compile("MAX force:(.*?)RMS force:(.*?)\n").findall(self.fileText)
        gradients = []
        for line in gradientSet:
            gradients.append(map(eval, line))
        return gradients

    def get_keyword_CORE(self):
        regExp = "FZDC.*?\n\n"
        info_block = re.compile(regExp).search(self.fileText)
        if not info_block: return "CORRELATED" #there's no frozen core
        else: return "TRUE"

    def get_keyword_JOBTYPE(self):
        check = re.compile("disp_irrep").search(self.fileText)
        if check:
            return "OPTIMIZATION"
        else:
            return "SINGLEPOINT"

    def get_keyword_MULTIPLICITY(self):
        try:
            mult = re.compile("multiplicity\s=\s(\d)").search(self.fileText).groups()[0]
            return eval(mult)
        except AttributeError:
            raise InfoNotFoundError('multiplicity')

    def getNumAtoms(self):
        numAtoms = eval(re.compile("Number of atoms\s+=\s?(.*?)\n").search(self.fileText).groups()[0])
        return numAtoms

    def get_keyword_POINTGROUP(self):
        pg = re.compile("Computational point group is(.*?)\n").search(self.fileText).groups()[0].strip().upper()
        return pg

    def get_keyword_REFERENCE(self):
        ref = re.compile(r"reference\s+=\s*(.*?)\n").search(self.fileText).groups()[0].strip().upper()
        return ref

    def get_keyword_TITLE(self):
        title = re.compile("LABEL\s+=\s?(.*?)\n").search(self.fileText).groups()[0].strip().upper()
        return title

    def get_keyword_UNITS(self):
        return "BOHR"

    def _get_INPUT_Units(self):
        return "BOHR"

    def _get_INITIAL_Units(self):
        return "BOHR"

    def getUnits(self):
        return "BOHR"

    def get_keyword_STATESYMMETRY(self):
        return "APP"

    def get_keyword_WAVEFUNCTION(self):
        try:
            method = re.compile("wfn\s+=\s(.*?)\n").search(self.fileText).groups()[0]
            if method.lower() == "ccsd_t":
                return "ccsd(t)"
            return method
        except AttributeError:
            raise InfoNotFoundError("wavefunction")

    def getOptUnits(self):
        return "BOHR"

    def label__gt__(self, other):
        if self.i > other.i or (self.i == other.i and self.j > other.j):
            return True
        return True

    def label__eq__(self, other):
        if self.i == other.i and self.j == other.j:
            return True
            return False

    def getR12PairEnergies(self):
        import data_analysis
        pairList = {}
        finalList = []
        for pairType in ("Alpha - Alpha", "Beta - Beta", "Alpha - Beta"):
            pairArea = re.compile("%s Pair energies.*?=====\n(.*?)=====" % pairType, re.DOTALL).search(self.fileText).groups()[0]
            pairLines = re.compile("(\d+)\s+(\d+)\s+([\-]\d+[.]\d+)\s+([\-]\d+[.]\d+)").findall(pairArea)
            for entry in pairLines:
                (i, j, mp2part, r12part) = map(eval, entry)
                if i <= j: #only include unique pairs
                    label = "%d-%d" % (i, j)
                    if label in pairList: pairList[label] += r12part #increment, if already exists
                    else: pairList[label] = r12part #create, if doesn't exist                    
        for label in pairList:
            finalList.append( data_analysis.DataPoint(pairList[label], label, "Pair Label", "Pair Energy") )

        return finalList

    def _get_INPUT_XYZ(self):
        import molecules
        geomArea = re.compile("Geometry before Center-of-Mass.*?Center.*?Z(.*?)SYMMETRY", re.DOTALL).search(self.fileText).groups()[0]
        geomLines = re.compile(r"([A-Z]+)\s+([-]?\d+[.]\d+)\s+([-]?\d+[.]\d+)\s+([-]?\d+[.]\d+)").findall(geomArea)
        coordinates = []
        atoms = []
        for line in geomLines:
            name = line[0]
            label = molecules.getAtomFromInfo("name", name)
            if not label:
                label = name
            xyz = map(eval, line[1:])
            coordinates.append(xyz)
            atoms.append(label)

        return atoms, coordinates        

    def _get_INITIAL_XYZ(self):
        import molecules
        geomArea = re.compile("Geometry after Center-of-Mass.*?Z(.*?)SYMMETRY", re.DOTALL).search(self.fileText).groups()[0]
        geomLines = re.compile(r"([A-Z]+)\s+([-]?\d+[.]\d+)\s+([-]?\d+[.]\d+)\s+([-]?\d+[.]\d+)").findall(geomArea)
        coordinates = []
        atoms = []
        for line in geomLines:
            name = line[0]
            label = molecules.getAtomFromInfo("name", name)
            if not label: #depending on the version of psi, this might be the name or atomic symbol
                label = name
            xyz = map(eval, line[1:])
            coordinates.append(xyz)
            atoms.append(label)

        return atoms, coordinates        

    def _getOptXYZ(self):
        import molecules
        numAtoms = self.getNumAtoms()
        regExp = "--disp_irrep --irrep.*?Cartesian geometry and possibly gradient in a.u. with masses(.*?)[GS]"
        geomSet = re.compile(regExp, re.DOTALL).findall(self.fileText)
        coordinates = []
        atoms = []
        for entry in geomSet:
            geomLines = entry.strip().splitlines()
            atoms = []
            coordinates.append([])
            for line in geomLines:
                splitLine = line.strip().split()
                if len(splitLine) > 3: #this is a geometry line
                    charge = eval(splitLine[0])
                    label = molecules.getAtomFromInfo("charge", charge)
                    xyz = map(eval, splitLine[2:])
                    coordinates[-1].append(xyz)
                    atoms.append(label)

        return atoms, coordinates

    ### Auxilliary Methods ###

    def getSingleSCFEnergy(self):
        self.checkSingleSCFConvergence()
        energy = re.compile( r"SCF total energy\s+=\s+(.*?)\n").search(self.fileText).groups()[0]
        return eval(energy)

    def _check_convergence_SCF(self):
        regExp = "Calculation has not converged"
        convCheck = re.compile(regExp).search(self.fileText)
        if convCheck: #did not converge
            return False
        return True

    def _check_convergence_CCSD(self):
        regExp = "Iterations converged"
        convCheck = re.compile(regExp).search(self.fileText)
        regExp = "Iterations failed to converge"
        failCheck = re.compile(regExp).search(self.fileText)
        if convCheck: #did converge
            return True
        if failCheck:
            return False

        raise InfoNotFoundError("CCSD convergence")

    def getSingleMP2Energy(self):
        if self.get_keyword_REFERENCE() == "ROHF":
            return self.getSingleZAPT2Energy()
        else:
            try:
                energy = re.compile( r"Total MBPT.*?Energy\s+=\s+(.*?)\n").search(self.fileText).groups()[0]
                return eval(energy)
            except AttributeError:
                pass #try a new one 
            try:
                energy = re.compile( r"MBPT\(2\) Energy\s+=\s+(.*?)\n").search(self.fileText).groups()[0]
                return eval(energy)
            except AttributeError:
                pass #try a new one
            try: 
                energy = re.compile( r"MP2 total energy\s+=\s+(.*?)\n" ).search(self.fileText).groups()[0] 
                return eval(energy)
            except AttributeError:
                raise InfoNotFoundError

    def getCorrelationEnergyZAPT2(self):
       try: 
           energy = re.compile( r"ZAPT2 Correlation Energy\s+=\s+(.*?)\n" ).search(self.fileText).groups()[0] 
           return eval(energy)
       except AttributeError:
           raise InfoNotFoundError
        

    def getCorrelationEnergyMP2(self):
        if self.get_keyword_REFERENCE() == "ROHF":
            return self.getCorrelationEnergyZAPT2()
        else:
            try: 
                energy = re.compile( r"MP2 correlation energy\s+=\s+(.*?)\n" ).search(self.fileText).groups()[0] 
                return eval(energy)
            except AttributeError:
                raise InfoNotFoundError
            


    def getSingleMP2R12Energy(self):
        if self.get_keyword_REFERENCE() == "ROHF":
            return self.getSingleZAPT2R12Energy()
        else:
            regExp = r"MBPT\(2\)[-]R12/A Energy.*?\s+Total Energy\s+=\s+(.*?)\n"
            energy = re.compile(regExp).search(self.fileText).groups()[0]
            return eval(energy)

    def getSingleZAPT2Energy(self):
        try:
            energy = re.compile( r"Final ZAPT2 energy\s+=\s(.*?)\n").search(self.fileText).groups()[0]
            return eval(energy)
        except AttributeError:
            raise InfoNotFoundError

    def getSingleZAPT2R12Energy(self):
       regExp = "R12 Energy.*?\nTotal Correlation Energy.*?\nTotal Energy\s+=\s+(.*?)\n"  
       energy = re.compile(regExp).search(self.fileText).groups()[0]
       return eval(energy)

    def getOptEnergies(self):
        energyFile = "psi.file11.dat"
        numAtoms = self.getNumAtoms()
        energyLines = commands.getoutput("cat %s" % energyFile)
        energyLinesArray = energyLines.splitlines()
        energies = []
        lineNumber = 1
        for line in energyLinesArray:
            if (lineNumber - 2) % (2 * numAtoms + 2) == 0:
                energy = eval(line.strip().split()[1])
                energies.append(energy)
            lineNumber += 1

        return energies


    def getAllOrbitals(self):
        return self.getOrbitals(self.fileText)

    def getOrbitals(self, text):
        regExp = r"(\d{1,3})([AB][p123]?[gup]?)\s+([\-]?\d+[.]\d+)"        
        rawList = re.compile(regExp).findall(text)
        finalList = []
        for orbital in rawList:
            (number, irrep, energy) = orbital
            number = eval(number)
            energy = eval(energy)
            irrep = irrep.upper()
            finalList.append( (number, irrep, energy) )
        return finalList
            

    def getDOCCOrbitals(self):
        regExp = "Doubly occupied orbitals(.*?)(Singly occupied orbitals|Unoccupied orbitals)"
        doccText = re.compile(regExp, re.DOTALL).search(self.fileText).groups()[0]
        return self.getOrbitals(doccText)

    def getSOCCOrbitals(self):
        try:
            regExp = "Singly occupied orbitals(.*?)Unoccupied orbitals"
            soccText = re.compile(regExp, re.DOTALL).search(self.fileText).groups()[0]
            return self.getOrbitals(soccText)
        except AttributeError:
            return () #no socc orbitals

    def getUOCCOrbitals(self):
        regExp = "Unoccupied orbitals(.*?)SCF total"
        uoccText = re.compile(regExp, re.DOTALL).search(self.fileText).groups()[0]
        return self.getOrbitals(uoccText)
