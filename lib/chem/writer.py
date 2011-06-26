from skynet.utils.utils import *
from skynet.errors import *
import os
PYBASIS = os.environ['PYBASIS']
PYTEMP = os.environ['PYTEMP']

class Writer:

    ROSETTA_STONE = {}
    BASIS_CONVERSIONS = {}
    #defines how arrays are to be written out
    ARRAY_FORMAT = "[%s]"
    ARRAY_DELIM = " "
    import grouptheory
    IRREP_ORDER = grouptheory.COTTON_ORDER
    #defines how certain data types should be formatted
    integer = "%d"
    string = "%s"
    float = "%12.8f"
    boolean = "lower"
    plus = False

    allcaps = False
    
    def __init__(self):
        #in case any lines need to be added at the end of the template
        self.linesAtEnd = []

    def __str__(self):
        return self.name

    def addLineAtEnd(self, text):    
        self.linesAtEnd.append(text)

    def getName(self):
        return self.name

    def translate_OPTCONVERGENCE(self, computation):
        return ""
    
    def makeFile(self, computation):
        format = Formatter(float=self.float, integer=self.integer, string=self.string, boolean=self.boolean, plus=self.plus)
        template_text = computation.getTemplate() #this may be a none type
        if not template_text: #if no template is given
            template_file = computation.findTemplate(program=self.name)
            if not template_file:
                wfn = str(computation.getAttribute("wavefunction")).replace("(", "_").replace(")","")
                jobtype = str(computation.getAttribute("jobtype"))
                reference = str(computation.getAttribute("reference"))
                raise GUSInputError("No template file for %s %s %s" % (wfn, jobtype, reference))
            template_text = open(template_file).read()

        regExp = r"([$][A-Z0-9]+)[,;:\n\s})\"/>]"
        parameterList = re.compile(regExp).findall(template_text)
        finalText = template_text[:]
        for param in parameterList:
            #get an initial value
            replacement = computation.getAttribute(param.strip("$"))
            #the replacement may require a special method
            method_name = "translate_%s" % param.strip("$").upper()
            if hasattr(self, method_name):
                method = getattr(self, method_name)
                replacement = method(computation)

            #alternatively, it may be simple enough that we can just look up the replacement in a hash table
            #of conversion
            try: 
                replacement = self.ROSETTA_STONE[param.strip("$").lower()][replacement] #try to do a simple translation
            except KeyError: 
                pass #this parameter needs no special translation

            if not replacement == None:
                #now that we have the final replacement, go ahead and put it in the input file
                finalText = finalText.replace( param, format(replacement) )

        final_text_array = finalText.splitlines()
        i = len(final_text_array) - 1
        #now, the replacement may require us to actually delete the keyword
        #for example, in ACES if there is no frozen core there is no reason to have DROPMO in the input file
        while i >= 0:
            if "DELETE" in final_text_array[i]:
                del final_text_array[i]
            i -= 1
        
        #add any special lines necessary at the end
        final_text_array.extend(self.linesAtEnd)
        self.linesAtEnd = []

        text = "\n".join(final_text_array)
        if self.allcaps:
            text = text.upper()
        return text

    def getCoordType(self, computation):
        coordtype = computation.getAttribute('coordtype')
        if coordtype == 'default':
            if computation.ZMatrix:
                return 'zmatrix'
            else:
                return 'xyz'
        else:
            return str(coordtype)

    def getCustomBasis(self, computation, basisName=None):
        if not basisName: basisName = computation.getAttribute("basis")
        basis_file = os.path.join( PYBASIS, "%s.basis" % basisName.lower() )
        if os.path.isfile(basis_file):
            basis_object = load(basis_file)
        else: #oh... we have to go to emsl
            basis_object = self.getEMSLBasis(computation, basisName)
        return basis_object, basisName

    def getEMSLBasis(self, computation, basisSet):
        import fetcher
        atoms_already_made = [] 
        for atom in computation.getAtoms():
            if not atom.getSymbol() in atoms_already_made:
                atoms_already_made.append(atom.getSymbol()) 
   
        try: basis_object = fetcher.getBasisSet(basis=basisSet, atomList=atoms_already_made) 
        except Exception, error:
            raise GUSInputError("I don't think %s is a real basis set" % basisSet)

        return basis_object

    def translate_GEOMETRY(self, computation):
        coordtype = computation.getAttribute("coordtype")
        if coordtype == 'default':
            zmat = computation.getZMatrix()
            #check for a zmat
            if zmat:
                coordtype = 'zmatrix'
            else:
                coordtype = 'xyz'
        
        if coordtype == "xyz":
            return self.getXYZ(computation)
        else:
            return self.getZMatrix(computation)

    def getXYZ(self, computation):
        return computation.getXYZTable()

    def getZMatrix(self, computation):
        pass #not yet implemented

    def translate_BASIS(self, computation):
        return self.checkBasis( computation.getAttribute("basis") )

    def translate_OCCUPATIONDOCC(self, computation):
        return self.getOccupation(computation, "docc")

    def translate_OCCUPATIONSOCC(self, computation):
        return self.getOccupation(computation, "socc")

    def translate_OCCUPATIONALPHA(self, computation):
        occ = computation.getAttribute('occupation')
        import input
        if not isinstance(occ, input.Occupation):
            return "DELETE"
        docc = occ.getOccupation(computation, 'docc')
        socc = occ.getOccupation(computation, 'socc')
        alpha = docc.copy()
        if socc:
            for irrep in socc:
                alpha[irrep] += socc[irrep]
        
        pg = computation.getAttribute('pointgroup')
        return self.makeOccupationArray(alpha, pg)

    def translate_OCCUPATIONBETA(self, computation):
        occ = computation.getAttribute('occupation')
        if not occ:
            return "DELETE"
        docc = occ.getOccupation(computation, 'docc')
        beta = docc.copy()
        pg = computation.getAttribute('pointgroup')
        return self.makeOccupationArray(beta, pg)
    
    def makeOccupationArray(self, occ_dict, pg):
        occ_order = self.IRREP_ORDER[pg]
        occ_arr = []
        if not occ_dict:
            return "DELETE"
        for irrep in occ_order:
            occ_arr.append("%d" % occ_dict[irrep])
        occ_text = self.ARRAY_FORMAT % self.ARRAY_DELIM.join(occ_arr)
        return occ_text

    def getOccupation(self, computation, space="docc"):
        occ = computation.getAttribute("occupation")
        pg = computation.getAttribute("pointgroup")
        import input
        if not isinstance(occ, input.OCCUPATION): #no occupation was given so delete the line
            return "DELETE"
        occ_dict = occ.getOccupation(computation, space)
        return self.makeOccupationArray(occ_dict, pg)

    def checkBasis(self, basis):
        if str(basis).lower() in self.ALLOWED_BASIS_SETS: #this basis is implemented
            try:
                basisConversion = self.BASIS_CONVERSIONS[basis]
                return basisConversion
            except KeyError:
                #there is no need to convert this basis
                #AttributeError means no bases need to be converted
                #KeyError means that specific basis does not need to be converted
                return basis #just send back the original basis
        else: 
            #send back none to let the routine know that we do not have the basis set
            return None
                


