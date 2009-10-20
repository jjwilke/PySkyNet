from RM import *
from errors import *

SCREEN_WIDTH = 80

"""
Example usage

    from getoptions import *

    #set the allowed command line options and user messages
    options = [
        InputOption(shortOption='s', longOption='save', optionTypes='file', valuesMandatory=True),
        InputOption(shortOption='a', longOption='action', optionTypes=['string'], valuesMandatory=True),
        InputOption(longOption='linx', optionTypes='int', listOfValues=True, valuesMandatory=True),
        InputOption(longOption='liny', optionTypes='int', listOfValues=True, valuesMandatory=True),
        ]
    optionList = OptionList(commandName="clip",
                            usageStructure=[ "[options]"],
                            optionsList=options)

    options_given = readOptions(optionList)
   
    #default options

    for option in options_given:

        if option in ('s', 'save'):
            filename = optionList[option].getValue()
            mol = getComputation(filename, xyzOnly, recenter, reorient, weakFind)
            if mol: 
                save(mol, MOLECULE_FILE)
            else:
                print "I don't think this is a valid file."
                harikari()

        elif option in ('', 'xyz'):
            xyzOnly = True

        elif option in ('', 'xyzfile'):
            mol = load(MOLECULE_FILE)
            print mol.getXYZFile()

        elif option in ('', 'zpve'):
            mol = load(MOLECULE_FILE) 
            zpve = mol.getZPVE()
            print zpve

"""

class OptionSet:
    
    def has(self, attr):
        return hasattr(self, attr)

