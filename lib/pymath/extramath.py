import numpy.linalg
import numpy
import math
import sys
import re
from utils.utils import *


#The grid spacing near the classical turning point, should be a fine grid, smaller=more accurate
GRID_SPACING_ROOT = 1E-5
#The grid everywhere else, smaller=more accurate
GRID_SPACING = 0.01 
#The value of the function after which all contributions can be neglected when integrating to infinity, smaller=more accurate
INFINITY_TAIL_THRESHOLD = 1E-5
#How close to integrate to the classical turning point, smaller=more accurate
TURNING_POINT_THRESHOLD = 1E-7
#How large the function should get before switching to a finer grid, smaller=more accurate
GRID_SWITCH_THRESHOLD = 10
#The guesses for the root
GUESS_LIST = [0.1, 0.9, 2.0, 4.0, 7.0, 10.0, 14.0, 20.0, 50.0, 100.0, 100.0]

## Performs a non linear regression
#  @param xArray The set of x values
#  @param yArray The set of y values
#  @param eqnArray A list of the individual terms in the equation.  All linear terms should be first.  The non-linear term should be last
#  @return A list of all the fitted paramters, in order of how the terms were given to the program
def nonLinearRegression(xArray, yArray, eqnArray, guess):    
    c = guess
    a = 0
    b = 0
    TOL = 1E-15
    derstep = 0.001
    #iterate until the sum of squares of the first derivatives is below the tolerance
    stepSize = 1
    step = 0
    landmarks = [1E-5, 1E-7, 1E-8, 1E-9]
    numSteps = 0
    correction = 10
    firstDer = 0
    secondDer = 0
    oldFirstDer = 0
    while stepSize > TOL:
        if not stepSize == 1:
            oldFirstDer = firstDer
        
        termVals =[]
        for entry in xArray:
            termVals.append([])
            for term in eqnArray:
                x = entry
                command = ""
                value = 0
                try:
                    command = "value = %s" % term.replace("^", "**").replace("c", "%25.15f" % c)
                except (TypeError, AttributeError):
                    command = "value = %25.15f" % term
                exec(command)
                termVals[-1].append(value)



        X = numpy.array(termVals)
        XT = numpy.transpose(X)
        Y = numpy.transpose(numpy.array(yArray))


        t = numpy.dot(XT,X)
        A = numpy.lingalg.inv(numpy.dot(XT,X))
        B = numpy.dot(XT,Y)
        Delta = numpy.dot(A,B)
        a = Delta[0]
        b = Delta[1]



        firstDer = 0
        secondDer = 0
        error = 0

        #derivative stuff will go here

        if not stepSize == 1:
            estSecondDer = (firstDer - oldFirstDer) / step
            correction = abs(secondDer / estSecondDer)
            
        step = (-1 * firstDer / secondDer) * correction #empirical correction factor
        c += step
        stepSize = abs(step)

    return [a,b,c]
    
## Performs a negative exponential regression for extrapolating SCF energies
#  @param xArray The set of x values
#  @param yArray The set of y values
#  @param guess The initial guess for the non-linear paramter of the SCF
#  @return The list of fitted paramters as [Basis set limit, linear parameter, non-linear exponentional parameter]
def extrapolateSCF(xArray, yArray):
    guess = math.log( (yArray[-3] - yArray[-2])/(yArray[-2] - yArray[-1]) )
    c = guess
    a = 0
    b = 0
    TOL = 1E-15
    derstep = 0.001
    #iterate until the sum of squares of the first derivatives is below the tolerance
    stepSize = 1
    step = 0
    landmarks = [1E-5, 1E-7, 1E-8, 1E-9]
    numSteps = 0
    correction = 10
    firstDer = 0
    secondDer = 0
    oldFirstDer = 0
    while stepSize > TOL:
        if not stepSize == 1:
            oldFirstDer = firstDer
        
        termVals =[]
        for entry in xArray:
            termVals.append([1, math.exp(-c*entry)])
            
        X = numpy.array(termVals)
        XT = numpy.transpose(X)
        Y = numpy.transpose(numpy.array(yArray))

        t = numpy.dot(XT,X)
        A = numpy.linalg.inv(t)
        B = numpy.dot(XT,Y)
        Delta = numpy.dot(A,B)
        a = Delta[0]
        b = Delta[1]

        firstDer = 0
        secondDer = 0
        error = 0
        for i in range(0, len(xArray)):
            y = yArray[i]
            x = xArray[i]
            exp = math.exp(-c*x)
            err = y - (a + b * exp)
            firstDer += 2 * err * x * b * exp
            secondDer += 2 * ( (x**2) * (b**2) * (exp**2)   -  err * (x**2) * b * exp ) 
            error += err**2

        if not stepSize == 1:
            estSecondDer = (firstDer - oldFirstDer) / step
            correction = abs(secondDer / estSecondDer)
            
        step = (-1 * firstDer / secondDer) * correction #empirical correction factor
        c += step
        stepSize = abs(step)

    return [a,b,c]    