class Molpro(Writer):

    ROSETTA_STONE = { 
        "reference" : { "rohf" : "rhf" },
        "core" : { "correlated" : "core", "frozen" : "" },
        "optconvergence" : { "tight" : ",gradient=1e-6,energy=1e-8", "normal" : "", "loose" : ""},
        }

    name = "molpro"

    ### DO NOT INCLUDE CORE BASIS SETS! MOLPRO FUCKS THIS UP BY GRABBING THE MP2-FIT BASIS INSTEAD!
    ALLOWED_BASIS_SETS = [
        "cc-pvdz",
        "cc-pvtz",
        "cc-pvqz",
        "cc-pv5z",
        "cc-pv6z",
        "aug-cc-pvdz",
        "aug-cc-pvtz",
        "aug-cc-pvqz",
        "aug-cc-pv5z",
        "aug-cc-pv6z",
        "sto-3g",
    ]

    def translate_BASIS(self, computation):
        basis = self.checkBasis(computation.getAttribute("basis"))
        if basis: return basis #no need to adjust name
        else: #uh oh, we need a custom basis
            basisObject,basisName = self.getCustomBasis(computation)
            try: 
                text = self.writeCustomBasis(basisObject, basisName, computation)
                return text
            except Exception, error:
                from traceback import format_exc
                print format_exc(sys.exc_traceback)
                raise OSError

    def translate_RIBASIS(self, computation):
        ribasis = computation.getAttribute("ribasis")
        found_jk = False
        for basis in self.ALLOWED_BASIS_SETS:
            test_basis = basis + "-JKFIT"
            if test_basis == ribasis: found_jk = True

        if not found_jk: raise GUSInputError("Only JK-Fitting Basis Sets are allowed for the RI")

        #no diffuse functions for jk fitting basis
        #also, remove the jk
        ribasis = ribasis.replace("AUG-", "").replace("-JKFIT","")
        return ribasis

    def writeCustomBasis(self, basisObject, basisName, computation):
        import BasisSets
        atoms_already_made = {}
        basisText = basisObject.getBasisText(program="molpro", name=basisName) 
        basisText += "\nEND\n"
        return basisText
    
    def translate_WAVEFUNCTION(self, computation):
        ref = computation.getAttribute("reference")
        wfn = computation.getAttribute("wavefunction")
        if ref == "rohf" or ref == "uhf":
            wfn = "u" + wfn
        return wfn

    def translate_ENERGYCONVERGENCE(self, computation):
        conv = computation.getAttribute("energyconvergence")
        if conv == "tight":
            return 'gthresh,orbital=1.0d-10,energy=1.0d-11,zero=1.d-122,oneint=1.d-122,twoint=1.d-122\nnocompress'
        else:
            return "DELETE"

    def translate_STATESYMMETRY(self, computation):
        import grouptheory
        import input
        pg = computation.getPointGroup()
        stateSymm = computation.getStateSymmetry()
        occ = computation.getAttribute('occupation')
        if isinstance(occ, input.OCCUPATION):
            socc = occ.getOccupation(computation, 'socc')
            if socc:
                stateSymm = grouptheory.getStateSymmetry(pg, socc)
        if not stateSymm:
            raise GUSInputError("state symmetry not specified correctly")
        try:
            conversion = grouptheory.getMolproIrrepNumber(pg, stateSymm)
        except KeyError:
            raise InputError("State symmetry %s not specified correctly for point group%s" % (stateSymm, pg))
        return "%d" % conversion

    def getXYZ(self, computation):
        print_units = computation.getAttribute("PRINTUNITS")
        coordinates = computation.getXYZMatrix(print_units)

        #in some cases, we will want to turn off symmetry
        nosymm = False
        if computation.getAttribute("wavefunction") == "mp2r12":
            nosymm = True

        str_array = []
        if print_units == "bohr":
            str_array.append("geomtyp=zmat")
            str_array.append("geometry={")
            if nosymm: str_array.append("nosymm;")
            #write out the xyz coordinates
            for atom in coordinates:
                label = atom[0].ljust(3)
                str_array.append( "%2s ,, %s" % (label, getXYZText(atom[1:], delimiter=" , ") ) )
            str_array.append("}")
            
        else:
            str_array.append("geomtyp=xyz")
            str_array.append("geometry={")
            if nosymm: str_array.append("nosymm;")
            #must write out the number of atoms
            numAtoms = len(coordinates)
            str_array.append("    %d" % numAtoms)
            #must write out an xyz title
            str_array.append("    xyz input")
            #write out the xyz coordinates
            for atom in coordinates:
                str_array.append(atom[0].ljust(3) + getXYZText(atom[1:], delimiter=" ") )
            str_array.append("}")

        return "\n".join(str_array)

    def getZMatrix(self, computation):
        units = computation.getAttribute("printunits")
        str_array = [] 
        str_array.append("geomtyp=zmat")
        str_array.append("geometry={")
        str_array.append("%s" % units)
        zmat_text = computation.getZMatrix().getZMatrix(minusPairs=True,constantsAreValues=True,units=units)
        str_array.append(zmat_text)
        str_array.append("}")
        var_text = computation.getZMatrix().getVariablesAndConstants(constantsAreValues=True,useMinusPairs=True,units=units)
        str_array.append(var_text)
        return "\n".join(str_array)

