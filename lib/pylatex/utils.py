import re

def make_numbers_subscript(word):
    number = re.compile("\d+").findall(word)
    for num in number:
        word = word.replace(num, "$_%s$" % num)
    return word

