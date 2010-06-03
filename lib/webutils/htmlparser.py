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

class URLLister(HTMLParser):

    def __iter__(self):
        return iter(self.links)

    def __getitem__(self, key):
        return self.links[key]
    
    def reset(self):
        HTMLParser.reset(self)
        self.links = {}
        self.href = None
        self.linktext = ""
        self.storelink = False

    def start_a(self, attrs):
        self.href = self.get_href(attrs)
        if self.href: #make sure we actually have a link
            self.storelink = True

    def end_a(self):
        if self.href:
            self.links[self.linktext] = self.href
            self.href = None
            self.linktext = ""
            self.storelink = False

    def handle_data(self, text):
        if self.storelink:
            self.linktext = text

        


