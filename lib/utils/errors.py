class GUSException(Exception):

    def __init__(self, msg=None):
        self.message = msg

    def __str__(self):
        strval = "%s" % self.__class__
        if self.message:
            strval += ": %s" % self.message
        return strval


class ParsingError(GUSException): pass

class InfoNotFoundError(ParsingError): pass

class ConvergenceError(ParsingError): pass

class ProgrammingError(GUSException): pass

class DataError(GUSException):
    
    def __init__(self, msg):
        self.message = msg

class ComputationError(GUSException): pass

class ExtrapolationError(ComputationError): pass

class GUSAttributeError(GUSException): pass

class GUSInputError(GUSException): pass


class RunError(GUSException): pass

class TaskError(GUSException): pass


class ControlFlowException(GUSException): pass

class ProjectSuspend(ControlFlowException): pass

class ProjectStop(ControlFlowException): pass

class AdvanceAndWait(ControlFlowException):
    def __init__(self, param=1):
        self.param = param
    def getAdvancer(self):
        return self.param

class Advance(ControlFlowException):
    def __init__(self, param=1):
        self.param = param
    def getAdvancer(self):
        return self.param

class InputError(GUSException): pass

class KeywordError(InputError): pass

class MachineError(GUSException): pass

class SocketError(GUSException): pass

class SocketOpenError(SocketError): pass

class SocketConfirmError(SocketError): pass


class ComputeError(GUSException): pass

class ConvergenceError(ComputeError): pass


class OptionsError(GUSException): pass

class InvalidOptionError(OptionsError): pass

class InvalidValueError(OptionsError): 

    def __init__(self, option="", value="", error=""):
        msg = "For option %s, value %s\n%s" % (option, str(value), error)
        OptionsError.__init__(self, msg)
