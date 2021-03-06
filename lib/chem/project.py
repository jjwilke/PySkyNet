from skynet.utils.utils import *  
from skynet.errors import *
from skynet.identity import *
from skynet.socket.pysock import Communicator

ERROR_WAIT = 1
debug = getDebug()

## Encapsulates a task performed within a given project
class Task(Identity):

    ##Constructor    
    # @param folderName The name of the folder where the task will do all of its work
    def __init__(self):
        self.assignID()

    def copy(self):
        newitem = Identity.copy(self)
        newitem.assignID()
        return newitem

    def assignID(self):
        check = repr(self)
        self.id = re.compile("object at(.*?)[>]").search(check).groups()[0].strip()

    ## Finalizes the class - this must be implemented on case by case basis
    def finalize(self):
        raise ProgrammingError("finalize is not yet implemented for %s" % self.__class__)

    def sendToMachine(self):
        raise ProgrammingError("sendToMachine is not yet implemented for %s" % self.__class__)

    def make(self):
        raise ProgrammingError("make is not yet implemented for %s" % self.__class__)

    def run(self):
        raise ProgrammingError("run is not yet implemented for %s" % self.__class__)

    def getID(self):
        return self.id

    def getJob(self):
        return self.job

    def setJob(self, job):
        self.job = job

