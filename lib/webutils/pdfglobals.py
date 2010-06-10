
class PDFGetGlobals:
    
    from webutils.acs import JACS, JOC, InorgChem, JPCA, JPCB, JCTC, JPC, OrgLett, ChemRev, ACR
    from webutils.aip import JCP, JMP
    from webutils.sciencedirect import CPL, PhysRep, ChemPhys, THEOCHEM, CompChem, JMS, JCompPhys
    from webutils.springer import TCA
    from webutils.aps import PRL, PRA, PRB, PROLA, RMP
    from webutils.wiley import AngeChem, IJQC, JPOC, JCC, ChemPhysChem
    from webutils.rsc import PCCP
    from webutils.iop import JPA, JPB, PhysScripta
    from webutils.informa import MolPhys

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
        "prl" : PRL,
        "pra" : PRA,
        "prb" : PRB,
        "rmp" : RMP,
        "pr" : PROLA,
        "prola" : PROLA,
        "ange" : AngeChem,
        #"ijqc" : IJQC,
        "pccp" : PCCP,
        "jpoc" : JPOC,
        "jcc" : JCC,
        "cpc" : ChemPhysChem,
        "theochem" : THEOCHEM,
        "compchem" : CompChem,
        "jms" : JMS,
        "jpa" : JPA,
        "jpb" : JPB,
        "physscripta" : PhysScripta,
        "jcompphys" : JCompPhys,
        "molphys" : MolPhys,
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
        "phys rev lett" : "prl",
        "phys rev a": "pra",
        "angew chem int edit" : "ange",
        #"int j quantum chem": "ijqc",
        "phys chem chem phys" : "pccp",
        "j phys org chem" : "jpoc",
        "j comput chem" : "jcc",
        "chemphyschem" : "cpc",
        "comput chem" : "compchem",
        "phys rev b" : "prb",
        "rev mod phys" : "rmp",
        "phys rev" : "pr",
        "j phys a" : "jpa",
        "j phys b" : "jpb",
        "physica scripta" : "physscripta",
        "j mol spectrosc" : "jms",
        "j comp phys" : "jcompphys",
        "mol phys" : "molphys",
    }

    def getJournal(cls, name):
        #lower case, strip periods
        name = name.replace(".", "").lower()
        if name in cls.journals:
            return cls.journals[name]()
        elif name in cls.abbrevs:
            return cls.journals[cls.abbrevs[name]]()
        else:
            return None
    getJournal = classmethod(getJournal)

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