class InputOption:

    regExpressions = {
        "int" : "[-]?\d+",
        "+int" : "[+]?\d+",
        "-int" : "[-]\d+",
        "number" : "[-]?\d+[.]?\d*",
        "+number" : "[+]?\d+[.]?\d*",
        "-number" : "[-]\d+[.]?\d*",
        "string" : ".*",
        "range" : "[-+]?\d=[.]?\d*\s*[-]\s*[-+]?\d=[.]?\d*",
        "intrange" : "[-+]?\d+\s*[-]\s*[-+]?\d+",
        "file" : ".*",
        }
    
    readMethods = {
        "intrange" : 'readRange',
        "range" : 'readRange',
        "file" : 'readFile',
    }

    fullDescriptions = {
        "string" : "String",
        "int" : "Integer",
        "+int" : "Positive Integer",
        "-int" : "Negative Integer",
        "+number" : "Positive Number",
        "-number" : "Negative Number",
        "number" : "Any numeric value",
        "range" : "Range of Numbers",
        "intrange" : "Range of Integers",
        "file" : "Filename",
        }

    numericTypes = [ "int", "+int", "-int", "+number", "-number" ]

    ## Constructor
    #  @param shortOption the one letter - option from the command line
    #  @param longOption the one word -- option from the command line
    #  @param optionType  the allowed option type. Allowed types are
    #   string, int, +int, -int, number, +number, -number, 
    #   range(a range of numbers as 1.2-3.5), intrange(a range of integers)
    #  @param isList Whether or not a list of values is to be specified or a single value
    #  @param valuesMandatory Whether or not we absolutely expect values to be given, or if values are "optional"
    #  @param allowedOptions an explicit list of allowed options if only a few options should be allowed.
    #  @param default A default value if none is specified
    #  @param bind Whether to bind the long option name to a variable name
    def __init__(self, shortOption=None, longOption=None, optionType='string', listOfValues=False, valuesMandatory=False, restrictedValues=None, default=None, bind=False, setbool=False, allowValues=True):
        self.shortOption = shortOption
        self.longOption = longOption

        self.optionType = optionType.lower()
        
        self.restrictedValues = restrictedValues
        self.values = []

        self.isList = listOfValues
        self.valuesMandatory = valuesMandatory
        self.allowValues = allowValues


        if default == None:
            self.default = None
        else:
            self.default = str(default)

        self.bind = bind

        self.setbool = setbool
        if setbool:
            self.default = None
            self.allowValues = False
            self.bind = True
            self.values = [False]

    def __str__(self):
        str_array = []
        str_array.append( "%s,%s" % ( self.getShortOptionDescription(), self.getLongOptionDescription() ) )
        if self.optionType: #we may or may not actually, expect options
            str_array.append( "Expected Type: %s" % self.optionType )
        if self.values:
            str_array.append("Values Given:")
            str_array.append("\n".join( map(toString, self.values) ) )
        return "\n".join(str_array)

    def setFound(self):
        if self.setbool:
            self.values = [True]

    def hasDefault(self):
        return self.default

    def chooseDefault(self):
        if not self.default:
            return

        self.reset()
        if self.isList:
            for entry in self.default:
                self.addEntry(entry)
        else:
            self.addValue(self.default)

    def compare(self, other):
        cmp1 = self.getCompareString() ; cmp2 = other.getCompareString()
        if cmp1 > cmp2: return 1
        elif cmp1 == cmp2: return 0
        else: return -1
    staticmethod(compare)

    def isNumeric(self):
        return self.optionType in self.numericTypes

    def getCompareString(self):
        if self.shortOption: return self.shortOption
        else: return self.longOption        

    def addValue(self, value):
        if not self.allowValues:
            raise InvalidValueError(option=self.getOptionDescription(), value=value,
                                     error="Option does not take any values")

        #first, check if the value meets the "optionType" criteria
        converted_value = self.checkValue(value) #this might throw an exception
        #here, a converted value is returned as specified by the regular expression
        #i.e. if it is an integer, convert to an integer, etc.   

        if not self.isList and self.values: #we already have a value
            raise InvalidValueError(option=self.getOptionDescription(), value=value,
                                     error="Only one value should be specified, not a list of values.")

        self.values.append(converted_value)

    def reset(self):
        if type(self.values) == list: self.values = []
        else: self.values = None

    def checkValue(self, value):
        import re

        #first, we might have been given only a finite set of allowed options
        if self.restrictedValues:
            if self.isNumeric():
                value = eval(value)
            if value in restrictedValues: return value

            #nope... no good
            raise InvalidValueError( option=self.getOptionDescription(), value=value,
                                     error="Input value not in allowed values:\n%s" % "\n".join( map(toString, self.restrictedValues) )  )

        
        #first verify the format
        pattern = self.regExpressions[self.optionType]
        if not re.match(pattern, value):
            #if we have gotten to this point, then the value did not match any of the allowed types
            errorMessage = "Expected a value of type:\n%s" % self.optionType
            raise InvalidValueError(option="%s,%s" % (self.shortOption, self.longOption), value=value, error=errorMessage)

        if self.readMethods.has_key(self.optionType):
            return getattr(self, self.readMethods[self.optionType])(value)
        elif self.isNumeric():
            return eval(value)
        else:
            return value

    def readFile(self, value):
        import os.path
        if not os.path.isfile(value):
            raise InvalidValueError(option="%s" % (self.longOption), value=value, error="Invalid Filename")
        return value

    def readRange(self, value):
        start, stop = map(eval, value.split("-"))
        values = []
        for i in range(start, stop+1):
            values.append(i)
        return values

    def getShortOption(self):
        return self.shortOption
        
    def getShortOptionDescription(self):
        if self.shortOption: return "-%s%s" % (self.shortOption, self.getOptionsString() )
        else: return None

    def getLongOption(self):
        return self.longOption
    
    def getLongOptionDescription(self):
        if self.longOption: return "--%s%s" % (self.longOption, self.getOptionsString() )
        else: return None

    def getValue(self):
        try:
            return self.values[0]
        except IndexError:
            if not self.valuesMandatory:
                return None

            option = self.longOption
            if self.shortOption:
                option += ",%s" % self.shortOption
            raise InvalidValueError(option=option, value="", error="No value given")

    def getValues(self):
        return self.values

    def getOptionDescription(self):
        desc = []
        if self.shortOption: desc.append("-%s" % self.shortOption)
        if self.longOption: desc.append("--%s" % self.longOption)
        return ",".join(desc)

    def getOptionsString(self):
        if self.isList and self.valuesMandatory:
            return " [OPTIONLIST]"
        elif self.isList:
            return " [?OPTIONLIST]"
        elif self.optionType and self.valuesMandatory: #this means that we do expect options
            return " [OPTION]"
        elif self.optionType: #this means options can be given, but not necessary
            return " [OPTION?]"
        else: #this means we do not expect any options to be given
            return ""

    def hasMandatoryValue(self):
        if self.valuesMandatory and not self.values: #oops
            return False
        return True

    def isBound(self):
        return self.bind

    def bindValue(self, optionSet):
        if not self.values: #nothing to bind   
            return 

        if not optionSet: #null value
            sys.exit("Trying to bind value to null object")

        if self.isList:
            setattr(optionSet, self.longOption, self.getValues())
        else:
            setattr(optionSet, self.longOption, self.getValue())

    def getName(self):
        if self.longOption:
            return self.longOption
        else:
            return self.shortOption

    def isFound(self, optlist):
        return self.longOption in optlist or self.shortOption in optlist


class OptionValueIterator:

    def __init__(self, optionsList, optionsObj):
        self.iter = iter(optionsList)
        self.optionsObj = optionsObj
        self.optionsList = optionsList

    def next(self):
        nextElement = self.iter.next()
        while nextElement in self.optionsObj.BUILT_INS:
            self.optionsObj.processBuiltIn(nextElement)
            nextElement = self.iter.next()
        return nextElement

    def __iter__(self):
        self.iter = iter(self.optionsList)
        return self

