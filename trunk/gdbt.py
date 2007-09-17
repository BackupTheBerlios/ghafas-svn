#!/usr/bin/env python2.5

import sys
import os.path

try:
    import gtk
except ImportError, (strerror):
    print >>sys.stderr, "%s.  Please make sure you have this library installed into a directory in Python's path or in the same directory as Sonata.\n" % strerror
    sys.exit(1)

import dbt


travelData = dbt.testTravelData


def _(s):
    return s
    
def error(window):
    error_dialog = gtk.MessageDialog(window, gtk.DIALOG_MODAL, gtk.MESSAGE_WARNING, gtk.BUTTONS_CLOSE, _("#######"))
    error_dialog.set_title(_("Error"))
    #error_dialog.connect('response', self.choose_image_dialog_response)
    error_dialog.show()


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


class Base:
    def __init__(self):
        self.timetable = False
            
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
        self.timetableBuffer = gtk.TextBuffer()
        timetableView = gtk.TextView(self.timetableBuffer)
        timetableView.set_editable(False)
        timetableView.set_wrap_mode(gtk.WRAP_WORD)
        timetableScrollWindow.add_with_viewport(timetableView)
        clienthbox.pack_start(timetableScrollWindow, True, True, 3)

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
        travelData = dbt.TravelData(
                self.fromentry.get_text(),
                self.toentry.get_text(),
                self.depdateentry.get_text(),
                self.deptimeentry.get_text(),
                self.destdateentry.get_text(),
                self.desttimeentry.get_text(),
                bahncard = self.card_combo.get_active(),
                )
    
        self.timetableBuffer.set_text('Searching ...\n')
        
        result = dbt.request_timetable_page(travelData)

        self.timetableBuffer.insert_at_cursor('...\n')
        result = dbt.get_resolved_timetable_page(result)
        
        self.timetableBuffer.set_text(_('Time table:\n'))

        for c in result.connections:
            self.timetableBuffer.insert_at_cursor('\n%s\n' % str(c))
            
        self.timetable = result

    def show_timetable_in_browser(self, action=None):
        if self.timetable:
            dbt.open_browser(self.timetable.url)
        
        
        
def main():
    gtk.gdk.threads_init()

    Base()

    gtk.main()

if __name__ == "__main__":
    main()


