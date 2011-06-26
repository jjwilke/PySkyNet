from skynet.errors import *
from skynet.utils.utils import *
from skynet.identity import *
import sys 
import numpy
import math

FROM_AU = {
    'angstrom' : 0.5291772108,
    'aj' : 4.3597441775,
    'bohr' : 1,
    'hartree' : 1,
    'kcal' : 627.51,
    'wavenumber' : 219474.63,
    'ev' : 27.211396,
    'kj' : 2625.5,
    'hartree/bohr' : 1,
    'mdyne' : 8.238725558311,
    'm' : 0.5291772108e-10,
    'nj' : 4.3597441775e-9,
    'degree' : 180/numpy.pi,
    'radian' : 1,
    'mhz' : 6579684000,
}

EXPAND_UNITS = {
'mdyne' : [1, "aj/angstrom"],
'mb' : [1e-31, "m^2"],
'cm' : [0.01, 'm'],
#'km' : [1e3, 'm'],
}

UNIT_TYPES = {
    '1' : '',
    'wavenumber' : 'energy',
    'hartree' : 'energy',
    'mol' : 'moles',
    'mhz' : 'energy',
    'aj' : 'energy',
    'nj' : 'energy',
    "j" : "energy",
    "kmmol" : "intensity",
    "kcal" : "energy",
    "kj" : "energy",
    "mol" : "mole",
    'angstrom' : 'distance',
    'bohr' : 'distance',
    'm' : 'distance',
}

#calculates the projection of vector1 onto vector2
def projection(vector1, vector2):
    numerator = numpy.dot(vector1, vector2)
    denominator = numpy.dot(vector2, vector2)
    component = numerator/denominator
    newVector = []
    for x in vector2:
        newVector.append(x * component)

    return newVector

def convertUnits(value, old,  new):
    if isinstance(old, Unit):
        conv = old.getConversion(new)
    elif isinstance(new, Unit):
        conv = 1.0/new.getConversion(old)
    else:
        conv = FROM_AU[new.lower()] / FROM_AU[old.lower()]
    return conv * value

class Component(Identity):
    
    def __init__(self, name, degree):
        self.name = name
        self.factor = 1.0
        self.degree = degree

    def __str__(self):
        if not self.degree:
            return ""
        out = "%s" % self.name
        if self.degree != 1:
            out += "^%d" % self.degree
        return out

    def increment(self, name, degree):
        self.degree += degree
        self.factor *= convertUnits(1.0, name, self.name)**degree

    def getDegree(self):
        return self.degree

    def getFactor(self):
        return self.factor

    def setFactor(self, conv):
        self.factor = conv

    def getConversion(self, other):
        conv = (FROM_AU[other.getName()] / FROM_AU[self.name])**self.degree
        return conv

    def divide(self, other):
        inv = other.copy()
        inv.invert()
        self.multiply(inv)

    def multiply(self, other):
        self.increment(other.name, other.degree)

    def getName(self):
        return self.name

    def convert(self, other):
        conv = self.getConversion(other)
        self.factor *= conv
        self.name = other.name

    def invert(self):
        self.degree = -1 * self.degree
        self.factor = 1.0/self.factor


class Unit(Identity):
    
    def __init__(self, flag, factor=1.0):
        #add an optional conversion factor
        self.factor = factor

        self.components = {}
        if not flag:
            return #nothing to do
        values = flag.lower().replace("(", "").replace(")", " ").replace("*", " ").split("/")
        numerator = values[0].split()
        self.processList(numerator)
        if len(values) > 1: #denominator
            denominator = values[1].split()
            self.processList(denominator, -1)

    def __eq__(self, other):
        return str(self) == str(other)

    def __repr__(self):
        return self.__str__()

    def __str__(self):
        str_arr = []
        for comp in self.components:
            str_arr.append(str(self.components[comp]))
        return " ".join(str_arr)

    def __mul__(self, other):
        newunits = self.copy()
        newunits.multiply(other)
        return newunits
    
    def __div__(self, other):
        newunits = self.copy()
        newunits.divide(other)
        return newunits

    def __pow__(self, number):
        newunits = self.copy()
        newunits.exponential(number)
        return newunits

    def consolidate(self):
        factor = self.factor
        for type in self.components.keys():
            comp = self.components[type]
            factor *= comp.getFactor()
            comp.setFactor(1.0)
            if self.components[type].getDegree() == 0:
                del self.components[type]
        self.factor = 1.0
        return factor

    def divide(self, other):
        inv = other.inverse()
        self.multiply(inv)

    def multiply(self, other):
        othercomp = other.getComponents()
        for type in othercomp:
            if not type in self.components:
                self.components[type] = othercomp[type].copy()
            else:
                self.components[type].multiply(othercomp[type])
        self.factor *= other.factor


    def processList(self, list, factor=1):
        for val in list:
            unit, exp = self.processValue(val)
            exp *= factor
            if unit in EXPAND_UNITS:
                factor, flag = EXPAND_UNITS[unit]
                flag = "%s^%d" % (flag, exp)
                unit = Unit(flag, factor)
                self.multiply(unit)
            else:
                type = UNIT_TYPES[unit]
                if not type: #unitless quantity
                    pass
                elif not type in self.components:
                    self.components[type] = Component(unit, exp)
                else:
                    self.components[type].increment(unit, exp)

    def processValue(self, val):
        values = val.split("^")
        unit = values[0]
        exp = 1
        if len(values) > 1:
            exp = eval(values[1])
        return unit, exp

    def getComponents(self):
        return self.components

    def convert(self, newunits):
        unitObj = newunits
        if not isinstance(unitObj, Unit):
            unitObj = Unit(newunits)
        otherComps = unitObj.getComponents()
        for comp in otherComps:
            other = otherComps[comp]
            selfcomp = self.components[comp]
            selfcomp.convert(other)

    def getConversion(self, newunits):
        unitObj = newunits
        if not isinstance(unitObj, Unit):
            unitObj = Unit(newunits)
        otherComps = unitObj.getComponents()
        conv = 1.0
        for comp in otherComps:
            other = otherComps[comp]
            selfcomp = self.components[comp]
            conv *= selfcomp.getConversion(other)
        return conv

    def inverse(self):
        newunits = self.copy()
        newunits.invert()
        return newunits
    
    def invert(self):
        for comp in self.components:
            self.components[comp].invert()

