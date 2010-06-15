import re

class PDFGetGlobals:
    
    from webutils.acs import JACS, JOC, InorgChem, JPCA, JPCB, JCTC, JPC, OrgLett, ChemRev, ACR
    from webutils.aip import JCP, JMP
    from webutils.sciencedirect import CPL, PhysRep, ChemPhys, THEOCHEM, CompChem, JMS, JCompPhys, CMS, CPC, JMB
    #from webutils.springer import TCA
    from webutils.aps import PRL, PRA, PRB, PROLA, RMP
    from webutils.wiley import AngeChem, IJQC, JPOC, JCC, ChemPhysChem
    from webutils.rsc import PCCP, CSR
    from webutils.iop import JPA, JPB, PhysScripta, JPCM
    from webutils.informa import MolPhys
    from webutils.jstor import Science

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
        #"tca" : TCA,
        "prl" : PRL,
        "pra" : PRA,
        "prb" : PRB,
        "rmp" : RMP,
        "pr" : PROLA,
        "prola" : PROLA,
        "ange" : AngeChem,
        #"ijqc" : IJQC,
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
        #"theor chem acc" : "tca",
        "phys rev lett" : "prl",
        "phys rev a": "pra",
        "angew chem int edit" : "ange",
        #"int j quantum chem": "ijqc",
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

    def get_journal(cls, name):
        #lower case, strip periods
        name = name.replace(".", "").lower()
        if name in cls.journals:
            return cls.journals[name]()
        elif name in cls.abbrevs:
            return cls.journals[cls.abbrevs[name]]()
        else:
            return None
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

def run_testsuite():
    from pdfget import download_pdf, Page
    #run the testsuite
    download_pdf("jpb", volume=32,issue=13,page=Page("R103"))
    download_pdf("jacs", volume=119,issue=38,page=Page("8925"))
    download_pdf("jcp", volume=126,issue=16,page=Page("164102"))
    download_pdf("prl", volume=76,issue=11,page=Page("1780"))
    download_pdf("pccp", volume=10,issue=23,page=Page("3410"))
    download_pdf("cpl", volume=208,issue=5,page=Page("359"))
    download_pdf("jcc", volume=18,issue=1,page=Page("20"))
