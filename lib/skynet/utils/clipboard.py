import os
import codecs

PYTEMP = os.environ["PYTEMP"]


def get_clipboard():
    cwd = os.getcwd()
    os.chdir(PYTEMP)
    os.system("osascript -e 'the clipboard as unicode text' >& .stdout")
    text = codecs.open(".stdout", "r", "utf-8").read()
    os.remove(".stdout")
    os.chdir(cwd)
    return text[:-1] #remove trailing new line

def set_clipboard(text):
    cwd = os.getcwd()
    os.chdir(PYTEMP)

    cmd = u"osascript -e 'set the clipboard to \"%s\"'" % text
    script = u"#! /usr/bin/env tcsh\n\n%s\n" % cmd
    #put the text on the clipboard
    scriptname = ".tcshscript"
    fileobj = codecs.open(scriptname, "w", "utf-8")
    fileobj.write(script)
    fileobj.close()
    os.system("chmod +x %s" % scriptname)
    os.system("./%s" % scriptname)
    os.remove(scriptname)

def monitor_clipboard(delay=1):
    import time
    set_clipboard("-")
    ref = "-"
    cliptext = "-"
    while cliptext == ref:
        if delay:
            time.sleep(delay)
        cliptext = get_clipboard()

    return cliptext


