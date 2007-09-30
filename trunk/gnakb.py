#!/usr/bin/env python2.5

# coding=utf-8
# $HeadURL$
# $Id$

__version__ = "0.1"

__license__ = """
GnaKB, a GTK+ client to query train connections & fares
Copyright 2007 tomfuks <xxxxxxxxxxxx>

This file is part of GnaKB.

Sonata is free software; you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation; either version 2 of the License, or
(at your option) any later version.

Sonata is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with Sonata; if not, write to the Free Software
Foundation, Inc., 51 Franklin St, Fifth Floor, Boston, MA  02110-1301  USA
"""


import sys
import os.path

try:
    import gtk
    import gobject
except ImportError, (strerror):
    print >>sys.stderr, "%s.  Please make sure you have this library installed into a directory in Python's path or in the same directory as GnaKB.\n" % strerror
    sys.exit(1)

import gettext
import threading
import kbclient


def init_gettext(domain):
    paths = [
        os.path.join(os.path.dirname(__file__), 'locale'),
        os.path.join(__file__.split('/lib')[0], 'share', 'locale'),
        '/usr/share/locale',
        ]
    for path in paths:
        try:
            gettext.install(domain, path, unicode=1)
            break
        except:
            pass
        
init_gettext('gnakb')


bahncards = [
        _("No reduction"),
        _("BC25, 2nd class"),
        _("BC25, 1st class"),
        _("BC50, 2nd class"),
        _("BC50, 1st class")
        ]

clazzes = [
        _("1st"),
        _("2nd"),
        ]

travelData = kbclient.testTravelData


def error(window):
    error_dialog = gtk.MessageDialog(window, gtk.DIALOG_MODAL, gtk.MESSAGE_WARNING, gtk.BUTTONS_CLOSE, _("#######"))
    error_dialog.set_title(_("Error"))
    #error_dialog.connect('response', self.choose_image_dialog_response)
    error_dialog.show()

def invoke_later(target):
    thread = threading.Thread(target=target)
    thread.setDaemon(True)
    thread.start()

def find_path(paths, filename):
    for path in paths:
        if os.path.exists(path):
            return os.path.abspath(path)
    return None

def find_pixmaps_path(filename):
    paths = [
    	(sys.prefix, 'share', 'pixmaps', filename),
    	(os.path.split(__file__)[0], filename),
    	(os.path.split(__file__)[0], 'pixmaps', filename),
     	(os.path.split(__file__)[0], 'share', filename),
     	(__file__.split('/lib')[0], 'share', 'pixmaps', filename),
        ]
    paths = [os.path.join(*path) for path in paths]
    return find_path(paths, filename)
 
def find_stations_path(filename):
    paths = [
    	(sys.prefix, 'share', 'gnakb', 'stations', filename),
    	(os.path.split(__file__)[0], filename),
    	(os.path.split(__file__)[0], 'stations', filename),
        ]
    paths = [os.path.join(*path) for path in paths]
    return find_path(paths, filename)
 

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
        sf = open(find_stations_path('ice-only.txt'), 'r')
        for line in sf.readlines():
            line = line.strip()
            if not (line.startswith('#') or len(line) == 0):
                stationliststore.append([line])
    return stationliststore


def set_markup_from_connection(tree_column, cell, model, iter, idx):
    obj = model.get_value(iter, idx)
    cell.set_property("markup", obj.markup())

def set_text_from_pyobject(tree_column, cell, model, iter, idx):
    obj = model.get_value(iter, idx)
    cell.set_property("text", str(obj))


