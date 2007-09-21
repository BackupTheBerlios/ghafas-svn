#!/usr/bin/env python2.5

import sys
import os.path

try:
    import gtk
    import gobject
except ImportError, (strerror):
    print >>sys.stderr, "%s.  Please make sure you have this library installed into a directory in Python's path or in the same directory as Sonata.\n" % strerror
    sys.exit(1)

import threading
import dbt


install_path = os.path.dirname(__file__)
travelData = dbt.testTravelData

def _(s):
    return s
    
def error(window):
    error_dialog = gtk.MessageDialog(window, gtk.DIALOG_MODAL, gtk.MESSAGE_WARNING, gtk.BUTTONS_CLOSE, _("#######"))
    error_dialog.set_title(_("Error"))
    #error_dialog.connect('response', self.choose_image_dialog_response)
    error_dialog.show()

def invoke_later(target):
    thread = threading.Thread(target=target)
    thread.setDaemon(True)
    thread.start()

class PropertyEntry(gtk.Entry):
    def __init__(self, name, value, layout=None):
        gtk.Entry.__init__(self)
        
        self.hbox = gtk.HBox()
        self.label = gtk.Label(name)
        self.label.set_alignment(0, 0.5)
        self.set_text(value)
        self.hbox.pack_start(self.label, False, False, 0)
        self.hbox.pack_start(self, False, False, 5)
        if layout:
            layout.pack_start(self.hbox, False, False, 2)

    def setup_completion(self, liststore):
        completion = gtk.EntryCompletion()
        completion.set_popup_completion(True)
        completion.set_inline_completion(True)
        completion.set_model(liststore)
        completion.pack_start(gtk.CellRendererText())
        completion.set_text_column(0)
        self.set_completion(completion)


stationliststore = None

def get_stationliststore():
    global stationliststore
    if not stationliststore:
        stationliststore = gtk.ListStore(gobject.TYPE_STRING)
        f = open(os.path.join(install_path, 'stations.txt'), 'r')
        for line in f.readlines():
            stationliststore.append([line.strip()])
    return stationliststore


