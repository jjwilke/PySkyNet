import vim
import sys
import os.path
import os


class PyVimGlobals:
    line = 0
    col = 0
    is_init = False

    std_stderr = None
    std_stdout = None

    stderr = None
    stdout = None

def disconnectErr():
    if not PyVimGlobals.stderr: #already disconnected
        home = os.environ["HOME"]
        errorfile = os.path.join(home, ".vimerr")
        fileobj = open(errorfile, "a+")
        PyVimGlobals.stderr = fileobj
        PyVimGlobals.std_stderr = sys.stderr
    sys.stderr = PyVimGlobals.stderr

def reconnectErr():
    sys.stderr = PyVimGlobals.std_stderr

def disconnectOut():
    if not PyVimGlobals.stdout: #already disconnected
        home = os.environ["HOME"]
        errorfile = os.path.join(home, ".vimout")
        fileobj = open(errorfile, "a+")
        PyVimGlobals.stdout = fileobj
        PyVimGlobals.std_stdout = sys.stdout
    sys.stdout = PyVimGlobals.stdout

def reconnectOut():
    sys.stdout = PyVimGlobals.std_stdout


def display(msg):
    home = os.environ["HOME"]
    file = home + "/vim.out"
    fileobj = open(file, "w")
    for folder in sys.path:
        fileobj.write("%s\n" % folder)
    fileobj.close()
    
    import pygtk
    import gtk
    window = gtk.Window(gtk.WINDOW_TOPLEVEL)
    window.connect("destroy", gtk.main_quit)
    entry = gtk.Entry()
    entry.set_text(msg)
    window.add(entry)

    entry.show()
    window.show()

    gtk.main()

def openReference():
    import os
    os.system("echo vim > ~/vim")
    from pylatex.pytex import loadCitation
    from pygui.utils import gtkIO
    os.system("echo vim >> ~/vim")
    #gtkIO.redirect_io()
    os.system("echo vim >> ~/vim")
    #disconnect stderr and out
    disconnectErr()
    disconnectOut()
    os.system("echo vim >> ~/vim")
    cword = getCurrentWord()
    os.system("echo vim >> ~/vim")
    loadCitation(cword)
    os.system("echo vim >> ~/vim")
    reconnectErr()
    reconnectOut()
    
def appendAtWord(word, *xargs):
    include = xargs
    resetXY()
    col = PyVimGlobals.col
    line = PyVimGlobals.line
    cline = vim.current.buffer[line]
    if not cline: #no line yet
        col = 0
    else:
        while col < len(cline) and (not cline[col] in (' ', ',', '.', ':', ';') or cline[col] in include):
            col += 1
    begin = cline[:col]
    end = cline[col:]
    newline = begin + word + end
    vim.current.buffer[line] = newline

def test():
    line, col = getXY()
    display("before = %d" % col)
    vim.command("l")
    line, col = getXY()
    display("after = %d" % col)

def getCurrentWord():
    resetXY()
    col = PyVimGlobals.col
    line = PyVimGlobals.line
    cline = vim.current.buffer[line]
    if len(cline) == 0: #nothing here
        return ""

    if cline[col] == ' ': #no letters
        return ""

    start = col
    while cline[start] != ' ' and start >= 0:
        start -= 1
    start += 1 #loop goes one too far

    word = []
    letter = start
    length = len(cline)
    while letter < length and cline[letter] != ' ':
        word.append(cline[letter])
        letter += 1

    word = "".join(word)

    #display("\n".join(map(str, dir(vim.current.buffer))))
    #vim.current.buffer.append(word)

    return word

def replace(old, new):
    col = PyVimGlobals.col
    line = PyVimGlobals.line
    cline = vim.current.buffer[line]
    newline = cline.replace(old, new)
    #display("%s %d %s" % (newline, line, newline.__class__))
    resetXY()
    try:
        vim.current.buffer[line] = newline
    except vim.error, error:
        pass
        #this should work anyway
        

def resetXY():
    line, col = vim.current.window.cursor
    line-=1 #1 based counting
    PyVimGlobals.col = col
    PyVimGlobals.line = line

def commentLine():
    resetXY()
    col = PyVimGlobals.col
    line = PyVimGlobals.line
    cline = vim.current.buffer[line]
    newline = '/* %s */' % cline
    vim.current.buffer[line] = newline

def init():
    if PyVimGlobals.is_init:
        return

    initParse()
    PyVimGlobals.is_init = True

def insertLine(newline):
    resetXY()
    #insert new line at current position
    vim.command('call append(line("."), "")')
    insertline = PyVimGlobals.line + 1
    vim.current.buffer[insertline] = newline

def initParse():
    filename = vim.current.buffer.name
    if not filename:
        return

    #display(filename)

    import pylatex.pytex
    method_map = {
        "tex": pylatex.pytex.init,
    }
    
    import os.path
    folder, file = os.path.split(filename)
    splitname = file.split(".")
    if len(splitname) == 1: #cannot identiy suffix
        return
    suffix = splitname[-1]

    flags = []
    for line in vim.current.buffer:
        if "%PyVim" in line:
            clean = line.replace("%PyVim","").strip()
            flags.append(clean)

    #display(str(flags))

    method = None
    try:
        method = method_map[suffix]
    except KeyError:
        return #no init fxn yet

    method(flags)

def getCurrentSentence():
    resetXY()
    col = PyVimGlobals.col
    line = PyVimGlobals.line
    cline = vim.current.buffer[line]

    def getSentence(cline):
        if len(cline) == 0: #nothing here
            return ""

        if cline[col] == '.': #no letters
            return ""

        start = col
        while cline[start] != '.'and start >= 0 and cline[start:start+2] != '  ' :
            start -= 1
        start += 1 #loop goes one too far

        word = []
        letter = start
        length = len(cline)
        while letter < length and cline[letter] != '.' and cline[letter:letter+2] != '  ':
            word.append(cline[letter])
            letter += 1

        #add the period, if there is one
        if letter < length and cline[letter] == '.':
            word.append('.')
        elif letter == length and cline[-1] == '.':
            word.append('.')
        else:
            pass

        word = "".join(word)
        return word

    word = getSentence(cline)

    return word

def deleteSentence():
    sent = getCurrentSentence()
    col = PyVimGlobals.col
    line = PyVimGlobals.line
    cline = vim.current.buffer[line]
    newline = cline.replace(sent, '')
    vim.current.buffer[line] = newline

resetXY()