def sqrt(value):
    if isinstance(value, DataPoint):
        return value.sqrt()
    else:   
        import math
        return math.sqrt(value)

class DataPointIterator:

    def __init__(self, dataPoint):
        self.dataPoint = dataPoint
        self.dataIter = iter(dataPoint.getValue())

    def __iter__(self):
        return self

    def next(self):
        nextValue = self.dataIter.next()
        valueFormats = self.dataPoint.getValueFormats()
        attributes = {}
        units = self.dataPoint.getUnits()
        return DataPoint(nextValue, units, valueFormats = valueFormats, attributes=attributes)

class Item(Identity):
        
    def __init__(self, attributes = None, **kwargs):
        finalAttributes = {}

        if not attributes:
            attributes = {}
        finalAttributes.update(attributes)
        finalAttributes.update(kwargs)
        self.attributes = {}
        for attr in finalAttributes:
            self.attributes[attr.lower()] = finalAttributes[attr.lower()]
        self.matchCriteria = []

    def __str__(self):
        str_arr = []
        for attr in self.attributes:
            str_arr.append("%s=%s" % ( str(attr).lower(), str(self.attributes[attr]).lower() ) )
        return "\n".join(str_arr)

    def getAttribute(self, attr):
        try: 
            return self.attributes[attr.lower()]
        except KeyError:
            return None

    def hasAttributes(self, attrlist):
        for attr in attrlist:
            if not self.hasAttribute(attr):
                return False
        #nope, we have them all
        return True

    def hasAttribute(self, attr):
        return self.attributes.has_key(attr.lower())

    def makeAttribute(self, name, *xargs):
        val_arr = []
        #combine the attributes into one
        for attr in xargs:
            attrval = self.getAttribute(attr)
            if attrval:
                val_arr.append(str(attrval))
            else:
                return #we don't have all the necessary attributes
        newval = " ".join(val_arr)
        self.setAttribute(name, newval)

    def getAttributes(self, *xargs):
        if xargs:
            attrs = {}
            for name in xargs:
                attrs[name] = self.getAttribute(name)
            return attrs
        else:
            return self.attributes.copy()

    def setAttribute(self, attr, value):
        #if isinstance(value, str):
        #    value = value.lower()
        self.attributes[attr.lower()] = value

    def setAttributes(self, attributes=None, **kwargs):
        DataSet.mergeAttributes(attributes, kwargs)
        for attr in kwargs:
            #we want to make sure this is the data point attribute setter
            Item.setAttribute(self, attr, kwargs[attr])

    def getCommonAttributes(self, dataPoint):
        otherAttributes = dataPoint.getAttributes()
        newAttributes = otherAttributes.copy()

        for attr in newAttributes.keys():
            selfAttr = self.getAttribute(attr)
            if selfAttr and DataPoint.attributeMatches(selfAttr, dataPoint.getAttribute(attr)):
                pass #leave it
            else:
                del newAttributes[attr] #delete it

        return newAttributes

    def getCommonAttributeNames(self, dp):
        selfnames = self.getAttributes().keys()
        dpnames = dp.getAttributes().keys()

        name_list = []
        for name in selfnames:
            if name in dpnames:
                name_list.append(name)
        return name_list

    def attributeMatches(cls, val1, val2):
        if val1 == val2:
            return True
        elif isinstance(val1, str) and isinstance(val2, str) and val1.lower() == val2.lower():
            return True
        else:
            return False
    attributeMatches = classmethod(attributeMatches)

    def matches(self, arg, match = []):
        #we are either trying to match a set of attributes or a data point
        matchAttributes = arg
        #if we are matching a data point, we must determine the attributes we want to try to match
        if isinstance(arg, DataPoint):
            #use whichever data point attributes are less specific, i.e. fewer
            attributeNames = self.getCommonAttributeNames(arg)
            matchAttributes = {}
            #we need to know if specific attributes are to be used in matching
            allMatch = not self.matchCriteria and not match
            for attr in attributeNames:
                #we only want include this if specifically told by
                #the matching criteria
                if allMatch or attr in self.matchCriteria or attr in match:
                    matchAttributes[attr] = arg.getAttribute(attr)

        try:
            for attr in matchAttributes:
                foundMatch = False #assume no match
                potential_matches = matchAttributes[attr]
                self_value = self.attributes[attr.lower()]
                #we need to handle lists of potential matches
                if not isinstance(potential_matches, list):
                    potential_matches = [potential_matches]
                for potential_match in potential_matches:
                    if DataPoint.attributeMatches(potential_match, self_value):
                        foundMatch = True
                        break
                #if we have gotten here, none of the above ifs matched... this data point does not match the requirements
                if not foundMatch:
                    return False
            #if they all match
            return True
        except KeyError:
            return False

    def addMatchCriteria(self, attr):
        self.matchCritera.append(attr)

    def setMatchCriteria(self, *matchCriteria):
        del self.matchCriteria[:]
        for entry in matchCriteria:
            if self.hasAttribute(entry):  #we only want to worry about attributes we actually have
                self.matchCriteria.append(entry)

    def resetMatchCriteria(self):
        self.matchCriteria = []


