## @package RM A module with a bunch of random methods for stuff
import os, os.path, sys, commands, re
import pickle, thread
from globalvals import *

def capitalize_word(word):
    if not word:
        return "" 

    new_word = word[0].upper() + word[1:].lower()
    return new_word

def clean_line(line):
    lowercase = [
        "and"
        "of"
        "the"
    ]

    words = []
    for entry in line.split(" "):
        if "-" in entry:
            dash_arr = []
            dashes = entry.split("-")
            for dash in dashes:
                dash_arr.append(capitalize_word(dash))
            words.append("-".join(dash_arr))
        elif entry in lowercase:
            words.append(entry.lower())
        else:
            words.append(capitalize_word(entry))
    
    return " ".join(words)


def getDate():
    date = commands.getoutput("date")
    return date.replace(" ","").replace(":","_")

def getDebug():
    for entry in sys.argv[1:]:
        if "debug" in entry:
            DEBUG = eval( entry.split("=")[1] )
            return DEBUG
    #nope, not set, so return 0
    return 0

def re_replace(regexp, original, new):
    matchobj = re.compile(regexp).search(original)
    if matchobj:
        matchtext = matchobj.groups()[0]
        return original.replace(matchtext, new)
    else:
        return original

SAFE_PRINT = thread.allocate_lock()
def print_safely(text):
    SAFE_PRINT.acquire()
    print text
    SAFE_PRINT.release()

PI= 3.14159265358979323846
CONVERSIONS = {
    "BOHR_TO_ANGSTROM" : 0.5291772108,
    "ANGSTROM_TO_BOHR" : 1.88972612499,
    "HARTREE_TO_WAVENUMBER" :  219474.63,
    "WAVENUMBER_TO_HARTREE" : 4.5563352812122E-06,
    "WAVENUMBER_TO_KCAL" : 0.0028591459523135, 
    "JOULE_TO_HARTREE" : 2.29371044869E17,
    "HARTREE_TO_JOULE" : 1/2.29371044869E17,
    "HARTREE_TO_KCAL" : 627.51,
    "RADIAN_TO_DEGREE" : 180/PI,
    "DEGREE_TO_RADIAN" : PI/180,
    "BOHR_TO_METER" : 0.529177210E-10,
    "METER_TO_BOHR" : 1/0.529177210E-10,
    "KG_TO_AMU" : 1/1.66053886E-27, 
    "AMU_TO_KG" : 1.66053886E-27, 
    "HERTZ_TO_WAVENUMBER" : 1/2.99792458E10,
}
CONVERSIONS["RADIAN_TO_BOHR-RAD-AU"] = 1.0
CONVERSIONS["DEGREE_TO_BOHR-RAD-AU"] = CONVERSIONS["DEGREE_TO_RADIAN"] 
CONVERSIONS["BOHR_TO_BOHR-RAD-AU"] = 1.0 
CONVERSIONS["ANGSTROM_TO_BOHR-RAD-AU"] = CONVERSIONS["ANGSTROM_TO_BOHR"] 


#a wrapper for the boolean false, in case anyone incorrectly forgets the capital
false=False

def copy(obj):
    pickle_string = pickle.dumps(obj)
    newProject = pickle.loads(pickle_string)
    return newProject

def deleteBlankLines(text):
    str_array = []
    for line in text.splitlines():
        if len( line.strip() ) > 0: str_array.append(line)
    return "\n".join(str_array)


def linuxName(text):
    return text.replace("(","_").replace(")","").replace("+", "plus")

def makeFolder(folder):
    if not folder[0] == "/":
        #relative path
        folder = os.path.join( os.getcwd(), folder)
    dirList = folder.split("/")
    currentDir = "/"
    for entry in dirList:
        currentDir = os.path.join(currentDir, entry)
        if not os.path.isdir(currentDir): 
            os.mkdir(currentDir)

def harikari():
    message = """This script you are using has crashed. 
    Please report the script name and error to:
    Jeremiah Wilke
    jjwilke@uga.edu
    706-542-7374
    Center for Computational Chemistry
    University of Georgia



    """

    sys.stderr.write(message)
    randomquote()
    sys.exit()

def randomquote():

    print """When you earnestly believe you can compensate for a lack of skill
    by doubling your efforts, there's no end to what you can't do.

    -Dr. E.L. Kersten
    """

