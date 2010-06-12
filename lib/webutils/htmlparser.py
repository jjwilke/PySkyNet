from sgmllib import SGMLParser
import sys

class URLGlobals:
    
    handler = None
    jar = None
    opener = None
    installed = False

    def install(cls):
        if cls.installed:
            return

        import urllib
        import urllib2
        import cookielib

        cls.jar = cookielib.CookieJar()
        cls.handler = urllib2.HTTPCookieProcessor(cls.jar)
        cls.opener = urllib2.build_opener(cls.handler)
        urllib2.install_opener(cls.opener)

        cls.installed = True
    install = classmethod(install)


def fetch_url(url):
    URLGlobals.install()

    import urllib
    import urllib2

    user_agent = 'Mozilla/4.0 (compatible; MSIE 5.5; Windows NT)'
    headers = { 'User-Agent' : user_agent }
    values = {
    }
    data = { }

    # set things up
    request = urllib2.Request(url, headers = headers)
    response = None
    try:
        response = urllib2.urlopen(request).read()
        print "Response received from %s" % url
    except urllib2.HTTPError, error:
        sys.stderr.write("Cannot find page %s\n" % url)
        return None
    
    return response

def save_url(url, filename):
    print "Downloading %s" % url
    fileobj = open(filename, "w")
    fileobj.write(fetch_url(url))
    fileobj.close()

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

    def get_href(self, attrs):
        return self.get_html_attr("href", attrs)

class Link:
    
    def __init__(self, url):
        self.url = url
        self.text_arr = []

    def get_text(self):
        return " ".join(self.text_arr)

    def add_text(self, text):
        return self.text_arr.append(text)

class URLLister(HTMLParser):

    BEGIN = 0
    STARTED = 1
    STOPPED = 2

    def __init__(self, start = None, stop = None):
        self.start = start
        self.stop = stop
        if self.start:
            self.status = self.BEGIN
        else:
            self.status = self.STARTED

        HTMLParser.__init__(self)

    def __len__(self):
        return len(self.links)

    def __iter__(self):
        return iter(self.links.keys())

    def __getitem__(self, key):
        return self.links[key].url

    def get_text(self, key):
        return self.links[key].get_text()
    
    def reset(self):
        HTMLParser.reset(self)
        self.links = {}
        self.link = None
        self.href = None
        self.linktext = ""
        self.storelink = False

    def start_a(self, attrs):
        self.href = self.get_href(attrs)
        if self.href: #make sure we actually have a link
            self.storelink = True

    def end_a(self):
        if self.href:
            self.link = Link(self.href)
            if self.status == self.STARTED:
                self.links[self.linktext] = self.link
            self.href = None
            self.linktext = ""
            self.storelink = False

    def handle_data(self, text):
        if self.start and self.status == self.BEGIN and self.start in text:
            self.status = self.STARTED
        elif self.stop and self.status == self.STARTED and self.stop in text:
            self.status = self.STOPPED

        if self.storelink:
            self.linktext = text
        elif self.link:
            self.link.add_text(text)

        


