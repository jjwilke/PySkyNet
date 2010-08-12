import re

class PDFGetGlobals:
    
    from papers.acs import JACS, JOC, InorgChem, JPCA, JPCB, JCTC, JPC, OrgLett, ChemRev, ACR, JPCL
    from papers.aip import JCP, JMP
    from papers.sciencedirect import CPL, PhysRep, ChemPhys, THEOCHEM, CompChem, JMS, JCompPhys, CMS, CPC, JMB
    from papers.aps import PRL, PRA, PRB, PROLA, RMP
    from papers.wiley import AngeChem, IJQC, JPOC, JCC, ChemPhysChem
    from papers.rsc import PCCP, CSR
    from papers.iop import JPA, JPB, PhysScripta, JPCM
    from papers.informa import MolPhys
    from papers.jstor import Science
    from papers.springer import TCA, TCActa

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
        "j am chem soc" : "jacs",
        "j chem theory comput" : "jctc",
        "j phys chem a" : "jpca",
        "j phys chem b" : "jpcb",
        "j org chem" : "joc",
        "j phys chem" : "jpc",
        "inorg chem" : "ioc",
        "chem rev" : "chemrev",
        "accounts chem res" : "acr",
        "j chem phys" : "jcp",
        "j math phys" : "jmp",
        "chem phys lett" : "cpl",
        "phys rep" : "physrep",
        "chem phys" : "chemphys",
        "theor chem acc" : "tca",
        "theo chim acta" : "tcacta",
        "phys rev lett" : "prl",
        "phys rev a": "pra",
        "angew chem int edit" : "ange",
        "int j quantum chem": "ijqc",
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
        from papers.utils import JournalCleanup
        #lower case, strip periods
        name = JournalCleanup.abbreviate(name).replace(".", "").lower()
        
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

def run_testsuite():
    from papers.pdfget import download_pdf, Page
    #run the testsuite
    download_pdf("jpb", volume=32,issue=13,page=Page("R103"))
    download_pdf("jacs", volume=119,issue=38,page=Page("8925"))
    download_pdf("jcp", volume=126,issue=16,page=Page("164102"))
    download_pdf("prl", volume=76,issue=11,page=Page("1780"))
    download_pdf("pccp", volume=10,issue=23,page=Page("3410"))
    download_pdf("cpl", volume=208,issue=5,page=Page("359"))
    download_pdf("jcc", volume=18,issue=1,page=Page("20"))