class Base:
    def __init__(self):
        self.timetable = None
            
        self.window = gtk.Window(gtk.WINDOW_TOPLEVEL)
        self.window.set_title('dbt')
        self.window.set_resizable(True)

        # main window layout
        mainhbox = gtk.HBox()
        # ... contains a:
        mainvbox = gtk.VBox()
        # ... contains a:
        clienthbox = gtk.HBox()
        # ... contains a:
        settingsvbox = gtk.VBox()
            
        # setup start & destination
        settingsvbox.pack_start(gtk.Label(str=_("Start & Destination")), False, False, 2)
        self.fromentry = PropertyEntry(_("From:"), travelData.get_start(), settingsvbox)
        self.toentry = PropertyEntry(_("To:"), travelData.get_destination(), settingsvbox)

        self.fromentry.setup_completion(get_stationliststore())
        self.toentry.setup_completion(get_stationliststore())

        # setup departure data
        settingsvbox.pack_start(gtk.Label(str=_("Departure (earliest)")), False, False, 2)
        self.deptimeentry = PropertyEntry(_("Time:"), travelData.get_departure_time(), settingsvbox)
        self.depdateentry = PropertyEntry(_("Date:"), travelData.get_departure_date(), settingsvbox)

        # setup destination data
        settingsvbox.pack_start(gtk.Label(str=_("Arrival (latest)")), False, False, 2)
        self.desttimeentry = PropertyEntry(_("Time:"), travelData.get_arrival_time(), settingsvbox)
        self.destdateentry = PropertyEntry(_("Date:"), travelData.get_arrival_date(), settingsvbox)

        # setup option panel; contains bahncard type, no of passengers
        settingsvbox.pack_start(gtk.Label(str=_("Options")), False, False, 2)
        optionsvbox = gtk.HBox()
        optionsvbox.pack_start(gtk.Label(str=_("BahnCard")), False, False, 2)

        self.card_combo = gtk.combo_box_new_text()
        for bc in dbt.bahncards:
            self.card_combo.append_text(bc)
        self.card_combo.set_active(travelData.bahncard)
        optionsvbox.pack_start(self.card_combo, False, False, 5)

        settingsvbox.pack_start(optionsvbox, False, False, 2)

        # setup button to start request for timetable
        self.prevbutton = gtk.Button("Go", None, True)
        settingsvbox.pack_start(self.prevbutton, False, False, 2)

        # setup button to start request for timetable
        self.showinbrowser = gtk.Button("Show in Browser", None, True)
        settingsvbox.pack_start(self.showinbrowser, False, False, 2)

        # finish settings vbox
        clienthbox.pack_start(settingsvbox, False, False, 3)

        # setup timetable; just a simple text dump
        ttlabel = gtk.Label()
        ttlabel.set_text(_("Timetable"))
        timetableScrollWindow = gtk.ScrolledWindow()
        timetableScrollWindow.set_policy(gtk.POLICY_AUTOMATIC, gtk.POLICY_AUTOMATIC)

        self.lvtimetable = gtk.TreeView()
        self.lvtimetable.set_headers_visible(False)
        self.lvtimetable.set_rules_hint(True)
        self.lvtimetable.set_reorderable(False)
        self.lvtimetable.set_enable_search(True)
        timetableScrollWindow.add_with_viewport(self.lvtimetable)
        clienthbox.pack_start(timetableScrollWindow, True, True, 3)

        self.lvtimetabledata = gtk.ListStore(str)
        self.lvtimetable.set_model(self.lvtimetabledata)

    	self.lvtimetablecell = gtk.CellRendererText()
    	self.lvtimetablecolumn = gtk.TreeViewColumn()
    	self.lvtimetablecolumn.pack_start(self.lvtimetablecell, True)
    	self.lvtimetablecolumn.set_attributes(self.lvtimetablecell, text=0)
    	self.lvtimetable.append_column(self.lvtimetablecolumn)

        # layout client area containing settings and timetable
        mainvbox.pack_start(clienthbox, True, True, 2)

        # setup status bar
        self.statusbar = gtk.Statusbar()
        mainvbox.pack_start(self.statusbar, False, False, 0)

        # window setup layout
        mainhbox.pack_start(mainvbox, True, True, 3)
        self.window.add(mainhbox)

        # Connect to signals
        self.prevbutton.connect('clicked', self.request_timetable)
        self.showinbrowser.connect('clicked', self.show_timetable_in_browser)

        # final main window setup
        self.window.set_size_request(600, -1)

        self.window.show_all()


    def request_timetable(self, action=None):
        invoke_later(target=self.request_timetable_async)

    def request_timetable_async(self):
        travelData = dbt.TravelData(
                self.fromentry.get_text(),
                self.toentry.get_text(),
                self.depdateentry.get_text(),
                self.deptimeentry.get_text(),
                self.destdateentry.get_text(),
                self.desttimeentry.get_text(),
                bahncard = self.card_combo.get_active(),
                )
    
        self.lvtimetabledata.clear()
        self.statusbar.push(self.statusbar.get_context_id(""), "Run query...")
    
        result = dbt.request_timetable_page(travelData)

        self.statusbar.push(self.statusbar.get_context_id(""), "Resolve query...")

        result = dbt.get_resolved_timetable_page(result)
        
        for c in result.connections:
            self.lvtimetabledata.append([str(c)])
            
        self.timetable = result.connections

        while self.timetable[-1].arr_time < travelData.arr_time:
            self.statusbar.push(self.statusbar.get_context_id(""), "Run query...")

            travelData.dep_time = self.timetable[-1].dep_time

            self.statusbar.push(self.statusbar.get_context_id(""), "Resolve query...")

            result = dbt.request_timetable_page(travelData)
            
            self.timetable.extend(result.connections)

            result = dbt.get_resolved_timetable_page(result)
            for c in result.connections:
                self.lvtimetabledata.append([str(c)])
        
        self.statusbar.push(self.statusbar.get_context_id(""), "")


    def show_timetable_in_browser(self, action=None):
        if self.timetable:
            dbt.open_browser(self.timetable[-1].url0)

        
        
def main():
    gtk.gdk.threads_init()

    Base()

    gtk.main()

if __name__ == "__main__":
    main()


