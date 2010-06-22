## @module identity  Implements the identity class, from which all classes derive.  Identity allows classes to copy themselves. 
## Two interfaces are also implemented.  Runnable allows a class to run a series of methods in succession.  Savable allows a class to 
## save and load a state from a pickle on the hard drive.
from utils.utils import * 
from errors import *
from utils.linkedlist import LinkedList

class Identity(object):

    def copy(self):
        newcopy = copy(self)
        return newcopy

    def setAttributes(self, **kwargs):
        for entry in kwargs:
            setattr(self, entry.lower(), kwargs[entry])

    def getAttribute(self, entry):
        return getattr(self, entry.lower())

class Savable(Identity):

    ## Recovers the object from a pickle save on the hard drive. The file name is determined
    #  from the object's ID, which is a unique identifier for the object.  The id is sent through and md5 
    #  hashing routine, and the final filename is ".%s.pickle" % hash. 
    #  @return None
    def recover(self):
        savedState = load(self.id)
        for entry in savedState.__dict__:
            self.__dict__[entry] = savedState.__dict__[entry]

    ## Gets the pickle name from the object's ID.  For details on pickle naming, see recover.
    #  @return A string. The name of the pickle file that the objects state is stored on
    def getPickleName(self):
        id = self.getID()
        import md5
        m = md5.new()
        m.update(id)
        ## This hash code will identify the project in case a restart needs to be performed
        hashCode = m.hexdigest()
        pickleName = ".%s.pickle" % hashCode
        return pickleName

    def getID(self):
        return self.id
    
    ## Sets the object's unique ID.
    #  @param newID The new string identifier for the object.  There are no restrictions on the string ID.
    def setID(self, newID):
        self.id = newID

    ## Saves the current state of the object to the savable state's pickle
    def save(self):
        save(self, self.id)

class Runnable(Identity):

    NOT_STARTED = 0 ; RUNNING = 1 ; STOPPED = 2; FINISHED = 3; ERROR = 4;

    ## Constructor
    def __init__(self):
        self.methodList = LinkedList()
        self.methodNode = None
        self.status = Runnable.NOT_STARTED
        if isinstance(self, Savable):
            self.savable = True
        else:
            self.savable = False

    ## Runs through the list of methods and executes each
    def run(self):
        if self.status == Runnable.NOT_STARTED:
            self.start()

        while self.methodNode:
            self.nextMethod = self.methodNode.getNext()
            if self.savable:
                self.save();
            #make sure we are to be in a running state
            if not self.status == Runnable.RUNNING:
                return self.status
            methodName = self.methodNode.getData()
            print "%s will now %s" % (self.__class__, methodName)
            method = getattr(self, methodName)
            method()
            numMethods = len(self.methodList)
            self.methodNode = self.nextMethod
            if self.savable:
                self.save();
        #we have reached the end of the iterator. set the finish flags
        self.finish()
        return self.status

    def getStatus(self):
        return self.status

    ## Stops execution of the current run
    def stop(self):
        print "%s has been stopped" % self.__class__
        self.status = Runnable.STOPPED
    
    ## Starts execution of the current run.  Warning! This resets the method iterator to the beginning.
    def start(self):
        self.status = Runnable.RUNNING
        self.methodNode = self.methodList.getStart()

    ## Sets appropriate flags to signal that the run is finished
    def finish(self):
        self.status = Runnable.FINISHED

    ## Continues execution of the current run. Warning! This skips ahead to the next method.  If you wish to resume
    ## the method that was previously stopped, you should use restart.
    def resume(self):
        if self.status == Runnable.FINISHED or self.status == Runnable.RUNNING:
            pass #we are already done or are already running
        else: 
            self.status = Runnable.RUNNING

    ## Resumes execution of the current run.  Warning! This restarts on the same method that was previously stopped.  If you wish
    ## to skip ahead to the next method on the list, you should use continue.
    def restart(self):
        if self.status == Runnable.FINISHED or self.status == Runnable.RUNNING:
            pass #we are already done or are already running
        else:
            self.status = Runnable.RUNNING
        
        print "Restarting at", self.methodNode

    ## Adds a method name to the list of methods for the run.
    #  @param methodName A string identifying the method name
    #  @param kargs      A dictionary giving keyword, value argument pairs for when the method is called
    #  @throws ProgrammingError If the method is not used appropriately
    def addMethod(self, methodName):
        try:
            method = getattr(self, methodName)
            #if we are here, the method name is a valid class attribute
            self.methodList.append(methodName)
        except AttributeError, error:
            print error
            raise ProgrammingError("No method named %s for class %s" % (methodName, self.__class__))

    def insertMethod(self, methodName, afterMethod):
        self.methodList.insertAfter(afterMethod, methodName)

    def insertMethodBefore(self, methodName, beforeMethod):
        self.methodList.insertBefore(beforeMethod, methodName)

    def setMethod(self, nextMethod):
        self.methodNode = self.methodList.find(nextMethod)
        self.nextMethod = self.methodNode.getNext()

    def setNextMethod(self, nextMethod):
        self.nextMethod = self.methodList.find(nextMethod)

    def clearMethods(self):
        self.methodList = LinkedList()
        #this must then stop us... we are back to the beginning
        self.status = Runnable.NOT_STARTED
        
            
        

        

