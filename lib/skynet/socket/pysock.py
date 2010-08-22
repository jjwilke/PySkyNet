class SocketOpenError(Exception): pass
class SocketConfirmError(Exception): pass

import sys

class Communicator(object):
    import os
    import os.path

    ONE_KB = 1024
    STRIDE = ONE_KB

    CONFIRM = 'conf'
    RECEIVED = 'received'

    socketMin = 1000
    socketMax = 2000

    def __init__(self, socketPort, hostName = '', numRequests = 5):
        import socket
        self.socketPort = socketPort
        self.hostName = hostName
        self.socketObj = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.socketOpen = False
        self.numRequests = numRequests

    def getSocketPort(self):
        return self.socketPort

    def getHostName(self):
        return self.hostName

    def getListener(cls):
        for i in range(cls.socketMin, cls.socketMax):
            comm = Communicator(socketPort = i)
            okay = comm.testandlock()
            if okay:
                return comm
    getListener = classmethod(getListener)

    def testandlock(self):
        try:
            self.bind()
            return True
        except:
            return False

    def send(self, message):
        if not self.socketOpen:
            self.open()
       
        try:
            stride = Communicator.STRIDE
            num_messages = len(message) / stride + 1
            for i in xrange(num_messages):
                start = i * stride
                finish = start + stride
                self.socketObj.send(message[start:finish])
                msg = self.receive()
                if msg: #okay, we heard back
                    pass
                else:
                    raise SocketConfirmError
        except (Exception, KeyboardInterrupt), error: #always cloes the connection
            self.close()
            raise error

    def sendObject(self, obj):
        import pickle
        text = pickle.dumps(obj)
        self.send(text)

    def receiveObject(self, obj):
        import pickle
        msg = self.receive()
        obj = pickle.loads(msg)
        return obj

    def setTimeout(self, to):
        self.socketObj.settimeout(to)

    def bind(self):
        if self.socketPort == 50000:
            print traceback()
        #print "binding socket on", self.hostName, self.socketPort
        self.socketObj.bind(('', self.socketPort)) #'' = local host
        self.socketObj.listen(self.numRequests) #only listen for one request at a time

    def accept(self):
        connection, address = self.socketObj.accept()
        try:
            message = ""
            while True:
                data = connection.recv(self.ONE_KB)
                if not data:
                    break
                message += data
                connection.send(self.RECEIVED)
            connection.close()
            return message

        except (Exception, KeyboardInterrupt), error: #always close the connection
            print "Cleaning up connection"
            connection.close()
            self.close()
            raise error

    def acceptObject(self):
        msg = self.accept()
        import pickle
        obj = pickle.loads(msg)
        return obj

    def getHostName(cls):
        import commands
        hostname = commands.getoutput("hostname -a").split()[-1]
        return hostname
    getHostName = classmethod(getHostName)

    def receive(self):
        try:
            msg = self.socketObj.recv(self.ONE_KB) 
            return msg
        except (Exception, KeyboardInterrupt), error: #always close the connection
            print "Cleaning up connection"
            self.close()
            raise error

    def close(self):
        #print "closing socket on", self.hostName, self.socketPort
        self.socketObj.close()
        self.socketOpen = False

    def open(self):
        if self.socketOpen:
            return
        try:
            #print "opening socket on", self.hostName, self.socketPort
            self.socketObj.connect((self.hostName, self.socketPort))
            self.socketOpen = True
        except Exception, error:
            sys.stderr.write("%s\n" % error)
            raise SocketOpenError