def getRegularExpressionNoCaseEntry(text):
    word_array = []
    for letter in text:
        word_array.append("[%s%s]" % (letter.upper(), letter.lower()))
    return "".join(word_array)


def getXYZText(coordinates, delimiter=",", formatString="%15.12f"):
    str_array = map( lambda x: formatString % x, coordinates)
    return delimiter.join(str_array)
    
def makeMPQCScript(walltime, numproc):
    text="""#PBS -V
#PBS -N mpqc
#PBS -l walltime=WT
#PBS -j oe
#PBS -l size=NUMPROC

module load mpqc
cd $PBS_O_WORKDIR
setenv XT_SYMMETRIC_HEAP_SIZE 512M
echo `pwd`
set scratch = ~/scratch/mpqc.$PBS_JOBID
mkdir $scratch
cp input.dat $scratch
cd $scratch

pbsyod -SN $MPQC_DIR/bin/mpqc input.dat > $PBS_O_WORKDIR/output.dat
rm -rf $scratch
    """
    fileText = text.replace("WT", "%d:00:00" % walltime).replace("NUMPROC", "%d" % numproc)
    fileObj = open("script", "w")
    fileObj.write(fileText)
    fileObj.close()

def makeCOBALTScript(directory, walltime=18, numproc_cpu=4, numproc_mem=8):
    text="""#!/bin/csh
#PBS -l ncpus=mem_cpu,walltime=WT
#PBS -q standard
#PBS -l mem=%dGB
#PBS -N  molprojob
######################################################

#
#
#
set IAm="jjwilke"
cd $SCR
pwd
setenv SCRATCH `/bin/pwd`
cp /u/ac/jjwilke/DIR_NAME/input.dat .
cp  /u/ac/jjwilke/DIR_NAME/* .
# set up environmental variables
#
setenv MOLPRO  /usr/apps/chemistry/molpro/PAR/molpro2006.1
setenv MOLPRO_PWD /u/ac/jjwilke/DIR_NAME
#
# run molpro
#
alias molprox $MOLPRO/bin/molpro
#
# run the program
unlimit
limit
limit -h
ln -sf    /u/ac/jjwilke/DIR_NAME/output.dat    output.dat
molprox  -k id=ncsaedu,date=:2007/10/10,version=:9999,mpp=32767,modules=mpp\&qOrLMosDzGS3cVcG  -N com_cpu -o output.dat -n com_cpu -d $SCR -I /u/ac/jjwilke/DIR_NAME -W /u/ac/jjwilke/DIR_NAME -L $MOLPRO/lib/ < input.dat
#

ls -la
#
# move the output and restart files to local disk
#
#/usr/sbin/unlink /u/ac/jjwilke/DIR_NAME/output.dat
/bin/cp output.dat /u/ac/jjwilke/DIR_NAME/output.dat
    """
    fileText = (text % (2 * numproc_mem)).replace("WT", "%d:00:00" % walltime).replace("mem_cpu", "%d" % numproc_mem).replace("DIR_NAME", directory).replace("com_cpu", "%d" % numproc_cpu)
    fileObj = open("script", "w")
    fileObj.write(fileText)
    fileObj.close()    

def convertXYZMatrixToVector(matrix):
    import numpy
    vector = []
    for row in matrix:
        for col in row:
            vector.append(col)
    return numpy.array(vector)

def convertVectorToXYZMatrix(vector):
    import numpy
    matrix = []
    atomNumber = 0
    for i in range(0, len(vector)/3):
        xyz = vector[3*i:3*i + 3]
        matrix.append(xyz)
        atomNumber += 1

    return numpy.array(matrix)

def readFCMFinal():
    import numpy
    #read in the file, but throw away the first line
    text = open("fcmfinal").read().splitlines()
    numCoordinates = eval( text[0].strip().split()[1] )
    fconstants = text[1:]
    fc_matrix = []
    coordNumber = 0
    for line in fconstants:
        if coordNumber % numCoordinates == 0:
            fc_matrix.append([])
        for entry in line.strip().split():
            fc_matrix[-1].append( eval(entry) )
            coordNumber += 1
    return numpy.array( fc_matrix )


