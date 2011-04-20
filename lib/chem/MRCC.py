## @package MRCC
## Handles parsing of MRCC output

import string
import commands
import sys
import os
import os.path
from parse import Parser, EnergyRegExp
import re
from skynet.errors import *
from skynet.utils.utils import *
from chem.data import *

class MRCCParser(Parser):    
    ALLOWED_ENERGIES = ["CCSD", "CCSD(T)", "CCSDT", "CCSDT(Q)"]

    class SinglepointCCSDT_Q(EnergyRegExp):
        re1 = "Total CCSDT\(Q\) energy.*?:\s+(.*?)\n"

    class SinglepointCCSDT(EnergyRegExp):
        re1 = "Total CCSDT energy.*?:\s+(.*?)\n"

    class SinglepointCCSD_T(EnergyRegExp):
        re1 = "Total CCSD\(T\) energy.*?:\s+(.*?)\n"
    
    def getSingleCCSDTEnergy(self):
        try:
            energy = eval(re.compile("").search(self.fileText).groups()[0])
            return energy
        except AttributeError:
            raise InfoNotFoundError("CCSDT Energy")

    def getSingleCCSDT_QEnergy(self):
        try:
            energy = eval(re.compile("Total CCSDT\(Q\) energy.*?:\s+(.*?)\n").search(self.fileText).groups()[0])
            return energy
        except AttributeError:
            raise InfoNotFoundError("CCSDT(Q) Energy")        

    def get_keyword_WAVEFUNCTION(self):
        try:
            best = re.compile("Total (CC.*?) energy /au/").findall(self.fileText)[-1]
            return best.strip().upper()
        except (AttributeError, IndexError):
            raise InfoNotFoundError("wavefunction")
            

    def getSingleCCSDEnergy(self):
        raise InfoNotFoundError("CCSD Energy")        

    def getSingleCCSD_TEnergy(self):
        try:
            energy = eval(re.compile("Total CCSD\(T\) energy.*?:\s+(.*?)\n").search(self.fileText).groups()[0])
            return energy
        except AttributeError:
            raise InfoNotFoundError("CCSD(T) Energy")        

from Aces import AcesParser
class MRCCAcesParser(MRCCParser, AcesParser):
    donothing = 0
    

from Molpro import MolproParser
class MRCCMolproParser(MRCCParser, MolproParser):
    donothing = 0
