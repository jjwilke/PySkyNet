
def set_aip_format():
    from pylatex.pybib import JournalArticle, ComputerProgram, Book, set, Record, BookSection

    Record.setDefaults()

    #entry JCP guidelines
    def journal_bibitem(r):
        format = "%s, %s %s, %s (%s)." % (r['authors'], r['journal'], r['volume'], r['pages'], r['year'])
        return format
    JournalArticle.bibitem = journal_bibitem
    set('authors', JournalArticle, delim = ',', lastname = False)
    set('volume', JournalArticle, style = 'bold')
    set('pages', JournalArticle, lastpage = False) #no style modification
    set('year', JournalArticle)
    set('journal', JournalArticle)

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






