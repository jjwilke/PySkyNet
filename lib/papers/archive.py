from xml.dom.minidom import parse, Document
import shutil
import os.path
import sys
from webutils.pdfget import Page

class Article:
    
    def __init__(self, node):
        self.topnode = node

    def __str__(self):
        return self.topnode.toprettyxml()

    def _get_child(self, tagname):
        pdfnodes = self.topnode.getElementsByTagName(tagname)
        if pdfnodes:
            return pdfnodes[0]
        else:
            return None

    def _get_text_node(self, tagname):
        node = self._get_child(tagname)
        text = node.firstChild.firstChild
        return text

    def create_node(self, tagname):
        node = self.topnode.ownerDocument.createElement(tagname)
        return node

    def create_text(self, tagname):
        node = self.topnode.ownerDocument.createTextNode(tagname)
        return node

    def _get_entry(self, tagname):
        node = self._get_child(tagname)
        if not node:
            return None

        text = node.firstChild.firstChild
        return text.nodeValue

    def get_first_author(self):
        author = self._get_entry("author") 
        lastname = author.split(",")[0]
        return lastname

    def get_issue(self):
        issue = self._get_entry("number")
        if issue:
            return int(issue.split("-")[0])
        else:
            return 0

    def get_journal(self):
        return self._get_entry("full-title")

    def get_year(self):
        return int(self._get_entry("year"))

    def get_volume(self):
        return int(self._get_entry("volume"))

    def get_page(self):
        entry = self._get_entry("pages")
        page = Page(entry.split("-")[0])
        return page

    def get_pages(self):
        return self._get_entry("pages")

    def get_title(self):
        return self._get_entry("title")

    def get_pdfnode(self):
        return self._get_child("pdf-urls")

    def has_pdf(self):
        pdfnode = self.get_pdfnode()
        return bool(pdfnode)

    def set_record_number(self, n):
        node = self._get_child("rec-number")
        node.firstChild.nodeValue = "%d" % n

    def set_pdf(self, path):
        if not os.path.isfile(path):
            sys.exit("%s is not a valid pdf file" % path)

        name = os.path.split(path)[-1]

        #check to see if we already have a pdf file
        node = self.get_pdfnode()
        if node:
            url = node.firstChild
            style = url.firstChild
            text = style.firstChild
            text.nodeValue = name
        else:
            urlnode = self._get_child("urls")
            node = self.create_node("pdf-urls")
            url = self.create_node("url")
            style = self.create_node("style")
            style.setAttribute("face", "normal")
            style.setAttribute("font", "default")
            style.setAttribute("size", "100%")
            text = self.create_text("pdfpath")
            urlnode.appendChild(node)
            node.appendChild(url)
            url.appendChild(style)
            style.appendChild(text)
            text.nodeValue = name

        shutil.copy(path, "Resources")

    def set_pages(self, pages):
        pagenode = self._get_text_node("pages")
        pagenode.nodeValue = str(pages)

class Archive:
    
    def __init__(self, file = None):
        if file:
            self.parser = parse(file)
            self.records = self.parser.getElementsByTagName("records")[0]
            nodes = self.parser.getElementsByTagName("record")
            self.articles = []
            for node in nodes:
                article = Article(node)
                self.articles.append(article)
        else:
            self.parser = xml.dom.minidom.Docment()
            xmlnode = self.parser.createElement("xml")
            self.parser.appendChild(xmlnode)
            self.records = self.parser.createElement("records")
            xmlnode.append(self.records)

    def __iter__(self):
        return iter(self.articles)

    def __str__(self):
        str_arr = []
        for article in self.articles:
            str_arr.append(str(article))
        return "\n".join(str_arr)

    def toxml(self):
        if not self.articles:
            return ""

        return self.articles[0].topnode.ownerDocument.toxml()

    



