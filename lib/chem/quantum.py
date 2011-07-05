from skynet.identity import *
from skynet.errors import *
from chem.project import *
from chem.data import *

class EnergyTask(Identity):
    
    #No constructor
    
    ## Gets an energy associated with the task. If best is specified, this should return the 'highest level' energy
    #  @param The type of energy to get.  Defaults to best
    #  @return The energy
    def getEnergy(self, type='best'):
        raise ProgrammingError("getEnergy is not yet implemented for %s" % self.__class__)

    ## Return all energies the task is capable of computing
    #  @return A dictionary containing with keys energy types and values the energies.  This will not include i
    #  best as an energy type! 
    def getAllEnergies(self):
        return self.energies

    def addXML(self, node):
        if not self.energies:
            raise InfoNotFoundError("No energies for energy task")

        document = node.ownerDocument
        eNode = document.createElement('energy')
        eNode.setAttribute('type', 'molecular')
        eNode.setAttribute('value', "%14.10f" % self.getEnergy())
        node.appendChild(eNode)
        for energy in self.energies:
            type = energy.getAttribute('wavefunction')
            if not type:
                type = energy.getAttribute('type')
            newNode = node.ownerDocument.createElement('energy')
            newNode.setAttribute('type', type)
            newNode.setAttribute('value', '%14.10f' % energy)
            node.appendChild(newNode)

class OptimizationTask(Identity):

    ## Gets the energy for a given step in the optimization
    #  @param The step number.  This is zero based counting... but zero corresponds to the initial geometry.
    #         1 corresponds to the first updated geometry, etc.  The string 'last', the default, gives the final energy.
    #  @return The energy for the given step
    def getEnergy(self, step="last"):
        raise ProgrammingError("getEnergy is not yet implemented for %s" % self.__class__)

    ## Gets the gradient matrix for a given step in the optimization
    #  @param The step number.  This is zero based counting... but zero corresponds to the initial geometry.
    #         1 corresponds to the first updated geometry, etc.  The string 'last', the default, gives the final gradient.
    #  @return The gradient for the given step
    def getGradient(self, step='last'):
        raise ProgrammingError("getGradient is not yet implemented for %s" % self.__class__)

    ## Gets the xyz matrix for a given step in the optimization
    #  @param The step number.  This is zero based counting... but zero corresponds to the initial geometry.
    #         1 corresponds to the first updated geometry, etc.  The string 'last', the default, gives the final geoemtry.
    #  @return The xyz matrix for the given step
    def getXYZ(self, step='last'):
        raise ProgrammingError("getXYZ is not yet implemented for %s" % self.__class__)


class GradientTask(EnergyTask): #whatever you have gradients for, you also have an energy for

    ## Gets the gradient for the given job
    #  @return The xyz gradient matrix
    def getGradients(self):
        return self.gradients #try to return gradients

    def printGradients(self):
        sys.stdout.write("Gradients in %s\n%s\n" % self.gradients.getUnits(), self.gradients)

    def addXML(self, node):
        EnergyTask.addXML(self, node)
        if not self.gradients:
            raise InfoNotFoundError("No gradients for gradient task")

        newNode = node.ownerDocument.createElement('gradient')
        newNode.setAttribute("type", "xyz")
        gradText = arrayToText(self.gradients, format='%18.12f')
        textNode = node.ownerDocument.createTextNode('gradients')
        textNode.nodeValue = gradText
        newNode.appendChild(textNode)
        node.appendChild(newNode)
    


class FrequencyTask(GradientTask): #whatever you have frequencies for, you also have gradients for

    def addXML(self, node):
        GradientTask.addXML(self, node)
        if not self.fc:
            raise InfoNotFoundError("No force constants for frequency task")

        newNode = node.ownerDocument.createElement('fc')
        newNode.setAttribute("type", self.getType())
        str_arr = []
        format = lambda x: "%18.12f" % x
        for row in self.fc:
            nextline = "".join(map(format, row))
            str_arr.append(nextline)
        fcText = "\n".join(str_arr)
        textNode = node.ownerDocument.createTextNode('fc')
        textNode.nodeValue = fcText
        newNode.appendChild(textNode)
        node.appendChild(newNode)

