# @package Machines  This encapsulates all the possible machines that can be used to run a job

import commands
import os
import sys
import time
import re
from skynet.identity import *
from skynet.errors import *
from skynet.utils.utils import *
from chem.jobs import *
from mutex import *

PYTEMP = os.environ["PYTEMP"]
QUEUE_WAIT = 100 #currently, wait forty minutes
QUEUE_SUBMIT_DELAY = 1
debug = getDebug()

DEBUG_SUBMIT = False
if debug >= 6:
    DEBUG_SUBMIT = True
    QUEUE_WAIT = 0
    QUEUE_SUBMIT_DELAY = 0

SUBMIT_LOCKS = {}
RESET_LOCKS = {}
TIME_STAMPS = {}
QUEUE_OUTLOOKS = {}

def queryUser(message, options):
    error = True
    while error:
        try:
            opt = raw_input(message)
            if opt in options:
                return opt
            else:
                print "Invalid input. Try again."
        except EOFError: #fix for interrupts
            print "Interrupt received. Retry"

def getDefaultMachine():
    try:
        default = os.environ['PYMACHINE']
        return getMachine(default)
    except KeyError:
        default = Manual.name
        return getMachine(default)


## Encapsulates all the methods associated with an abstract machine 
class Machine(Identity):
   
    name = 'default'
    WAIT_DELAY = 300
    qCheck = {}
    memory = {}

    def __init__(self):
        self.batchList = []

    def __hash__(self):
        return hash(self.name)

    def __str__(self):
        return self.name

    ## The default job set up, assuming one task per job
    def setUpJobs(self, batch, taskList):
        import jobs
        topFolder = os.getcwd()
        for task in taskList:
            filetext = task.getInputFileText()
            filepath = task.getInputPath()
            newTask = MachineTask(filepath, filetext)
            newJob = jobs.Job([task.getID()], [newTask])
            batch.addJob(newJob)

    def gather(self):
        pass #nothing to do by default

    ## Returns the name of the machine
    #  @return A string identifying the machine
    def getName(self):
        return self.name

    def getMemoryAllocation(self, program):
        name = str(program)
        return self.memory[name]


## A machine that encapsulates running jobs by hand... i.e. this does nothing
class Manual(Machine):

    name = "manual"

    def isRunningJob(self, jobObject):
        #all this can say is the files exists or doesn't
        #this is just put in as a check to make sure people don't do stupid stuff
        outputFile = jobObject.getID()
        if os.path.isfile(outputFile):
            return False
        else:
            return True
        
    def submitBatch(self, batch):
        for job in batch:
            for task in job.getMachineTasks():
                task.execute()
        raise AdvanceAndWait(2) #skip past the wait for current tasks

    
class VoltronMachine(Machine):

    WAIT_DELAY = 1
    SUBMIT_DELAY = 1
    name = "voltronmachine"

    ## Determines whether or not the given machine is free
    #  @param jobObject The job to check for on the machine.
    #  @return A boolean.  True if the job is running on this machine.  False otherwise.
    def isRunningJob(self, jobObject):
        jobName = jobObject.getPID()
        qCheck = self.getQueueCheck()

        # 01/07/2008 bizarre bug - for some reason a job with the name 0 got added
        # thus the queue always finds it running
        # for now let's band-aid it and just assume that particular job is not running
        if jobName == "0": return False

        if not jobName: return False #no job running yet
        if "ERROR" in qCheck: return True #something happened while updating the queue, wait for now

        print "looking for job", jobName, "in", qCheck
        #okay, no queue errors.  Is this job still running?
        if jobName in qCheck: 
            return True #job still running
        else:
            return False #job finished   

    ## The default job set up, assuming one task per job
    def setUpJobs(self, batch, taskList):
        topFolder = os.getcwd()
        for task in taskList:
            program = str(task.getAttribute('program'))
            memory = self.getMemoryAllocation(program)
            task.getComputation().setAttribute("memory", memory)
            filetext = task.getInputFileText()
            folder = task.getFolder()
            filepath = task.getInputPath()
            inputFile = task.getInputFile()
            outputFile = task.getOutputFile()
            command = "sjob -q %s -p %s -i %s -o %s" % (self.name, program, inputFile, outputFile)
            newTask = MachineTask(filepath, filetext)
            newJob = VoltronJob([task.getID()], [newTask], command, folder)
            batch.addJob(newJob)

## Encapsulates the opt06 queue
class Opt(VoltronMachine):

    memory = {
            "molpro" : 400,
            "molpro2002" : 400,
            "aces" : 1900,
            "psi" : 1900,
            "mpqc" : 1900,
            "mrcc" : 1900,
            "qchem" : 400,
        }
    
    name = "opt"