class DataPoint(Item):
    
    DEFAULT_FORMATS = {
        'latex' : Formatter(float="$%5.2f$", plus=True),
        'default' : Formatter(),
    }
    
    def __new__(cls, value, units = None, valueFormats = {}, attributes = {}, **kwargs):
        storeValue = None
        clsType = None
        #copy attributes... we don't want to link to the passed in attributes
        finalAttributes = attributes.copy()
        #check whether we are replicating another data point
        if isinstance(value, DataPoint):
            finalAttributes.update(value.getAttributes())
            storeValue = value.getValue()
        else:
            storeValue = value
 
        import data
        #check what type of data we have
        if isArray(value):
            storeValue = numpy.array(storeValue)
            clsType = data.DataPointArray
        else:
            storeValue = value
            clsType = data.DataPointValue
 
        #get the units set up
        if "units" in finalAttributes:
            units = finalAttributes["units"]
        unitObj = units
        if not isinstance(unitObj, Unit):
            unitObj = Unit(units)
 
        #fix the value
        factor = unitObj.consolidate()
        if factor != 1.0:
            storeValue = factor * storeValue
 
        #check value formats
        valueFormats = valueFormats.copy()
        for type in cls.DEFAULT_FORMATS:
            if not valueFormats.has_key(type):
                #make sure we have a default format
                valueFormats[type] = cls.DEFAULT_FORMATS[type]
 
        return object.__new__(clsType, storeValue, units, valueFormats, attributes)

    def __init__(self, value, units = None, valueFormats = {}, attributes = {}, **kwargs):
        DataSet.mergeAttributes(attributes, kwargs)
        Item.__init__(self, attributes=kwargs)
        self.setValue(value)
        self.setUnits(units)
        self.valueFormats = valueFormats

    def __bool__(self):
        return True

    def __len__(self):
        return 1

    def getValue(self, units=None):
        selfunits = self.getUnits()
        if units:
            conv = selfunits.getConversion(units)
            return conv * self.value
        else:
            return self.value

    def resetValueFormats(self):
        for type in self.DEFAULT_FORMATS:
            #make sure we have a default format
            valueFormats[type] = self.DEFAULT_FORMATS[type]
        
    def setValue(self, value, units=None):
        storeValue = value
        if isinstance(value, DataPoint):
            if not units:
                units = value.getUnits()
            storeValue = value.getValue(units)

        if isArray(storeValue):
            if not self.__class__ == DataPointArray:
                raise ProgrammingError("Cannot assign array to a non-array data point type")
            self.value = numpy.array(storeValue)
        else:
            if not self.__class__ == DataPointValue:
                raise ProgrammingError("Cannot assign value to an array data point type")
            self.value = storeValue

        if units:
            self.setUnits(units)

    def convertUnits(self, newUnits):
        try:
            selfunits = self.getUnits()
            selfunits.convert(newUnits)
            factor = selfunits.consolidate()
            self.value *= factor
        except KeyError:
            raise DataError("could not convert units")

    def __abs__(self):
        dp = self.copy()
        dp.setValue( abs(self.value) )
        return dp

    def __neg__(self):
        dp = self.copy()
        dp.setValue(-self.value)
        return dp

    def __add__(self, other):
        dp = self.copy()
        val1, val2, units, attributes = self.matchDataPoint(other)
        #make sure the units 
        return DataPoint(val1 + val2, units=units, valueFormats = self.valueFormats, attributes = attributes)

    def __radd__(self, other):
        val1, val2, units, attributes = self.matchDataPoint(other)
        #make sure the units 
        return DataPoint(val1 + val2, units=units, valueFormats = self.valueFormats, attributes = attributes)

    def __sub__(self, other):
        val1, val2, units, attributes = self.matchDataPoint(other)
        #make sure the units 
        return DataPoint(val1 - val2, units=units, valueFormats = self.valueFormats, attributes = attributes)

    def __rsub__(self, other):
        val1, val2, units, attributes = self.matchDataPoint(other)
        #make sure the units 
        return DataPoint(val1 - val2, units=units, valueFormats = self.valueFormats, attributes = attributes)

    def __str__(self):
        str_arr = []
        str_arr.append("%s %s" % (self.value, self.units))
        str_arr.append(Item.__str__(self))
        return "\n".join(str_arr)

    def __repr__(self):
        value = str(self.value)
        units = self.getUnits()
        if units:
            value += " %s" % units
        return value

    def reverse(self):
        self.value.reverse()

    def sort(self):
        self.value.sort()

    def getTranspose(self):
        new = self.copy()
        new.transpose()
        return new

    def outerProduct(self, other):
        mat1 = numpy.transpose(numpy.array([self.value]))
        dp1 = self.copy()
        dp1.value = mat1
        mat2 = numpy.array([other.value])
        dp2 = other.copy()
        dp2.value = mat2
        op = dp1 * dp2
        return op

    def transpose(self):
        self.value = numpy.transpose(self.value)

    def sqrt(self):
        import numpy
        return DataPoint(numpy.sqrt(self.value), valueFormats=self.valueFormats, attributes=self.attributes)

    def toMatrix(self, nrow, ncol):
        newval = []
        num = 0
        for i in xrange(nrow):
            for j in xrange(ncol):
                if num % ncol == 0:
                    newval.append([])
                newval[-1].append( self.value[num] )
                num += 1
        self.value = numpy.array(newval)

    def setUnits(self, units):
        unitObj = units
        if not isinstance(unitObj, Unit):
            unitObj = Unit(units)
        self.units = unitObj

    def getUnits(self):
        return self.units

    def getFormattedValue(self, environment=None):
        valueFormat = None
        if environment and self.valueFormats.has_key(environment.lower()):
            #we should attempt to format this for a specific environment
            valueFormat = self.valueFormats[environment.lower()]
        else:
            #we should try to get a default value
            valueFormat = "%8.4f"
        return valueFormat % self.value

    def getValueFormats(self):
        return self.valueFormats
            
    def setValueFormat(self, format="%12.8f", environment="default"):
        self.valueFormats[environment.lower()] = format

    def matchUnits(self, other):
        units = None
        convertVal = 0
        units = self.getUnits()

        if isinstance(other, DataPoint):
            if units:
                convertedVal = other.getValue(units=units)
            elif other.getUnits():
                convertedVal = other.getValue()
                units = other.getUnits()
            else:
                convertedVal = other
        else:
            convertedVal = other

        return convertedVal, units

    def matchDataPoint(self, other):
        if isinstance(other, DataPoint):
            commonAttributes = self.getCommonAttributes(other)
            otherValue, newUnits = self.matchUnits(other)
            return self.value, other.getValue(), newUnits, commonAttributes
        else: #not another data point... so assign all the attributes from me
            return self.value, other, self.units, self.getAttributes()

    def inverse(self):
        val = 0
        if isinstance(self.value, numpy.ndarray):
            val = numpy.linalg.inv(self.value)
        else:
            val = 1.0/self.value
        newunits = self.getUnits().inverse()
        return DataPoint(val, valueFormats = self.valueFormats, attributes = self.getAttributes(), units=newunits)

    def diagonalize(self):
        evals, evecs = numpy.linalg.eig(self.value)
        eval_dp = DataPoint(evals, valueFormats = self.valueFormats, attributes = self.getAttributes(), units = self.getUnits())
        evec_dp = DataPoint(evecs, valueFormats = self.valueFormats, attributes = self.getAttributes(), units = None) #no units
        return eval_dp, evec_dp

    def __mul__(self, other):
        newval = 0
        newUnits = self.getUnits()
        if isinstance(self.value, numpy.ndarray):
            if isinstance(other, numpy.ndarray):
                newval = numpy.dot(self.value, other)
            elif isinstance(other, DataPoint) and isinstance(other.getValue(), numpy.ndarray):
                otherVal = other.getValue()
                newval = numpy.dot(self.value, otherVal)
            else:
                newval = self.value * other
        else:
            newval = self.value * other

        if isinstance(other, DataPoint):
            otherUnits = other.getUnits()
            newUnits = self.getUnits() * otherUnits
            newval *= newUnits.consolidate()

        return DataPoint(newval, units = newUnits, valueFormats = self.valueFormats, attributes = self.getAttributes())

    def __rmul__(self, number):
        return DataPoint(self.value * number, valueFormats = self.valueFormats, attributes = self.getAttributes(), units=self.units)

    def __div__(self, other):
        newunits = self.getUnits()
        nevwal = 0
        if isinstance(other, DataPoint):
            newval = self.value / other.getValue()
            otherUnits = other.getUnits()
            newUnits = self.getUnits() * otherUnits
            newval *= newUnits.consolidate()
        else:
            newval = self.value / other
        return DataPoint(newval, valueFormats = self.valueFormats, attributes = self.getAttributes(), units=newunits)

    def __rdiv__(self, other):
        newunits = self.getUnits()
        if isinstance(other, DataPoint):
            newunits = self.getUnits() / other.getUnits()
        return DataPoint(other/self.value, valueFormats = self.valueFormats, attributes = self.getAttributes(), units=newunits)

    def __int__(self):
        return int(self.value)

    def __float__(self):
        return float(self.value)

    def __lt__(self, other):
        otherVal, units = self.matchUnits(other)
        return self.value < otherVal
    
    def __eq__(self, other):
        otherVal, units = self.matchUnits(other)
        return self.value == otherVal
    
    def __lteq__(self, other):
        otherVal, units = self.matchUnits(other)
        return self.value <= otherVal

    def __gteq__(self, other):
        otherVal, units = self.matchUnits(other)
        return self.value >= otherVal

    def __gt__(self, other):
        otherVal, units = self.matchUnits(other)
        return self.value > otherVal

    def __div__(self, other):
        newunits = self.getUnits()
        nevwal = 0
        if isinstance(other, DataPoint):
            newval = self.value / other.getValue()
            otherUnits = other.getUnits()
            newUnits = self.getUnits() * otherUnits
            newval *= newUnits.consolidate()
        else:
            newval = self.value / other
        return DataPoint(newval, valueFormats = self.valueFormats, attributes = self.getAttributes(), units=newunits)


