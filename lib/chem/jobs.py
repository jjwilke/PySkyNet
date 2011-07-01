from skynet.identity import *
import commands

class Job(Identity):

    def __init__(self, taskIDS, machineTasks = [], cmd=None, folder=None):
        self.taskIDS = taskIDS[:]
        self.PID = 0 #not yet given
        self.machineTasks = machineTasks[:]
        self.cmd = cmd
        self.folder = folder

    def execute(self, cmd=None, submitFolder=None):
        for task in self.machineTasks:
            task.execute()

        if not cmd:
            cmd = self.cmd
        if not submitFolder:
            submitFolder = self.folder

        if cmd:
            import os
            topdir = os.getcwd()
            if submitFolder:
                os.chdir(submitFolder) 
            output = commands.getoutput(cmd)
            os.chdir(topdir)
            return output

    def gatherOutput(self):
        for task in self.machineTasks:
            task.gatherOutput()

    def finalizeOutput(self):
        for task in self.machineTasks:
            task.finalizeOutput()

    def getMachineTasks(self):
        return self.machineTasks[:]

    def __iter__(self):
        return iter(self.taskIDS)

    def __str__(self):
        str_array = ["Job %s with tasks:" % self.PID]
        for id in self.taskIDS:
            str_array.append(id)
        return "\n".join(str_array)

    def setPID(self, ID):
        self.PID = ID

    def getPID(self):
        return self.PID

    def getTaskIDS(self):
        return self.taskIDS

class Batch(Identity):

    def __init__(self, machine, taskList, socketPort = None, hostName = ''):
        self.socketPort = socketPort
        if not hostName:
            import commands
            self.hostName = "voltron.ccqc.uga.edu" #"hostname --long"
        else:
            self.hostName = hostName
        import machines
        self.machine = machines.getMachine(machine)
        self.jobList = {}
        self.machine.setUpJobs(self, taskList)

    def __str__(self):
        str_arr = ["Batch:"]
        for job in self:
            for taskid in job:
                str_arr.append("\tTask: %s" % taskid)
        return "\n".join(str_arr)

    def addTask(self, task):
        if hasattr(task, "iter"):
            self.taskList.extend(task)
        else:
            self.taskList.append(task)

    def addJob(self, job):
        self.jobList[job] = 1

    def getJobs(self):
        return self.jobList.keys()

    def run(self, wait=False):
        comm = None
        socketPort = None
        if wait:
            import remote
            if not self.socketPort:
                socketPort = remote.getSocketPort()
                comm = remote.Communicator(socketPort, self.hostName, numRequests = 10)
            else:
                socketPort = self.socketPort
                comm = remote.Communicator(self.socketPort, self.hostName)
            comm.bind()
        self.machine.submitBatch(self)
        if not wait:
            return
        
        idsWaiting = []
        for job in self.jobList:
            idsWaiting.extend(job.getTaskIDS())
        while idsWaiting:
            print "waiting for jobs"
            jobList = comm.acceptObject()
            idList = []
            for job in jobList:
                job.finalizeOutput()
                idList.extend(job.getTaskIDS())
            for i in range(0, len(idsWaiting)):
                taskID = idsWaiting[i]
                if taskID in idList:
                    print "Finished job", taskID
                    del idsWaiting[i]
                    break
                #if we got here, we don't know what the job is
                print "Received unknown job", taskID
        comm.close()
        if not self.socketPort: #we don't own the socket
            remote.releaseSocketPort(self.socketPort)

    def __iter__(self):
        return iter(self.jobList.keys())

    def getMachine(self):
        return self.machine

    def reportAll(self):
        self.reportJobs(self.jobList.keys())

    def reportJobs(self, jobs):
        try:
            if isinstance(jobs, list):
                jobsReported = jobs[:]
            else:
                jobsReported = [jobs]
            validJobs = []
            for job in jobsReported:
                try:
                    del self.jobList[job]
                    validJobs.append(job)
                except KeyError: #reporting a job that we don't have
                    pass
            if self.socketPort:
                print "reporting jobs to", self.socketPort, self.hostName
                import remote
                communicator = remote.Communicator(self.socketPort, self.hostName) 
                idlist = []
                for job in validJobs:
                    job.gatherOutput()
                print "reporting finished tasks", idlist
                communicator.sendObject(validJobs)
        except SocketError:
            raise MachineError

class MachineTask(Identity):

    def __init__(self, filepath, filetext, cmd=None, id=None):
        self.folder, self.file = os.path.split(filepath)
        self.inputtext = filetext
        self.cmd = cmd
        self.id = id

    def getRunFolder(self):
        return self.folder

    def getRunFile(self):
        return self.file

    def getFolder(self):
        return self.folder

    def getInputText(self):
        return self.inputtext

    def getID(self):
        return self.id

    def getCommand(self):
        return self.cmd
    
    def gatherOutput(self):
        #by default, nothing to do
        pass

    def finalizeOutput(self):
        pass

    def execute(self):
        import os, os.path, commands
        folder = self.getRunFolder()
        file = self.getRunFile()
        if self.inputtext:
            filepath = os.path.join(folder, file)
            makeFolder(folder)
            fileObj = open(filepath, "w")
            fileObj.write(self.inputtext)
            fileObj.close()
        #if not command, don't execute anything
        if not self.cmd:
            return

        topdir = os.getcwd()
        os.chdir(folder)
        print "%s: %s" % (folder, self.cmd)
        output = commands.getoutput(self.cmd)
        os.chdir(topdir)
        return output

class RemoteMachineTask(MachineTask):

    def __init__(self, inputpath, inputtext, outputpath, cmd=None, id=None):
        import os
        home = os.environ["HOME"] + "/"
        self.outputpath = outputpath
        self.remoteinputpath = inputpath.replace(home, "")
        self.remoteoutputpath = outputpath.replace(home, "")
        self.outputtext = None
        MachineTask.__init__(self, inputpath, inputtext, cmd, id)
    
    def getRunFolder(self):
        home = os.environ["HOME"]
        folder = os.path.split(self.remoteinputpath)[0]
        return os.path.join(home, folder)

    def getRunFile(self):
        file = os.path.split(self.remoteinputpath)[1]
        return file

    def getOutputPath(self):
        return self.outputpath

    def getRemoteOutputPath(self):
        import os, os.path
        home = os.environ["HOME"]
        return os.path.join(home, self.remoteoutputpath)

    def getRemoteInputPath(self):
        import os, os.path
        home = os.environ["HOME"]
        return os.path.join(home, self.remoteinputpath)

    def gatherOutput(self):
        self.outputtext = open(self.remoteoutputpath).read()

    def finalizeOutput(self):
        fileobj = open(self.outputpath, "w")
        fileobj.write(self.outputtext)
        fileobj.close()

## Encapsulates a machine on Voltron
class VoltronJob(Job):
    
    def execute(self, cmd=None, submitFolder=None):
        output = jobs.Job.execute(self, cmd, submitFolder)
        print output
        id = re.compile("Job submitted:\s*(\d+)").search(output).groups()[0]
        self.setPID(id)

class NerscJob(Job):

    def execute(self, cmd=None, submitFolder=None):
        output = Job.execute(self, cmd, submitFolder)
        id = re.compile("The job.*?nersc.gov.(\d+)").search(output).groups()[0]
        self.setPID(id)