class Formatter:

    def __init__(self, float="%12.8f", string="%10s", integer="%5d", plus=False, boolean="capitalize", noWhiteSpace = False):
        self.float=float
        self.string=string
        self.integer=integer
        self.plus = plus
        self.noWhiteSpace = noWhiteSpace
        self.bool = boolean.lower()

    def __str__(self):
        str_array = []
        for attr in self.__dict__:
            str_array.append( "%s = %s" % (attr, self.__dict__[attr]) )
        return "\n".join(str_array)

    def formatItem(self, item):
        val = None
        if isinstance(item, bool):
            if self.bool == "capitalize":
                val =  str(item)
            elif self.bool == "allcaps":
                val = str(item).upper()
            else:
                val = str(item).lower()
        elif isinstance(item, int): 
            if self.plus and item > 0: 
                val = self.integer.replace("%", "+%") % item
            else: 
                val = self.integer % item
        elif isinstance(item, float):
            if self.plus and item > 0:  
                val = self.float.replace("%", "+%") % item
                import re
                regExp = re.compile("[+](\s*)")
                numWhiteSpaces = len(regExp.search(val).groups()[0])
                oldPlus = "+" + " " * numWhiteSpaces
                newPlus = " " * numWhiteSpaces + "+"
                val = val.replace(oldPlus, newPlus)

            else:
                val = self.float % item
            
        else: 
            val = self.string % item  

        if self.noWhiteSpace:
            val = val.replace(" ","")
        return val
    
    def __mod__(self, item):
        return self.formatItem(item)

    def __call__(self, item):
        return self.formatItem(item)

## Deletes a specific line a file
#  @param lineNumber an integer giving the line number to delete
#  @param file The full path of the file to delete from
def deleteLineInFile(lineNumber, file):
    command = "sed '%dd' %s > newfile "  % (lineNumber, file)
    commands.getoutput(command)
    commands.getoutput("mv newfile %s " % file)    

def formatter(float="%12.8f", string="%10s", integer="%5d", unknown=None ):
    if unknown: #we have some unknown to take care of
        if 'f' in unknown: float=unknown
        elif 's' in unknown: string=unknown
        elif 'd' in unknown: integer = unknown
    formatObject = Formatter(float, string, integer)
    return formatObject

## Takes a string, float, integer, etc. and returns an appropriately formatted string
def getStringRepr(value):
    try:
        text = "%12.8f" % value
        return text
    except TypeError:
        pass

    try:
        text = "%d" % value
        return text
    except TypeError:
        pass

    #must be a string
    return value

## Gets a list of files from a certain folder
#  @param parentFolder The folder where the files are located
#  @param suffixArray The suffixes to include in the list
#  @return A list of filenames (without the folder, just the filename)
def getFileList(parentFolder, suffixArray):
    directory = commands.getoutput("ls " + parentFolder)
    directoryArray = string.split(string.strip(directory), "\n")
    fileList = []
    for line in directoryArray:
        splitLine = string.split(string.strip(line))
        for file in splitLine:
            suffix = string.split(file, ".")[-1]
            #we only want the files that end in log, out, or dat since these are going to be output files
            if suffix in suffixArray:
                fileList.append(file)
            #else do nothing

    return fileList

def getFiles(directory="."):
    import os, os.path
    file_list = [elem for elem in os.listdir(directory) if os.path.isfile(elem)]
    return file_list

def getDirectories(directory="."):
    import os, os.path
    topdir = os.getcwd()
    os.chdir(directory)
    dir_list = [elem for elem in os.listdir(".") if os.path.isdir(elem)]
    os.chdir(topdir)
    return dir_list

## Takes a set of command line options and returns an input and output file
#  @param optionArray The array of options to check for an input file in
def getInputFile(optionArray):
    import os.path
    inputFile = optionArray[-1]
    if not os.path.isfile(inputFile):
        raise IOError
    #else
    return (optionArray[:-1], inputFile)
    
## Takes a set of command line options and returns an input and output file
#  @param optionArray The array of options to check for an input file in
#  @param defaultOutput  What the output file should default to if not specicified.  If not default
#                     is given, an exception will be thrown if no output file is found
def getInputAndOutputFile(optionArray, defaultOutput = None):
    import os.path

    inputFile = optionArray[-2]
    if os.path.isfile(inputFile): #we have an input file and output file given
        outputFile = optionArray[-1]
        if not os.path.isfile(outputFile):
            raise IOError
        return (optionArray[:-2], inputFile, outputFile)
    else:
        if not defaultOutput: #an output file was required to be specified and we don't have both an input and output
            raise IOError
        inputFile = optionArray[-1]

        if not os.path.isfile(inputFile):
            raise IOError
        outputFile = defaultOutput
        return (optionArray[:-1], inputFile, outputFile)        