class DataPointValue(DataPoint):

    def __init__(self, value, units = None, valueFormats = {}, attributes = {}, **kwargs):
        DataPoint.__init__(self, value, units, valueFormats, attributes, **kwargs)

    def __pow__(self, number):
        newunits = self.getUnits() ** number
        return DataPoint(self.value ** number, units=newunits, valueFormats = self.valueFormats, attributes = self.getAttributes())
        

    def __rdiv__(self, other):
        newunits = self.getUnits()
        if isinstance(other, DataPoint):
            newunits = self.getUnits() / other.getUnits()
        return DataPoint(other/self.value, valueFormats = self.valueFormats, attributes = self.getAttributes(), units=newunits)

class DataPointArray(DataPoint):

    def __getitem__(self, index):
        newVal = self.value[index]
        attributes = {}
        units = self.getUnits()
        return DataPoint(newVal, valueFormats=self.valueFormats, attributes=attributes, units=units)

    def __setitem__(self, index, value):
        self.value[index] = value

    def __iter__(self):
        return iter(self.value)

    def magnitude(self):
        val = math.sqrt(numpy.dot(self.value, self.value))
        return DataPoint(val, units=self.getUnits())

    def __len__(self):
        return len(self.value)

    def extend(self, data): 
        newval = self.value.tolist()
        newval.extend(data)
        self.value = numpy.array(newval)

    def toVector(self):
        newVal = []
        for row in self.value:
            for val in row:
                newVal.append(val)
        self.value = numpy.array(newVal)

    def toXYZ(self):
        newVal = []
        for i in xrange(len(self.value)/3): 
            newVal.append(self.value[i*3:i*3 + 3])
        return DataPoint(newVal, units=self.units, valueFormats=self.valueFormats, attributes=self.attributes)

    def gramSchmidtOrthogonalize(self):
        newmat = []
        for vec in self.value:
            newvec = numpy.array(vec[:])
            for prev in newmat:
                proj = projection(vec, prev)
                newvec = newvec - proj
            mag = numpy.sqrt(numpy.dot(newvec, newvec))
            newvec = newvec / mag
            newmat.append(newvec)
        self.value = numpy.array(newmat)

    def cross(self, other):
        otherval = other.getValue(self.units)
        newval = numpy.cross(self.value, otherval)
        return DataPoint(newval, valueFormats=self.valueFormats, attributes=self.attributes)

    def dot(self, other):
        otherval = other.getValue(self.units)
        newval = numpy.dot(self.value, otherval)
        return DataPoint(newval, units = self.units, valueFormats=self.valueFormats, attributes=self.attributes)

