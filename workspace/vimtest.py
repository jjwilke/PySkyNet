def display(msg):
    import pygtk
    import gtk
    window = gtk.Window(gtk.WINDOW_TOPLEVEL)
    window.connect("destroy", gtk.main_quit)
    entry = gtk.Entry(100)
    entry.set_text(msg)
    window.add(entry)

    entry.show()
    window.show()

    gtk.main()

display("hello world")