class OptionList:
    
    BUILT_INS = ['debug']

    def __init__(self, commandName, usageStructure = ["[options]"], optionsList=[]):
        self.commandName = commandName
        self.usageStructure = []
        for entry in usageStructure: 
           self.usageStructure.append( entry.upper() )
        self.optionsList = {}
        for option in optionsList:
            shortOption = option.getShortOption()
            longOption = option.getLongOption()
            if shortOption: 
                self.optionsList[shortOption] = option
            if longOption: 
                self.optionsList[longOption] = option

        #always add the debug flag
        debug = InputOption(longOption='debug', valuesMandatory=True, optionType='int')
        self.optionsList['debug'] = debug


    def processBuiltIn(self, option):
        if option in ('', 'debug'):
            import globalvals
            debug = self[option].getValue()
            globalvals.Debug.debug = debug

    def __str__(self):
        str_array = []
        for entry in self.optionsList:
            str_array.append("%s %s" % (entry, str(self.optionsList[entry].getValue())))
        return "\n".join(str_array)


    def __getitem__(self, key):
        return self.optionsList[key]

    def __iter__(self):
        #we have a problem at this point... which is that the list
        #actually contains two copies of everything
        valueList = self.optionsList.values()
        #let's cut out the doubles using a hash table
        hashList = {}
        for value in valueList: hashList[value] = 0
        #okay doubles, cut out
        newValueList = hashList.keys()
        #now sort it
        newValueList.sort(cmp=InputOption.compare)
        return iter(newValueList)

    
    def isOptionValid(self, option):
        for entry in self:
            if option[:2] == "--": 
                longOption = entry.getLongOption()
                if longOption == option[2:]: 
                    return True
            elif option[0] == "-":
                shortOption = entry.getShortOption()
                if shortOption == option[1:]: 
                    return True
        #if we got here, none of the options matched the given option
        return False

    def usage(self):
        usage_array = []
        #first, make the initial usage line
        line = "Usage: %s" % self.commandName
        for entry in self.usageStructure:
            line += " %s" % entry
        usage_array.append(line)

        #first do all the short options
        line = ""
        for option in self:
            shortOption = option.getShortOptionDescription()
            if shortOption:
                if len(shortOption) + len(line) > SCREEN_WIDTH:
                    usage_array.append( line.strip(",") )
                    line = "%s" % shortOption
                else: line += ", %s" % shortOption
        usage_array.append( line.strip(",") )

        #now do all the long options
        line = ""
        for option in self:
            longOption = option.getLongOptionDescription()
            if longOption:
                if len(longOption) + len(line) > SCREEN_WIDTH:
                    usage_array.append( line.strip(",") )
                    line = "%s" % longOption
                else: line += ", %s" % longOption
        usage_array.append( line.strip(",") )

        return "\n".join(usage_array)
        
import sys
def readOptions(optionList, optionsInput=sys.argv[1:], optionSet=None):
    options_given = []
    try:
        current_option = None
        for entry in optionsInput:
            if entry == "--help": #should be standard for all
                print optionList.usage()
                sys.exit()
            elif entry[0] == "-":
                #check to see if it is a valid option
                if not optionList.isOptionValid(entry): 
                    raise InvalidOptionError(entry)
                #if we got here, option is valid
                current_option = entry.strip("-")
                #hmm, okay, we'll overwrite what's there
                if current_option in options_given: 
                    optionList[current_option].reset()
                else: 
                    options_given.append(current_option)

                optionList[current_option].setFound()

            else:
                try:
                    optionList[current_option].addValue(entry)
                except KeyError:
                    raise InvalidOptionError(entry)

        #at the vary last now, go through all the options given
        #and if any options required values, but were not given any
        #throw an exception
        for option in options_given:
            if not optionList[option].hasMandatoryValue():
                raise InvalidValueError(option, value=None, error="No value given, but option requires value.")

        for option in optionList:
            if not option.hasDefault() or option.isFound(options_given):
                continue
            options_given.append(option.getName())
            option.chooseDefault()

        for option in optionList:  
            if option.isBound(): option.bindValue(optionSet)

        #return all the options that were specified
        opts = OptionValueIterator(options_given, optionList)

        for opt in opts: #loop through to process anything
            pass

        return opts

    except InvalidOptionError, error:
        print error
        #here, the usage should be printed so the person knows what are valid options
        print optionList.usage()
        sys.exit()
    except InvalidValueError, error:
        print error
        #here there is no need to print the usage string because the person has specified a valid option
        #but simply given an incorrect value
        sys.exit()