def extrapolate2PointSCF(xArray, yArray):
    return linearRegression(xArray, yArray, ['1', '(x+1) * math.exp(-9 * math.sqrt(x))'])

## Performs a non linear regression
#  @param xArray The set of x values
#  @param yArray The set of y values
#  @param eqnArray A list of the individual terms in the equation.
#  @return A list of all the fitted paramters, in order of how the terms were given to the program
def linearRegression(xArray, yArray, eqnArray, full=False):
    termVals = []
    for entry in xArray:
        termVals.append([])
        for term in eqnArray:
            x = entry
            command = ""
            value = 0
            try:
                command = "value = %s" % term.replace("^", "**")
            except TypeError:
                command = "value = %25.15f" % term
            exec(command)
            termVals[-1].append(value)


    X = numpy.array(termVals)
    XT = numpy.transpose(X)
    Y = numpy.transpose(numpy.array(yArray))
    YT = numpy.transpose(Y)

    final = numpy.dot(numpy.linalg.inv(numpy.dot(XT, X)), XT)

    regVals = numpy.dot(numpy.dot(numpy.linalg.inv(numpy.dot(XT, X)), XT), Y)

    if full: #do a full statistical analysis
        paramList = ['a', 'b', 'c', 'd', 'e', 'f', 'g', 'h']
        eqnDisplay = []
        for i in range(0, len(eqnArray)):
            if eqnArray[i] == "1":
                eqnDisplay.append(paramList[i])
            else:
                eqnDisplay.append(paramList[i]+ "*" + eqnArray[i])
        eqnString = " + ".join(eqnDisplay)
        print eqnString
        n = len(Y)
        p = len(X[0])
        XTX_inv = numpy.linalg.inv(numpy.dot(XT, X))
        error = Y - numpy.dot(X, regVals)
        sigma = math.sqrt( numpy.dot(numpy.transpose(error), error) / (n - p) )
        bxy = numpy.dot( numpy.dot(numpy.transpose(regVals), XT), Y)
        u = numpy.array([1]*n)
        uT = numpy.transpose(u)
        yuuy = 1/n * numpy.dot( numpy.dot(YT,u), numpy.dot(uT, Y) )
        ssr = bxy - yuuy
        ess = numpy.dot(YT,Y) - bxy
        tss = ssr + ess
        r2 = ssr / tss
        print "Sigma = %12.8f" % sigma        
        print "R^2 = %12.8f" % r2
        print "Individual Terms"
        for i in range(0, len(regVals)):
            err = math.sqrt(XTX_inv[i][i])*sigma*1.119
            print "Parameter %s = %12.8f +/- %12.8f" % (paramList[i], regVals[i], err)
            
        return regVals
    else:
        return regVals

def calcSumSquares(guessArray, yArray):
    length = len(guessArray)
    errorsum = 0
    for i in range(0, length):
        errorsum += (guessArray[i] - yArray[i]) * (guessArray[i] - yArray[i])
    return errorsum

#returns a 2-tuple of the first derivative and second derivative at the point x based on a simpson's rule interpolation of 3 points
def calcDerivativeSimpson(xArray, yArray, x):
    coefficients = calcQuadraticRegression(xArray, yArray)
    c = coefficients[0]
    b = coefficients[1]
    a = coefficients[2]

    firstder = 2*a*x + b
    secondder = 2*a

    return [firstder, secondder]

def spellCheck(function):

    for name in ("cos", "sin", "exp"):
        function = function.replace(name, "math.%s" % name)
    function = function.replace("^", "**")
    function = function.replace("math.math", "math") #in case math got doubled up
    
    return function