class Locatable(Identity):

    FOLDER_ATTRIBUTES = [ 'title', 'jobtype', 'wavefunction', 'basis' ]

    def __init__(self):
        self.folderAttributes = self.FOLDER_ATTRIBUTES[:]

    def addFolderAttribute(self, attr):
        self.folderAttributes.append(attr)

    def renameFolder(self, *xargs, **kwargs):
        baseFolder = os.getcwd()
        if "baseFolder" in kwargs:
            baseFolder = kwargs[baseFolder]
            del kwargs[baseFolder]
        newFolderAttrs = self.folderAttributes[:]
        newFolderAttrs.extend(xargs)

        self.folder = baseFolder
        for attr in newFolderAttrs:
            attrval =  self.getAttribute(attr)
            if attrval:
                self.folder = os.path.join(self.folder, str(attrval))
        for attr in kwargs:
            attrval = "%s_%s" % ( toString(kwargs[attr]), toString(self.getAttribute(attr)) )
            self.folder = os.path.join(self.folder, attrval)

        #clean up the name
        self.folder = self.folder.replace("(", "_").replace(")","")

## Encapsulates a generic quantum chemistry calculation, i.e. something you can make an input file for and run
class QuantumTask(Task, Runnable, Locatable):    
    
    ATTRIBUTE_SET_METHODS = {
        "machine" : "setMachine",
    }

    FOLDER_ATTRIBUTES = [ 'title', 'jobtype', 'wavefunction', 'basis' ]

    sendnumber = 1
    
    ##Constructor
    # @param computation The computation object that specifies the single point
    # @param machine The machine to run the task on.  This can be a machine object or string identifier
    # @param inputFile 
    # @param outputFile
    # @param folder
    def __init__(self, computation, machine=None, inputFile = "input.dat", outputFile = "output.dat", folder=None):
        self.computation = computation


        Locatable.__init__(self)

        #get the file names, and potentially the folders if they are given with the file name
        inputFolder, self.inputFile = os.path.split(inputFile)
        outputFolder, self.outputFile = os.path.split(outputFile)
        if not folder and inputFolder: #get the folder from the input file
            self.setFolder(inputFolder)
        elif not folder and outputFolder:
            self.setFolder(outputFolder)
        elif not folder: 
            self.renameFolder()
        else:
            self.setFolder(folder)
        
        ## An instance of a job class that is carrying out the process of running the single point calculation
        ## This is not initialized in the constructor, but rather must be set later when the task is actually run
        self.job = None
        ## Parser to be created later
        self.parser = None

        #if no machine param is given, just make it the opt queue
        if not machine:
            import chem.machines
            self.machine = chem.machines.getDefaultMachine()
        else:
            import chem.machines
            self.machine = chem.machines.getMachine(machine)

        self.energies = None
        self.gradients = None
        self.fc = None

        Task.__init__(self)

    def __str__(self):
        str_array = ["Folder=%s" % self.folder]
        str_array.append("Input File=%s" % self.getInputFile() )
        str_array.append("Output File=%s" % self.getOutputFile() )
        str_array.append("Machine=%s" % self.machine)
        str_array.append("Computation:\n%s" % self.computation)
        return "\n".join(str_array)
   
    ## Required interface method. All quantum tasks are required to return an instance of themselves that is compatible
    ## with a single point calcluation. Unless overridden, it just returns a copy
    def getSinglePointCopy(self):
        return self.copy()
    
    ## Finalizes the task, performing any special operations.  For the parent class, it just creates a parser
    ## for the input file
    def finalize(self):
        import parse
        path = os.path.join(self.folder, self.outputFile)
        self.parser = parse.getParser(path)
        if not self.parser:
            raise TaskError("Unable to build parser for \n%s" % path)
    
        energy = self.parser.getEnergy(self.computation.getAttribute("wavefunction"))
        self.computation.setEnergy(energy)


        newXYZ = self.parser.getXYZ("initial") #we must match the gradients to the initial orientation
        self.computation.setXYZ(newXYZ)

        try:
            self.energies = self.parser.getAllEnergies()
        except InfoNotFoundError, error:
            sys.stderr.write("%s\n%s\n" % (traceback(error), error))
            sys.exit("no energies found")
        
        try:
            self.xyzgradients = self.parser.getGradients()
            self.xyzgradients.convertUnits('hartree/bohr')
            self.gradients = self.xyzgradients.copy(); self.gradients.toVector()
        except InfoNotFoundError:
            pass

        try:
            self.fc = self.parser.getForceConstants()
            self.fc.convertUnits('hartree/bohr^2')
        except InfoNotFoundError:
            pass

    ## Returns a named attribute.  If attribute is not found, it returns None.  Currently, all named attributes come 
    ## directly from the computation object.
    #  @param The name of the named attribute (case insensitive)
    #  @return The value of the named attribute
    def getAttribute(self, name):
        return self.computation.getAttribute(name)

    ## Gets the computation object associated with the given task
    #  @return The computation object
    def getComputation(self):
        return self.computation

    ## Gets the input file associated with this task
    #  @return The name of the input file, relative to the folder. i.e. not the full path
    def getInputFile(self):
        return self.inputFile 

    ## Gets the folder the task is running in
    #  @return The folder
    def getFolder(self):
        return self.folder

    ## Gets the job associated with this task
    # @return An instance of a job class
    def getJob(self):
        return self.job

    ## Gets the machine object this task is associated with
    #  @return The task's machine object
    def getMachine(self):
        return self.machine

    ## Gets the molecule associated with this tasks.  This is actually a full Computation object,
    ## but a Computation inherit from the Molecule class
    #  @return A molecule instance... the parent molecule
    def getMolecule(self):
        return self.computation

    ## Gets the output file associated with the task
    #  @return The name of the output file, relative to the folder. i.e. not the full path
    def getOutputFile(self):
        return self.outputFile

    ## Rather than just the filename, get the full path of the output file
    #  @return Full path of output file
    def getOutputPath(self):
        return os.path.join(self.folder, self.outputFile)
    
    ## Rather than just the filename, get the full path of the input file
    #  @return Full path of input file
    def getInputPath(self):
        return os.path.join(self.folder, self.inputFile)

    ## Gets the parser object
    # @return A parser object for the quantum task.  None if no parser exists yet
    def getParser(self):
        return self.parser

    ## Gets the program associated with this single point calculation
    #  @return A string identifying the program
    def getProgram(self):
        return self.computation.getAttribute("program")

    ## Checks whether or not the given task is completed by checking to see whether the corresponding job is done
    #  @return A boolean. True if the job is completed. False if the job is not completed.
    def isCompleted(self):
        if self.job: #it has been created
            return self.job.isCompleted()
        else: #no job has been created yet, so it couldn't possible be done
            return None

    def getEnergy(self):
        return self.computation.getEnergy()

    ## Creates the input file text and returns it as a string
    #  @return The text of the input file associated with the computation
    def getInputFileText(self):
        return self.computation.makeFile()

    def make(self):
        self.writeFile()

    def sendToMachine(self):
        self.__class__.sendnumber += 1
        import machines
        self.machine.addTask(self)

    ## Tells the machine to run this job
    def run(self, wait=False):
        import jobs
        batch = jobs.Batch(self.machine, [self])
        batch.run(wait=True)

    ## Sets a given attribute for the task.  This may set an attribute for the computation
    ## or it may call a special method from the static ATTRIBUTE_SET_METHODS.
    def setAttribute(self, attributeName, attributeValue):
        if attributeName.lower() in self.ATTRIBUTE_SET_METHODS:
            method = getattr(self, self.ATTRIBUTE_SET_METHODS[attributeName.lower()])
            method(attributeValue)
        else:
            self.computation.setAttribute(attributeName, attributeValue)
    
    ## Set the computation object associated with the input file
    ## @param newComp The new computation
    def setComputation(self, newComp):
        self.computation = newComp

    def setInputFile(self, file):
        (directory, filename) = os.path.split(file)
        self.inputFile = filename
        if directory:
            self.setFolder(directory)
            
    ## Sets the folder for the task.  This will convert all relative paths to absolute paths
    #  @param The new folder
    def setFolder(self, folder):
        #if the folders are given as a relative path, make them absolute
        if folder[:2] == "./":   
            folder = os.path.join(os.getcwd(), folder[2:])
        elif folder == ".":
            folder = os.getcwd()
        elif not folder[0] == "/":
            folder = os.path.join(os.getcwd(), folder)
        self.folder = folder


    ## Sets the job corresponding to this task
    #  @param job An instance of a job object
    def setJob(self, job):
        self.job = job

    ## Sets a new machine object for the task
    #  @param Either a machine object or a string identify the machine
    def setMachine(self, machine):
        if isinstance(machine, str):
            import Machines
            self.machine = Machines.getMachine(machine)
        else:
            self.machine = machine

    ## Sets the output file that this task will read in after it is finished
    #  @param A string giving the name of the output file
    def setOutputFile(self, file):
        (directory, filename) = os.path.split(file)
        self.outputFile = filename
        if directory: #if a full file path has been given
            self.setFolder(directory)
    
    ## Sets the xyz coordinates for the moleculue
    #  @param The new xyz coordinates.  Must be a compatible matrix or DataPoint object
    def setXYZ(self, xyz):
        self.computation.setXYZ(xyz)

    ## Allows the user to give a piece of info to the object, and it tries to determine
    ## what needs to be done.
    #  @param object Some variable to update the task
    #  @return A boolean.  Whether or not the task was able to update itself.
    def update(self, object):
        if isinstance(object, Input.Computation):
            self.computation = object
            return True
        else:
            return False

    ## Actually creates an input file to the disk and ensures that the input and output folders exist
    def writeFile(self):
        #ensure the directories exist
        makeFolder(self.folder)

        fileText = self.computation.makeFile()

        import writer
        if isinstance(fileText, writer.MultiFile):
            #write out all the auxilliary files to the folder
            otherFiles = fileText.getOtherFiles()
            for filename in otherFiles:
                filepath = os.path.join(self.folder, filename)
                fileObj = open(filepath, "w")
                fileObj.write( otherFiles[filename] )
                fileObj.close()

            fileText = fileText.getMainFile()

        fileObj = open( os.path.join(self.folder, self.inputFile), "w")
        fileObj.write(fileText)
        fileObj.close()
        files_to_copy = self.computation.getFilesToCopy()
        for file in files_to_copy:
            copyLocation = os.path.join(self.folder, files_to_copy[file])
            sys.stderr.write("Copying %s to %s\n" % (file, copyLocation))
            os.system("cp %s %s" % (file, copyLocation) )    

    def addXML(self, node):
        parent = node.ownerDocument
        molNode = parent.createElement('molecule')
        self.computation.addXML(molNode)
        node.appendChild(molNode)

