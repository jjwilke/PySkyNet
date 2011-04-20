## @package Gamess
## Handles the parsing of Gamess output files

import commands
import sys
import os
import os.path
import re
from skynet.errors import *
from skynet.utils.utils import *
from chem.data import *

from parse import Parser, EnergyRegExp

class GaussianParser(Parser):
    ALLOWED_ENERGIES = ["SCF", "MP2", "B3LYP", "BEST"]
    program = "GAUSSIAN"

    class SinglepointB3LYP(EnergyRegExp):
        re1 = "B\+HF\-LYP\)\s+=\s+([-]\d+[.]\d+)"

    def getOptGradients(self):
        gradientSet = re.compile("MAXIMUM GRADIENT = (.*?)[\n\s]+RMS GRADIENT = (.*?)\n").findall(self.fileText)
        gradients = []
        for entry in gradientSet:
            gradients.append(map(eval, entry))
        return gradients

    def _getFundamentals(self):
        try:
            regexp = "Fundamental Bands(.*?)Overtone"
            anhmatch = re.compile(regexp, re.DOTALL)
            groups = anhmatch.search(self.fileText)
            anhtext = groups.groups()[0]
            funds = []
            for line in anhtext.splitlines()[1:-1]:
                fund = line.strip().split()[2]
                funds.append(eval(fund))
            return funds
        except (AttributeError, IndexError):
            raise InfoNotFoundError("Anharmonic fundamentals")

    def get_keyword_BASIS(self):
        try:
            titleLine = self.getTitleLine()
            regExp = "[/]([a-zA-Z\d+*\-]+)[\s\n]?"
            basis = re.compile(regExp).search(titleLine).groups()[0].upper().strip()
            return basis
        except (AttributeError, IndexError):
            raise InfoNotFoundError("BASIS SET")

    def get_keyword_CHARGE(self):
        try:
            regExp = "Charge =\s?([-]?\d)"
            charge = re.compile(regExp).search(self.fileText).groups()[0]
            return eval(charge)
        except AttributeError:
            return 0 #default to zero
        
    def get_keyword_CORE(self):
        try:
            coreLine = re.compile("INPUT CARD>.*?NACORE").search(self.fileText)
            if coreLine:
                return "CORRELATED"
            else:
                return "FROZEN"
        except AttributeError:
            raise InfoNotFoundError("CORE")

    def get_keyword_COORDTYPE(self):
        try:
            regExp = "Symbolic Z-matrix:\n.*?\n(.*?)\n"
            firstGeomLine = re.compile(regExp).search(self.fileText).groups()[0]
            numEntriesOnLine = len( firstGeomLine.strip().split() )
            if numEntriesOnLine == 4: return "XYZ"
            else: return "Z-MATRIX"
        except (AttributeError, IndexError):
            raise InfoNotFoundError("GEOMETRY TYPE")

    def get_keyword_JOBTYPE(self):
        titleLine = self.getTitleLine()
        if "OPT" in titleLine:
            return "OPTIMIZATION"
        else:
            return "SINGLEPOINT"

    def get_keyword_MULTIPLICITY(self):
        try:
            mult = eval(re.compile("Multiplicity =\s?(\d)").search(self.fileText).groups()[0])
            return mult
        except AttributeError:
            return 1 #default to 1

    def get_keyword_POINTGROUP(self):
        pg = re.compile("THE POINT GROUP.*?MOLECULE IS (.*?)\n").search(self.fileText).groups()[0]
        axis = re.compile("ORDER OF THE PRINCIPAL AXIS IS\s+(.*?)\n").search(self.fileText).groups()[0]
        pointGroup = pg.replace("N", axis) 
        return pointGroup

    def get_keyword_REFERENCE(self):
        reference = re.compile("INPUT CARD>.*?SCFTYP=(.*?)[\s\n]").search(self.fileText).groups()[0]
        return reference

    def _getHarmonicFrequencies(self):
        freqLines = re.compile(r"Frequencies \-\-(.*?)\n").findall(self.fileText)

        if len(freqLines) == 0: #none found
            raise InfoNotFoundError
            
        frequencies = []
        for line in freqLines:
            freqs = line.strip().split()
            for freq in freqs:
                frequencies.append(eval(freq))
        return frequencies
        
    def get_keyword_STATESYMMETRY(self):
        return "A"

    def get_keyword_TITLE(self):
        try:
            regExp = r"[-]+\n(.*?)\n\s[-]+\n\sSymbol"
            title = re.compile(regExp).search(self.fileText).groups()[0].strip().upper()
            return title
        except AttributeError:
            raise InfoNotFoundError("TITLE")

    def get_keyword_WAVEFUNCTION(self):
        titleLine = self.getTitleLine()
        if "MP2" in titleLine:
            return "MP2"
        elif "HF" in titleLine:
            return "SCF"
        elif "B3LYP" in titleLine:
            return "B3LYP"

    def getNumAtoms(self):
        return len(self.getXYZ())

    def _get_INPUT_Units(self):
        titleLine = self.getTitleLine()
        if "UNITS" in titleLine and "BOHR" in titleLine:
            return "BOHR"
        else:
            return "ANGSTROM"

    def _get_INITIAL_Units(self):
        #the individual geometries are always displayed in angtroms
        return "ANGSTROM"

    def getOptUnits(self):
        #the individual geometries are always displayed in angtroms
        return "ANGSTROM"

    def _get_INPUT_XYZ(self):
        return self._get_INITIAL_XYZ()
        
    def _get_INITIAL_XYZ(self):
        coordinateLines = re.compile("Standard orientation.*?X.*?Z(.*?)Rotational constants", re.DOTALL).search(self.fileText).groups()[0].strip().splitlines()[1:-1]
        geom = []
        atoms = []
        for line in coordinateLines:
            values = map(eval, line.strip().split())
            atomicNumber = values[1]
            xyz = values[-3:]
            from Molecules import getAtomFromInfo
            atomName = getAtomFromInfo("ATOMIC NUMBER", atomicNumber)
            geom.append(xyz)
            atoms.append(atomName)
        return atoms, geom

    def _get_OPT_XYZ(self):
        coordinateLines = re.compile("Standard orientation.*?X.*?Z(.*?)Rotational constants", re.DOTALL).findall(self.fileText)
        allCoordinates = []
        for entry in coordinateLines:
            allCoordinates.append([])
            xyzArray = entry.splitlines()[2:-2]
            for line in xyzArray:
                [number, atomicNumber, x, y, z] = map(eval, line.strip().split())
                from Molecules import getAtomFromInfo
                atomName = getAtomFromInfo("ATOMIC NUMBER", atomicNumber)
                allCoordinates[-1].append([atomName, x, y, z])

        return allCoordinates
    
    def _check_convergence_SCF(self):
        return True

    def _check_convergence_B3LYP(self):
        return True

    ### Auxilliary Methods ###
    def getTitleLine(self, verbatim=False):
        titleLine = re.compile("Gaussian \d+:.*?#(.*?)\n", re.DOTALL).search(self.fileText).groups()[0].strip()
        if verbatim: return titleLine
        else: return titleLine.upper()

    def _getOptEnergies(self):
        rep = lambda x: x.replace("D", "E")
        wfn = self.get_keyword_WAVEFUNCTION()
        energies = []
        if wfn == "MP2":
            energies = map(eval, map(rep, re.compile("E[U]?MP2\s*=\s*(\-\d+[.]\d+.*?)\n").findall(self.fileText) ) )
        elif wfn == "SCF":
            energies = map(eval, re.compile(r"\s+=\s+(.*?)A[.]U[.]").findall(self.fileText))
        return energies
