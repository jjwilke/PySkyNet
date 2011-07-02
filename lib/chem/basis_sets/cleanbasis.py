import sys
from RM import *

name = sys.argv[1]

print name
basis = load(name)
for key in basis.basisDictionary.keys():
    if len(basis.basisDictionary[key]) == 0:
        del basis.basisDictionary[key]
save(basis, name)