class Aces(Writer):

    ROSETTA_STONE = {
        "coordtype" : {"xyz" : "cartesian", "z-matrix" : "internal", "zmatrix" : "internal", }
        }

    allcaps = True

    name = "aces"

    ALLOWED_BASIS_SETS = [
        "cc-pvdz",
        "cc-pvtz",
        "cc-pvqz",
        "CC-PV5Z",
        "cc-pv5z",
        "cc-pv6z",
        "aug-cc-pvdz",
        "aug-cc-pvtz",
        "aug-cc-pvqz",
        "aug-cc-pv5z",
        "aug-cc-pv6z",
        "sto-3g",
    ]

    def translate_MEMORY(self, computation):
        mem = computation.getAttribute("memory")
        return int(1E6 * mem) #give it back in words

    def translate_COORDTYPE(self, computation):
        coordtype = self.getCoordType(computation)
        return self.ROSETTA_STONE['coordtype'][coordtype]

    def translate_BASIS(self, computation):
        basis = Writer.translate_BASIS(self, computation)
        if basis: #okay, the basis set exists
            basisConversion = basis.replace("cc-p", "p")
            return basisConversion
        else: #uh oh, we need a custom basis
            basisObject,basisName = self.getCustomBasis(computation)
            try: 
                self.writeCustomBasis(basisObject, basisName, computation)
            except Exception, error:
                print traceback(error)
                print error
                raise OSError
            return "SPECIAL" #in the actual basis set keyword, we should write special

    def translate_OPTCONVERGENCE(self, computation):
        optconv = computation.getAttribute("optconvergence")
        if optconv == "normal": return "DELETE"
        elif optconv == "tight": return "7" #10^-7 convergence
        elif optconv == "loose": return "3" #10^-3 convergence

    def translate_CCPROGRAM(self, computation):
        wav = computation.getAttribute('wavefunction')
        if wav == 'scf' or wav == 'mp2':
            return "DELETE"
        else:
            return "ECC"

    def translate_WAVEFUNCTION(self, computation):
        wfn = computation.getAttribute("wavefunction")
        if wfn == "ccsd(t)": return "ccsd[t]" #brackets, ugh, aces
        if wfn == "scf":
            #because aces is the second biggest piece of shit ever written(second only to intdif)
            #even if you request 11 digits of accuracy in the scf energy, it only prints 10 digits
            #if you run an MP2 computation, it prints 12 digits though. So basically the hack here
            #is to run a "completely frozen core" mp2 routine that does nothing, but then prints
            #out more digits of scf energy
            conv = computation.getAttribute("energyconvergence")
            if conv == "tight":
                num_orbitals = computation.getNumberOfOrbitals()
                key = "mp2\n       dropmo=1>%d" % num_orbitals
                return key
            else: 
                return "scf"
        else: return wfn #no need to change

    def translate_CORE(self, computation):
        wav = computation.getAttribute("wavefunction")
        #no core to freeze in scf
        if wav == "scf": return "DELETE"
        core = computation.getAttribute("core")
        if core == "frozen":
            core_electrons = computation.getNumberOfCoreElectrons()
            if core_electrons == 0: return "DELETE" #no core to freeze
            else: return "1>%d" % core_electrons
        else: return "DELETE" #don't freeze core, so no need to include line

    def translate_ENERGYCONVERGENCE(self, computation):
        conv = computation.getAttribute("energyconvergence")
        if conv == "tight":
            key = "scf_conv=11"
            wav = computation.getAttribute("wavefunction")
            if "cc" in wav:
                key += "\n       cc_conv=9"
            return key
        else:
            return "DELETE"

    def translate_JOBTYPE(self, computation):
        jobtype = computation.getAttribute("jobtype")
        if jobtype == "frequency":
            reference = computation.getAttribute("reference")
            wfn = computation.getAttribute("wavefunction")
            if reference == "rhf" or reference == "uhf" or wfn == "scf": return "vib=exact"
            else: return "vib=findif"
        elif jobtype == "oeprop":
            return "prop=first_order"

        else: return "DELETE" #single points and optimizations have no keyword

    def deleteKeyword(self, keyword, fileText):
        regExp = r"[ ]+[$]%s\n" % keyword
        newText =  re.sub(regExp, "", fileText)
        return newText

    def getXYZ(self, computation):
        printUnits = computation.getAttribute("printunits")
        xyz = computation.getXYZTable(printUnits)
        return xyz
    
    def getZMatrix(self, computation):
        units = computation.getAttribute("printunits")
        is_optimization = ( computation.getAttribute("jobtype").lower() == "optimization")
        zmat_text = computation.getZMatrix().getZMatrix(asterisks=is_optimization,units=units)
        var_text = computation.getZMatrix().getVariablesAndConstants(units=units) 
        return "%s\n\n%s" % (zmat_text , var_text)
    
    def writeCustomBasis(self, basisObject, basisName, computation):
        import glob, BasisSets
        atoms_already_made = {}
        basisName = BasisSets.cleanBasisName(computation.getAttribute("basis")).upper()
        basisName = "TEST"
        numFiles = len( glob.glob( os.path.join(PYTEMP, "GENBAS*") ) )
        genbas_file = os.path.join(PYTEMP, "GENBAS%d" % numFiles) 
        genbas = open(genbas_file, "w") 
        basisText = basisObject.getBasisText(program="aces", name=basisName) 
        genbas.write(basisText)
        genbas.close()

        #aces requires some special stuff at the end
        for atom in computation.getAtoms():
            self.addLineAtEnd( "%s:%s" % ( atom.getSymbol(), basisName ) )     
        self.addLineAtEnd("\n")    
    
        #let the computation know it has to copy the genbas file to wherever it might need it
        sys.stderr.write("Created %s\n" % genbas_file)
        computation.addFileToCopy(name=genbas_file, nameToCopy="GENBAS")