class Short(VoltronMachine):

    memory = {
            "molpro" : 400,
            "molpro2002" : 400,
            "aces" : 1900,
            "psi" : 1900,
            "mpqc" : 1900,
            "mrcc" : 1900,
            "qchem" : 400,
        }
    
    name = "short"
        
class Opt2p(VoltronMachine):
    memory = {
            "molpro" : 350,
            "molpro2002" : 350,
            "aces" : 700,        
            "psi" :700,
            "mpqc": 700,
            'qchem' : 350,
        }

    name = "opt2p"

class Reg(VoltronMachine):
    memory = {
            "molpro" : 250,
            "aces" : 250,
            "gaussian" : 250,
        }

    name = "reg"


## Encapsulates an interactive machine such as Opt30, etc.
class Interactive(Machine):
   
    RUN_COMMANDS = {}
    WAIT_DELAY = 0
    REMOTE = False

    ## The default job set up, assuming one task per job
    def setUpJobs(self, batch, taskList):
        import jobs
        topFolder = os.getcwd()
        for task in taskList:
            program = task.getProgram().getName()
            task.setAttribute("MEMORY", self.memory[program])
            filetext = task.getInputFileText()
            #this is a hack for now
            task.writeFile()
            command, folder, inputFile, outputFile = self.getRunCommand(program, task)
            id = task.getID()
            newTask = None
            inputpath = os.path.join(folder, inputFile)
            outputpath = os.path.join(folder, outputFile)
            newTask = MachineTask(inputpath, filetext, command, id)
            newJob = jobs.Job([task.getID()], [newTask])
            batch.addJob(newJob)

    def submitJobs(self, batch):
        topdir = os.getcwd()
        joblist = batch.getJobs()
        for job in joblist:
            for task in job.getMachineTasks():
                output = task.execute()
                print output
        batch.reportJobs(joblist)

    def getRunCommand(self, program, task):
        cmd = None
        folder =  task.getFolder()
        inputFile = task.getInputFile()
        outputFile = task.getOutputFile()
        try:
            cmd = self.RUN_COMMANDS[program].replace("$INPUT",inputFile).replace("$OUTPUT", outputFile)
        except SyntaxError: #oops, doesn't depend on output file
            cmd = self.runCommands[program].replace("$INPUT",inputFile)
        return cmd, folder, inputFile, outputFile

    def resetUseInfo(self, timeStamp = None):
        command = "ps aux | grep -v 'root' "
        qCheck = commands.getoutput(command)
        self.qCheck = qCheck

