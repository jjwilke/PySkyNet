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


class MPQCParser(Parser):

    program = "MPQC"

    OPT_E_REGEXPS = {
        "scf" : "total scf energy\s=\s(.*?)\n",
        "mp2" : "MP2 energy.*?:(.*?)\n",
    }

    class SinglepointSCF(EnergyRegExp):

        re1 = "[ROU]*HF energy.*?:\s+(.*?)\n"
        re2 = "Reference energy:(.*?)\n"
        re3 = "MolecularEnergy:(.*?)\n"

    class SinglepointMP2(EnergyRegExp):

        re1 = "[ZM][A]?P[T]?2 energy.*?:(.*?)\n"
        re2 = "Total ZAPT2 energy:\s*([-]?\d+[.]\d+)\n"
        re3 = ("Total ZAPT2 correlation energy:\s+([-]?\d+[.]\d+)\n"
               "Total energy:\s+([-]?\d+[.]\d+)\n")

    class SinglepointMP2R12(EnergyRegExp):
        re1 = [
            #the first regular expression gets the individual sections
            [re.compile("MP2[-]R12\s.*?\sPair[/]Amplitudes\s.*?[/]Approximation\s.*?\n.*?Total energy:.*?\n", re.DOTALL), #regexp
             'findall', #get all matches
             {}, #no attributes, et
            ],
            #now that we have all of the sections, get the attributes and value
            #the first regular expression gets the individual sections
            ["Total energy:(.*?)\n", #regexp
             'search', #no need to get all matches here
             {
                'r12 pair type' : 'MP2[-]R12\s(.*?)\sPair',
                'amplitude method' : 'Amplitudes\s(.*?)[/]A',
                'approximation' : 'Approximation\s(.*?)\n',
             }, 
            ],
        ]
        re2 = "MBPT2-F12/\s*[ABC][']?\s*energy\s*\[au\]:\s+([-]?\d+[.]\d+)" 

    def getProgram(self):
        return "MPQC"

    def getOptGradients(self):
        gradientSet = re.compile("MAXIMUM GRADIENT = (.*?)[\n\s]+RMS GRADIENT = (.*?)\n").findall(self.fileText)
        gradients = []
        for entry in gradientSet:
            gradients.append(map(eval, entry))
        return gradients

    def getNumberOfBasisFunctions(self):
        regExp = "nbasis\s=\s(\d+)"
        num_basis = re.compile(regExp).findall(self.fileText)[-1]
        return eval(num_basis)

    def get_keyword_BASIS(self):
        try:
            basis = re.compile("Basis is(.*?)[.]").findall(self.fileText)[-1].upper().strip()
            if basis == "CUSTOM":
                basisSize = re.compile(r"n\(basis\):\s+(\d+)\n").search(self.fileText).groups()[0].upper().strip()
                BASIS_CONVERSIONS = {
                    "1458" : "aug-cc-pV5Z",
                    "891" : "aug-cc-pVQZ",
                    "891" : "aug-cc-pVQZ",
                    "492" : "aug-cc-pVTZ",
                    "233" : "aug-cc-pVDZ",
                    }
                basisName = BASIS_CONVERSIONS[basisSize]
                return basisName

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
        checkOpt = re.compile("MPQC options:.*?optimize\s+=\s+(.*?)\n", re.DOTALL).search(self.fileText)
        if checkOpt: #there was a hit
            yesOrNo = checkOpt.groups()[0]
            if yesOrNo == "yes":
                return "OPTIMIZATION"

        #nothing special
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
        wavlist = [
            ['mp2r12', "MBPT2_R12"],
            ['mp2r12', "R12 correlation"],
            ['mp2', "MBPT2"],
            ['mp2', "ZAPT2"],
            ['scf', "CLHF"],
            ['scf', "CLSCF"],
            ['scf', "HSOSHF"],
            ['scf', "HSOSSCF"],
            ['scf', "UnrestrictedHF"],
        ]
        reiter = iter(wavlist)
        try:
            while 1:
                wav, regexp = reiter.next()
                if re.compile(regexp).search(self.fileText):
                    return wav
        except StopIteration:
            raise InfoNotFoundError("wavefunction")

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

    def _check_convergence_SCF(self):
        return True

