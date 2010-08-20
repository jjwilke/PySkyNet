
from selenium import selenium
from skynet.socket.server import ServerRequest, ServerAnswer, Server



class PDFAnswer(ServerAnswer):

    def __init__(self):
        ServerAnswer.__init__(self, PDFServer.ANSWER_PORT)


class PDFRequest(ServerRequest):
    
    def __init__(self):
        ServerRequest.__init__(self, PDFServer.REQUEST_PORT, PDFAnswer)

class PDFServer(Server):

    REQUEST_PORT = 22353
    ANSWER_PORT = 22354


    def __init__(self):
        Server.__init__(self, self.REQUEST_PORT, self.ANSWER_PORT)
        self.selenium = selenium("localhost", 4444, "*chrome", "http://www.ccc.uga.edu")
        self.selenium.start()

    def process(self, obj):
        return obj.url(self.selenium)

    def run(self):
        try:
            Server.run(self)
        except KeyboardInterrupt:
            self.selenium.stop()
            sys.exit()