class RemoteSocketMachine(Machine):
    
    hostname = None
    socket = None
    jobfile = None
    reportfile = None
    fifoname = None
    signal = 12
    WAIT_DELAY = 30
    SOCKET_ERROR_DELAY = 1

    def __init__(self):
        Machine.__init__(self)

    #@param queue The queue object that will handle the processing of all jobs
    def run(self, lock): 
        self.lock = lock
        import remote
        self.comm = remote.Communicator(self.socket, self.hostname, numRequests = 5)
        self.comm.bind()
        self.loadJobs()
        self.loadReports()
        self.currentJob = None
        self.currentBatch = None
        import os
        self.pid = os.getpid()
        import signal
        #set up the main thread to hangle signal interrupts
        signal.signal(signal.SIGINT, self.crash)
        #set up the main thread to handle jobs finishing
        signal.signal(self.signal, self.handleFinishedJob)
        import thread
        thread.start_new(self.receiveJobs, ())
        self.runJobs()

    def receiveJobs(self):
        try:
            import remote, time
            while 1:
                try:
                    batch = self.comm.acceptObject()
                    self.lock.testandset()
                    for job in batch:
                        self.jobs.append( [job, batch] )
                    self.lock.unlock()
                except SocketError:
                    print "Socket error on %s" % self.__class__
                    time.sleep(self.SOCKET_ERROR_DELAY)
        except Exception, error:
            print error
        except KeyboardInterrupt:
            print "Thread got the interrupt"

    def handleFinishedJob(self, signum, stacktrace):
        print "job finished"
        self.running = False

    def runJobs(self):
        import time
        nextJob = None
        #block until next job is available
        while 1:
            try:
                print "Getting next job"
                self.getNextJob()
                print "Running next job"
                self.runNextJob()
                print "Reporting next job"
                self.reportFinishedJobs()
            except Exception, error:
                print error
                print traceback(error)
                raw_input("hit enter to continue\n")
                sys.exit()
            
            time.sleep(self.WAIT_DELAY)

    def getNextJob(self):
        import time
        while not self.currentJob:
            self.lock.testandset()
            if self.jobs:
                self.currentJob, self.currentBatch = self.jobs.pop(0)
                self.lock.unlock()
            else:
                self.lock.unlock()
                time.sleep(self.WAIT_DELAY)

    def runNextJob(self):
        import os,signal,sys,time
        #first create a file descriptor for ipc
        pipein, pipeout = os.pipe()

        #run the job in the child proces
        pid = os.fork()
        if pid == 0:
            os.close(pipein)
            #first, start a new process group - this detaches the process
            os.setsid()
            newpid = os.fork()
            if newpid == 0:
                os.close(pipeout)
                self.currentJob.execute()
                #let the parent know the job is done 
                os.system("kill -12 %d" % self.pid)
                sys.exit()
            else:
                #report the new child process id back to the main thread
                os.write(pipeout, "%d" % newpid)
                sys.exit()
        else:
            os.close(pipeout)
            pipein = os.fdopen(pipein)
            line = pipein.readline()
            self.childpid = int(line)
            pipein.close()
            self.running = True
            #wait for the child to finish running the job
            while self.running:
                signal.pause()

    def reportFinishedJobs(self):
        #reset the current job and batch
        self.jobsToReport.append([self.currentJob, self.currentBatch])
        self.currentJob = None
        self.currentBatch  = None

        failedReports = []
        print "reporting finished jobs", self.jobsToReport
        while self.jobsToReport:
            try:
                job, batch = self.jobsToReport.pop(0)
                print "Sending %s for batch report" % repr(job)
                batch.reportJobs(job)
            except (SocketError, MachineError, Exception), error:
                print "Unable to report job", error
                print job
                failedReports.append([job, batch])
        for job, batch in failedReports:
            self.jobsToReport.append([job,batch])

    def submitBatch(cls, batch):
        import remote
        comm = remote.Communicator(cls.socket, cls.hostname)
        comm.sendObject(batch)

    def crash(self, signum, stacktrace):
        check = queryUser("(r)esume, (s)top machine (m)aintenance?", ['r','s','m'])
        if check == "s":
            self.stop()
        elif check == "m":
            self.maintenance()
        elif check == "r":
            print "Resuming"

    def maintenance(self):
        validInput = False 
        while not validInput:
            check = raw_input("clear (r)eports?")
            validInput = True
            if check == "r":
                print "Jobs to report cleared"
                self.jobsToReport = []
            else:
                print "Invalid entry. Try again"
                validInput = False
        
    def killjob(self):
        import os
        try:
            os.kill(self.childpid, 9) #use 9 to terminate with extreme prejudice
            check = queryUser("(k)eep current job  (d)elete current job?", ['k', 'd'])
            validInput = True
            if check == "k":
                self.jobs.insert(0, [self.currentJob, self.currentBatch])
            elif check == "d":
                #treat the job as having run
                self.currentBatch.reportJobs(self.currentJob)
        except OSError:
            print "%s already finished" % self.childpid

    def stop(self):
        if self.currentJob:
            self.killjob()

        self.saveJobs()
        self.saveReports()

        #close the sockets
        self.comm.close()
        sys.exit("%s brought down" % self.__class__)

    def saveJobs(self):
        save(self.jobs, self.jobfile)

    def saveReports(self):
        save(self.jobsToReport, self.reportfile)

    def loadReports(self):
        self.jobsToReport = load(self.reportfile)
        if not self.jobsToReport:
            self.jobsToReport = []

    def loadJobs(self):
        self.jobs = load(self.jobfile)
        if not self.jobs:
            self.jobs = []

## Encapsulates Tabby
class Tabby(Interactive):

    runCommands = {
        "molpro" : "molpro --nouse-logfile -o $OUTPUT $INPUT",
        "aces" : "ut_aces2 $INPUT $OUTPUT",
        "psi" : "psi3 $INPUT $OUTPUT",
        "gamess" : "gms $INPUT >& $OUTPUT",
        "gaussian": "g94 $INPUT $OUTPUT"
        }

    ## in Megawords
    memory = {
            "molpro" : 100,
            "aces" : 100,
            "gamess" : 100,
            "psi" : 100,
            "gaussian" : 100,
            }

    name = "tabby"
    max_cpu_usage = 70

    def isFree(self):
        return True