## @class SinglePoint Encapsulates a single point calculation
class Property(QuantumTask, EnergyTask):
    ##Constructor
    # @param comp The computation object that specifies the single point
    # @param prog The program to use in running the single point
    # @param taskName The name to identify this single point object. If default "CHOOSE" is given, the program
    #                 selects a suitable name based on the keywords.
    def __init__(self, computation, machine = None, inputFile = "input.dat", outputFile = "output.dat", folder=None):
        computation.setAttribute("jobtype", "oeprop")
        QuantumTask.__init__(self, computation, machine, inputFile, outputFile, folder)

## @class SinglePoint Encapsulates a single point calculation
class SinglePoint(QuantumTask, EnergyTask):
    ##Constructor
    # @param comp The computation object that specifies the single point
    # @param prog The program to use in running the single point
    # @param taskName The name to identify this single point object. If default "CHOOSE" is given, the program
    #                 selects a suitable name based on the keywords.
    def __init__(self, computation, machine = None, inputFile = "input.dat", outputFile = "output.dat", folder=None):
        computation.setAttribute("jobtype", "singlepoint")
        QuantumTask.__init__(self, computation, machine, inputFile, outputFile, folder)

    def __str__(self):
        str_array = [ QuantumTask.__str__(self) ]
        if self.energies:
            for energy in self.energies:
                type = energy.getAttribute('wavefunction')
                str_array.append( "%s=%14.10f" % (type, energy) )
        return "\n".join(str_array)

    ## Gets all the energies associated with this single point calculation
    #  @return A dictionary where the keys are wavefunction types and the values are energies
    def getAllEnergies(self):
        return self.energies

    ## Gets a specific type of energy - which is only valid after the task has finished
    #  @param energyType A string identfying the type of energy you wish to grab
    #  @return A float, the energy requested
    #  @throws InfoNotFoundError if the requested type of energy does not exist in this single point
    def getEnergy(self, energyType="best"):
        try:
            if energyType.lower() == "best": #if best is sent, figure out which is best from the list
                energyType = self.computation.getAttribute("wavefunction")
            energy = self.energies[energyType] #this might throw an exception
            return energy
        except KeyError: #this is not a valid energy type
            raise TaskError("Energy type %s does not exist for\n%s" % (energyType, self))

    ## Finalizes the task, in this case reads all the info that can be found from a single point calculation
    def finalize(self):
        QuantumTask.finalize(self)

    def addXML(self, node):
        QuantumTask.addXML(self, node)
        EnergyTask.addXML(self, node)

