from skynet.utils.RM import capitalize_word
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

    caps = [
        "mrci",
        "ci",
        "qcisd",
        "bccd",
        "diis",
        "ccd",
        "ccsdt",
        "ccsdt(q)",
        "cisd",
        "cc2",
        "eom",
        "rohf",
        "nmr",
        "scf",
        "dft",
        "dna",
        "h2o",
        "ch4",
        "nh3",
        "nh4",
        "hf",
        "h2",
        "ccsd",
        "ccsd[\(]t[\)]",
        "mp2",
        "mbpt",
        "mp4",
        "giao",
        "iglo",
        "cepa",
        "cid",
        "gga",
        "v",
        "vi",
        "vii"
        "viii",
        "ii",
        "iii",
        "iv",
        "casscf",
        "ao",
        "mo",
        "pno",
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

    def check_lowercase(cls, word):
        for entry in cls.lowercase:
            regexp = "^[\(]?(%s)[\)]?[.,-]?$" % entry
            match = re.compile(regexp, re.IGNORECASE).search(word)
            if not match:
                continue

            repl = match.groups()[0]
            word = word.replace(repl, repl.lower())
        return word
    check_lowercase = classmethod(check_lowercase)

    def check_caps(cls, word):
        for entry in cls.caps:
            match = re.compile("^[\(]?(%s)[\)]?[.,-]?$" % entry, re.IGNORECASE).search(word)
            if not match:
                continue

            repl = match.groups()[0]
            word = word.replace(repl, repl.upper())
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

    


