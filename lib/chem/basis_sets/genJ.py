from RM import *
from basisset import *
import sys

name = sys.argv[1]
filename = name + ".basis"

spinatoms = [
    'N',
]

newlist_H = [
    ["S", 11],
    ["S", 24],
    ["P", 10],
    ["D", 2],
]
newlist_heavy = [
    ["S", 11],
    ["S", 26],
    ["P", 6],
    ["D", 4],
]

basis = load(filename)

ubasis = basis.decontract()

subasis = basis.copy()

for atom in spinatoms:
    subasis = subasis.decontractAtom(atom)

def makeJBasis(basis, spinonly=False):
    for atom in basis:
        if spinonly and not atom in spinatoms:
            continue

        maxmap = {
            "S" : 0,
            "P" : 0,
            "D" : 0,
        }
        shells = basis[atom]
        for shell in shells:
            angmom = shell.getAngularMomentum()
            if not angmom in maxmap:
                continue
            max = shell.getLargestExponent()
            if max > maxmap[angmom]:
                maxmap[angmom] = max
        
        makelist = []
        if atom == "H" or atom == "HE":
            makelist = newlist_H
        else:
            makelist = newlist_heavy

        for angmom, scalefactor in makelist:
            exp = maxmap[angmom]
            if not exp:
                continue #no basis functions

            newexp = scalefactor * exp
            newshell = Shell(atom, angmom, [newexp], [[1.0]])
            basis[atom].append(newshell)

    return basis

newbasis = makeJBasis(basis, spinonly=True)
newname = name + "-jso.basis"
save(newbasis, newname)

newbasis = makeJBasis(subasis, spinonly=True)
newname = name + "-juncso.basis"
save(newbasis, newname)

newbasis = makeJBasis(basis)
newname = name + "-jall.basis"
save(newbasis, newname)

newbasis = makeJBasis(ubasis)
newname = name + "-jall-u.basis"
save(newbasis, newname)