class Gradient(QuantumTask, GradientTask):

    ##Constructor
    # @param computation The computation object that specifies the single point
    # @param machine The machine to run the task on.  This can be a machine object or string identifier
    # @param inputFile 
    # @param outputFile
    # @param folder
    def __init__(self, computation, machine = None, inputFile = "input.dat", outputFile = "output.dat", folder=None):
        if not folder: 
            folder = os.path.join( os.getcwd(), "gradient" )

        QuantumTask.__init__(self, computation, machine, inputFile, outputFile, folder)
        ## The xyz gradients
        self.gradients = []
        self.computation.setAttribute("jobtype", "gradient")

    def getGradients(self):
        return self.gradients

    def printGradients(self):
        sys.stdout.write("Gradients in %s\n%s\n" % self.gradients.getUnits(), self.gradients)

    def finalize(self):
        QuantumTask.finalize(self)

    def addXML(self, node):
        QuantumTask.addXML(self, node)
        GradientTask.addXML(self, node)

    def getGradientType(self):
        return "xyz"

class Frequency(QuantumTask, FrequencyTask):

    ##Constructor
    # @param computation The computation object that specifies the single point
    # @param machine The machine to run the task on.  This can be a machine object or string identifier
    # @param inputFile 
    # @param outputFile
    # @param folder
    def __init__(self, computation, machine = None, inputFile = "input.dat", outputFile = "output.dat", folder=None):
        if not folder: 
            folder = os.path.join( os.getcwd(), "freq" )

        QuantumTask.__init__(self, computation, machine, inputFile, outputFile, folder)
        ## The xyz gradients
        self.gradients = []
        self.computation.setAttribute("jobtype", "frequency")

    def getGradients(self):
        import numpy
        grads = []
        for entry in self.gradients:
            grads.extend(map(float, entry))
        return DataPoint(grads, attributes=self.gradients.getAttributes())

    def getXYZGradients(self):
        return self.gradients

    def finalize(self):
        QuantumTask.finalize(self)

    def addXML(self, node):
        QuantumTask.addXML(self, node)
        FrequencyTask.addXML(self, node)

    def getType(self):
        return "xyz"