# Encapsulates a continuous function, not piecewise
class function:
    # @param func_text A string defining the equation
    # @param start The lower bound of the domain, this can be a float or the string "Infinity" for no lower bound
    # @param finish The upper bound of the domain, this can be a float or the string "Infinity" for no upper bound
    def __init__(self, func_text, start="Infinity", finish="Infinity"):

        #Try statements in case a string is sent for bounds
        try:
            self.start = start + 0.0
        except TypeError:
            self.start = "INFINITY"
        try:
            self.finish = finish + 0.0
        except TypeError:
            self.finish = "INFINITY"

        #reformat the equation for Python syntax
        self.func_text = spellCheck(func_text)

        #display text for str function
        display = func_text
        for char in ('*', '\n', ' ', ')'):
            display = re.sub("0+[%s]" % char, "0%s" % char, display)
        display = re.sub("0+\n", "0\n", display)
        display = display.replace(" ", "")
        self.display = display

    def __str__(self):
        return "f(x)=%s : %s < x < %s" % (self.display, str(self.start), str(self.finish))

    #A function called on a separate thread to monitor jobs that function is doing
    #@param numpoints The number of points associated with the given task
    def check_done(self, numpoints):
        import time
        import thread
        while True:
            time.sleep(1)
            percent_done = 100.0 * self.point_number / numpoints
            if percent_done > 99.9:
                thread.exit()
            sys.stdout.write("%4.1f Percent Completed...\n" % percent_done)
            sys.stdout.flush()

    #Compute the derivative at a given point using secant line
    #@param x A float, the point at which to compute the derivative
    def getDerivative(self,x):
        x -= 0.0001
        value_a = self.getValue(x)
        x += 0.0002
        value_b = self.getValue(x)
        deriv = (value_b - value_a) / (0.0002)
        return deriv

    #Finds the root of the function with Newton's method
    #@param guess A float defining where to start the search
    def findRoot(self, guess_number=0):
        ROOT_TOLERANCE_Y = 1E-50
        ROOT_TOLERANCE_X = 1E-12
        MAX_ITERATIONS = 1000
        
        #appropriately cast guess
        guess = GUESS_LIST[guess_number]

        #start at guess and proceed with Newton's method
        x = guess
        value = self.getValue(x)
        step = ROOT_TOLERANCE_X + 1.0
        num_iterations = 0
        while abs(value) > ROOT_TOLERANCE_Y and abs(step) > ROOT_TOLERANCE_X:
            deriv = self.getDerivative(x)
            step = -1.0 * value/deriv
            #damp the steps if too large
            if step > 0.01:
                step = 0.01
            elif step <= -0.01:
                step = -0.01
            x += step
            value = self.getValue(x)
            num_iterations += 1
            if guess > 25:
                sys.exit("Unable to converge on root.  Are you sure this potential has a turning point?")                
            #too many iterations, change the starting guess
            elif num_iterations > MAX_ITERATIONS:
                guess_number += 1
                value = self.findRoot(guess_number)
                return value
                
        return x

    #Computes the integral of the function using Simpson's rule
    #@param lowerBound A finite value, lower bound of integration
    #@param upperBound A finite value, upper bound of integration
    #@param grid       The grid spacing, defaults to constant defined by GRID_SPACING
    def calcIntegral(self, lowerBound, upperBound, grid=GRID_SPACING):        
        #get the number of points to evaluate
        #stay as close to the requested grid as possible by determining
        #the number of grid points between max and min
        numpoints = int( (upperBound - lowerBound + 0.0) / grid ) #0.0 protects from integer division
        #however, we must have an even number of steps to fit Simpson's rule
        #thus, if we have an odd number, increase the number of points by 1
        numpoints += numpoints % 2 
        #find the step size based on the number of points
        step = (upperBound - lowerBound + 0.0) / numpoints #0.0 protects from integer divison        

        #initialize the integral
        x = lowerBound
        integral = self.getValue(x)
        x += step
        point_number = [1]
        #start a thread to show status of integral
        import thread        
        #when starting the thread, send the arguments as reference objects
        if numpoints > 1E5:
            thread.start_new_thread(self.check_done, (numpoints,))
        self.point_number = 1

        
        while  self.point_number < numpoints - 2: #the last two points must be done specially
            integral += 4.0 * self.getValue(x)
            x += step
            integral += 2.0 * self.getValue(x)
            x += step
            self.point_number += 2
        integral += 4.0 * self.getValue(x)
        x += step
        integral += self.getValue(x)
        integral *= step / 3.0

        return integral

    # @return Lower bound of domain
    def getLowerBound(self):
        return self.start

    # @return Upper bound of domain
    def getUpperBound(self):
        return self.finish

    # @return The string defining the equation of the function
    def getText(self):
        return self.func_text

    # @param x A float
    # @return Returns the float f(x)
    def getValue(self, x):
        try:
            return eval(self.func_text)
        except (ValueError, ZeroDivisionError), error:
            print "Error at value x=%f" % x
            sys.exit()


def areLinearlyDependent(vector1, vector2):
    vec_1 = numpy.array( vector1 )
    vec_2 = numpy.array( vector2 )
    dot_product_squared = ( numpy.dot( vec_1, vec_2.transpose() ) ) ** 2
    mags_squared = numpy.dot( vec_1, vec_1.transpose() ) * numpy.dot( vec_2, vec_2.transpose() ) 
    if abs(dot_product_squared - mags_squared) < 1E-6: return True
    else: return False

def rowReduce(matrix, vector):
    new_matrix = numpy.array(matrix)
    new_vector = numpy.array(vector)
    for i in range(0, len(matrix)):
        #set the first element in the row to unity
        first_elem = new_matrix[i][i]
        new_matrix[i] *= 1.0/first_elem
        #repeat the action on the vector
        vector[i] *= 1.0/first_elem
        #now, eliminate the other elements in the column
        for j in range(0, i):
            multiplier = -new_matrix[j][i]
            new_matrix[j] += (multiplier * new_matrix[i])
            new_vector[j] += multiplier * new_vector[i]
        for j in range(i+1, len(matrix)):
            multiplier = -new_matrix[j][i]
            new_matrix[j] += (multiplier * new_matrix[i])
            new_vector[j] += multiplier * new_vector[i]

    return new_matrix, new_vector

def magnitude(vector):
    return math.sqrt( numpy.dot(vector, vector) )
