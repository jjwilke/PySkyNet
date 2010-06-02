from htmlparser import HTMLParser

class PDFArticle:
    
    def __init__(self):
        self.title = "No title"
        self.start_page = 0
        self.end_page = 1

    def __str__(self):
        return "%s pp %d-%d" % (self.title, self.start_page, self.end_page)

    def set_pdfurl(self, url):
        self.url = url

    def set_title(self, text):
        self.title = text

    def set_pages(self, start_page, end_page):
        self.start_page = start_page
        self.end_page = end_page

class ArticleParser(HTMLParser):

    def __iter__(self):
        return iter(self.articles)

    def null_handler(self, args):
        pass

    def append_text(self, text):
        self.entries.append(text)

    def call_method(self, prefix, attr, args = None):
        method = "%s_%s" % (prefix, attr)
        if not hasattr(self, method):
            return

        method = getattr(self, method)
        if args:
            method(args)
        else:
            method()

    def get_text(self):
        text = " ".join(self.entries)
        self.entries = []
        return text

    def handle_data(self, text):
        self.call_method(self.text_frame, "text", text)

    def reset(self):
        HTMLParser.reset(self)
        self.articles = []
        self.article = None #the article currently being built
        self.entries = []
        self.a_frame = None
        self.text_frame = None

    def start_div(self, attrs):
        cls = self.get_html_attr("class", attrs)
        self.push_frame("div", cls)
        if not cls: #no class attribute, move on
            return

        self.call_method("_start", cls, attrs)

    def end_div(self):
        cls = self.pop_frame("div")
        if not cls: #no class attribute, move on
            return

        self.call_method("_end", cls)