class Psi(Writer):
    ROSETTA_STONE = {
        "core" : {"correlated" : "false", "frozen" : "true"},
        }
    name = "psi"
    ARRAY_FORMAT = "(%s)"
    ALLOWED_BASIS_SETS = [
        "cc-pcvdz",
        "cc-pcvtz",
        "cc-pcvqz",
        "cc-pcv5z",
        "cc-pcv6z",
        "cc-pvdz",
        "cc-pvtz",
        "cc-pvqz",
        "cc-pv5z",
        "cc-pv6z",
        "aug-cc-pcvdz",
        "aug-cc-pcvtz",
        "aug-cc-pcvqz",
        "aug-cc-pcv5z",
        "aug-cc-pcv6z",
        "aug-cc-pvdz",
        "aug-cc-pvtz",
        "aug-cc-pvqz",
        "aug-cc-pv5z",
        "aug-cc-pv6z",
        "sto-3g",
    ]

    def getXYZ(self, computation):
        str_array = []
        print_units = computation.getAttribute("printunits")
        xyz = computation.getXYZTable(units=print_units, includeLabels=True, delim= " ")
        str_array.append("geometry=(")
        str_array.append(xyz)
        #write out the xyz coordinates
        str_array.append("   )")
        return "\n".join(str_array)

    def translate_WAVEFUNCTION(self, computation):
        wfn = computation.getKeyword("wavefunction")
        if wfn == "ccsd(t)":
            return "ccsd_t"
        else:
            return wfn
    
    def getZMatrix(self, computation):
        str_array = []
        print_units = computation.getAttribute("printunits")
        zmat = computation.getZMatrix()
        zmat_text = zmat.getZMatrix(units=print_units, constantsAreValues=True)
        vars_text = zmat.getVariablesAndConstants(units=print_units, delim = " ", constantsAreValues=True)
        str_array.append("zmat=(")
        str_array.append(zmat_text)
        str_array.append("  )")
        if vars_text:  
            str_array.append("    zvars=(")
            str_array.append(vars_text)
            str_array.append("  )")
        return "\n".join(str_array)

    def translate_BASIS(self, computation):
        basis_name = computation.getAttribute("basis")
        return self.processBasis(basis_name, computation)

    def processBasis(self, basisName, computation):
        basis = self.checkBasis(basisName)
        if basis: #okay, we're good to go
            return basis
        else: #custom basis
            basis_object, basis_name = self.getCustomBasis(computation, basisName)
            self.writeCustomBasis(basis_object, basis_name, computation)
            #the name must go in for the basis
            return '"%s"' % basis_name.upper()

    def writeCustomBasis(self, basisObject, basisName, computation):
        import BasisSets
        atomList = computation.getAtoms()
        labelList = []
        for atom in atomList:
            label = atom.getSymbol()
            if not label in labelList: labelList.append(label)

        basisText = basisObject.getBasisText(program="psi", name=basisName, atomList=labelList) 
        self.addLineAtEnd(basisText)

    def translate_MEMORY(self, computation):
        memory = computation.getAttribute("memory")
        mem_in_mb = memory * 8
        return r"(%d MB)" % mem_in_mb  

    def translate_OPTCONVERGENCE(self, computation):
        conv = computation.getAttribute("optconvergence")
        if conv == "tight": return "7"
        elif conv == "normal" : return "delete"

    def translate_ENERGYCONVERGENCE(self, computation):
        conv = computation.getAttribute("energyconvergence")
        if conv == "tight": return "12"
        elif conv == "normal" : return "DELETE"

