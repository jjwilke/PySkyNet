from sgmllib import SGMLParser

def fetch_url(url):
    import urllib
    import urllib2
    import cookielib

    user_agent = 'Mozilla/4.0 (compatible; MSIE 5.5; Windows NT)'
    headers = { 'User-Agent' : user_agent }
    values = {
    }
    data = { }

    # set things up
    jar = cookielib.CookieJar()
    handler = urllib2.HTTPCookieProcessor(jar)
    opener = urllib2.build_opener(handler)
    urllib2.install_opener(opener)
    request = urllib2.Request(url, headers = headers)
    response = urllib2.urlopen(request).read()
    
    return response

def save_url(url, filename):
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