def getOutputMolecule(file, xyzOnly = False):
    import parse, os.path
    
    parser = None
    if xyzOnly: 
        parser = parse.getParser(file, keywords = {"COORDTYPE" : "XYZ"} )
    else: 
        parser = parse.getParser(file)

    if parser:
        return parser.getMolecule(weakFind=True)

def getMolecule(file, xyzOnly = False):
    #try to get output file first
    mol = getOutputMolecule(file, xyzOnly)
    if mol:
        return mol
    else: #maybe an input file
        import input
        return input.readInputFile(file)

def getComputationFromMolecule(mol, program, ZMatrix=None, keywords = {}, **kwargs):
    import input
    keywords.update(kwargs)
    newComp = input.Computation(program=program, keywords=keywords,
                                atomList=mol.getAtoms(), ZMatrix=ZMatrix, charge=mol.getCharge(),
                                multiplicity=mol.getMultiplicity(), stateSymmetry=mol.getStateSymmetry(),
                                moleculeName=mol.getTitle(), energy=mol.getEnergy() )
    #set the other attributes
    newComp.setGradients( mol.getGradients() )
    newComp.setFrequencies( mol.getFrequencies() )
    newComp.setIntensities( mol.getIntensities() )
    newComp.setDipole( mol.getDipole() )
    return newComp
    
def getComputation(file, xyzOnly=False, reorient=True, recenter=True, weakFind=False, **kwargs):
    import parse, os.path, input
    try: #maybe a pickle
        obj = load(file)
        if isinstance(obj, input.Computation): 
            return obj
    except Exception, error:
        pass

    if xyzOnly: 
        parser = parse.getParser(file, keywords = {"coordtype" : "xyz"} )
    else: 
        parser = parse.getParser(file)


    computation = None
    if parser:
        computation = parser.getComputation(weakFind)
    else:
        #oops, must be an input file
        try:
            computation = input.readInputFile(file, reorient=reorient, recenter=recenter)
        except Exception, error:
            import globalvals
            if globalvals.Debug.debug:
                print error
                print traceback(error)

    if computation:
        for key in kwargs:
            computation.setAttribute(key, kwargs[key])

    return computation

def getComputationInFolder(folder = ".", globstring = "*"):
    currentDir = os.getcwd()
    os.chdir(folder) 
    import glob
    file_list = glob.glob(globstring)
    for file in file_list:
        comp = getComputation(file)
        if comp:   
            os.chdir(currentDir)
            return comp, file 
    os.chdir(currentDir)

def getComputationsInFolder(folder = "."):
    currentDir = os.getcwd()
    os.chdir(folder) 
    comp_list = []
    file_list = [elem for elem in os.listdir(".") if not os.path.isdir(elem)]
    for file in file_list:
        comp = getComputation(file)
        if comp:
            #print file, comp.getMolecularFormula()
            comp_list.append(comp)
    os.chdir(currentDir)

    return comp_list

## Gets a list of files from an ls command in the shell
#  @param parentFolder The folder where the files are located
#  @param lsDirective  The argument for the ls command
#  @return A list of filenames (without the folder, just the filename)
def getFilesFromLS(parentFolder, lsDirective):
    currentDir = os.getcwd()
    os.chdir(parentFolder)
    lsOutput = commands.getoutput("ls %s" % lsDirective)
    if "No such file" in lsOutput:
        return "None"
    fileList = []
    for line in lsOutput.splitlines():
        splitLine = line.strip().split()
        for file in splitLine:
            fileName = os.path.split(file)[1]
            fileList.append(fileName)

    os.chdir(currentDir)
    return fileList

## Takes an object and determines if it is a list or not
def isList(object):
    obj_type = str( type(object) )
    if "tuple" in obj_type or "list" in obj_type:
        return True
    return False

## Takes a string representation of something and determines if it is a decimal number.  Returns true for floats and integers.
#  @param number The string to test
#  @return  A boolean. True if the string is a number. False otherwise.
def isNumber(number):
    try:
        x = float(number)
        return True
    except:
        return False