class Gamess(Writer):
    ROSETTA_STONE = {}
    name = "gamess"

class Gaussian(Writer):
    
    name = "gaussian"
    ALLOWED_BASIS_SETS = [
        "sto-3g",
        "6-31g*",
        "cc-pvdz",
        "6-311++g**",
        'aug-cc-pvtz',
        'aug-cc-pvdz',
        ]

    def getXYZ(self, computation):
        printunits = computation.getAttribute("printunits")
        xyz = computation.getXYZTable(units=printunits)
        return xyz

    def translate_BASIS(self, computation):
        basis = self.checkBasis(computation.getAttribute("basis"))
        if basis: return basis #no need to adjust name
        else: #uh oh, we need a custom basis
            basisObject,basisName = self.getCustomBasis(computation)
            try: 
                text = self.writeCustomBasis(basisObject, basisName, computation)
                return text
            except Exception, error:
                from traceback import format_exc
                print format_exc(sys.exc_traceback)
                raise OSError

    def translate_JOBTYPE(self, computation):
        #this is a total hack at this point... add a blank line at the end
        self.addLineAtEnd("")
        jobtype = computation.getAttribute("jobtype")
        optconvergence = computation.getAttribute("optconvergence")
        #no need for anything special with single point
        if jobtype == "singlepoint": return ""
        elif jobtype == "optimization": 
            trans = "opt"
            if optconvergence == "tight": trans += "=tight"
            return trans
        elif jobtype == "frequency": return "freq"

    def writeCustomBasis(self, basisObject, basisName, computation):
        import BasisSets
        atomList = computation.getAtoms()
        labelList = []
        for atom in atomList:
            label = atom.getSymbol()
            if not label in labelList: labelList.append(label)

        basisText = basisObject.getBasisText(program="gaussian", name=basisName, atomList=labelList) 
        self.addLineAtEnd(basisText)
        #need a blank line at the end of the file
        self.addLineAtEnd("")
        return "gen" #tells gaussian to do a general basis