class DataSet(Identity):

    def __init__(self, values=[], units=None, valueFormats = {}, attributes = None, **kwargs):
        self.points = []

        #merge the attributes and keywords
        if not attributes:
            attributes = {}
        attributes.update(kwargs)

        for val in values:
            self.addDataPoint(val, units=units, valueFormats=valueFormats, attributes=attributes) 

    def resetValueFormats(self):
        for point in self:
            point.resetValueFormats()

    def __str__(self):
        str_array = ["*** %s ***" % self.__class__]
        for point in self.points:
            str_array.append( "\t%s" % point )
        return "\n".join(str_array)
    
    def __getitem__(self, integer):
        return self.points[integer]

    def __iter__(self):
        return iter(self.points)

    def __abs__(self):
        newpoints = []
        for point in self:
            newpoints.append(abs(point))
        return DataSet(newpoints)

    def maxdiff(self):
        mean = self.average()
        max = 0
        current = None
        for point in self:
            diff = abs(point - mean)
            if diff > max:
                max = diff
                current = point
        return current

    def subtract(self, *xargs):
        other = xargs[0] #there has to be at least one argument
        match = []
        if isinstance(other, DataSet):
            match = xargs[1:]
        else:
            other = self
            match = xargs

        doubleSet = self.getSetsForOperation(other=other, match=match)
        newVals = []
        for val1, val2 in doubleSet:
            newVal = val1 - val2
            newVals.append(newVal)
        newDataSet = DataSet(newVals)
        return newDataSet

    def makeAttributes(self, **kwargs):
        for entry in kwargs:
            values = kwargs[entry]
            for point in self:
                point.makeAttribute(entry, *values)

    def __bool__(self):
        return bool(self.points)

    def __len__(self):
        return len(self.points)

    def __add__(self, other):
        newVals = []
        for point in self:
            match = other.findMatch(point)
            if match:
                newVal = point + match
                newVals.append(newVal)
            else: pass
        newDataSet = DataSet(newVals)
        return newDataSet

    def __sub__(self, other):
        newVals = []
        for point in self:
            match = other.findMatch(point)
            if match:
                newVal = point - match
                newVals.append(newVal)
        newDataSet = DataSet(newVals)
        return newDataSet

    def add(self, value):
        if isinstance(value, DataPoint):
            self.addDataPoint(value)
        elif isinstance(value, float):
            dp = DataPoint(float)
            self.addDataPoint(dp)
        else:
            self.addData(value)

    def findValue(self, value):
        for point in self:
            if abs(point - value) < 1e-12:
                return point

    def addDataPoint(self, value, units=None, valueFormats = {}, attributes = None, **kwargs):
        dataPoint = value
        if not attributes:
            attributes = {}
        attributes.update(kwargs)
        if not isinstance(value, DataPoint): #must be a data point
            dataPoint = DataPoint(value=value, units=units, valueFormats = valueFormats, attributes=kwargs) 
        else:
            for attr in attributes:
                dataPoint.setAttribute(attr, attributes[attr])
        self.points.append(dataPoint) 

    def addData(self, data, attributes = None, **kwargs):
        if not attributes:
            attributes = {}
        for attr in attributes:
            if not attr in kwargs:
                kwargs[attr] = attributes[attr]

        for dataPoint in data:
            dataPoint.setAttributes(**kwargs)
            self.points.append(dataPoint)

    def extend(self, data):
        for point in data:
            self.addDataPoint(point)

    def clear(self):
        del self.points[:]

    def multiply(self, number, **kwargs):
        dataList = self.getData(attributes = kwargs)
        newVals = []
        for val in dataList:
            newVal = val * number
            newVals.append(newVal)
        newDataSet = DataSet(newVals)

    def findMatch(self, *xargs, **kwargs):
        attributes = kwargs

        dataPoint = None
        match = []
        if xargs and isinstance(xargs[0], DataPoint):
            dataPoint = xargs[0]
            match = xargs[1:]
        else:
            match = xargs
            
        if not dataPoint: #match attributes
            for point in self.points:
                if point.matches(attributes, match=match):
                    return point
        else:
            for point in self.points:
                if point.matches(dataPoint,match=match):
                    return point
        #unable to find match
        return None

    def removeData(self, attributes = None, **kwargs):
        DataSet.mergeAttributes(attributes, kwargs)
        newpoints = []
        for point in self:
            if not point.matches(kwargs):
                newpoints.append(point)
        return DataSet(newpoints)
        
    def getData(self, attributes = None, **kwargs): #get the data that matches the giving kwargs
        if not attributes and not kwargs: #empty, return all
            return DataSet(self.points)

        if not attributes:
            attributes = {}
        else:
            attributes = attributes.copy()
        attributes.update(kwargs)
        
        selectData = []
        for data_point in self.points:
            if data_point.matches(attributes):
                selectData.append(data_point)

        newDataSet = DataSet(selectData)
        return newDataSet

    def getDataPoint(self, attributes = None, **kwargs):
        if not attributes:
            attributes = {}

        for attr in attributes:
            if not attr in kwargs:
                kwargs[attr] = attributes[attr]
        
        for data_point in self.points:
            if data_point.matches(kwargs,match=kwargs.keys()):
                return data_point

    def getSetsForOperation(self, other=None, match=[]):
        dict1 = {} ; dict2 = {}
        if not other:
            other = self #we are matching data to self
        set1 = self.getData()
        set2 = other.getData()
        
        airList = []
        for point in set1:
            matchPoint = set2.findMatch(point, match=match)
            if matchPoint:
                pairList.append( (point, matchPoint) )

        return pairList

    def refine(self, selection, **kwargs):
        newdata = DataSet()
        for dp in self:
            if dp.matches(kwargs):
                if dp.matches(selection):
                    newdata.add(dp)
            else:
                newdata.add(dp)
        return newdata

    def mean(self):
        return self.average()

    def average(self):
        mean = self.points[0]
        for point in self.points[1:]:
            mean = mean + point
        mean = mean / len(self)
        return mean

    def variance(self):
        mean = self.average()
        diff = self.points[0] - mean
        var = diff * diff
        for point in self.points[1:]:
            diff = point - mean
            var = var + diff * diff
        var = var / len(self)
        return var
        
    def stdev(self):
        units = self.average().getUnits()
        var = self.variance()
        val = math.sqrt(var.getValue())
        dp = DataPoint(val, units=units, attributes=var.getAttributes())
        return dp

    def mad(self):
        mean = self.average()
        mad = abs(self.points[0] - mean)
        for point in self.points[1:]:
            mad = mad + abs(point - mean)
        mad = mad / len(self)
        return mad

    def meanabs(self):
        mean = abs(self.points[0])
        for point in self.points[1:]:
            mean = mean + abs(point)
        mean = mean / len(self)
        return mean

    def getAttributeSet(self, attr):
        attrList = []
        for point in self.points:
            val = point.getAttribute(attr)
            if val and not val in attrList:
                attrList.append(val)
        return attrList

    def getDataTable(self, row, column, rowLabels=None, columnLabels=None, title="Title", sort=True, rowInclude=None, columnInclude=None):
        rowAttrs = []

        if not isinstance(row, list) and not isinstance(row, tuple): #only a row type is given
            rowType = row
            rowAttrs = self.getAttributeSet(row)
        else:
            rowType, rowAttrs = row
        #if there are a limited number of things to include
        if rowInclude:
            rowInclude = map( lambda x: x.lower(), rowInclude )
            includedAttrs = []
            for attr in rowAttrs:
                if attr.lower() in rowInclude:
                    includedAttrs.append(attr)
            rowAttrs = includedAttrs


        colAttrs = []
        if not isinstance(column, list) and not isinstance(column, tuple): #only a col type is given
            colType = column
            colAttrs = self.getAttributeSet(column)
        else:
            colType, colAttrs = column
        #if there are a limited number of things to include
        if columnInclude:
            columnInclude = map( lambda x: x.lower(), columnInclude )
            includedAttrs = []
            for attr in colAttrs:
                if attr.lower() in columnInclude:
                    includedAttrs.append(attr)
            colAttrs = includedAttrs

        if not rowLabels:
            rowLabels = rowAttrs
        if not columnLabels:
            columnLabels = colAttrs

        data_table = {}
        for row_label in rowLabels:
            data_table[row_label] = {}
            for col_label in columnLabels:
                data_table[row_label][col_label] = None

        for i in xrange(len(rowLabels)):
            for j in xrange(len(columnLabels)):
                rowAttr = rowAttrs[i]
                rowLabel = rowLabels[i]
                colAttr = colAttrs[j]
                colLabel = columnLabels[j]
                attributesToMatch = { rowType : rowAttr, colType : colAttr }
                dataPoint = self.findMatch(**attributesToMatch)
                data_table[rowLabel][colLabel] = dataPoint

        return DataTable(data_table, rowLabels=rowLabels, columnLabels=columnLabels, rowType=rowType, columnType=colType, title=title, sort=sort)

    def setAttributes(self, attributes = None, **kwargs):
        DataSet.mergeAttributes(attributes, kwargs)
        for point in self.points:
            point.setAttributes(attributes=kwargs)

    def setValueFormat(self, valueFormat, environment="default", attributes=None, **kwargs):
        if not attributes:
            attributes = {}
        attributes.update(kwargs)
        if attributes: #match specific values
            for data_point in self:
                if data_point.matches(attributes): 
                    data_point.setValueFormat(environment=environment, format=valueFormat)
        else: #set it for all data points
            for data_point in self:
               data_point.setValueFormat(environment=environment, format=valueFormat) 

    def keepData(self, attributes=None, **kwargs):
        DataSet.mergeAttributes(attributes, kwargs)
        attrnames = kwargs.keys()
        newpoints = []
        for point in self:
            if point.hasAttributes(attrnames) and not point.matches(kwargs):    
                pass #don't include
            else:
                newpoints.append(point)

        dset = DataSet(newpoints)
        return dset
    
    def mergeAttributes(cls, attributes, kwargs):
        if not attributes:
            attributes = {}
        for attr in attributes:
            if not attr in kwargs:
                kwargs[attr] = attributes[attr]
    mergeAttributes = classmethod(mergeAttributes)

    def setData(self, data):
        self.points = []
        for point in data:
            self.points.append(point)

    
    def getSorted(cls, data, attrOrder):    
        if not attrOrder:
            data.sort()
            return data
            
        sortDict = {}
        nextAttr = attrOrder[0] #start with the first
        attrList = data.getAttributeSet(nextAttr)
        attrList.sort()
        newData = []
        for attrVal in attrList:
            subset = data.getData(attributes = {nextAttr : attrVal})
            sortedSubset = cls.getSorted(subset, attrOrder[1:])
            newData.extend(sortedSubset)
        return newData

    def addMatchCriteria(self, attr):
        for point in self:
            pint.addMatchCritera(attr)

    def setMatchCriteria(self, *matchCriteria):
        for point in self:
            point.setMatchCriteria(*matchCriteria)

    def resetMatchCriteria(self):
        for point in self:
            point.resetMatchCriteria()

    def convertUnits(self, newUnits):
        for point in self:
            point.convertUnits(newUnits)

    def sort(self, *xargs):
        if not xargs:
            self.points.sort()
            return
        
        newData = self.getSorted(self, xargs)
        self.points = []
        for point in newData:
            self.points.append(point)

    classmethod(getSorted)