class Optimization(QuantumTask, OptimizationTask):

    ##Constructor
    # @param computation The computation object that specifies the single point
    # @param machine The machine to run the task on.  This can be a machine object or string identifier
    # @param inputFile 
    # @param outputFile
    # @param folder
    def __init__(self, computation, machine = None, inputFile = "input.dat", outputFile = "output.dat", folder=None):
        OptimizationTask.__init__(self) #doesn't actually do anything... yet anyway

        if not folder: folder = os.path.join( os.getcwd(), "opt" )

        QuantumTask.__init__(self, computation, machine, inputFile, outputFile, folder)
        ## A list of the eneriges at each step
        self.energies = []
        ## A list of the xyz gradients at each step
        self.gradients = []
        ## A list of the xyz geometries at each step
        self.geometries = []
        self.computation.setAttribute("jobtype", "optimization")

    ## Sends back a string representation, i.e. info description, of this class
    # @return A string name
    def __str__(self):
        return QuantumTask.__str__(self)

    ## Gets all the energies associated with this single point calculation
    #  @return A dictionary where the keys are wavefunction types and the values are energies
    def getOptEnergies(self):
        return self.energies

    def getEnergy(self, step="last"):
        if step.lower() == "last":
            return self.energies[-1]
        else:
            return self.energies[step]

    def getGradient(self, step='last'):
        if step.lower() == "last":
            return self.gradients[-1]
        else:
            return self.gradients[step]

    ## Finalizes the task, in this case reads all the info that can be found from a single point calculation
    def finalize(self):
        QuantumTask.finalize(self)
        self.energies = self.parser.getOptEnergies()
        self.gradients = self.parser.getOptGradients()
        self.geometries = self.parser.getOptXYZ()

## @class EnergyCorrection This is just an identifier for a task to say that it is not meant to give a full blown
## electronic energy, but rather an energy correction like relativity or dboc.
class EnergyCorrection(SinglePoint): 

    def __init__(self, computation, machine = None, inputFile = "input.dat", outputFile = "output.dat", folder=None):
        SinglePoint.__init__(self, computation, machine, inputFile, outputFile, folder)
        computation.setAttribute("jobtype", "relativity")
        if self.hasattr('program'):
            computation.setAttribute("program", "program")

    def getEnergy(self, type=None):
        if not type or type.lower() == self.type:
            return self.correction
        else:
            return SinglePoint.getEnergy(self, type)

    ## Finalizes the task, in this case reads all the info that can be found from a single point calculation
    def finalize(self):
        QuantumTask.finalize(self)
        self.correction = self.parser.getEnergy(self.type)


class Relativity(SinglePoint):
    
    type = 'relativity'
    program = 'aces' #only run with ACES

class DBOC(EnergyCorrection, SinglePoint):

    type = 'dboc'
    program = 'aces' #only run with ACES
    
