import re

class PDFGetGlobals:
    
    from papers.acs import JACS, JOC, InorgChem, JPCA, JPCB, JCTC, JPC, OrgLett, ChemRev, ACR, JPCL
    from papers.aip import JCP, JMP
    from papers.sciencedirect import CPL, PhysRep, ChemPhys, THEOCHEM, CompChem, JMS, JCompPhys, CMS, CPC, JMB, CCR
    from papers.aps import PRL, PRA, PRB, PROLA, RMP
    from papers.wiley import AngeChem, IJQC, JPOC, JCC, ChemPhysChem
    from papers.rsc import PCCP, CSR
    from papers.iop import JPA, JPB, PhysScripta, JPCM
    from papers.informa import MolPhys, IRPC
    from papers.jstor import Science
    from papers.springer import TCA, TCActa
    from papers.default import *

    journals = {
        "jacs" : JACS,
        "jctc" : JCTC,
        "jpca" : JPCA,
        "jpcb" : JPCB,
        "joc" : JOC,
        "jpc" : JPC,
        "ioc" : InorgChem,
        "orglett" : OrgLett,
        "chemrev" : ChemRev,
        "acr" : ACR,
        "jcp" : JCP,
        "jmp" : JMP,
        "cpl" : CPL,
        "physrep" : PhysRep,
        "chemphys" : ChemPhys,
        "tca" : TCA,
        "tcacta" : TCActa,
        "prl" : PRL,
        "pra" : PRA,
        "prb" : PRB,
        "rmp" : RMP,
        "pr" : PROLA,
        "prola" : PROLA,
        "ange" : AngeChem,
        "ijqc" : IJQC,
        "pccp" : PCCP,
        "csr" : CSR,
        "jpoc" : JPOC,
        "jcc" : JCC,
        "cpc" : ChemPhysChem,
        "jmb" : JMB,
        "theochem" : THEOCHEM,
        "compchem" : CompChem,
        "jms" : JMS,
        "jpa" : JPA,
        "jpb" : JPB,
        "physscripta" : PhysScripta,
        "jcompphys" : JCompPhys,
        "cms" : CMS,
        "cpc" : CPC,
        "molphys" : MolPhys,
        "jpcm" : JPCM,
        "science" : Science,
    }

    abbrevs = {
        "angew chem int ed" : "ange",
        "accounts chem res" : "acr",
        "chem phys" : "chemphys",
        "chem phys lett" : "cpl",
        "chem rev" : "chemrev",
        "inorg chem" : "ioc",
        "int j quantum chem": "ijqc",
        "j am chem soc" : "jacs",
        "j chem theory comput" : "jctc",
        "j phys chem a" : "jpca",
        "j phys chem b" : "jpcb",
        "j org chem" : "joc",
        "j phys chem" : "jpc",
        "j chem phys" : "jcp",
        "j math phys" : "jmp",
        "phys rep" : "physrep",
        "theor chem acc" : "tca",
        "theo chim acta" : "tcacta",
        "phys rev lett" : "prl",
        "phys rev a": "pra",
        "angew chem int edit" : "ange",
        "phys chem chem phys" : "pccp",
        "j phys org chem" : "jpoc",
        "j comput chem" : "jcc",
        "chemphyschem" : "cpc",
        "j mol biol" : "jmb",
        "comput chem" : "compchem",
        "phys rev b" : "prb",
        "rev mod phys" : "rmp",
        "phys rev" : "pr",
        "angew chem" : "ange",
        "angew chem int ed engl" : "ange",
        "angew chem, int ed engl" : "ange",
        "angew chem int ed in english" : "ange",
        "j phys a" : "jpa",
        "j phys b" : "jpb",
        "physica scripta" : "physscripta",
        "j mol spectrosc" : "jms",
        "j comp phys" : "jcompphys",
        "comp mat sci" : "cms",
        "comp phys comm" : "cpc",
        "mol phys" : "molphys",
        "j phys cond matt" : "jpcm",
        "chem soc rev" : "csr",
    }

    def get_initials(cls, journal):
        str_arr = []
        for word in journal.split():
            str_arr.append(word[0])
        return "".join(str_arr)
    get_initials = classmethod(get_initials)

    def get_object(cls, abbrev):
        if abbrev in cls.journals:
            return cls.journals[abbrev]()

        #attempt to build the journal object as a name
        abbrev = abbrev.upper()

        if hasattr(cls, abbrev):
            obj = getattr(cls, abbrev)
            return obj()

        #if we are here, no object
        return None
    get_object = classmethod(get_object)

    def get_journal(cls, name):
        from papers.pdfget import Journal
        if isinstance(name, Journal):
            return name #already a journal

        name = name.replace("\n"," ")

        from papers.utils import JournalCleanup

        #lower case, strip periods
        name = JournalCleanup.abbreviate(name).replace(".", "").lower()

        if name in cls.abbrevs:
            return cls.get_object(cls.abbrevs[name])
        
        #attempt to object assuming this is the abbreviation
        jobj = cls.get_object(name)
        if jobj:
            return jobj
        
        #nope! no worries!
        abbrev = cls.get_initials(name)
        if abbrev in cls.abbrevs:
            abbrev = cls.abbrevs[abbrev]
        return cls.get_object(abbrev)
    get_journal = classmethod(get_journal)

    def find_journal_in_entry(cls, entry):
        new_entry = entry.lower().replace(".", "")
        for name in cls.abbrevs:
            if name in new_entry: #Great!
                re_arr = []
                for word in name.split():
                    re_arr.append("%s[.]?" % word)
                regexp = "\s*".join(re_arr)
                match = re.compile(regexp, re.DOTALL | re.IGNORECASE).search(entry)
                if not match:
                    return None

                journal = match.group()
                return journal
    find_journal_in_entry = classmethod(find_journal_in_entry)

    def get_valid_journals(cls):
        journals = cls.journals.keys()
        journals.sort()
        return journals
    get_valid_journals = classmethod(get_valid_journals)

if __name__ == "__main__":
    name = "Proceedings of the National Academy of Sciences of the United States of America"
    jobj = PDFGetGlobals.get_journal(name)