class MRCC(Writer):

    name = "mrcc"
    def makeFile(self, computation):
        aces_obj = Aces()
        main = aces_obj.makeFile(computation) 

        wfn = computation.getAttribute("wavefunction")
        open_shell = computation.isOpenShell() 
        reference = computation.getAttribute("reference")
        mult = computation.getAttribute("multiplicity")
        mem = computation.getAttribute("memory")*8
        int_array = []

        exc_level = 0
        if "ccsdtq" in wfn and "5" in wfn: exc_level = 5
        elif "ccsdt" in wfn and "q" in wfn: exc_level = 4 
        int_array.append(exc_level)

        if mult == 1: int_array.append(1)
        else: int_array.append(0)
        if mult == 3: int_array.append(1)
        else: int_array.append(0)

        #incrementally solve
        int_array.append(2)
        
        #perturbative or no
        if "(" in wfn: int_array.append(3)
        else: int_array.append(1)
    
        #random stuff
        int_array.extend( [0,0,1,0] )

        if open_shell: int_array.append(0)
        else: int_array.append(1)

        if reference == "uhf": int_array.append(0)
        else: int_array.append(1)

        int_array.append(0)

        if open_shell: int_array.append(1)
        else: int_array.append(0)

        int_array.extend([0,0,6,0,0,0,0])

        int_array.append(mem)

        clean = lambda x: "%d" % x
        str_array = map(clean, int_array)
        mrcc_file = "  ".join(str_array)

        file = MultiFile(main, { "fort.56" : mrcc_file} )
        return file

