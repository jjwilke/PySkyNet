from sgmllib import SGMLParser

class HTMLParser(SGMLParser):

    def reset(self):
        SGMLParser.reset(self)
        self.frames = {}

    def push_frame(self, tag, attr):
        if not self.frames.has_key(tag):
            self.frames[tag] = []

        self.frames[tag].append(attr)

    def pop_frame(self, tag):
        attr = self.frames[tag].pop()
        return attr

    def get_html_attr(self, name, attrs):
        for key, value in attrs:
            if name == key:
                return value
        return None

