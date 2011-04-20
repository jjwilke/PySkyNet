import re
import pybib

def make_numbers_subscript(word):
    number = re.compile("\d+").findall(word)
    for num in number:
        word = word.replace(num, "$_%s$" % num)
    return word

def unicode_to_latex(text):
    latex_map = pybib.XMLRequest.LOOKUP_TABLE
    for entry in latex_map:
        conv = latex_map[entry]
        text = text.replace(entry, conv)
    return text

def unicode_to_ascii(text):
    latex_map = pybib.XMLRequest.LOOKUP_TABLE
    simplify_map = pybib.AuthorsFormat.simplify_map 
    for entry in latex_map:
        conv = latex_map[entry]
        if conv in simplify_map:
            text = text.replace(entry, simplify_map[conv])
        else:
            text = text.replace(entry, conv)
    return text
        
        

