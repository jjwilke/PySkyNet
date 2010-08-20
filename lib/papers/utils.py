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
        'D',
        'X',
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
        'V',
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
        "DNA",
        "RNA",
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
        for delim in "/", "-":
            if delim in word and not word[-1] == delim:
                return cls.capitalize_hyphenated_word(word, delim)
        else:
            return capitalize_word(word)
    capitalize_word = classmethod(capitalize_word)

    def capitalize_hyphenated_word(cls, word, delim):
        dash_arr = []
        dashes = word.split(delim)
        for dash in dashes:
            dash_arr.append(cls.clean_word(dash))
        return delim.join(dash_arr)
    capitalize_hyphenated_word = classmethod(capitalize_hyphenated_word)

    def get_repl(cls, word, *xargs):
        for arr in xargs:
            for entry in arr:
                match = cls.check_word(entry, word)
                if not match:
                    continue

                repl = match.groups()[0]
                return repl

        return None #found nothing
    get_repl = classmethod(get_repl)

    def check_word(cls, reword, word):
        regexp = "^[\(]?(%s)[\)]?[.,-]?$" % reword
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
            word = word.replace(repl, repl.upper())
        return word
    check_caps = classmethod(check_caps)

    def check_split(cls, word):
        if word.lower() in cls.split:
            return cls.split[word.lower()]
        else:
            return word
    check_split = classmethod(check_split)

    def clean_word(cls, word, newsentence = False):
        for delim in "$",:
            if delim in word:
                return word #return verbatim

        word = word.lower()
        word = cls.capitalize_word(word)
        if not newsentence:
            word = cls.check_lowercase(word)
        word = cls.check_caps(word)
        word = cls.check_split(word)

        if cls.is_molecule(word) and cls.contains_number(word):
            word = cls.texify_molecule(word)

        return word
    clean_word = classmethod(clean_word)

    def first_word(cls, word):
        word = cls.clean_word(word)
        word = word[0].upper() + word[1:]
        return word
    first_word = classmethod(first_word)

    def ends_sentence(cls, word):
        if not word:
            return ""

        matches = [".", ":", "!", "?"]
        return word[-1] in matches
    ends_sentence = classmethod(ends_sentence)

    def clean_title(cls, line):
        entries = line.split(" ")
        words = []
        firstword = entries[0]
        if firstword:
            words.append(cls.first_word(firstword))
        newsentence = cls.ends_sentence(entries[0])
        for entry in entries[1:]:
            entry = entry.strip()
            if not entry:
                continue
            words.append(cls.clean_word(entry, newsentence))
            newsentence = cls.ends_sentence(entry)
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

    def get_elements(cls, element):
        if len(element) == 1: #only one thing
            return element.upper()

        element = element[0].upper() + element[1:].lower()
        if element in cls.elements:
            return [element]
        
        #try splitting it
        final = map(lambda x: x.upper(), element)
        return final
        
    get_elements = classmethod(get_elements)

    def get_molecular_formula(cls, word):
        regexp = re.compile("([\(]?)([A-Za-z]{1,2})([-]?)(\d{0,1}(?!\d))([+-]?\d*)([)]?)")
        elements = regexp.findall(word)
        final = []
        for open, element, dash, number, charge, close in elements:
            element_list = cls.get_elements(element)
            if len(element_list) == 1:
                final.append([open, element, dash, number, charge, close])
            elif len(element_list) == 2:
                final.append([open, element_list[0], "", "", "", ""])
                final.append(["", element_list[1], dash, number, charge, close])
            else:
                sys.exit("how?")

        if not final:
            return []

        open = 0
        element = 1
        dash = 2
        number = 3
        charge = 4
        close = 5
        if final[-1][dash] and not final[-1][number] and not final[-1][charge]: #last dash is minus
            final[-1][dash] = ""
            final[-1][charge] = "-"

        return final
    get_molecular_formula = classmethod(get_molecular_formula)

    def contains_number(cls, word):
        match = re.compile("\d").search(word)
        return bool(match) or "(n)" in word
    contains_number = classmethod(contains_number)

    def is_molecule(cls, word):
        for delim in "=", ":", "$", "_":
            if delim in word:
                return False

        elements = cls.get_molecular_formula(word)
        if not elements:
            return False

        for open, element, dash, number, charge, close in elements:
            element = element[0].upper() + element[1:].lower()
            if not element in cls.elements:
                return False

        return True

    is_molecule = classmethod(is_molecule)

    def texify_molecule(cls, word):
        elements = cls.get_molecular_formula(word)
        if not elements:
            return word

        #we have a molecule
        word_arr = []
        for open, element, dash, number, charge, close in elements:
            elem = element[0].upper() + element[1:].lower()
            if not elem in cls.elements:
                return word

            repl = "%s%s" % (open, elem)
            if number:
                repl += "$_{%s}$" % number

            if charge:
                repl += "$^{%s}$" % charge
            repl += close
            #entry = "%s%s%s%s" % (element, dash, number, charge)
            #word = word.replace(entry, repl)
            word_arr.append(repl)
        word = "".join(word_arr)

        parnums = re.compile("\(([\dnN])\)").findall(word)
        for entry in parnums:
            word = word.replace("(%s)" % entry, "$_{%s}$" % entry.lower())
        word = word.replace("(+)", "$^{+}$")
        word = word.replace("$$", "")
        return word
    texify_molecule = classmethod(texify_molecule)