class MPQC(Writer):
    ROSETTA_STONE = {
        "core" : {"correlated" : "none", "frozen" : "auto"},
        "reference" : {"rhf" : "CLHF", "rohf" : "HSOSHF", "uhf" : "UnrestrictedHF" },
        }

    ALLOWED_BASIS_SETS = [
        "cc-pvtz-jfkit",
        "cc-pvdz-f12-ri",
        "cc-pvtz-f12-ri",
        "cc-pvqz-f12-ri",
        "cc-pvdz-f12",
        "cc-pvtz-f12",
        "cc-pvqz-f12",
        "cc-pvdz",
        "cc-pvtz",
        "cc-pvqz",
        "cc-pv5z",
        "cc-pv6z",
        "aug-cc-pvdz",
        "aug-cc-pvtz",
        "aug-cc-pvqz",
        "aug-cc-pv5z",
        "aug-cc-pv6z",
        "sto-3g",
    ]

    name = "mpqc"

    def getXYZ(self, computation):
        str_array = []
        units = computation.getAttribute("printunits")
        xyz = computation.getAtoms()
        for atom in xyz:
            str_array.append("%s [ %s ]" % (atom.getSymbol(), getXYZText(atom.getXYZ().getValue(units), 
                             delimiter=" ", formatString = "%16.12f")))

        #write out the xyz coordinates
        return "\n".join(str_array)

    def translate_CORE(self, computation):
        core = computation.getKeyword("core")
        if core == "frozen": 
            return "auto"
        else:   
            return "none"

    def translate_BASIS(self, computation):
        basis_name = computation.getAttribute("basis")
        return self.processBasis(basis_name, computation)

    def processBasis(self, basisName, computation, ri=False):
        basis = self.checkBasis(basisName)
        if basis: #okay, we're good to go
            basis = str(basis)
            match = re.compile(r'p[w]?([c]?v[dtq56]z)').search(basis)
            if match and not 'f12' in basis.lower():
                repl = match.groups()[0]
                basis = basis.lower().replace(repl, repl.upper())
            elif match:
                basis = basis.lower()
            #the basis set goes in quotes
            return "\"%s\"" % basis
        else: #custom basis
            basis_object, basis_name = self.getCustomBasis(computation, basisName)
            if ri: 
                basis_text = self.writeRIBasis(basis_object, basis_name, computation)
            else: 
                basis_text = self.writeCustomBasis(basis_object, basis_name, computation)
            #in mpqc, the name and basis set are written out in the immediate place
            basis_to_write = " \"%s\" \n%s " % (basis_name, basis_text)
            return basis_to_write

    def translate_ENERGYCONVERGENCE(self, computation):
        wfn = computation.getAttribute('wavefunction')
        conv = computation.getAttribute('energyconvergence')
        level = 8
        if conv == 'tight':
            level = 10
        elif conv == 'loose':
            level = 6
        elif isInteger(conv):
            level = eval(conv)
        return "1e-%d" % level
        
    def translate_RIBASIS(self, computation):
        basis_name = computation.getAttribute("ribasis")
        return self.processBasis(basis_name, computation, ri=True)

    def translate_MEMORY(self, computation):
        memory = computation.getAttribute("memory")
        return memory * 8000000
   
    def translate_PRINTUNITS(self, computation):
        return computation.getAttribute("printunits").lower()

    def writeCustomBasis(self, basisObject, basisName, computation):
        atoms_to_write = []
        for atom in computation.getAtoms():
            name = atom.getSymbol()
            if not name in atoms_to_write: atoms_to_write.append(name)
        stuff = basisObject.getBasisText("mpqc", basisName, atoms_to_write)
        return stuff

    def writeRIBasis(self, basisObject, basisName, computation):
        atoms_to_write = []
        for atom in computation.getAtoms():
            name = atom.getSymbol()
            if not name in atoms_to_write: atoms_to_write.append(name)
        self.addLineAtEnd( basisObject.getBasisText("mpqcri", basisName, atoms_to_write) )
        return ""

