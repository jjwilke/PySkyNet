import os.path
import sys
import os
import re
from utils.RM import save, load

class Author:
    
    def __init__(self, name):
        self.name = name
        self.files = []

    def __str__(self):
        str_arr = ["%s" % self.name]
        str_arr.extend(map(lambda x: "\t%s" % x, self.files))
        return "\n".join(str_arr)

    def add_pdf(self, path):
        self.files.append(path)

    def find(self, volume, page):
        regexp = "%d\s+%s[-.]" % (volume, page)
        for file in self.files:
            match = re.compile(regexp).search(file)
            if match:
                return file
        return None

class Year:

    def __init__(self, year):
        self.authors = {}
        self.year = year

    def __str__(self):
        str_arr = ["=========%d===========" % self.year]
        for author in self.authors:
            str_arr.append(str(self.authors[author]))
        return "\n".join(str_arr)

    def add_author(self, author):
        self.authors[author.name.lower()] = author

    def find(self, volume, page, author = None):
        if not author:
            for name in self.authors:
                check = self.authors[name].find(volume, page)
                if check:
                    return check
            return None #nothing found

        if not self.has_key(author.lower()):
            return None

        authorobj = self.authors[author.lower()]
        return authorobj.find(volume, page)

class Library:
    
    papers_path = "/Users/jjwilke/Documents/Papers"
    pickle = ".papers.index"

    def __init__(self):
        pickle = os.path.join(self.papers_path, self.pickle)
        if os.path.isfile(pickle):
            self.years = load(pickle)
        else:
            self.years = {}

    def __iter__(self):
        return iter(self.years)

    def index(self):
        self.years = {}
        self.walk_years(self.papers_path)

        pickle = os.path.join(self.papers_path, self.pickle)
        save(self.years, pickle)

    def walk_years(self, path):
        files = os.listdir(path)
        for year in files:
            fullpath = os.path.join(path, year)
            if not os.path.isdir(fullpath):
                continue

            match = re.compile("\d+").search(year)
            if not match:
                continue

            yearint = int(year) 
            yearobj = Year(yearint)
            self.walk_authors(yearobj, fullpath)
            self.years[yearint] = yearobj

    def walk_authors(self, year, path):
        files = os.listdir(path)
        for author in files:
            if author == "Spotlight":
                continue

            fullpath = os.path.join(path, author)
            if not os.path.isdir(fullpath):
                continue

            authorobj = Author(author)
            fullpath = os.path.join(path, author)
            pdfs = [elem for elem in os.listdir(fullpath) if elem.endswith("pdf")]
            for pdf in pdfs:
                pdfpath = os.path.join(fullpath, pdf)
                authorobj.add_pdf(pdfpath)
            year.add_author(authorobj)

    def find(self, year, volume, page, author = None):
        if not self.years.has_key(year):
            return None

        yearobj = self.years[year]
        path = yearobj.find(volume, page, author)
        return path

    def __str__(self):
        str_arr = []
        for year in self.years:
            str_arr.append(str(self.years[year]))
        return "\n".join(str_arr)

if __name__ == "__main__":
    lib = Library()
    lib.index()
    print lib