class JournalCleanup:

    erase = [
        "and",
        "of",
        "the",
        "&",
        "in",
    ]

    keep = [
        "cancer",
    ]

    upper = [
        "theochem",
    ]

    lower = [
    ],

    special = {
        "structure-theochem"  : "structure",
    }

    repl = {
        'ser-a' : 'Ser A',
        '&' : '',
        'of america' : 'a',
    }

    abbrev_map = {
        "acad" : "acad",
        "account" : "acc",
        "advance" : "adv",
        "americ" : "am",
        "angewan" : "angew",
        "annual" : "ann",
        "biomol" : "biomol",
        "biochem" : "biochem",
        "canad" : "can",
        "chem" : "chem",
        "chimica" : "chim",
        "collect" : "collect",
        "comput" : "comput",
        "commun" : "commun",
        "condensed" : "cond",
        "coord" : "coord",
        "czech" : "czech",
        "edition" : "ed",
        "edit" : "ed",
        "europ" : "eur",
        "inorg" : "inorg",
        "intern" : "int",
        "journal" : "j",
        "letter" : "lett",
        "material" : "mat",
        "math" : "math",
        "matter" : "matt",
        "molec" : "mol",
        "national" : "natl",
        "organic" : "org",
        "organomet" : "organomet",
        "phys" : "phys",
        "proc" : "proc",
        "rep" : "rep",
        "review" : "rev",
        "royal" : "r",
        "sci" : "sci",
        "society" : "soc",
        "spectros" : "spectrosc",
        "states" : "s",
        "struct" : "struct",
        "theor" : "theor",
        "topic" : "top",
        "united" : "u",
        "zeitsch" : "zeit",
    }

    abbrevs = abbrev_map.values()

    def _startswith(cls, word, fragment):
        length = len(fragment)
        return word[:length] == fragment
    _startswith = classmethod(_startswith)

    def _abbrev_word(cls, word):
        new_word = word
        if not word in cls.keep:
            new_word = word
            for entry in cls.abbrev_map:
                if cls._startswith(word, entry):
                    new_word = cls.abbrev_map[entry]
                    break

        if new_word in cls.upper:
            new_word = new_word.upper()
        elif new_word in cls.lower:
            new_word = new_word.lower()
        else:
            new_word = capitalize_word(new_word)

        new_word = cls._add_period(new_word)
        return new_word
    _abbrev_word = classmethod(_abbrev_word)

    def _add_period(cls, word):
        word = word.strip(".")
        check = word.lower()
        for abb in cls.abbrevs:
            regexp = "^%s$" % abb
            match = re.compile(regexp, re.IGNORECASE).search(check)
            if match:
                return word + "."
        return word
    _add_period = classmethod(_add_period)


    def abbreviate(cls, journal):
        journal = journal.lower()
        for entry in cls.special:
            journal = journal.replace(entry, cls.special[entry])
        words = journal.replace("-"," ").strip().split()

        if len(words) == 1: #don't abbreivate
            title = capitalize_word(words[0])
            return title

        str_arr = []
        for word in words:
            if word in cls.erase:
                continue

            str_arr.append(cls._abbrev_word(word))

        return " ".join(str_arr)
    abbreviate = classmethod(abbreviate)


if __name__ == "__main__":
    x = "What Is the Nature of Polyacetylene Neutral and Anionic Chains Hc2nh and Hc2nh- (n=6-12) That Have Recently Been Observed?"
    print Cleanup.clean_title(x)
