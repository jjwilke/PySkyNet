import vim

line = 0
col = 0

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
    PyTex.loadBibliography()
    PyTex.loadCitation()
    
def appendAtWord(word):
    cline = vim.current.buffer[line]
    if not cline: #no line yet
        col = 0
    else:
        while col < len(cline) and not cline[col] in (' ', ',', '.', ':', ';'):
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
    cline = vim.current.buffer[line]
    newline = cline.replace(old, new)
    display("%s %d %s" % (newline, line, newline.__class__))
    resetXY()
    try:
        vim.current.buffer[line] = newline
    except vim.error, error:
        pass
        #this should work anyway
        

def resetXY():
    line, col = vim.current.window.cursor
    line-=1 #1 based counting

def commentLine():
    cline = vim.current.buffer[line]
    newline = '/* %s */' % cline
    resetXY()
    vim.current.buffer[line] = newline

resetXY()

