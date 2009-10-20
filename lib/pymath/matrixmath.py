import math
import string
import numpy

#calculates the projection of vector1 onto vector2
def projection(vector1, vector2):
    numerator = numpy.dot(vector1, vector2)
    denominator = numpy.dot(vector2, vector2)
    component = numerator / denominator
    newVector = []
    for x in vector2:
        newVector.append(x * component)

    return newVector
               
#returns a new basis, with the particular vector1 as the 'z-axis', vector2 as 'y-axis' and vector3 as 'x-axis'
def getGramSchmidtBasis(vectorX, vectorY, vectorZ):
    magVector = math.sqrt(numpy.dot(vectorZ, vectorZ))
    newZ = []
    for i in range(0, len(vectorZ)):
        newZ.append(vectorZ[i] / magVector)

    #project out components of vectorZ to make a new 'y-axis'
    nextVector = []
    proj1 = projection(vectorY, newZ)
    for i in range(0, len(vectorY)):
        nextVector.append(vectorY[i] - proj1[i])
    magNextVector = math.sqrt(numpy.dot(nextVector, nextVector))
    newY = []
    for i in range(0, len(nextVector)):
        newY.append(nextVector[i] / magNextVector)

    #project out components of vectors 1 and 2 from vector 3
    nextVector = []
    proj1 = projection(vectorX, newY)
    proj2 = projection(vectorX, newZ)
    for i in range(0, len(vectorX)):
        nextVector.append(vectorX[i] - proj1[i] - proj2[i])
    magNextVector = math.sqrt(numpy.dot(nextVector, nextVector))
    newX = []
    for i in range(0, len(nextVector)):
        newX.append(nextVector[i] / magNextVector)

    return [newX, newY, newZ]
    

## Gets a matrix for a counter-clockwise rotation about an arbitrary axis
# @param axis The axis of rotation
# @param angle The angle of rotation in degrees
def getRotationMatrix(axis, angle):
    import numpy

    #if abs(angle - 0.0) < 1E-10:
    #    return numpy.identity(3).tolist()

    radians = angle * math.pi / 180
    newVec = getUnitVector(axis)
    x = newVec[0] * radians
    y = newVec[1] * radians
    z = newVec[2] * radians
    gener = [
        [0, -z, y],
        [z, 0, -x],
        [-y, x, 0]
        ]
    rotMat = numpy.real( matrixExp(gener) )

    return rotMat

## Finds the exponential of a square matrix
# @param matrix The matrix to take the exponential of
# @reutrn The exponentiated matrix
def matrixExp(matrix):
    initMat = numpy.array(matrix).astype(numpy.float64)
    [eigVals, eigVecs] = numpy.linalg.eig(numpy.array(initMat))
    T = numpy.transpose(eigVecs)
    size = len(matrix)
    mat = numpy.identity(size)
    newMat = mat.astype(numpy.complex128)
    for i in range(0, size):
        mag = math.exp(eigVals[i].real) + 0j
        theta = eigVals[i].imag
        com = math.cos(theta) + math.sin(theta)*1j
        newMat[i][i] = mag * com
    finalMat = numpy.dot(eigVecs, numpy.dot(newMat, numpy.linalg.inv(eigVecs)))

    return finalMat

## Takes a vector of arbitrary length and returns a unit vector pointing in the same direction
# @param vector The vector to normalize
# @return The normalized unit vector
def getUnitVector(vector):
    import numpy
    floatVector = numpy.array(vector).astype(numpy.float64)
    magVector = numpy.float( numpy.sqrt( numpy.dot(floatVector, floatVector) ) )
    return floatVector/magVector