class Orca(Writer):

    ROSETTA_STONE = {
        "printunits" : {  
            "angstrom" : "angs",
            "bohr" : "bohrs",
            }
    }   

    ALLOWED_BASIS_SETS = [
        "cc-pvdz",
        "cc-pvtz",
        "cc-pvqz",
        "cc-pv5z",
        "cc-pv6z",
        "aug-cc-pvdz",
        "aug-cc-pvtz",
        "aug-cc-pvqz",
        "aug-cc-pv5z",
        "aug-cc-pv6z",
        "sto-3g",
    ]

    name = 'orca'

    def translate_WAVEFUNCTION(self, computation):
        wfn = computation.getAttribute("wavefunction")
        if wfn == 'scf':
            return computation.getAttribute("reference")
        else:
            return wfn

    def getXYZ(self, computation):
        units = computation.getAttribute("printunits")
        return computation.getXYZTable(units=units)
        
class QChem(Writer):
    ROSETTA_STONE = {
        "jobtype" : {  
            "optimization" : "opt",
            "frequency" : "freq",
            "singlepoint" : "sp",
            }
    }   

    ALLOWED_BASIS_SETS = [
        "cc-pvdz",
        "cc-pvtz",
        "cc-pvqz",
        "cc-pv5z",
        "cc-pv6z",
        "aug-cc-pvdz",
        "aug-cc-pvtz",
        "aug-cc-pvqz",
        "aug-cc-pv5z",
        "aug-cc-pv6z",
        "sto-3g",
    ]

    name = "qchem"

    def getXYZ(self, computation):
        #print_units = computation.getAttribute("PRINTUNITS")
        print_units = "angstrom"
        xyz = computation.getXYZTable(units=print_units)
        return xyz

    def translate_BASIS(self, computation):
        basis_name = computation.getAttribute("basis")
        return self.processBasis(basis_name, computation)

    def processBasis(self, basisName, computation, ri=False):
        basis = self.checkBasis(basisName)
        if not basis: #not found!
            basis_object, basis_name = self.getCustomBasis(computation, basisName)
            basis_text = self.writeCustomBasis(basis_object, basis_name, computation)
            #in mpqc, the name and basis set are written out in the immediate place
            return basis_text
        else:
            return basis

    def translate_CATIONGUESS(self, computation):
        charge = computation.getAttribute("charge")
        return "%d" % (charge + 2)

    def translate_REFERENCE(self, computation):
        ref = computation.getAttribute("reference")
        if ref == "uhf":
            return "true"
        else:
            return "false"

    def translate_MEMORY(self, computation):
        memory = computation.getAttribute("memory")
        #megabytes
        return memory * 8 
   
    def translate_PRINTUNITS(self, computation):
        return computation.getAttribute("printunits").lower()

    def writeCustomBasis(self, basisObject, basisName, computation):
        atoms_to_write = []
        for atom in computation.getAtoms():
            name = atom.getSymbol()
            if not name in atoms_to_write: atoms_to_write.append(name)
        stuff = "$basis\n"
        stuff += basisObject.getBasisText("qchem", basisName, atoms_to_write)
        stuff += "\n$end"
        self.addLineAtEnd(stuff)
        return "gen"

class MultiFile:

    def __init__(self, mainFile, otherFiles):
        self.mainFile = mainFile
        self.otherFiles = otherFiles

    def getMainFile(self):
        return self.mainFile

    def getOtherFiles(self):
        return self.otherFiles