class MultiTask(Project):
    
    def __init__(self, computation):
        Project.__init__(self)
        self.molecule = computation
        self.attributeTasks = []

    def getSinglePointCopy(self):
        return self.taskList[0].getSinglePointCopy()

    def addAttributeTask(self, task):
        self.attributeTasks.append(task)

    def addRunTask(self, task):
        Project.addTask(self, task)

    def addTask(self, task):
        self.attributeTasks.append(task)
        Project.addTask(self, task)

    def writeFile(self):
        for task in self.getAllTasks():
            task.writeFile()
    
    def getMolecule(self):
        return self.molecule

    def getComputation(self):
        return self.molecule

    def setAttribute(self, attr, value):
        for task in self.attributeTasks:
            task.setAttribute(attr, value)

    def renameFolder(self, *xargs):
        for task in self.attributeTasks:
            task.renameFolder(*xargs)

    def addFolderAttribute(self, attr):
        for task in self.attributeTasks:
            task.addFolderAttribute(attr)

    def setFolder(self, folder):
        for task in self.attributeTasks:
            task.setFolder(folder)

    def setInputFile(self, file):
        for task in self.attributeTasks:
            task.setInputFile(file)

    def setOutputFile(self, file):
        for task in self.attributeTasks:
            task.setOutputFile(file)

    def setXYZ(self, xyz):
        for task in self.attributeTasks:
            task.setXYZ(xyz)
        self.molecule.setXYZ(xyz)

    def getMachine(self):
        return self.machine

    def setMachine(self, machine):
        for task in self.attributeTasks:
            task.setMachine(machine)

class CoreCorrection(EnergyTask, MultiTask):

    FOLDER_ATTRIBUTES = QuantumTask.FOLDER_ATTRIBUTES[:]
    FOLDER_ATTRIBUTES.append('core')

    def __init__(self, computation, machine = None, inputFile = "input.dat", outputFile = "output.dat", folder=None):
        MultiTask.__init__(self, computation)
                 
        basis = computation.getAttribute("basis")
        core_basis = None
        core_type = re.compile("[-](p[w]?)").search(basis.lower())
        if core_type:
            core_type = core_type.groups()[0]
            zeta_level = re.compile("([dtqDTQ5])[zZ]").search(basis).groups()[0]
            core_basis = "cc-%sCV%sZ" % (core_type, zeta_level)
            if "+" in basis or "AUG" in basis: #diffuse functions
                core_basis = "aug-" + core_basis
        else: #this must be a special user specified base
            core_basis = basis.lower()

        self.molecule = computation

        core_folder = folder
        froz_folder = folder
        if folder:
            core_folder = os.path.join(folder, 'correlated')
            froz_folder = os.path.join(foler, 'frozen')

        correlated = computation.copy()
        correlated.setAttribute("core", "correlated")
        correlated.setAttribute("basis", core_basis)

        frozen = computation.copy()
        frozen.setAttribute("core", "frozen")
        frozen.setAttribute("basis", core_basis)

        #best to keep track here
        self.correlated = taskmake(correlated, 'sp', machine=machine, inputFile=inputFile, outputFile=outputFile, folder=core_folder)
        self.frozen = taskmake(frozen, 'sp', machine=machine, inputFile=inputFile, outputFile=outputFile, folder=froz_folder)

        self.addTask(self.correlated)
        self.addTask(self.frozen)

    def getEnergy(self, type = 'best'):
        energy = self.correlated.getEnergy(type) - self.frozen.getEnergy(type)
        return energy

    def setFolder(self, folder):
        self.correlated.setFolder( os.path.join(folder, 'correlated'))
        self.frozen.setFolder( os.path.join(folder, 'frozen'))

