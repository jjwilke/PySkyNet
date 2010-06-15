class LinkedListNode:
    
    def __init__(self, data, next=None, prev=None):
        self.data = data
        self.next = next
        self.prev = prev

    def __str__(self):
        str_arr = []
        next = "none"
        prev = "none"
        if self.next:
            next = str(self.next.getData())
        if self.prev:
            prev = str(self.prev.getData())

        str_arr.append("%s   :   Next = %5s Prev = %5s" % (str(self.data),next,prev))
        return "\n".join(str_arr)

    def __eq__(self, other):
        if isinstance(other, LinkedListNode):
            return self.data == other.data
        else:
            return False

    def setPrevious(self, prev):
        self.prev = prev

    def setNext(self, next):
        self.next = next

    def getData(self):
        return self.data

    def getNext(self):
        return self.next

    def getPrevious(self):
        return self.prev

    def insertBefore(self, node):
        node.setPrevious(self.prev)
        node.setNext(self)
        if self.prev:
            self.prev.setNext(node)
        self.prev = node

    def insertAfter(self, node):
        node.setPrevious(self)
        node.setNext(self.next)
        if self.next:
            self.next.setPrevious(node)
        self.next = node

class LinkedListIterator:

    def __init__(self, start):
        startNode = LinkedListNode(None)
        startNode.setNext(start)
        self.node = startNode

    def iter(self):
        return self
    
    def next(self):
        self.node = self.node.getNext()
        if not self.node:
            raise StopIteration
        return self.node

class LinkedList:

    def __init__(self):
        self.start = None

    def __iter__(self):
        return LinkedListIterator(self.start)

    def __len__(self):
        length = 0
        node = self.start
        while node:
            node = node.getNext()
            length += 1
        return length

    def getStart(self):
        return self.start

    def getEnd(self):
        return self.end

    def getNode(self, node):
        if not isinstance(node, LinkedListNode):
            node = LinkedListNode(node)
            return node
        else:
            return node

    def insertAfter(self, value, newnode):
        newnode = self.getNode(newnode)
        for node in self:
            if node.getData() == value:
                node.insertAfter(newnode)
                if not newnode.getNext(): #this node is the new end
                    self.end = newnode
                return

        raise Exception

    def insertBefore(self, value, newnode):
        newnode = self.getNode(newnode)
        for node in self:
            if node.getData() == value:
                node.insertBefore(newnode)
                if not newnode.getPrevious(): #this is now the beginning
                    self.start = newnode
                return

        raise Exception

    def append(self, newnode):
        newnode = self.getNode(newnode)
        if not self.start: 
            self.start = newnode
            self.end = newnode
        else:
            self.end.insertAfter(newnode)
            self.end = newnode

    def find(self, value):
        for node in self:
            if node.getData() == value:
                return node
        
    def __str__(self):
        str_arr = []
        for node in self:
            str_arr.append(str(node))
        return "\n".join(str_arr)
        

