## @package MPQC
## Handles the parsing of MPQC output files

import commands
import sys
import os
import os.path
import re
from skynet.errors import *
from skynet.utils.utils import *
from chem.data import *
from chem.parse import *


class YETIParser(Parser):

    program = "YETI"

    OPT_E_REGEXPS = {
        "scf" : "total scf energy\s=\s(.*?)\n",
        "mp2" : "MP2 energy.*?:(.*?)\n",
    }

    class SinglepointSCF(EnergyRegExp):
        re1 = "[ROU]*HF energy.*?:\s+(.*?)\n"
        re2 = "Reference energy:(.*?)\n"
        re3 = "MolecularEnergy:(.*?)\n"

    def get_energy_DCFT(self):
        #egamma = re.compile(r"E.GAMMA.\s*[=]\s*([-]\d+[.]\d+)").search(self.fileText).groups()[0]
        #elambda = re.compile(r"E.LAMBDA.\s*[=]\s*([-]\d+[.]\d+)").search(self.fileText).groups()[0]
        #return eval(egamma) + eval(elambda)
        etot = re.compile(r"E.TOT.\s*[=]\s*([-]\d+[.]\d+)").search(self.fileText).groups()[0]
        return eval(etot)

    def getProgram(self):
        return "YETI"

    def getNumberOfBasisFunctions(self):
        regExp = "nbasis\s=\s(\d+)"
        num_basis = re.compile(regExp).findall(self.fileText)[-1]
        return eval(num_basis)

    def get_keyword_BASIS(self):
        try:
            basis = re.compile("Basis is(.*?)[.]").findall(self.fileText)[-1].upper().strip()
            return basis
        except (AttributeError, IndexError):
            raise InfoNotFoundError("BASIS SET")
        except KeyError:
            return "unknown"

    def get_keyword_CHARGE(self):
        try:
            charge = eval(re.compile("total charge = (.*?)\n").search(self.fileText).groups()[0].upper().strip())
            return charge
        except AttributeError:
            return 0 #default to zero
        
    def get_keyword_CORE(self):
        try:
            coreLine = re.compile("nvir\s+nfzc\s+nfzv\s*\n(.*?)\n").search(self.fileText).groups()[0].strip()
            numCore = eval(coreLine.split()[-2])
            if numCore == 0:
                return "CORRELATED"
            else:
                return "FROZEN"
        except AttributeError:
            return "CORRELATED" #if it can't be found, it must be zero

    def get_keyword_COORDTYPE(self):
        return "XYZ"

    def get_keyword_JOBTYPE(self):
        return "SINGLEPOINT"

    def get_keyword_MULTIPLICITY(self):
        try:
            multLine = re.compile("socc\s+=\s+\[(.*?)\]").search(self.fileText).groups()[0].strip()
            socc = map(eval, multLine.split())
            mult = 1
            for entry in socc:
                mult += entry
            return mult
        except AttributeError:
            return 1 #default to 1

    def get_keyword_POINTGROUP(self):
        pg = re.compile("symmetry = (.*?)\n").search(self.fileText).groups()[0].strip().upper()
        return pg

    def get_keyword_REFERENCE(self):
        reference = re.compile("([ROU]*HF) energy").search(self.fileText).groups()[0]
        return reference

    def get_keyword_STATESYMMETRY(self):
        return "A"

    def get_keyword_TITLE(self):
        return "NONE"

    def get_keyword_WAVEFUNCTION(self):
        wav = re.compile("Running\sYETI\s(.*?)\n").search(self.fileText).groups()[0]
        return wav.lower()

    def getNumAtoms(self):
        return len(self.getXYZ())

    def _get_INITIAL_Units(self):
        try:
            units = re.compile("unit = \"(.*?)\"").search(self.fileText).groups()[0].upper()
            return units
        except AttributeError:
            return "ANGSTROM" #default

    def _get_INPUT_Units(self):
        return self._get_INITIAL_Units()

    def _getOptEnergies(self):
        regexp = self.OPT_E_REGEXPS[self.getKeyword("wavefunction")]
        energyList = re.compile(regexp).findall(self.fileText)
        energies = map(eval, energyList)
        return energies       

    def _get_OPT_Units(self):
        return self._getUnits("initial")

    def _get_INPUT_XYZ(self):
        return self._get_INITIAL_XYZ()

    def _get_INITIAL_XYZ(self):
        try:
            coordinateLines = re.compile("{\s+n atoms\s+geometry\s+}={(.*?)}", re.DOTALL).search(self.fileText).groups()[0].upper().strip().splitlines()
            coordinates = []
            atoms = []
            for line in coordinateLines: 
                splitLine = line.replace("]", " ").strip().split()
                label = removeNumberSuffix(splitLine[1])
                xyz = map(eval, splitLine[3:])
                coordinates.append(xyz)
                atoms.append(label)
            return (atoms, coordinates)
        except AttributeError:
            raise InfoNotFoundError("XYZ")
        
    def _get_OPT_XYZ(self):
        coordinateSet = re.compile("{\s+n atoms\s+geometry\s+}={(.*?)}", re.DOTALL).findall(self.fileText)
        coordinates = []
        atoms = []
        for entry in coordinateSet:
            atoms = []
            coordinateLines = entry.replace("]","").replace("[","").strip().splitlines()
            coordinates.append([])
            for line in coordinateLines:
                splitLine = line.strip().split()
                label = removeNumberSuffix(splitLine[1])
                xyz = map(eval, splitLine[2:])
                coordinates[-1].append(xyz)
                atoms.append(label)

        return atoms, coordinates

    def _check_convergence_DCFT(self):
        return True

    def _check_convergence_SCF(self):
        return True