class CompositeTask(MultiTask):
    ##Constructor

    ATTRIBUTE_MAP = {
        "energy" : "getEnergy",
        "gradients" : "getGradients",
        "fc" : "getForceConstants",
    }

    def __init__(self, computation, equation, machine = None, 
                 inputFile = "input.dat", outputFile = "output.dat", folder=None,  
                 **kwargs):

        MultiTask.__init__(self, computation)
        self.addRunMethods()
        self.addMethod('compute')

        self.equation = equation
        self.tasks = {}

        nameregexp = "[\d* ]*([a-zA-Z\d]+)"
        tasknames = re.compile(nameregexp).findall(self.equation)
        for name in tasknames:
            task = kwargs[name]
            task.setAttribute('taskname', name)
            task.addFolderAttribute('taskname')
            task.renameFolder()
            self.tasks[name] = task
            self.addTask(task)

        self.molecule = computation

    def buildTasks(self, inputArea):
        inputArea = kwargs['inputArea'].lower() #lower case only
        template = None
        if kwargs.has_key('template'):
            template = kwargs['template']
        task_regexp = r"([a-zA-Z]+)\s+([a-zA-Z\d]+)\s*=\s*[{][\s\n]*(.*?)[}]"
        task_input_list = re.compile(task_regexp, re.DOTALL).findall(inputArea)
        self.tasks = {}

        for tasktype, taskname, options in task_input_list:
            import quantum
            newcomp = computation.copy()
            #set all the necessary options
            option_regexp = "([a-zA-Z\d]+)\s*[=]\s*([a-zA-Z\)\(\-\d]+)"
            option_list = re.compile(option_regexp).findall(options)
            for key, value in option_list:
                try:
                    newcomp.setAttribute(key, value)
                except GUSInputError: #not a real keyword, just ignore
                    sys.stderr.write("Invalid molecule attribute %s. Skipping for now.\n" % key)


            task = None
            if template:
                task = template.copy()
            else:
                task = taskmake(newcomp, jobtype=tasktype, machine = machine, inputFile = inputFile, 
                                outputFile = outputFile, folder = folder)

            for key, value in option_list:
                task.setAttribute(key, value)

            #make the folder task specific
            if folder:
                newfolder = os.path.join(folder, taskname)
                task.setFolder(newfolder)
            else:
                task.addFolderAttribute('__class__')
                task.renameFolder()

            self.tasks[taskname] = task #store as lowercase version
            self.addTask(task)

    def setFolder(self, folder):
        for taskname in self.tasks:
            newfolder = os.path.join(folder, taskname)
            self.tasks[taskname].setFolder(newfolder)

    def computeAttribute(self, attr):
        try:
            values = {}
            buildMethod = self.ATTRIBUTE_MAP[attr]
            for taskname in self.tasks:
                task = self.tasks[taskname]
                task.finalize()
                method = getattr(task, buildMethod)
                value = method()
                values[taskname] = value
            numeqn = self.equation[:]
            for taskname in values:
                numeqn = numeqn.replace(taskname, "values['%s']" % taskname)
            finalval = eval(numeqn)
            setattr(self, attr, finalval)
        except Exception, error:
            sys.stderr.write("%s\n%s\n",traceback(error),error)
            pass #we don't have it

    def getEnergy(self):
        return self.energy

    def getGradients(self):
        return self.gradients

    def getForceConstants(self):
        return self.fc

    def saveHessian(self):
        save(self.fc, "hessian") 

    def finalize(self):
        for taskname in self.tasks:
            self.tasks[taskname].finalize()
        self.compute()

    def compute(self):
        for attr in self.ATTRIBUTE_MAP:
            self.computeAttribute(attr)

    def addXML(self, node):
        parent = node.ownerDocument
        molNode = parent.createElement('molecule')
        self.molecule.addXML(molNode)
        node.appendChild(molNode)

class CompositeEnergy(CompositeTask, EnergyTask):

    def getAllEnergies(self):
        return [DataPoint(self.energy, type="molecular")]

    def addXML(self, node):
        CompositeTask.addXML(self, node)
        EnergyTask.addXML(self, node)

class CompositeFrequency(CompositeTask, FrequencyTask):

    def __init__(self, computation, equation, machine = None, 
                 inputFile = "input.dat", outputFile = "output.dat", folder=None, type="internals",
                 **kwargs):
        CompositeTask.__init__(self, computation, equation, machine = machine, 
                     inputFile = inputFile, outputFile = outputFile, folder=folder,
                     **kwargs)
        self.fctype = type

    def getForceConstantType(self):
        return self.fctype

    def addXML(self, node):
        CompositeTask.addXML(self, node)
        GradientTask.addXML(self, node)

class CompositeGradient(CompositeTask, GradientTask):

    def __init__(self, computation, equation, machine = None, 
                 inputFile = "input.dat", outputFile = "output.dat", folder=None, type="internals",
                 **kwargs):
        CompositeTask.__init__(self, computation, equation, machine = machine, 
                     inputFile = inputFile, outputFile = outputFile, folder=folder,
                     **kwargs)
        self.gradienttype = type
    
    def getGradientType(self):
        return self.gradienttype

    def addXML(self, node):
        CompositeTask.addXML(self, node)
        FrequencyTask.addXML(self, node)


