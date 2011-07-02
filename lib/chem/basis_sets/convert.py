from RM import *
import os
import basisset
files = os.listdir(".")
for file in files:
    print file
    try:
        basis = load(file)
        newBasis = basisset.BasisSet()
        for attr in basis.__dict__:
            newBasis.__dict__[attr] = basis.__dict__[attr]
        save(newBasis, file)
        print newBasis.__class__
    except Exception, error:
        pass