class Local(Interactive):

    
    WAIT_DELAY = 0
    name = "local"

    def __init__(self, memory=None, **kwargs):
        Machine.__init__(self)
        if not memory:
            self.memory = Tabby.memory
        for prog in kwargs:
            self.RUN_COMMANDS[prog] = kwargs[prog]

    def runJobs(self):
        Machine.runJobs(self)
        raise Advance(2)

    def runNextBatch(self):
        batch = self.batchList.pop(0)
        try:
            self.submitJobs(batch)
        except RunError:
            self.batchList.insert(0, batch)
            #add the batch back
            raise RunError("Local machine is not available or not working properly for submitting jobs")
            #epic failure

class Voltron(Interactive, RemoteSocketMachine):
    
    hostname = 'voltron.ccqc.uga.edu'
    jobfile = ".voltron.jobs"
    reportfile = ".voltron.reports"
    name = 'voltron'
    RUN_COMMANDS = {
    "molpro" : "/opt/molpro/2006.1/x86_64/eth0/bin/molprop_2006_1_i8_x86_64_tcgmsg -o $OUTPUT $INPUT",
    "mpqc" : "mpqc $INPUT > $OUTPUT",
    "aces" : "/opt/aces/mab/2005/x86_64/eth0/bin/mabaces2 $INPUT $OUTPUT",
    "psi" : "psi3",
    }
    socket = 50103
    WAIT_DELAY = 0

    ## in Megawords
    memory = {
            "molpro" : 400,
            "aces" : 1900,
            "gamess" : 400,
            "mpqc" : 1900,
            "psi" : 1900
            }

class DeepThought(Interactive, RemoteSocketMachine):
    
    hostname = 'deepthought.ccqc.uga.edu'
    jobfile = ".deepthought.jobs"
    reportfile = ".deepthought.reports"
    name = 'deepthought'
    RUN_COMMANDS = {
    "molpro" : "/opt/molpro/2006.1/x86_64/eth0/bin/molprop_2006_1_i8_x86_64_tcgmsg -n4 -o $OUTPUT $INPUT",
    "mpqc" : "mpqc $INPUT > $OUTPUT",
    "aces" : "/opt/aces/mab/2005/x86_64/eth0/bin/mabaces2 $INPUT $OUTPUT",
    "psi" : "psi3",
    }
    socket = 50102
    WAIT_DELAY = 0

    memory = {
            "molpro" : 400,
            "molpro2002" : 400,
            "aces" : 1000,
            "psi" : 1900,
            "mpqc" : 1900,
            "qchem" : 400,
        }
    
## Encapsulates a generic super computer, for example NERSC or Pittsburgh
class SuperComputer(Machine):
    
    numscripts = 0

    def __init__(self, walltime, numPerScript=1):
        Machine.__init__(self)
        self.numPerScript = numPerScript
        self.walltime = walltime
    
    ## Gets the number of jobs that the current script is set up to run
    #  @return An integer, the number of jobs being run on a given script
    def getNumPerScript(self):
        return self.numPerScript

    def __str__(self):
        return "%s wt=%d numperscript=%d" % (self.name, self.walltime, self.numPerScript)

    ## Runs a set of tasks on the given machine
    #  @param tasks Either a single task or an array of task objects to run on the given queue
    def setUpJobs(self, batch, taskList):
        #variables to hold useful info
        taskNumber = 1
        taskIDs = []
        machTasks = []
        for task in taskList:
            taskIDs.append(task.getID())
            program = task.getProgram().getName()
            task.setAttribute("MEMORY", self.memory[program])
            task.writeFile()
            inputtext = task.getInputFileText()
            inputpath = task.getInputPath()
            outputpath = task.getOutputPath()
            newTask = RemoteMachineTask(inputpath, inputtext, outputpath) 
            machTasks.append(newTask)
            #create a PBS script for submission and move it into the folder to be zipped
            if taskNumber == len(taskList):
                newJob = NerscJob(taskIDs, machTasks)
                #add the job to the list... but don't make a new because we are done
                batch.addJob(newJob)
            elif taskNumber % self.numPerScript == 0:
                newJob = NerscJob(taskIDs, machTasks)
                batch.addJob(newJob)
                taskIDs = []
                machTasks = [] 
                #add the job to the list
                #and then make a new job
            taskNumber += 1

    def submitScript(self, job):
        import os
        cwd = os.getcwd()
        os.chdir(PYTEMP)
        files = []
        home = os.environ["HOME"]
        for task in job.getMachineTasks():
            inputpath = task.getRemoteInputPath()
            outputpath = task.getRemoteOutputPath()
            files.append([inputpath, outputpath])
        if not files:
            print "No files on job"
            print job
            return

        scriptname = "script_" + getDate() + "_%d" % self.numscripts
        self.numscripts += 1 #keep a static count for the given crontab run
        scripttext = self.getScript(files, scriptname)
        print scripttext
        fileobj = open(scriptname,"w")
        fileobj.write(scripttext)
        fileobj.close()
        cmd = "%s %s" % (self.qSubmitCommand, scriptname)
        job.execute(cmd, PYTEMP)
        os.chdir(cwd)
        
    def submitBatch(self, batch):
        import os, commands
        cwd = os.getcwd()
        os.chdir(PYTEMP)
        tmpfile = "." + self.name + commands.getoutput("date").replace(" ","").replace(":","_") + "_pickle"
        save(batch, tmpfile)
        sendcmd = "scp %s %s:~/" % (tmpfile, self.location)
        print sendcmd
        sendoutput = commands.getoutput(sendcmd)
        print sendoutput
        os.system("rm %s" % tmpfile)
        os.chdir(cwd)

    def gather(self, batch):
        import os, commands
        cwd = os.getcwd()
        os.chdir(PYTEMP)
        tmpfile = ".gather" + self.name + commands.getoutput("date").replace(" ","").replace(":","_") + "_pickle"
        save(batch, tmpfile)
        sendcmd = "scp %s %s:~/" % (tmpfile, self.location)
        print sendcmd
        sendoutput = commands.getoutput(sendcmd)
        print sendoutput
        os.system("rm %s" % tmpfile)

    def getWalltime(self):
        return self.walltime

    ## Sets the number of jobs that should be run on a given script - i.e. if you have a series of short jobs
    ## then you should run them all on one script so you don't have to them all wait on the queue
    #  @param number The number of jobs to run on one script
    def setNumPerScript(self, number):
        self.numPerScript = number