class ROHFCorrection(EnergyTask, MultiTask):

    FOLDER_ATTRIBUTES = QuantumTask.FOLDER_ATTRIBUTES[:]
    FOLDER_ATTRIBUTES.extend(['reference'])
    
    def __init__(self, computation, machine=None, inputFile='input.dat', outputFile = 'output.dat', folder=None):
        MultiTask.__init__(self, computation)


        from focal import FocalPoint
        energyList = FocalPoint.ENERGY_LIST[:]
        energyList.reverse() #go from high to low

        #the wavefunction for running the perturbation
        pertwfn = computation.getAttribute('wavefunction')
        #the wavefunction for running the full treatment
        fullwfn = None
        for i in range(len(energyList) - 1):
            if wfn == energyList[i].lower():
                fullwfn = energyList[i+1].lower()
                break
        if not fullwfn:
            raise ProgrammingError("You cannot do an ROHF correction for %s" % pertwfn)

        self.uhfwfn = pertwfn
        self.rohfwfn = fullwfn
    
        fullrohf = computation.copy()
        fullrohf.setattribute("wavefunction", fullwfn)
        fullrohf.setattribute("reference", "rohf")
        self.rohf_task = SinglePoint(fullrohf, machine, inputFile, outputFile, folder)

        pertuhf = computation.copy()
        pertuhf.setattribute("wavefunction", self.high)
        pertuhf.setattribute("reference", "uhf")
        self.rohf_task = SinglePoint(pertuhf, machine, inputFile, outputFile, folder)

        self.addTask(self.rohf_task)
        self.addTask(self.uhf_task)

    def getAllEnergies(self):
        edict = self.rohf_task.getAllEnergies()
        edict[self.high] = self.getEnergy()
        return edict

    def getEnergy(self):
        low_ROHF = self.rohf_task.getEnergy(self.rohfwfn)
        low_UHF = self.uhf_task.getEnergy(self.rohfwfn)
        high_UHF = self.uhf_task.getEnergy(self.uhfwfn)
        energy = high_UHF - low_UHF + low_ROHF
        return energy

class taskmake(object):

    SPECIAL_CASES = {
        ROHFCorrection : {
            'wavefunction' : ['ccsdt(q)'],
            'reference' : ['rohf'],
        }
    }

    CLASS_LIST = {
        'singlepoint' : SinglePoint,
        'sp' : SinglePoint,
        'oeprop' : Property,
        'optimization' : Optimization,
        'opt' : Optimization,
        'core' : CoreCorrection,
        'dboc' : DBOC,
        'relativity' : Relativity,
        'rel' : CoreCorrection,
        'composite': CompositeTask,
        'gradient' : Gradient,
        'frequency' : Frequency,
        'freq' : Frequency,
        'fc' : Frequency,
    }
    
    def __new__(cls, computation, jobtype=None, machine=None, inputFile='input.dat', outputFile='output.dat', folder=None, **kwargs):
        if not jobtype:
            jobtype = computation.getAttribute('jobtype')
        specialClass = cls.checkSpecialCases(computation)
        if specialClass:
            return specialClass(computation.copy(), machine, inputFile, ouptutFile, folder, **kwargs)
        else:
            regularClass = taskmake.CLASS_LIST[jobtype.lower()]
            return regularClass(computation.copy(), machine, inputFile, outputFile, folder, **kwargs)

    def buildTask(obj):
        import input
        import parse
        if isinstance(obj, input.Computation):
            newTask = taskmake(obj)
            newTask.finalize()
            return newTask
        elif os.path.isfile(obj):
            parser = parse.getParser(obj)
            if parser:
                comp = parser.getComputation()
                if comp:
                    newTask = taskmake(comp)
                    newTask.setOutputFile(obj)
                    newTask.finalize()
                    return newTask

    def checkSpecialCases(cls, computation):
        for classtype in cls.SPECIAL_CASES:
            attrchecks = cls.SPECIAL_CASES[classtype]
            foundMatch = True
            for attr in attrchecks:
                selfattr = computation.getAttribute(attr)
                foundMatch = False #assume no match
                for potential_match in attrchecks:
                    if potential_match == selfattr:
                        foundMatch = True
                        continue
                if not foundMatch:
                    continue #this is not a match
            if foundMatch:
                return classtype
        #if we get here, having not returned, we should just return None
        return None

    checkSpecialCases=classmethod(checkSpecialCases)
    buildTask=staticmethod(buildTask)

def rebuildtask(task, **kwargs):
    newtask = task.copy()
    for attr in kwargs:
        val = kwargs[attr]
        newtask.setAttribute(attr, val)
    return newtask
