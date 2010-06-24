from skynet.utils.utils import capitalize_word
import re

def find_pdf_in_folder(journal, volume, page, folder = "."):
    pdfs = [elem for elem in os.listdir(folder) if elem.endswith("pdf")]
    abbrev = ISIArticle.get_journal(journal)
    for pdf in pdfs:
        if abbrev in pdf and "%d" % volume in pdf and str(page) in pdf:
            return pdf
    return None

class Cleanup:

    exact = [
        "van der Waals",
    ]

    elements = [
        'H',
        'He',
        'Li',
        'Be',
        'B',
        'C',
        'N',
        'O',
        'F',
        'Ne',
        'Na',
        'Mg',
        'Al',
        'Si',
        'P',
        'S',
        'Cl',
        'Ar',
        'K',
        'Ca',
        'Sc',
        'Ti',
        'V',
        'Cr',
        'Mn',
        'Fe',
        'Co',
        'Ni',
        'Cu',
        'Zn',
        'Ga',
        'Ge',   
        'As',
        'Se',
        'Br',
        'Kr',
        'Rb',
        'Sr',
        'Y',
        'Zr',
        'Nb',
        'Mo',
        'Tc',
        'Ru',
        'Rh',
        'Pd',
        'Ag',
        'Cd',
        'In',
        'Sn',
        'Sb',
        'Te',
        'I',
        'Xe',
        'Cs',
        'Ba',
        'Lu',
        'Hf',
        'Ta',
        'W',
    ]

    acronyms = [
        "PSI3",
        "MOLPRO",
        "ACES",
        "TURBOMOLE",
        "MRCI",
        "CI",
        "QCISD",
        "BCCD",
        "DIIS",
        "CCD",
        "CCSDT",
        "CCSDT(Q)",
        "CISD",
        "CC2",
        "EOM",
        "ROHF",
        "NMR",
        "SCF",
        "DFT",
        "DNA",
        "CCSD",
        "CCSD[\(]T[\)]",
        "MP2",
        "MP2-R12",
        "MP2-F12",
        "MBPT",
        "MP4",
        "GIAO",
        "IGLO",
        "CEPA",
        "CID",
        "GGA",
        "V",
        "VI",
        "VII"
        "VIII",
        "II",
        "III",
        "IV",
        "CASSCF",
        "AO",
        "MO",
        "PNO",
        "R12",
    ]

    caps = [
    ]

    split = {
        "abinitio" : "Ab Initio",
    }

    lowercase = [
        "and",
        "of",
        "the",
        "within",
        "for",
        "by",
        "with",
        "to",
        "on",
        "as",
        "from",
        "into",
        "in",
        "it",
        "its",
        "a",
        "an",
        "at",
    ]

    def capitalize_word(cls, word):
        if "-" in word:
            return cls.capitalize_hyphenated_word(word)
        else:
            return capitalize_word(word)
    capitalize_word = classmethod(capitalize_word)

    def capitalize_hyphenated_word(cls, word):
        dash_arr = []
        dashes = word.split("-")
        for dash in dashes:
            dash_arr.append(cls.clean_word(dash))
        return "-".join(dash_arr)
    capitalize_hyphenated_word = classmethod(capitalize_hyphenated_word)

    def get_repl(cls, word, *xargs):
        for arr in xargs:
            for entry in arr:
                match = cls.check_word(word)
                if not match:
                    continue

                repl = match.groups()[0]
                return repl

        return None #found nothing
    get_repl = classmethod(get_repl)

    def check_word(cls, word):
        regexp = "^[\(]?(%s)[\)]?[.,-]?$" % entry
        match = re.compile(regexp, re.IGNORECASE).search(word)
        return match
    check_word = classmethod(check_word)

    def check_lowercase(cls, word):
        repl = cls.get_repl(word, cls.lowercase)
        if repl:
            word = word.replace(repl, repl.lower())
        return word
    check_lowercase = classmethod(check_lowercase)

    def check_caps(cls, word):
        repl = cls.get_repl(word, cls.caps, cls.acronyms)
        if repl:
            word = word.replace(repl, repl.lower())
        return word
    check_caps = classmethod(check_caps)

    def check_split(cls, word):
        if word.lower() in cls.split:
            return cls.split[word.lower()]
        else:
            return word
    check_split = classmethod(check_split)

    def clean_word(cls, word):
        word = word.lower()
        word = cls.capitalize_word(word)
        word = cls.check_caps(word)
        word = cls.check_lowercase(word)
        word = cls.check_split(word)

        if cls.is_molecule(word):
            word = word.upper()

        return word
    clean_word = classmethod(clean_word)

    def first_word(cls, word):
        word = cls.clean_word(word)
        word = word[0].upper() + word[1:]
        return word
    first_word = classmethod(first_word)

    def clean_title(cls, line):
        entries = line.lower().split(" ")
        words = [ cls.first_word(entries[0]) ]
        for entry in entries[1:]:
            words.append(cls.clean_word(entry))
        title = " ".join(words)

        for entry in cls.exact:
            regexp = r"[\(]?(%s)[\)]?[,-]?" % entry
            match = re.compile(regexp, re.IGNORECASE).search(title)
            if not match:
                continue

            repl = match.groups()[0]
            title = title.replace(repl, entry)

        return title

    clean_title = classmethod(clean_title)

    def get_molecular_formula(cls, word):
        regexp = re.compile("([A-Z][a-z]{0,1})(\d{0,1}(?!\d))([+-]?\d*)")
        elements = regexp.findall(word)
        return elements
    get_molecular_formula = classmethod(get_molecular_formula)

    def is_molecule(cls, word):
        elements = cls.get_molecular_formula(word)
        if not elements:
            return False

        for element, number, charge in elements:
            if not element in self.elements:
                return False

        return True

    is_molecule = classmethod(is_molecule)

    def texify_molecule(cls, word):
        elements = cls.get_molecular_formula(word)
        if not elements:
            return word

        #we have a molecule
        for element, number, charge in elements:
            if not element in cls.elements:
                return word

            repl = element
            if number:
                repl += "$_{%s}$" % number

            if charge:
                repl += "$^{%s}$" % charge
            entry = "%s%s%s" % (element, number, charge)
            word = word.replace(entry, repl)
        
        return word

    texify_molecule = classmethod(texify_molecule)

    