class TableIterator:
   
    def __init__(self, labels, values):
        self.values = values
        self.labelIterator = iter(labels)

    def __iter__(self):
        return self 

    def next(self):
        nextRow, nextCol = self.labelIterator.next()
        return self.values[nextRow][nextCol]

class DataTable(Identity):
    
    def __init__(self, data, rowLabels, columnLabels, rowType, columnType, title=None, sort=True):
        self.data = data
        self.title = title
        self.rowLabels = rowLabels
        self.columnLabels = columnLabels
        self.rowType = rowType
        self.columnType = columnType

        if sort:
            self.rowLabels.sort()
            self.columnLabels.sort()

        if not self.title:
            self.title = "Table"

        self.aliases = {}

    def __iter__(self):
        iterLabels = []
        for row in self.rowLabels:
            for column in self.columnLabels:
                iterLabels.append( (row, column) )
        return TableIterator(iterLabels, self.data)

    def __len__(self):
        return len(self.data)

    def __str__(self):
        import filemaker
        return filemaker.makeTable(self)

    def __repr__(self):
        return str(self)

    def __getitem__(self, key):
        return self.data[key]

    def getRowType(self):
        return self.rowType

    def getColumnType(self):
        return self.columnType

    def updateLabel(self, label):
        for alias in self.aliases:
            repl = self.aliases[alias]
            label = label.replace(alias, repl)
        return label

    def getRowLabels(self):
        return self.rowLabels

    def getColumnLabels(self):
        return self.columnLabels

    def getTitle(self):
        return self.title

    def setTitle(self, title):
        self.title = title

    def transpose(self):
        row_labels = self.getRowLabels()
        col_labels = self.getColumnLabels()

        new_data = {}
        for col_label in col_labels:
            new_data[col_label] = {}
            for row_label in row_labels:
                new_data[col_label][row_label] = self.data[row_label][col_label]

        return DataTable(new_data, rowLabels=self.columnLabels, columnLabels=self.rowLabels)

    def makeTable(self, type='default'):
        import filemaker
        return filemaker.makeTable(self, type)

    def getNumberOfColumns(self):
        return len(self.columnLabels)

    def setAlias(self, alias = None, **kwargs):
        DataSet.mergeAttributes(alias, kwargs)
        self.aliases.update(kwargs)



class DataSetAndPoint(DataSet, DataPoint):

    def __iter__(self):
        return DataSet.__iter__(self)

    def convertUnits(self, newunits):
        return DataPoint.convertUnits(self, newunits)

    def setValueFormat(self, format="%12.8f", environment="default", attributes = {}, **kwargs):
        DataPoint.setValueFormat(self, format, environment)
        DataSet.setValueFormat(self, format, environment, attributes, **kwargs)
