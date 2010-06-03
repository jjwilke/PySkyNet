
from pdfget import ArticleParser, PDFArticle
from htmlexceptions import HTMLException
import sys


class ISIArticle(PDFArticle):

    journal_map = {
        "JOURNAL OF CHEMICAL PHYSICS" : "jcp",
    }
    
    def set_journal(self, journal):
        journal = self.journal_map[journal]
        PDFArticle.set_journal(self, journal)

class ISIParser(ArticleParser):

    def reset(self):
        ArticleParser.reset(self)

        #treat paragraph breaks as divisions
        self.start_p = self.start_div
        self.end_p = self.end_div

        self.title_text = self.append_text
        self.pages_text = self.append_text
        self.citation_text = self.append_text

    def start_a(self, attrs):
        if self.a_frame == "ref":
            self.text_frame = "title"

    def end_a(self):
        if self.a_frame == "ref":
            self.text_frame = "citation"
            title = self.get_text()
            self.article.set_title(title)
        
        self.a_frame = None

    def _start_citedRef(self, attrs):
        self.article = ISIArticle()
        self.a_frame = "ref"
        self.text_frame = "ref"

    def _end_citedRef(self):
        citation = self.get_text()
        import re
        regexp = "([A-Z ]+)(\d+)\s[:]\s(\d+)\s(\d+)"
        matches = re.compile(regexp).search(citation).groups()
        journal, volume, page, year = matches
        self.article.set_journal(journal.strip())
        self.article.set_volume(int(volume))
        self.article.set_pages(int(page))
        self.article.set_year(int(year))
        
        self.articles.append(self.article)
        self.article = None


if __name__ == "__main__":
    parser = ISIParser()
    parser.feed(open("isi.html").read())
    for article in parser:
        print article


