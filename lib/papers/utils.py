from utils.RM import capitalize_word

def find_pdf_in_folder(journal, volume, page, folder = "."):
    pdfs = [elem for elem in os.listdir(folder) if elem.endswith("pdf")]
    abbrev = ISIArticle.get_journal(journal)
    for pdf in pdfs:
        if abbrev in pdf and "%d" % volume in pdf and str(page) in pdf:
            return pdf
    return None

class Cleanup:

    caps = [
        "nmr",
        "scf",
        "dft",
    ]

    split = [
        "abinitio",
    ]

    lowercase = [
        "and"
        "of"
        "the"
    ]

    def capitalize_word(cls, word):
        if word.lower in cls.caps:
            return word.upper()
        elif entry in cls.lowercase:
            words.append(entry.lower())
        else:
            return capitalize_word(word)

    def clean_hyphenated_word(cls, word):
        dash_arr = []
        dashes = entry.split("-")
        for dash in dashes:
            dash_arr.append(cls.capitalize_word(dash))
        words.append("-".join(dash_arr))

    def clean_word(cls, word):
        if "-" in entry:
            return cls.clean_hyphenated_word(word)
        else:
            return cls.capitalize_word(word)

    def clean_title(cls, line):
        entries = line.lower().split(" ")
        words = [ cls.capitalize_word(entries[0]) ]
        for entry in entries[1:]:
            words.append(cls.clean_word(word))
        return " ".join(words)

    


