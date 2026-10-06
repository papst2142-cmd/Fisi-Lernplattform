import gi; gi.require_version("Gtk","3.0"); from gi.repository import Gtk, GLib
w=Gtk.Window(title="GTK-Gegenprobe"); w.add(Gtk.Button(label="GTK-Knopf")); w.show_all()
GLib.timeout_add(8000, Gtk.main_quit); Gtk.main()