## Encapsulates the NERSC supercomputer
class Nersc(SuperComputer):

    memory = {
        "molpro" : 380,
        }
    name = "nersc"
    location = "bassi.nersc.gov"
    qSubmitCommand = "llsubmit"
    qCheckCommand = "llqs"
    qFile = ""#os.path.join(PY, "nersc")
    
    ## Makes a script for use at NERSC
    #  @param fileList The list of files to include
    #  @param scriptName The name to give the script. This should just be an identifier - not the full path
    #  @param wallClockLimit The number of hours to use for the job
    #  @return The name of the script that was created
    def getScript(self, files, scriptName):
        str_arr = []
        #write out the header
        str_arr.append("#@job_name=%s" % scriptName)
        str_arr.append("#@output=$(job_name).o$(jobid)")
        str_arr.append("#@error=$(job_name).e$(jobid)")
        str_arr.append("#@job_type=parallel")
        str_arr.append("#@network.LAPI=csss,shared,us")
        str_arr.append("#@tasks_per_node=8")
        str_arr.append("#@class=regular")
        str_arr.append("#@node=1")
        str_arr.append("#@wall_clock_limit=%d:00:00" % self.walltime)
        str_arr.append("#@queue\n")
        str_arr.append("module load molpro/2006.1\n")

        for input, output in files:
            str_arr.append("mkdir $SCRATCH/%s" % scriptName )
            str_arr.append("molpro -d $SCRATCH/%s -o %s %s" % (scriptName, output, input))
            str_arr.append("rm -rf $SCRATCH/%s\n" % scriptName )

        return "\n".join(str_arr)


MACHINE_MAP = {
   Opt2p.name : Opt2p,
   Opt.name : Opt,
   Short.name : Short,
   DeepThought.name : DeepThought,
   VoltronMachine.name : VoltronMachine,
   Manual.name : Manual,
   Voltron.name : Voltron,
   Nersc.name : Nersc,
}

SUPER_LIST = [Nersc.name]

RUN_MAP = {
   Opt2p.name : VoltronMachine,
   Opt.name : VoltronMachine,
   VoltronMachine.name : VoltronMachine,
   Voltron.name : Voltron,
   DeepThought.name : DeepThought,
}

## Takes a string argument and then returns an instance of the appropriate machine
#  @return  An instance of a machine object
def getMachine(machine, walltime=1, numPerScript=1):
    from machines import Machine

    if not machine:
        raise MachineError("requested machine object, but received none type")

    if isinstance(machine, Machine):
        return machine

    machine = machine.lower()

    try:
        classType = MACHINE_MAP[machine]
        if machine in SUPER_LIST:
            return classType(walltime, numPerScript)
        else:
            return classType()
    except KeyError:
        return None

def getQueueStatuses():
    MACHINE_LIST = [VoltronMachine]#, Nersc]
    for machine in MACHINE_LIST:
        machine.getQueueStatus()
        