def load(filename):
    import pickle
    try:
        fileObj = open(filename)
        objToLoad = pickle.load(fileObj)
        fileObj.close()
        return objToLoad
    except Exception:
        return None

## Takes a string representation of something and determines if it is an integer.
#  @param number The string to test
#  @return  A boolean. True if the string is an integer. False otherwise.
def isIntegerString(number):
    try:
        stringTest = eval(number)
        if int(stringTest) == stringTest:
            return True
        else:
            return False
    except (NameError, SyntaxError, TypeError):
        return False

def isInteger(number):
    try: return int(number) == number
    except Exception: return False
       
## Takes the sys.argv array (minus the zeroth entry) and returns a formatted "command set"
#  @param options The sys.aryv[1:] array
def parseInputFlags(options):
    if len(options) == 0:
        return [] #return nothing

    commandArray = []
    for option in options:
        if option[0] == "-": #dash means new directive
            newCommand = substring1(option, 1)
            commandArray.append([newCommand, []])
        elif len(commandArray) == 0:
            sys.exit("Error in command line options")
        else: #no dash means modifier for the current directive
            commandArray[-1][1].append(option)
            
    return commandArray

def printDictionaryOfLists(dictionary):
    keyList = dictionary.keys()
    keyList.sort()
    for key in keyList:
        for element in dictionary[key]:
            print element

## Removes a number suffix from a word.  Useful in extracting atomic symbols from labels such as C1 or Li3
#  @param word The word to modify
#  @return The word without the number suffix
def removeNumberSuffix(word):
    foundNumber = False
    i = 0
    while not foundNumber and i < len(word):
        nextChar = word[i]
        if word[i].isdigit():
            foundNumber = True
        else:
            i = i + 1

    newWord = substring2(word, 0, i)
    return newWord

def getNumberSuffix(word):
    foundLetter = False
    i = len(word) - 1
    char_array = []
    while not foundLetter and i >= 0:
        if not word[i].isdigit():
            foundLetter = True
        else:
            i -= 1 

    number = word[i+1:]
    if number: return eval(number)

## Sends an e-mail
#  @param recipient The e-mail address to send to
#  @param message A string containing the message to send
#  @param subject A string giving the subject line
def sendMail(recipient, message, subject="Re:"):
    from email.Message import Message
    import smtplib
    msg = Message()
    msg['From'] = EMAIL
    msg['To'] = recipient
    msg['Subject'] = subject
    msg.set_payload(message)
    text = msg.as_string()
    server = smtplib.SMTP(SERVER_NAME)
    server.sendmail(EMAIL, recipient, text)
    server.quit()
    
    #out_file = open(message_file, "w")
    #out_file.write(message)
    #out_file.close()
    #command = "mail %s -s '%s' < %s" % (recipient, subject, message_file)
    #commands.getoutput(command)
    #os.system("rm %s" % message_file)

def substring2(oldString, startIndex, endIndex):
    newString = ""
    for i in range(startIndex, endIndex):
        newString = newString + oldString[i]
    return newString

def substring1(oldString, startIndex):
    newString = ""
    for i in range(startIndex, len(oldString)):
        newString = newString + oldString[i]
    return newString

## Saves a class to a given location
#  @param object The class to be saved
#  @param fileName  The file to hold the class
def save(object, fileName):
    import pickle
    file = open(fileName, "w")
    pickle.dump(object, file)
    file.close()

def toString(item, capitalize=False):
    item_type = str( type(item) )
    if "float" in item_type:
        return "%14.10f" % item
    elif hasattr(item, "__iter__"):
        return " ".join(map(toString, item))
    elif "int" in item_type:
        return "%d" % item
    else: # a string or something that can be cast as a string
        newString = "%s" % item
        if capitalize: return newString.upper()
        else: return newString
    
