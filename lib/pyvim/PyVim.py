import vim


class PyVimGlobals:
    line = 0
    col = 0
    is_init = False

    stderr = None
    stdout = None

def disconnectErr():
    if PyVimGlobals.stderr: #already disconnected
        return

    import sys
    import os.path, os
    home = os.environ["HOME"]
    errorfile = os.path.join(home, ".vimerr")
    fileobj = open(errorfile, "a+")
    PyVimGlobals.stderr = sys.stderr
    sys.stderr = fileobj

def reconnectErr():
    if not PyVimGlobals.stderr: #already connected
        return

    import sys
    fileobj = sys.stderr
    sys.stderr = PyVimGlobals.stderr
    #fileobj.close()
    PyVimGlobals.stderr = None

def disconnectOut():
    if PyVimGlobals.stdout: #already disconnected
        return

    import sys
    import os.path, os
    home = os.environ["HOME"]
    errorfile = os.path.join(home, ".vimout")
    fileobj = open(errorfile, "a+")
    PyVimGlobals.stdout = sys.stdout
    sys.stdout = fileobj

def reconnectOut():
    if not PyVimGlobals.stdout: #already connected
        return

    import sys
    fileobj = sys.stderr
    sys.stdout = PyVimGlobals.stdout
    #fileobj.close()
    PyVimGlobals.stdout = None


def display(msg):
    import sys, os
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
    import PyTex
    #disconnect stderr and out
    #disconnectErr()
    #disconnectOut()
    cword = getCurrentWord()
    PyTex.loadCitation(cword)
    #reconnectErr()
    #reconnectOut()
    
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

    import PyTex
    method_map = {
        "tex": PyTex.init,
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