class Base:
    def __init__(self):
        self.timetable = None

        gtk.gdk.threads_init()

        init_gettext('gnakb')

        # add some icons:
        self.iconfactory = gtk.IconFactory()
        sonataset1 = gtk.IconSet()
        filename1 = [find_pixmaps_path('gnakb.png')]
        icons1 = [gtk.IconSource() for i in filename1]
        for i, iconsource in enumerate(icons1):
            iconsource.set_filename(filename1[i])
            sonataset1.add_source(iconsource)
        self.iconfactory.add('sonata', sonataset1)
        self.iconfactory.add_default()

        self.window = gtk.Window(gtk.WINDOW_TOPLEVEL)
        self.window.set_title('GnaKB')
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
        for bc in bahncards:
            self.card_combo.append_text(bc)
        self.card_combo.set_active(travelData.bahncard)
        optionsvbox.pack_start(self.card_combo, False, False, 5)
        settingsvbox.pack_start(optionsvbox, False, False, 2)

        optionsvbox = gtk.HBox()
        optionsvbox.pack_start(gtk.Label(str=_("Class")), False, False, 2)
        self.clazz_combo = gtk.combo_box_new_text()
        for cl in clazzes:
            self.clazz_combo.append_text(cl)
        self.clazz_combo.set_active(travelData.clazz)
        optionsvbox.pack_start(self.clazz_combo, False, False, 5)
        settingsvbox.pack_start(optionsvbox, False, False, 2)

        # setup button to start request for timetable
        self.prevbutton = gtk.Button("Go", None, True)
        settingsvbox.pack_start(self.prevbutton, False, False, 2)

        # setup button to start request for timetable
        self.showinbrowser = gtk.Button("Show in Browser", None, True)
        settingsvbox.pack_start(self.showinbrowser, False, False, 2)

        # finish settings vbox
        clienthbox.pack_start(settingsvbox, False, False, 3)

        # setup timetable
        ttlabel = gtk.Label()
        ttlabel.set_text(_("Timetable"))
        timetableScrollWindow = gtk.ScrolledWindow()
        timetableScrollWindow.set_policy(gtk.POLICY_AUTOMATIC, gtk.POLICY_AUTOMATIC)

        self.lvtimetable = gtk.TreeView()
        self.lvtimetable.set_rules_hint(True)
        self.lvtimetable.set_reorderable(False)
        self.lvtimetable.set_enable_search(True)
        timetableScrollWindow.add_with_viewport(self.lvtimetable)
        clienthbox.pack_start(timetableScrollWindow, True, True, 3)

        self.lvtimetabledata = gtk.ListStore(gobject.TYPE_PYOBJECT, gobject.TYPE_PYOBJECT, gobject.TYPE_PYOBJECT)
        self.lvtimetable.set_model(self.lvtimetabledata)

        self.lvtimetablecolumn0 = gtk.TreeViewColumn()
        self.lvtimetablecolumn0.set_title(_('Connection'))
        self.lvtimetablecell0 = gtk.CellRendererText()
        self.lvtimetablecolumn0.pack_start(self.lvtimetablecell0, True)
        self.lvtimetablecolumn0.set_cell_data_func(self.lvtimetablecell0, set_markup_from_connection, 0)
        self.lvtimetable.append_column(self.lvtimetablecolumn0)
        
        self.lvtimetablecolumn1 = gtk.TreeViewColumn()
        self.lvtimetablecolumn1.set_title(_('Normal fare'))
        self.lvtimetablecell1 = gtk.CellRendererText()
        self.lvtimetablecolumn1.pack_start(self.lvtimetablecell1, True)
        self.lvtimetablecolumn1.set_cell_data_func(self.lvtimetablecell1, set_text_from_pyobject, 1)
        self.lvtimetable.append_column(self.lvtimetablecolumn1)
        
        self.lvtimetablecolumn2 = gtk.TreeViewColumn()
        self.lvtimetablecolumn2.set_title(_('Savings fare'))
        self.lvtimetablecell2 = gtk.CellRendererText()
        self.lvtimetablecolumn2.pack_start(self.lvtimetablecell2, True)
        self.lvtimetablecolumn2.set_cell_data_func(self.lvtimetablecell2, set_text_from_pyobject, 2)
        self.lvtimetable.append_column(self.lvtimetablecolumn2)

        # layout client area containing settings and timetable
        mainvbox.pack_start(clienthbox, True, True, 2)

        # setup status bar
        self.statusbar = gtk.Statusbar()
        mainvbox.pack_start(self.statusbar, False, False, 0)

        # window setup layout
        mainhbox.pack_start(mainvbox, True, True, 3)
        self.window.add(mainhbox)

        # Connect to signals
        self.prevbutton.connect('clicked', self.on_request_timetable)
        self.showinbrowser.connect('clicked', self.on_show_timetable_in_browser)
        self.lvtimetable.connect('row_activated', self.on_connection_activated)

        icon = self.window.render_icon('gnakb', gtk.ICON_SIZE_DIALOG)
        self.window.set_icon(icon)

        # final main window setup
        self.window.set_size_request(600, -1)
        self.window.show_all()

    def on_connection_activated(self, treeview, path, column=0):
        model = treeview.get_model()
        row_iter = model.get_iter(path)
        obj = model.get_value(row_iter, treeview.get_columns().index(column))
        if obj and obj.url:
            kbclient.open_browser(obj.url)

    def on_request_timetable(self, action=None):
        invoke_later(target=self.request_timetable_async_checked)

    def request_timetable_async_checked(self):
        try:
            self.request_timetable_async()
        except kbclient.UnexpectedPage, e:
            kbclient.open_browser(e.url)

    def request_timetable_async(self):
        travelData = kbclient.TravelData(
                self.fromentry.get_text(),
                self.toentry.get_text(),
                self.depdateentry.get_text(),
                self.deptimeentry.get_text(),
                self.destdateentry.get_text(),
                self.desttimeentry.get_text(),
                bahncard = self.card_combo.get_active(),
                clazz = self.clazz_combo.get_active(),
                )
        self.lvtimetabledata.clear()

        self.statusbar.push(self.statusbar.get_context_id(""), "Run query...")
        result = kbclient.request_timetable_page(travelData)

        self.statusbar.push(self.statusbar.get_context_id(""), "Resolve query...")
        result = kbclient.get_resolved_timetable_page(result)

        for c in result.connections:
            self.lvtimetabledata.append(c.fields())

        self.timetable = result.connections

        while self.timetable[-1].arr_time < travelData.arr_time:
            self.statusbar.push(self.statusbar.get_context_id(""), "Run query...")
            travelData.dep_time = self.timetable[-1].dep_time

            self.statusbar.push(self.statusbar.get_context_id(""), "Resolve query...")
            result = kbclient.request_timetable_page(travelData)
            self.timetable.extend(result.connections)
            result = kbclient.get_resolved_timetable_page(result)
            for c in result.connections:
                self.lvtimetabledata.append(c.fields())

        self.statusbar.push(self.statusbar.get_context_id(""), "")


    def on_show_timetable_in_browser(self, action=None):
        if self.timetable:
            kbclient.open_browser(self.timetable[-1].url)


    def main(self):
        gtk.main()



if __name__ == "__main__":
    Base().main()


