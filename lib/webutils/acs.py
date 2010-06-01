from pdfget import ArticleParser

class ACSArticle:
    
    def __init__(self):
        self.title = "No title"
        self.start_page = 0
        self.end_page = 1

    def __str__(self):
        return "%s pp %d-%d" % (self.title, self.start_page, self.end_page)

    def set_title(self, text):
        self.title = text

    def set_pages(self, text):
        if not "pp" in text:
            raise Exception("%s is not a properly formatted page spec" % text)
            
        import re
        self.start_page, self.end_page = map(int, re.compile("\d+").findall(text))

class ACSParser(ArticleParser):

    def title_a(self, attrs):
        self.text_frame = "title"

    def start_strong(self, attrs):
        if self.text_frame == "pages": #nuke the frame
            self.text_frame = None
            pages = self.get_text()
            self.article.set_pages(pages)
        
    def _start_articleBoxMeta(self, attrs):
        self.a_frame = "title"
        self.article = ACSArticle()

    def _end_articleBoxMeta(self):
        self.articles.append(self.article)
        self.article = None

    def _start_articleAuthors(self, attrs):
        #we are done with the title... commit the title to the article
        title = self.get_text()
        self.article.set_title(title)
        self.text_frame = None
        self.a_frame = None

    def _end_articleAuthors(self):
        self.text_frame = "pages"
