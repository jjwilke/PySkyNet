from htmlparser import HTMLParser

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
        self.title_text = self.append_text
        self.pages_text = self.append_text

    def start_a(self, attrs):
        self.call_method(self.a_frame, "a", attrs)

    def end_a(self):
        pass

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
