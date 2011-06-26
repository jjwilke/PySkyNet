import sys

class EnergySet:
    
    def __init__(self):
        self.energies = {}
        self.attrs = []
        self.attrvals = {}

    def __str__(self):
        elist = self.getall()
        if not elist:
            return "Empty"

        str_arr = []
        for e in elist:
            str_arr.append(str(e))


        return "\n".join(str_arr)

    def __len__(self):
        return len(self.getall())

    def subset(self, **kwargs):
        newset = EnergySet()

        for entry in kwargs:
            if isinstance(kwargs[entry], str):
                kwargs[entry] = [kwargs[entry]]

        entries = []
        try:
            self._getMatch(self.energies, self.attrs[0], self.attrs[1:], entries, kwargs)
        except IndexError, error:
            sys.stderr.write("Only have attrs %s\n" % self.attrs)
            return newset
            

        if len(entries) == 1:
            return entries[0]

        for entry in entries:
            newset.add(entry)

        return newset

    def attrnames(self):
        return self.attrs

    def attrvalues(self, attrname):
        return self.attrvals[attrname]

    def _getMatch(self, map, attrname, attrlist, entries, kwargs):
        for attrval in self.attrvals[attrname]:
            if attrname in kwargs and not attrval in kwargs[attrname]:
                continue

            if attrlist: #there are more to do
                try:
                    self._getMatch(map[attrval], attrlist[0], attrlist[1:], entries, kwargs)
                except KeyError:
                    pass
            else:
                try:
                    entries.append(map[attrval])
                except KeyError:
                    pass
        
        #if here, and there were no matches
        if not entries and attrname in kwargs:
            import sys
            sys.stderr.write("no matches for attribute %s in %s\n" % (attrname, kwargs[attrname]))

    def _getStr(self, map, attrname, attrlist, elist):
        for attrval in self.attrvals[attrname]:
            if attrlist: #there are more to do
                try:
                    self._getStr(map[attrval], attrlist[0], attrlist[1:], elist)
                except KeyError:
                    pass
            else:
                elist.append(map[attrval])

    def update(self, set):
        entries = set.getall()
        for entry in entries:
            self.add(entry)

    def getall(self):
        entries = []
        if not self.attrs: #no attrs
            return entries

        self._getMatch(self.energies, self.attrs[0], self.attrs[1:], entries, {}) #pass with no filter
        return entries

    def get(self, *xargs):
        return self._getFrom(self.energies, xargs[0], xargs[1:])

    def _getFrom(self, map, attrval, attrlist):
        if not attrlist:
            return map[attrval]

        nextmap = map[attrval]
        return _getFrom(nextmap, attrlist[0], attrlist[1:])

    def add(self, energy):
        attrtypes = energy.__dict__.keys()
        attrtypes.sort()
       
        attrs = []
        for attr in attrtypes:
            if not attr in ("energy", "mol"):
                attrs.append(attr)

        self._addTo(self.energies, energy, attrs[0], attrs[1:])

    def _addTo(self, map, energy, attrname, attrlist):
        attrval = getattr(energy, attrname)

        if not attrname in self.attrs:
            self.attrs.append(attrname)

        if not self.attrvals.has_key(attrname):
            self.attrvals[attrname] = []

        if not attrval in self.attrvals[attrname]:
            self.attrvals[attrname].append(attrval)

        if not attrlist: #none left
            map[attrval] = energy
            return

        if not map.has_key(attrval):
            map[attrval] = {}
        nextmap = map[attrval]

        self._addTo(nextmap, energy, attrlist[0], attrlist[1:])
        

class Energy:

    def __init__(self, energy, mol, **kwargs):
        self.energy = energy
        self.mol = mol
        for entry in kwargs:
            setattr(self, entry, kwargs[entry])

    def __len__(self):
        return 1

    def __str__(self):
        attrs = []
        for attr in self.__dict__:
            if attr in ("energy", "mol"):
                continue
            
            val = self.__dict__[attr]
            if len(val) < 20: #too long to include
                attrs.append(val)

        return "E(%s:%s) = %14.10f" % (self.mol.getMolecularFormula(), ",".join(attrs), self.energy)


class EnergyPoint:
    
    def __init__(self, type, getbasis, basisfile, gete, efile, molfile):
        self.bfile = basisfile
        self.efile = efile
        self.type = type
        self.getbasis = getbasis
        self.gete = gete
        self.molfile = molfile

    def getEnergy(self, title):
        from skynet.utils.utils import getMolecule
        btext = open(self.bfile).read()
        etext = open(self.efile).read()
        mol = getMolecule(self.molfile)
        basis = self.getbasis(btext)
        e = self.gete(etext)
        energy = Energy(e, mol, type=self.type, basis=basis, title=title)
        return energy

    def validDirectory(self, files):
        return self.efile in files and self.bfile in files


def energyWalk(args, dirname, files):
    import os
    from skynet.utils.utils import traceback
    eset, objlist, topdir = args
    os.chdir(dirname)
    title = dirname[2:].split("/")[0]
    for obj in objlist:
        if obj.validDirectory(files):
            try:
                e = obj.getEnergy(title)
                print title, e
                eset.add(e)
            except Exception, error:
                print dirname, error, traceback(error)
    os.chdir(topdir)
