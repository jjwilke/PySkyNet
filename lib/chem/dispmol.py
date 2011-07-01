from chem.project import Project
from skynet.utils.utils import *
from skynet.errors import * 
from chem.data import *

class DisplacementProject(Project):
    ##Constructor
    # @param task The task for an energy at each displacement
    def __init__(self, energyTask, energyFile="psi"):
        self.templateTask = energyTask
        self.energies = None #no energies yet
        self.energyFile = energyFile.upper()
        Project.__init__(self)

        self.addMethod('readDispCart')
        self.addRunMethods()
        self.addMethod('readDisplacements')

    def __str__(self):
        str_array = [ Project.__str__(self) ]
        energy = self.getEnergy()
        if energy: str_array.append("Energy=%14.10f" % energy)
        return "\n".join(str_array)

    def getMolecule(self):
        return self.templateTask.getMolecule()

    def getEnergies(self):
        return self.energies

    def getEnergy(self):
        if self.energies: return self.energies[0] #if there are energies
        else: return None #if there are no energies

    ## Reads the dispcart file and stores the coordinates in a list of 2-D coordinate arrays.  This
    #  is only set up to read a file named "dispcart" in the current working directory.
    #  @return A list of molecules
    def readDispCart(self, taskFolder=None):
        import re
        fileText = ""
        try:
            disp_file = "dispcart"
            fileText = open(disp_file).read()
        except (IOError, IndexError):
            raise RunError("no dispcart file")

        if not taskFolder: taskFolder = os.getcwd() #none specified, just use the top folder 
        if not os.path.isdir(taskFolder): os.mkdir(taskFolder) #if it does not yet exist, make it
            
        def makeNewTask(geomText, geomNumber):
            geomLines = re.compile("\s+([-]?\d+[.]\d+)\s+([-]?\d+[.]\d+)\s+([-]?\d+[.]\d+)").findall(geomText)
            coordinates = []
            for line in geomLines:
                (x, y, z) = map(eval, line)
                coordinates.append( [x, y, z] )
            coordinates = DataPoint(coordinates, units='bohr')
            newTask = self.templateTask.copy()
            #all of the geometries in the dispcart file are in bohr, let the task know
            newTask.setXYZ(coordinates)
            newTask.setAttribute("coordtype", "xyz")
            newTask.setAttribute("disp", "disp_%d" % geomNumber)
            newTask.addFolderAttribute("disp")
            newTask.renameFolder()
            self.addTask(newTask)

        geomNumber = 1
        regExp = r"(?<!\d)%d\s*\n(.*?)\n%d\s*\n"
        geomFound = re.compile(regExp % (geomNumber, geomNumber + 1), re.DOTALL).search(fileText)
        while geomFound: #while we are still finding geometry
            geomText = geomFound.groups()[0]
            makeNewTask(geomText, geomNumber)
            #try for the next geometry
            geomNumber += 1
            geomFound = re.compile(regExp % (geomNumber, geomNumber + 1), re.DOTALL).search(fileText)        
        #pick up the last set of coordinates
        geomText = re.compile("(?<!\d)%d\s*\n(.*)" % geomNumber, re.DOTALL).search(fileText).groups()[0]
        makeNewTask(geomText, geomNumber)

    ## Reads all the energies in a folder and writes the list of energies to energy.dat
    # @return None. Writes all the output to energy.dat
    def readDisplacements(self):        
        #add the xml document that will display all the data from the displacements
        import xml.dom.minidom
        xmldoc = xml.dom.minidom.Document()
        docelem = xmldoc.createElement('project')
        xmldoc.appendChild(docelem)

        energies = []
        geometries = []
        failedTasks = {} #keeps track of anything that failed
        self.failedTasks = []
        dispnumber = 1
        for task in self.getAllTasks():
            try:
                energy = task.getEnergy()
                if not energy: 
                    raise InfoNotFoundError
                energies.append(energy)
                mol = task.getMolecule()
                xyz = mol.getXYZ().getValue(units='bohr')
                newdisp = xmldoc.createElement('displacement')
                newdisp.setAttribute('number', '%d' % dispnumber)
                task.addXML(newdisp)
                xmldoc.documentElement.appendChild(newdisp)
                geometries.append(xyz)
                dispnumber += 1
            except ConvergenceError:
                fileName = task.getOutputPath()
                failedTasks[fileName] = "CONVERGENCE ERROR"
                self.failedTasks.append(task)
            except InfoNotFoundError, error:
                fileName = task.getOutputPath()
                failedTasks[fileName] = "NO ENERGY FOUND"
                self.failedTasks.append(task)

        if len(failedTasks) > 0:
            #recipient = EMAIL
            subject = "Error in project"
            message = ""
            for failure in failedTasks:
                message += "\n%s %s" % (failure, failedTasks[failure])
            #sendMail(recipient, message, subject)
            sys.stderr.write("%s\n" % message)
            #we are currently in the process of reading the displacement energies
            #however, since the tasks have failed, we will want to revert ourselves back to refinalize
            #all the tasks
            self.nextMethod = "finalizeTasks"
            self.save()
            raise ProjectStop

        #okay all energies were computed properly, hip-hip hurray

        if self.energyFile == "PSI": #make an energy.dat file
            out_file = open("energy.dat", "w")
            str_array = []
            for energy in energies:
                str_array.append("%18.12f" % energy)
            out_file.write( "\n".join(str_array) )
            out_file.close()

        elif self.energyFile == "MATHEMATICA":
            out_file = open("data.m", "w")
            str_array = ['levels = {"%s"};' % self.templateTask.getAttribute("wavefunction") ]
            str_array.append('ec = Part[Position[levels, theory], 1, 1];')
            str_array.append('EdataX = {')

            fl_to_str = lambda x: "%18.12f" % x
            EdataX_part = []
            for i in range(0, len(energies)):
                current_entry = "\t{\n\t\t{\n%s\n\t\t},\n\t\t{%18.12f}\n\t}" 
                energy = energies[i]
                xyz = geometries[i]
                geom_part = []
                for atom in xyz:
                    geom_part.append( "\t\t\t{%s}" % ",".join(map(fl_to_str, atom[1:])) )
                geom_part = ",\n".join(geom_part)
                current_entry = current_entry % (geom_part, energy)
                EdataX_part.append(current_entry)
            EdataX_part = ",\n".join(EdataX_part)
            str_array.append(EdataX_part)
            str_array.append("};")
            #now, finally, write out the data to the file
            out_file.write("\n".join(str_array))
            out_file.close()

        #store the energies as a member variable
        self.energies = energies
        self.geometries = geometries

        #output all important info as an xml file
        filetext = xmldoc.toprettyxml()
        fileObj = open("data.xml", "w")
        fileObj.write(filetext)
        fileObj.close()

