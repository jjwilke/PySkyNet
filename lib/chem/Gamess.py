## @package Gamess
## Handles the parsing of Gamess output files

import string
import commands
import sys
import os
import os.path
import re
from skynet.errors import *
from skynet.utils.utils import *
from chem.data import *

from parse import Parser
class GamessParser(Parser):
    ALLOWED_ENERGIES = ["SCF", "MP2"]
    program = "GAMESS"

    def getOptGradients(self):
        gradientSet = re.compile("MAXIMUM GRADIENT = (.*?)[\n\s]+RMS GRADIENT = (.*?)\n").findall(self.fileText)
        gradients = []
        for entry in gradientSet:
            gradients.append(map(eval, entry))
        return gradients

    def get_keyword_BASIS(self):
        try:
            basis = re.compile("INPUT CARD>.*?GBASIS=(.*?)[\s\n]").search(self.fileText).groups()[0].upper().strip()
            from GamessWriter import BASIS_CONVERSIONS
            for entry in BASIS_CONVERSIONS:
                if BASIS_CONVERSIONS[entry] == basis:
                    return entry
        except AttributeError:
            raise InfoNotFoundError("BASIS SET")

    def get_keyword_CHARGE(self):
        try:
            charge = eval(re.compile("INPUT CARD>.*?ICHARG=(.*?)[\s\n]").search(self.fileText).groups()[0].upper().strip())
            return charge
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
        geomType = re.compile("INPUT CARD>.*?COORD=(.*?)[\n\s]").search(self.fileText).groups()[0].strip()
        if geomType == "CART":
            return "XYZ"
        else:
            return "ZMATRIX"

    def get_keyword_JOBTYPE(self):
        job = re.compile("INPUT CARD>.*?RUNTYP=(.*?)[\n\s]").search(self.fileText).groups()[0].strip()
        if job == "HESSIAN":
            return "FREQUENCY"
        elif job == "OPTIMIZE":
            return "OPTIMIZATION"
        else:
            return "SINGLEPOINT"

    def get_keyword_MULTIPLICITY(self):
        try:
            mult = eval(re.compile("INPUT CARD>.*?MULT=(.*?)[\s\n]").search(self.fileText).groups()[0])
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

    def get_keyword_STATESYMMETRY(self):
        return "A"

    def get_keyword_TITLE(self):
        title = re.compile("RUN TITLE\n.*?\n(.*?)\n").search(self.fileText).groups()[0].strip()
        return title

    def get_keyword_WAVEFUNCTION(self):
        mp = self.getMPLevel()
        if mp > 0:
            return ("MP" + repr(mp))
        else:
            return "SCF"

    def getNumAtoms(self):
        return len(self.getXYZ())

    def getInitialUnits(self):
        units = re.compile("ATOM.*?ATOMIC.*?COORDINATES \((.*?)\)").search(self.fileText).groups()[0]
        if units == "ANGS":
            return "ANGSTROM"
        else:
            return "BOHR"

    def getInputUnits(self):
       units = re.compile("UNITS =(.*?)\s").search(self.fileText).groups()[0]
       if units == "ANGS": return "ANGSTROM"
       else: return "BOHR"

    def getOptUnits(self):
        units = re.compile("COORDINATES OF ALL ATOMS ARE \((.*?)\)").search(self.fileText).groups()[0]
        if units == "ANGS":
            return "ANGSTROM"
        else:
            return "BOHR"
        
    def getInitialXYZ(self):
        coordinateLines = re.compile("ATOM.*?ATOMIC.*?COORDINATES.*?Z(.*?)I", re.DOTALL).search(self.fileText).groups()[0].strip().splitlines()
        coordinates = []
        for line in coordinateLines:
            splitLine = line.strip().split()
            label = removeNumberSuffix(splitLine[0])
            x = eval(splitLine[2])
            y = eval(splitLine[3])
            z = eval(splitLine[4])
            coordinates.append([label, x, y, z])

        return coordinates

    def getOptXYZ(self):
        coordinateSet = re.compile("NSERCH=.*?COORDINATES.*?Z(.*?)[*I](?!TH)", re.DOTALL).findall(self.fileText)[:-1]
        coordinates = []
        for entry in coordinateSet:
            coordinates.append([])
            coordinateLines = entry.replace("-","").strip().splitlines()
            for line in coordinateLines:
                splitLine = line.strip().split()
                label = removeNumberSuffix(splitLine[0])
                x = eval(splitLine[2])
                y = eval(splitLine[3])
                z = eval(splitLine[4])
                coordinates[-1].append([label, x, y, z])            

        return coordinates

    def getInputZMatrix(self):
        try:
            data_section = re.compile("INPUT CARD.*?DATA(.*?)END", re.DOTALL).search(self.fileText).groups()[0] 
            xyz = self.getInitialXYZ()
            atom_list = []
            for atom in xyz: atom_list.append(atom[0])
            #build the regular expression
            regExp = []
            for atom in atom_list:
                regExp.append( r" INPUT CARD>(%s.*?)\n" % atom )
            regExp = "".join(regExp)
            zmat_tuple = re.compile(regExp).search(data_section).groups()
            #convert the zmat_lines into a list
            zmat_lines = []
            for entry in zmat_tuple: zmat_lines.append(entry)
            #now get anything that would be z matrix variable
            zmat_lines.append("Variables")
            regExp = "[A-Z\d]+\s*[=]\s*[-]?\d+[.]?\d*"
            vars = re.compile(regExp).findall(data_section)
            for var in vars:
                zmat_lines.append(var)
            zmat_text = "\n".join(zmat_lines)
            import Input
            atomList, zmatObject = Input.readZMatrix(zmat_text)
            return zmatObject
        except Exception, error:
            raise InfoNotFoundError("Z-Matrix")

    ### Auxilliary Methods ###
    def getMPLevel(self):
        mpLevel = re.compile("INPUT CARD>.*?MPLEVL=(.*?)[\s\n]").search(self.fileText).groups()[0]
        return eval(mpLevel)

    def getRunType(self): #returns either scf or dft
        try:
            scf = re.compile("INPUT CARD>.*?RUNTYP=(.*?)[\s\n]").search(self.fileText).groups()[0]
            return "SCF"
        except AttributeError:
            return "DFT"

    def getSingleMP2Energy(self):
        energy = eval(re.compile("E\(MP2\)\s*=\s*(.*?)\n").search(self.fileText).groups()[0])
        return energy

    def getSingleSCFEnergy(self):
        energy = eval(re.compile("FINAL [A-Z]*HF ENERGY IS\s+(.*?)\s").search(self.fileText).groups()[0])
        return energy     

    def getSingleZAPT2Energy(self):
        return self.getSingleMP2Energy()

    def getOptEnergies(self):
        energies = map(eval, re.compile("NSERCH=.*?ENERGY=\s+(.*?)\n").findall(self.fileText))
        return energies