## Prints usage information for a given module
#  @param program The program name
#  @param programLine A string giving the structure of the command line input
#  @param shortOptions See Python getopt docs
#  @param longOptions See Python getopt docs
def usage(program, programLine, shortOptions, longOptions):
    usageArray = ["Usage: %s %s" % (program, programLine),
                  "Options:"]
    optionsToAdd = []
    i = 0
    while i < len(shortOptions):
        entry = shortOptions[i]
        if len(optionsToAdd) == 5:
            usageArray.append("\t" + str(optionsToAdd))
            optionsToAdd = []
        if (i+1)  < len(shortOptions) and shortOptions[i+1] == ":":
            optionsToAdd.append("-" + entry + " [OPTION]")
            i += 1
        else:
            optionsToAdd.append("-" + entry)
        i += 1
    usageArray.append("\t" + str(optionsToAdd))
    optionsToAdd = []
    for entry in longOptions:
        if len(optionsToAdd) == 2:
            usageArray.append("\t" + str(optionsToAdd))
            optionsToAdd = []
        if "=" in entry:
            optionsToAdd.append("--" + entry.strip("=") + " [OPTION]")
        else:
            optionsToAdd.append("--" + entry.strip("="))
    usageArray.append("\t" + str(optionsToAdd))        

    usageText = "\n".join(usageArray)
    sys.stderr.write(usageText + "\n")   

def splitArrayText(text):
    import re
    text = re.compile("[\(\[\)\]]").sub("", text)
    arr = re.compile("[, ]+").split(text)
    return arr

def isBoolean(str_text):
    if str_text.upper() == "FALSE" or str_text.upper() == "TRUE":
        return True
    else: return False

def strToBool(value):
    if value.upper() == "TRUE": return True
    elif value.upper() == "FALSE": return False

## Takes an unknown data type.  If it is a string, it returns the upper case
#  If it is not a string, then it just returns the value
#  @param value The attribute to canonicalize
#  @return The canonicalized value.  An uppercase string or the original value
def canonicalize(value):
    if hasattr(value, 'lower'):
        return value.lower()
    else:
        return value

## Takes a string and converts to appropriate data type, for example boolean or number or upper case string
def stringToDataType(value, capitalize=True):
    if isNumber(value): return eval(value)
    elif isBoolean(value): return strToBool(value)#either true or false text
    else: 
        #I guess we have a regular string
        if capitalize: return value.upper()
        else: return value

def constrainedSearch(file, folder):
    matches = []

    def walker(match_list, dirname, names):
        if folder in dirname:
            for name in names:
                if file in name:
                    match_list.append( os.path.join(dirname, name) )

    os.path.walk(".", walker, matches)
    print matches

def traceback(error=None):
    import sys
    import traceback
    if error:
        tb_list = traceback.format_tb(sys.exc_info()[2])
        return "%s\n%s" % (error, "\n".join(tb_list))
    else:
        import StringIO
        output = StringIO.StringIO()
        traceback.print_stack(file=output)
        contents = output.getvalue()
        return contents


## Reads the dispcart file and stores the coordinates in a list of 2-D coordinate arrays.  This
#  is only set up to read a file named "dispcart" in the current working directory.
#  @return A list of molecules
def readDispCart():
    import re
    fileText = ""
    try:
        import glob
        disp_file = glob.glob("*dispcart*")[0]
        fileText = open(disp_file).read()
    except (IOError, IndexError):
        raise CannotProceedError
        
    allXYZ = []
    def getNextXYZ(geomText, geomNumber):
        geomLines = re.compile("\s+([-]?\d+[.]\d+)\s+([-]?\d+[.]\d+)\s+([-]?\d+[.]\d+)").findall(geomText)
        coordinates = []
        for line in geomLines:
            (x, y, z) = map(eval, line)
            coordinates.append( [x, y, z] )
        allXYZ.append(coordinates)

    geomNumber = 1
    regExp = r"(?<!\d)%d\s*\n(.*?)\n%d\s*\n"
    geomFound = re.compile(regExp % (geomNumber, geomNumber + 1), re.DOTALL).search(fileText)
    while geomFound: #while we are still finding geometry
        geomText = geomFound.groups()[0]
        getNextXYZ(geomText, geomNumber)
        #try for the next geometry
        geomNumber += 1
        geomFound = re.compile(regExp % (geomNumber, geomNumber + 1), re.DOTALL).search(fileText)        
    #pick up the last set of coordinates
    geomText = re.compile("(?<!\d)%d\s*\n(.*)" % geomNumber, re.DOTALL).search(fileText).groups()[0]
    getNextXYZ(geomText, geomNumber)

    return allXYZ

def matchTraceback(file, lineNumber, routine):
    tracebackText = traceback()
    lineFlag = "line %d" % lineNumber
    for line in tracebackText.splitlines():
        if file in line and lineFlag in line and routine in line:
            return True
    return False