class Project(Runnable, Savable):
    
    unsavable = [
        "listener",
    ]

    def __init__(self):
        super(Project, self).__init__()

        ## For now, just set the ID of the project to correspond to the class
        self.setID(str(self.__class__))

        ## Assume no parent for now... this might be set later
        self.parent = None

        ## Create a job list.  This is a dictionary with keys machines and values the list of jobs for each machine
        self.jobList = {} ## 

        ## Set up the project and task lists
        self.taskList = []
        self.finishedTasks = []
        self.projectList = []

        self.hostname = ''
        self.socketPort = 1

    def finish(self):   
        Runnable.finish(self)

    def addRunMethods(self):
        self.addMethod("runProjects")
        self.addMethod("runCurrentTasks")
        self.addMethod("waitForCurrentTasks")
        self.addMethod("finalize")
        self.addMethod("restartProjects")

    def save(self):
        #We should only bother to save ourselves if we don't have a parent
        if self.parent:
            pass #the parent will save us
        else:
            sys.stdout.write("Saving %s\n%s\n%s\n\n" % (self.__class__, self.methodNode, self.nextMethod))
            unsaved = {}
            for attr in self.unsavable:
                if hasattr(self, attr):
                    unsaved[attr] = getattr(self, attr)
                    del self.__dict__[attr]
            Savable.save(self)
            for attr in unsaved:
                self.__dict__[attr] = unsaved[attr]

            test = load(self.id)
            if not test.methodNode == self.methodNode:
                sys.stderr.write("Save doesn't match current state\n%s\n%s\n" % (test.methodNode,self.methodNode))
                sys.exit()

    def setParent(self, parent):
        self.parent = parent
        #send all of our tasks onto the parent
        for task in self.taskList:
            parent.addTask(task)
        self.taskList = []

    def resetFinalize(self):
        self.setNextMethod("finalize")
        for proj in self.projectList:
            proj.stop()
            proj.resetFinalize()

    def addJob(self, job):
        if self.parent:
            self.parent.addJob(job)
        #no parent... actually add the job
        machine = job.getMachine()
        if not self.jobList.has_key(machine):
            self.jobList[machine] = []
        if not job in self.jobList[machine]: #only want to work with unique jobs
            self.jobList[machine].append(job)

    def addTasks(self, tasklist):   
        for task in tasklist:
            self.addTask(task)

    def addTask(self, task):
        #if there is a parent, we don't worry about this
        if self.parent:
            self.parent.addTask(task)

        #determine whether or not we have a project or a task
        if isinstance(task, Project):
            self.projectList.append(task)
            task.setParent(self)
        elif isinstance(task, Task):
            self.taskList.append(task)
        else:
            raise ProgrammingError("%s is not a valid project or task and cannot be added" % task.__class__)

    def run(self):
        status = self.getStatus()
        if status == Runnable.NOT_STARTED:
            self.start()
            status = self.getStatus()
        while status == Runnable.RUNNING or status == Runnable.ERROR:
            try:
                status = Runnable.run(self)
            except TaskError, error:
                import time
                sys.stderr.write("%s\n%s\n" % (traceback(error), error))
                time.sleep(ERROR_WAIT) #wait a little bit... and then try again
            except RunError, error: #run errors should cause immediate exit, regardless of parentage
                sys.stderr.write("%s\n%s\n" % (traceback(error), error))
                self.save()
                sys.exit()
            except (ProjectStop, ProjectSuspend): #calls for stop should happen immediately
                self.save()
                sys.exit()
            except Advance, error:
                num = error.getAdvancer()
                sys.sdterr.write("Advancing %d steps\n" % num)
                self.save()
            except AdvanceAndWait, error:
                num = error.getAdvancer()
                for i in range(num):
                    self.methodNode = self.nextMethod
                    self.nextMethod = self.methodNode.getNext()
                self.save()
                sys.exit()
            except KeyboardInterrupt:
                method = self.getCurrentMethod()
                if method == "waitForCurrentTasks":
                    self.queryUser()
                else:#just quite
                    self.save()
                    sys.exit()

    def gatherTasks(self):
        machineTasks = {}
        machineMap = {}
        for task in self.taskList:
            machine = task.getMachine()
            machinename = str(machine)
            if not machinename in machineMap:
                machineMap[machinename] = machine
                machineTasks[machinename] = []
            machineTasks[machinename].append(task)

        for machinename in machineMap:
            machine = machineMap[machinename]
            mach = machines.getMachine(machine)
            taskList = machineTasks[machinename]
            batch = jobs.Batch(mach, taskList, self.socketPort, self.hostname)
            mach.gather(batch)

    def getCurrentMethod(self):
        return self.methodNode.getData()

    def quit(self):
        if hasattr(self, "listener"):
            self.listener.close()
        self.save()
        sys.exit()

    def queryUser(self):
        validResponse = False
        while not validResponse:
            request = raw_input("(q)uit, (r)esubmit jobs, (k)eep waiting, (g)ather jobs, (c)ontinue?")
            if request == "q":
                self.quit()
            elif request == "r":
                self.setMethod("runCurrentTasks")
                validResponse = True
            elif request == "k":
                self.setMethod("waitForCurrentTasks")
                validResponse = True
            elif request == "g":
                self.gatherTasks()
                validResponse = True
            elif request == "c":
                self.setMethod("finalize")
                validResponse = True
            else:
                sys.stderr.write("Invalid input. Try again.\n")

    def runProjects(self):
        for proj in self.projectList:
            proj.run()

    def runCurrentTasks(self):
        #if we have a parent class, we should stop and let the parent continue us when necessary
        if self.parent:
            self.stop()
            return

        if debug >= 5:
            return

        #why don't I have a socket?
        if not hasattr(self, "socketPort") or not hasattr(self, "hostname"):
            sys.stdout.write("Getting default socket port and hostname\n")
            self.listener = Communicator.getListener()
            if not self.listener:
                sys.stderr.write("Couldn't get socket for project")
                sys.exit()
            self.socketPort = self.listener.socketPort
            self.hostname = ''

        import machines
        machineTasks = {}
        machineMap = {}
        for task in self.taskList:
            machine = task.getMachine()
            machinename = str(machine)
            if not machinename in machineMap:
                machineMap[machinename] = machine
                machineTasks[machinename] = []
            machineTasks[machinename].append(task)

        import machines, jobs
        for machinename in machineMap:
            machine = machineMap[machinename]
            mach = machines.getMachine(machine)
            taskList = machineTasks[machinename]
            batch = jobs.Batch(mach, taskList, self.socketPort, self.hostname)
            batch.run()
                
    def clearTasks(self):
        self.taskList = []

    def getAllTasks(self):
        taskList = self.taskList[:]
        taskList.extend(self.projectList)
        return taskList

    def restartProjects(self):
        #now that we are done, restart any projects
        for proj in self.projectList:
            proj.restart()
            proj.run()

    def waitForCurrentTasks(self):
        if debug >= 5:
            return

        import remote
        if self.parent: #this doesn't need to wait
            sys.stdout.write("not waiting since %s has a parent\n" % self.__class__)
            return

        tasksLeft = self.taskList[:]
        for task in self.taskList:
            sys.stdout.write("Waiting for %s\n" % task.getID())


        if not hasattr(self, "listener"): #make a new listener
            self.listener = Communicator(self.socketPort, self.hostname)
            self.listener.bind()

        sys.stdout.write("Listening on port %s with hostname %s\n" % (self.socketPort, self.hostname))
        while tasksLeft:
            sys.stdout.write("Waiting for jobs to finish... %d left\n" % len(self.taskList))
            jobList = self.listener.acceptObject()
            for job in jobList:
                job.finalizeOutput()
                for id in job.getTaskIDS():
                    sys.stdout.write("Received %s\n" % id)
                    try:
                        taskNum, match = self.getMatchingTask(id, tasksLeft)
                        #match.finalize()
                        del tasksLeft[taskNum]
                    except GUSException, error:
                        sys.stderr.write("Machine reporting error\n%s\n",traceback(error))
                        pass #no reporting, for now
                    except ValueError, error:
                        sys.stderr.write("%s\n" % traceback(error))
                        sys.stderr.write("task:\n%s\n was reported, but does not belong to this project\n" % task)

    def getMatchingTask(self, id, taskList):
        for i in xrange(len(taskList)):
            nextTask = taskList[i]
            if id == nextTask.getID():
                return i, nextTask
        #not found
        raise ValueError

    def finalize(self):
        for task in self.taskList:
            try:
                task.finalize()
            except Exception, error:
                sys.stderr.write("%s\n%s\n" % (traceback(error), error))
                sys.exit(task.getFolder())
                
                
                

    def clearTasks(self):
        self.taskList = []
                
        



        


