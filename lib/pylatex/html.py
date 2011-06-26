
def set_html_format():
    import re
    from pylatex.pybib import JournalArticle, ComputerProgram, Book, set, Record, BookSection, Bibliography, RecordObject

    def bibitem(self, key):
        return ""
    Bibliography.bibitem = bibitem

    RecordObject.sort_criterion = "label"
    RecordObject.reverse_sort = True

    Record.setDefaults()

    def replace_subscript(match):
        text = match.groups()[0]
        return "<sub>%s</sub>" % text

    def journal_bibitem(r):
        title = r['title']
        title = re.sub(r'[$]_[{]?(.*?)[}]?[$]',replace_subscript,title)
        format = """<li><a href=http://dx.doi.org/%s>%s</a><br>
        %s, %s <b>%s</b>, %s (%s).</li>""" % (r['doi'], title, r['authors'], r['journal'], r['volume'], r['pages'], r['year'])
        return format
    JournalArticle.bibitem = journal_bibitem
    set('authors', JournalArticle, delim = ',', lastname = False)
    set('volume', JournalArticle)
    set('pages', JournalArticle, lastpage = False) #no style modification
    set('year', JournalArticle)
    set('journal', JournalArticle)
    set('doi', JournalArticle)

    def program_bibitem(r):
        format = "%s. %s." % (r['authors'], r['title'])

        year = r['year']
        if year:
            format += " %s." % year
        
        publisher = r['publisher']
        if publisher:
            format += " %s." % publisher

        url = r['url']
        if url:
            format += " %s." % url

        return format
    ComputerProgram.bibitem = program_bibitem
    set('title', ComputerProgram) #defaults are fine
    set('year', ComputerProgram)
    set('authors', ComputerProgram, delim = ',', lastname = False)
    set('publisher', ComputerProgram) #defaults are fine
    set('url', ComputerProgram) #defaults are fine


    def book_bibitem(r):
        format = "%s, %s." % (r['authors'], r['title'])

        editors = r['editors']
        if editors:
            format += " edited by %s." % editors

        format += " (%s, %s, %s)." % (r['publisher'], r['city'], r['year'])

        return format
    Book.bibitem = book_bibitem
    set('title', Book, style='italic') #defaults are fine
    set('year', Book)
    set('edition', Book)
    set('authors', Book, delim = ',', lastname = False)
    set('editors', Book, delim = ',', lastname = False)
    set('publisher', Book) #defaults are fine
    set('city', Book) #defaults are fine

    def book_section_bibitem(r):
        format = "%s, `%s' in \\textit{%s}" % (r['authors'], r['title'], r['booktitle'])

        editors = r['editors']
        if editors:
            format += " edited by %s." % editors

        format += " (%s, %s, %s)." % (r['publisher'], r['city'], r['year'])
        return format
    BookSection.bibitem = book_section_bibitem
    set('authors', BookSection, delim = ',', lastname = False)
    set('editors', BookSection, delim = ',', lastname = False)
    set('year',    BookSection)
    set('title',   BookSection) #defaults are fine
    set('booktitle',   BookSection) #defaults are fine
    set('label',   BookSection) #defaults are fine
    set('publisher',   BookSection) #defaults are fine
    set('city',   BookSection) #defaults are fine