def findMolecule(args, dirname, files):
    mollist, glob = args
    import parse, re
    print dirname
    for file in files:
        if glob and not re.compile(glob).match(file):
            continue

        path = os.path.join(dirname, file)
        mol = getComputation(path)
        if mol:
            mollist.append( (path, mol) )

def findParser(args, dirname, files):
    parserlist = args[0]
    import parse
    for file in files:
        path = os.path.join(dirname, file)
        ispickle = load(path)
        if ispickle:
            continue
        parser = parse.getParser(path)
        if parser:
            parserlist.append( (path, parser) )
    

def walkForParsers(dirname = "."):
    parserlist = []
    os.path.walk(dirname, findParser, (parserlist,))
    return parserlist

def walkForMolecules(dirname = ".", glob=None):
    mollist = []
    os.path.walk(dirname, findMolecule, (mollist, glob))
    return mollist

def resubmit(args, dirname, files):
    import os.path, parse, quantum
    type, machine, baseFolder, searchFolder, rename, attrs = args

    for file in files:
        filepath = os.path.join(dirname, file)
        parser = parse.getParser(filepath)
        if parser:
            comp = parser.getComputation()
            if comp:
                for attr in attrs:
                    comp.setAttribute(attr, attrs[attr])
                newTask = quantum.taskmake(comp, type)
                #at this point the task has customized its own directory
                if not rename: #if we want to keep the same directory structure
                    lastFolder = os.path.split(searchFolder)[-1]
                    newFolder = os.path.join(baseFolder, dirname.split(lastFolder)[1]).strip("/") #this is a relative path
                    newTask.setFolder(newFolder)
                if machine:
                    machine.runTasks(newTask)
                else:
                    newTask.writeFile()
                    
def submitanew(classtype, folder = ".", machine=None, rename=False, **kwargs):
    import os.path
    args = classtype, machine, os.getcwd(), folder, rename, kwargs
    os.path.walk(folder, resubmit, args)


def getEnergyPoints(*kargs,**kwargs):
    points = []
    from data import DataPoint, DataSet
    from parse import getParser
    import os

    globopt = None
    if kwargs.has_key('glob'):
        globopt = kwargs['glob']
        del kwargs['glob']
    topdir = os.getcwd()

    def grabEnergy(args, dirname, files):
        os.chdir(dirname)
        filelist = files
        if globopt:
            import glob
            filelist = glob.glob(globopt)

        for file in filelist:
            parser = getParser(file)
            if parser:
                comp = parser.getComputation()
                if comp:
                    all_energies = parser.getAllEnergies()
                    for dpoint in all_energies:
                        for attr in kargs:
                            dpoint.setAttribute(attr, comp.getAttribute(attr))
                        for attr in kwargs:
                            fullname = attr
                            storename = kwargs[attr]
                            dpoint.setAttribute(storename, comp.getAttribute(fullname))
                        points.append(dpoint)
        os.chdir(topdir)

    import os.path
    os.path.walk(".", grabEnergy, None)

    dset = DataSet(points)
    return dset

def addPythonPath(folder):
    import os, sys
    sys.path.append(folder)


def arrayToText(arr, format):
    str_arr = []
    for entry in arr:
        str_arr.append( format % entry )
    return "\n".join(str_arr)

def arraysEqual(arr1, arr2):
    if not len(arr1) == len(arr2):
        return False

    for i in xrange(len(arr1)):
        if not abs(arr1[i] - arr2[i]) < 1e-10:
            return False

def matchesType(value, *xargs):
    for datatype in xargs:
        if isinstance(value, datatype):
            return True
    return False

def isArray(value):
    import numpy
    return matchesType(value, tuple, list, numpy.ndarray)
    

def getDataSets(folder = ".", glob = None):
    globString = glob
    import os, data
    topdir = os.getcwd()
    filelist = []
    if globString:
        import glob
        filelist = glob.glob(globString)
    else:
        filelist = os.listdir()

    dset = data.DataSet()
    os.chdir(folder)
    for file in filelist:
        obj = load(file)
        if isinstance(obj, data.DataSet):
            dset.add(obj)
    return dset

def acquire(msg):
    msg = "%s:\n" % msg
    entries = []
    entry = "start"
    try:
        while 1:
            entry = raw_input(msg).decode("utf-8")
            entries.append(entry)
            msg = ""
    except KeyboardInterrupt:
        pass

    return "\n".join(entries)

