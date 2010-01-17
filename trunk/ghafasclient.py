#!/usr/bin/env python2.5
# -*- coding: utf-8 -*-

# $HeadURL$
# $Id$

__version__ = '0.1'

__license__ = """
GHAFAS, a GTK+ client to query train connections & fares
Copyright 2007 tomfuks <casualcoding@gmail.com>

This file is part of GHAFAS.

GHAFAS is free software; you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation; either version 2 of the License, or
(at your option) any later version.

GHAFAS is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with GHAFAS; if not, write to the Free Software
Foundation, Inc., 51 Franklin St, Fifth Floor, Boston, MA  02110-1301  USA
"""


import datetime
import getopt
import logging
import os
import os.path
import random
import re
import time
import sys
import urllib2
import StringIO
import tempfile
import sqlite3
import hashlib

ghafaslib_path = os.path.join(os.path.dirname(__file__), 'ghafaslib')
sys.path.insert(0, ghafaslib_path)

import ClientForm
from BeautifulSoup import BeautifulSoup


MARK_LINK_LATER = u'Sp&#228;ter'
MARK_LINK_CHECK_AVAILABILTY = u'Verf&#252;gbarkeit pr&#252;fen'
MARK_LINK_CHECK_ALL_AVAIL = u'Alle pr&#252;fen'
MARK_LINK_BOOKING = u'Zur&nbsp;Buchung'
MARK_LINK_BACK = u'Zur&#252;ck'
MARK_TEXT_FROM = u'ab'

BAHN_BASE_URL = 'http://reiseauskunft.bahn.de'
BAHN_QUERY_URL = BAHN_BASE_URL + '/bin/query.exe/d'

archive_pages = False
browse_results = False


def init_logger(level):
    format = '%(asctime)s %(levelname)s %(message)s'
    format = '%(levelname)s: %(message)s'

    logging.basicConfig(level=level, format=format, stream=sys.stderr)
    #filename='/tmp/myapp.log', filemode='w'


class Database:
    def __init__(self):
        self.db_path = 'kursbuch.db'

        db_missing = not os.path.exists(self.db_path)

        self.conn = sqlite3.connect(self.db_path)

        self.c = self.conn.cursor()

        # Create table
        if db_missing:
            self.c.execute("""create table connections (
                    hash text,
                    station0 text, station1 text, time0 text, time1 text,
                    duration text, trains text, changes integer
                    )""")

        # Save (commit) the changes
        self.conn.commit()

    def close(self):
        # We can also close the cursor if we are done with it
        c.close()

    def add(self, c):
        if self.contains(c.hash()):
            return

        # Insert a row of data
        self.c.execute("""insert into connections values (
                '%s','%s','%s','%s','%s','%s','%s',%s
                )""" % (
                    c.hash(),
                    enc_html2utf8(c.st_dep),
                    enc_html2utf8(c.st_arr),
                    format_time('%d.%m.%y %H:%M', c.dep_time),
                    format_time('%d.%m.%y %H:%M', c.arr_time),
                    ','.join(c.trains),
                    c.duration,
                    c.changes,
                ))
        self.conn.commit()

    def contains(self, hashcode):
        self.c.execute("""select * from connections
                where hash = '%s'
                """ % hashcode
                )
        return self.c.fetchall()

    def dump(self):
        self.c.execute('select * from connections order by time0')
        for row in self.c:
            print row

db = Database()


def tuples2dict(ts):
    d = {}
    for t in ts:
        d[t[0]] = t[1]
    return d

def sleep():
    t = random.uniform(1.5, 2)
    logging.info('wait %.1fs...' % t)
    time.sleep(t)

def open_browser(link):
    logging.info('open link in browser: %s' % link)
    xdgopen = '/usr/bin/xdg-open'
    if os.path.exists(xdgopen):
        cmd = xdgopen
    else:
        # mac os x
        cmd = 'open'
    os.system('%s "%s"' % (cmd, link))

def open_browser_and_exit(link):
    open_browser(link)
    sys.exit(1)

def urlopen(url):
    if isinstance(url, urllib2.Request):
        s = url.get_full_url()
    else: s = url
    logging.debug('urlopen: open %s' % s)
    return urllib2.urlopen(url)

def parse_time(d, t):
    try:
        return time.mktime(time.strptime('%s %s' % (d, t), '%d.%m.%Y %H:%M'))
    except ValueError:
        return time.mktime(time.strptime('%s %s' % (d, t), '%d.%m.%y %H:%M'))

def format_time(f, t):
    return time.strftime(f, time.localtime(t))

def convert_encoding(s, src='utf-8', dst='iso-8859-1'):
    return s.decode(src).encode(dst)

def enc_html2utf8(s):
    conv = (('&#223;', u'ß'), ('&#228;', u'ä'), ('&#246;', u'ö'), ('&#252;', u'ü'), )
    for a, b in conv:
        s = s.replace(a, b)
    return s

class Fare:
    def __init__(self, fare=None, confirmed=False, url=None, clazz=2, conn_past=False):
        if fare:
            # FIXME: test for string type
            fare = float(fare.replace(',', '.'))

        self.fare = fare
        self.confirmed = confirmed # confirmed availability
        self.url = url
        self.clazz = clazz
        self.conn_past = conn_past

    def to_csv(self):
        s = ''
        if self.fare:
            f = '%.2f' % (self.fare)
            if not self.confirmed:
                s += '?'
        else:
            f = '-'
        # FIXME this is wrong, should be self.clazz !+ travaller.clazz
        if self.clazz == 1:
            s += 'F'
        if self.conn_past:
            s += 'P'
        return ';'.join((f, s))

    def __str__(self):
        s = ''
        if self.fare:
            s += '%.2f' % (self.fare)
        if not self.confirmed:
            s += '?'
        if self.clazz == 1:
            s += '*'
        return s

class Traveller:
    def __init__(self, alias='John Doe', age=43, bahncard=0):
        self.alias = alias
        self.age = age
        self.bahncard = bahncard


class TravelData:
    def __init__(
            self,
            fr0m, to, dep_date, dep_time, arr_date=None, arr_time=None,
            travellers=None, clazz=2
            ):
        self.fr0m = fr0m
        self.to = to
        self.dep_time = parse_time(dep_date, dep_time)
        if not arr_date or arr_date == '-':
            arr_date = dep_date
        if not arr_time or arr_time == '-':
            arr_time = dep_time
        self.arr_time = parse_time(arr_date, arr_time)
        if travellers:
            if isinstance(travellers, str):
                self.travellers = [Traveller(bahncard=int(travellers))]
            else:
                self.travellers = travellers
        else:
            self.travellers = [Traveller()]
        self.clazz = clazz

    def get_start(self):
        return self.fr0m

    def get_destination(self):
        return self.to

    def get_departure_time(self):
        return format_time('%H:%M', self.dep_time)

    def get_departure_date(self):
        return format_time('%d.%m.%Y', self.dep_time)

    def get_arrival_time(self):
        return format_time('%H:%M', self.arr_time)

    def get_arrival_date(self):
        return format_time('%d.%m.%Y', self.arr_time)


class Connection:
    def __init__(self,
            st_dep, st_arr, dt_dep, tm_dep, dt_arr, tm_arr,
            duration, changes, trains
            ):
        self.st_dep = st_dep
        self.st_arr = st_arr

        self.dep_time = time.mktime(time.strptime(
                dt_dep + ' ' + tm_dep, '%d.%m.%y %H:%M'
                ))
        self.arr_time = time.mktime(time.strptime(
                dt_arr + ' ' + tm_arr, '%d.%m.%y %H:%M'
                ))

        self.duration = duration
        self.changes = changes
        self.trains = [s.strip() for s in trains.split(',')]

        self.fare_n = Fare()
        self.fare_s = Fare()

        self.url = None

    def __cmp__(self, other):
        r = cmp(self.dep_time, other.dep_time)
        if r: return r
        return cmp(self.arr_time, other.arr_time)

    def hash(self):
        s = ' '.join((
            enc_html2utf8(self.st_dep),
            enc_html2utf8(self.st_arr),
            format_time('%d.%m.%y;%H:%M', self.dep_time),
            format_time('%d.%m.%y;%H:%M', self.arr_time),
            ','.join(self.trains),
            self.duration, self.changes,
            ))
        return hashlib.md5(s).hexdigest()

    def fields(self):
        return [self, self.fare_n, self.fare_s]

    def markup(self):
        time_f = '<span foreground="blue"><b>%s</b></span>'
        return (
            '<small>%s - %s, %s, %sx</small>\n' +
            '%s %s - %s %s <small>(%s)</small>'
            ) % (
            self.st_dep,
            self.st_arr,
            ','.join(self.trains),
            self.changes,
            format_time('%d.%m.%y', self.dep_time),
            time_f % format_time('%H:%M', self.dep_time),
            format_time('%d.%m.%y', self.arr_time),
            time_f % format_time('%H:%M', self.arr_time),
            self.duration,
            )

    def to_csv(self):
        return ';'.join((
            enc_html2utf8(self.st_dep),
            enc_html2utf8(self.st_arr),
            format_time('%d.%m.%y;%H:%M', self.dep_time),
            format_time('%d.%m.%y;%H:%M', self.arr_time),
            ','.join(self.trains),
            self.duration, self.changes,
            self.fare_n.to_csv(), self.fare_s.to_csv(),
            ))

    def __str__(self):
        return ' > %-20s %s  %s\n   %-20s %s   %5s %-2s  %6s  %6s' % (
            enc_html2utf8(self.st_dep),
            format_time('%d.%m.%y %H:%M', self.dep_time),
            ','.join(self.trains),
            enc_html2utf8(self.st_arr),
            format_time('%d.%m.%y %H:%M', self.arr_time),
            self.duration, self.changes,
            self.fare_n, self.fare_s,
            )


class UnexpectedPage:
    def __init__(self, page = 'Unknown', url = None):
        self.page = page
        self.url = url

    def __str__(self):
        return 'UnexpectedPage: %s' % self.page

class HtmlPage:
    def __init__(self, arg):
        if isinstance(arg, HtmlPage):
            self.url = arg.url
            self.response = arg.response
            self.content = arg.content
            self.soup = arg.soup
        else:
            self.url = arg

        logging.debug('HtmlPage: %s' % self.url)

        self.response = urlopen(self.url)
        self.content = self.response.read()
        self.soup = BeautifulSoup(self.content)

        progress_list = self.soup.find(
                'ul', attrs = {'class' : re.compile('process-list')}
                )
        progress_pos = progress_list.find(
                'li', attrs = {'class' : re.compile('active')}
                )
        self.progress_pos = progress_pos.span.contents[0]

        if archive_pages:
            fd, self.content_file = tempfile.mkstemp(prefix='gh-', suffix='.html', text=True)
            logging.info('save page to %s' % self.content_file)
            os.write(fd, self.content)
            os.close(fd)

    def get_stream(self):
        return StringIO.StringIO(self.content)

    def get_forms(self):
        return ClientForm.ParseFile(self.get_stream(), self.response.geturl())

    def get_form(self, name):
        for form in self.get_forms():
            if form.name == name:
                return form
        raise RuntimeError('form %s not found' % name)


class FindConnectionPage(HtmlPage):
    def __init__(self, arg):
        HtmlPage.__init__(self, arg)

        if self.progress_pos <> 'Suche':
            raise UnexpectedPage(self.progress_pos, self.response.geturl())

        #for form in self.get_forms():
        #    logging.debug('form:\n' + str(form))

        self.form = self.get_form('formular')
        logging.debug('selected form:\n' + str(self.form))

    def fill_form(self, travelData):
        logging.info('fill form "%s"...' % self.form.name)
        self.form['REQ0JourneyStopsS0G'] = convert_encoding(travelData.fr0m)
        self.form['REQ0JourneyStopsZ0G'] = convert_encoding(travelData.to)
        self.form['REQ0JourneyDate'] = travelData.get_departure_date()
        self.form['REQ0JourneyTime'] = travelData.get_departure_time()
        self.form['REQ0Tariff_TravellerReductionClass.1'] = [str(travelData.travellers[0].bahncard)]
        self.form['REQ0Tariff_Class'] = [str(travelData.clazz)]

    def submit(self):
        logging.info('submit form "%s"...' % self.form.name)
        return self.form.click('start')


class FindConnectionPageUnclear(FindConnectionPage):
    def __init__(self, arg):
        FindConnectionPage.__init__(self, arg)

        self.options_fr0m = None
        self.options_to = None
        self.time_error = None
        self.date_error = None

        m = self.soup.find('select', attrs = {'name' : re.compile('REQ0JourneyStopsS0K')})
        if m:
            self.options_fr0m = [(i.string, i['value']) for i in m.findAll('option')]
        m = self.soup.find('select', attrs = {'name' : re.compile('REQ0JourneyStopsZ0K')})
        if m:
            self.options_to = [(i.string, i['value']) for i in m.findAll('option')]
        m = self.soup.find('div', attrs = {'id' : re.compile('timeErr0')})
        if m and m.string != '&nbsp;':
            self.time_error = enc_html2utf8(m.string.strip())
        m = self.soup.find('div', attrs = {'id' : re.compile('dateErr20')})
        if m and m.string != '&nbsp;':
            self.date_error = enc_html2utf8(m.string.strip())

    @classmethod
    def check(cls, page):
        # <select class="locInput locInput" name="REQ0JourneyStopsS0K" id="REQ0JourneyStopsS0K"
        m = page.soup.find('select', attrs = {'name' : re.compile('REQ0JourneyStops(S|Z)0K')})
        if m:
            return True
        # <div id="timeErr0" class="errormsg clearfix ">...</div>
        m = page.soup.find('div', attrs = {'id' : re.compile('timeErr0')})
        if m:
            return True
        m = page.soup.find('div', attrs = {'id' : re.compile('dateErr20')})
        if m:
            return True
        return False

    def dump(self):
        if self.options_fr0m:
            logging.error('Unknown or ambiguous departure station:')
            s = ['  %-6s %s' % (k, enc_html2utf8(s)) for s, k in self.options_fr0m]
            print >> sys.stderr, '\n'.join(s)
        if self.options_to:
            logging.error('Unknown or ambiguous destination station:')
            s = ['  %-6s %s' % (k, enc_html2utf8(s)) for s, k in self.options_to]
            print >> sys.stderr, '\n'.join(s)
        if self.time_error:
            logging.error('Wrong time: %s' % self.time_error)
        if self.date_error:
            logging.error('Wrong date: %s' % self.date_error)


re_rarePep = re.compile('farePep')
re_fareStd = re.compile('fareStd')
re_eur = re.compile(r'([0-9]+,[0-9]+) EUR')

class TimetablePage(HtmlPage):
    def __init__(self, arg):
        logging.info('open time table page')
        HtmlPage.__init__(self, arg)

        self.ok = False
        self.age_required = False
        self.links_check_availability = []
        self.link_check_all_avail = None
        self.link_later = None
        self.connections = []

        if self.progress_pos <> 'Auswahl':
            raise UnexpectedPage(self.progress_pos, self.response.geturl())

        self.form = self.get_form('formular2')

        logging.debug('selected form:\n' + str(self.form))

        control = self.form.find_control('REQ0Tariff_TravellerAge.1')
        if not control.value and not control.readonly:
            self.age_required = True
            return

        table = self.soup.find(
                'table',
                attrs={'class':'result', 'cellspacing':'0'}
                )

        if not table:
            raise UnexpectedPage(url = self.response.geturl())

        self.ok = True

        for incident in self.soup('a'):
            if incident.contents and incident.contents[0] == MARK_LINK_LATER:
                if not self.link_later:
                    self.link_later = incident['href']

        departurerow = None
        for row in table.findAll('tr', recursive=False):
            for incident in row.findAll('a'):
                if incident.contents and MARK_LINK_CHECK_ALL_AVAIL in incident.contents[0]:
                    self.link_check_all_avail = incident['href']
                if incident.contents and incident.contents[0] == MARK_LINK_CHECK_AVAILABILTY:
                    link = incident['href']
                    self.links_check_availability.append(link)

            #colums = row.findAll('td', recursive=False)
            #if len(colums) < 2 or colums[2].contents[0] != MARK_TEXT_FROM:
            #    continue

            try:
                row_class = row['class']
            except KeyError:
                continue

            if row_class == ' firstrow':
                departurerow = row
                continue
            elif row_class == ' last':
                arrivalrow = row
            else:
                continue

            conn = self.parse_connection(departurerow, arrivalrow)
            self.connections.append(conn)

            departurerow = None
            arrivalrow = None

        self.connections.sort()

    def __str__(self):
        return '\n'.join([unicode(c) for c in self.connections])

    def fill_form(self, travelData):
        logging.info('fill form "%s"...' % self.form.name)
        self.form['REQ0Tariff_TravellerAge.1'] = str(travelData.travellers[0].age)

    def submit(self):
        logging.info('submit form "%s"...' % self.form.name)
        return self.form.click('HWAI=~GLOBALAPPLICATION;&newTariff')

    def parse_connection(self, departure_row, arrival_row):
        departure_cols = departure_row.findAll('td', recursive=False)
        arrival_cols = arrival_row.findAll('td', recursive=False)

        conn = (
            # st_dep
            departure_cols[0].contents[3].contents[0],
            # st_arr
            arrival_cols[0].contents[0],
            # dt_dep
            departure_cols[1].contents[0].split()[1],
            # tm_dep
            departure_cols[3].contents[0],
            # dt_arr
            arrival_cols[1].contents[0].split()[1],
            # tm_arr
            arrival_cols[3].contents[0],
            # duration
            departure_cols[4].string,
            # changes
            departure_cols[5].string,
            # trains
            departure_cols[6].a.contents[-1],
            )
        conn = [urllib2.unquote(i.replace('&nbsp;', '').strip()) for i in conn]
        conn = Connection(*conn)

        farePep = departure_row.find('td', attrs = {'class' : re_rarePep})
        fareStd = departure_row.find('td', attrs = {'class' : re_fareStd})

        conn.fare_s = self.parse_fare(farePep)
        conn.fare_n = self.parse_fare(fareStd)

        conn.url = self.response.geturl()
        return conn

    def parse_fare(self, content):
        if not content: return Fare()

        url = None
        confirmed = True
        conn_past = False

        MARK_CONN_PAST = 'Verbindung liegt in der Vergangenheit'
        for incident in content.findAll('a'):
            if incident.contents[0] == MARK_LINK_CHECK_AVAILABILTY:
                confirmed = False
            elif incident.span and incident.span.contents[0] == MARK_LINK_BOOKING:
                url = incident['href']
        for incident in content.findAll('span'):
            if incident.string == MARK_CONN_PAST:
                conn_past = True

        c = str(content).replace('&nbsp;', ' ')
        m = re_eur.search(c)
        if m:
            if '1.Klasse' in c:
                clazz = 1
            else:
                clazz = 2
            return Fare(m.group(1), url=url, clazz=clazz, confirmed=confirmed)
        return Fare(confirmed=confirmed, conn_past=conn_past)

    def get_link_later(self):
        logging.debug('get_link_later...')
        return BAHN_BASE_URL + self.link_later


class AvailabilityPage(HtmlPage):
    def __init__(self, arg):
        HtmlPage.__init__(self, arg)
        self.link_back = None

        if self.progress_pos <> 'Auswahl':
            raise UnexpectedPage(self.progress_pos, self.response.geturl())

        for incident in self.soup('a'):
            if incident.contents[0] == MARK_LINK_BACK:
                if not self.link_back:
                    self.link_back = incident['href']

    def get_link_back(self):
        logging.info('get_link_back...')
        return self.link_back



def request_timetable_page(travelData, complete=True):
    logging.info('request timetable...')

    find_page = FindConnectionPage(BAHN_QUERY_URL)
    find_page.fill_form(travelData)
    find_page_result = find_page.submit()

    unknown_page = HtmlPage(find_page_result)

    try:
        timetable_page = TimetablePage(unknown_page)
    except UnexpectedPage, e:
        if FindConnectionPageUnclear.check(unknown_page):
            fcpu = FindConnectionPageUnclear(unknown_page)
            fcpu.dump()
            sys.exit(-1)

        # Handle the case where the request page is shown again
        # to display a warning regarding bahncard/class mismatch.
        # Be ignorant about it and feed it in again.
        # FIXME: make it more general
        logging.warning('bahncard/class mismatch')
        find_page_result = FindConnectionPage(find_page_result).submit()
        timetable_page = TimetablePage(find_page_result)

    if timetable_page.age_required:
        timetable_page.fill_form(travelData)
        timetable_page_result = timetable_page.submit()
        timetable_page = TimetablePage(timetable_page_result)

    logging.info('Results table:\n%s' % timetable_page)

    if timetable_page.link_check_all_avail:
        timetable_page = TimetablePage(timetable_page.link_check_all_avail)

    if not timetable_page.ok:
        open_browser_and_exit(timetable_page.response.geturl())

    if browse_results:
        open_browser(timetable_page.response.geturl())

    if complete:
        while timetable_page.connections[-1].arr_time < travelData.arr_time:
            if not timetable_page.link_later:
                break
            logging.info('extend time table')
            response = timetable_page.get_link_later()
            timetable_page = TimetablePage(response)
            logging.info('Results table:\n%s' % timetable_page)

    return timetable_page


def show_all_availability_pages(timetable_page):
    logging.info('show_all_availability_pages...')

    for link in timetable_page.links_check_availability:
        open_browser(link)
        sleep()


def get_resolved_timetable_page(timetable_page):
    logging.info('get_resolved_timetable_page...')

    return timetable_page


def show_resolved_yourtimetable_page(timetable_page):
    logging.info('show_resolved_yourtimetable_page...')

    timetable_page = get_resolved_timetable_page(timetable_page)
    open_browser(timetable_page.response.geturl())


def query(travelData, f_log, f_init=None, f_add=None):
    f_log('Run query...')
    result = request_timetable_page(travelData)
    #show_resolved_yourtimetable_page(result)

    f_log('Resolve query...')
    result = get_resolved_timetable_page(result)

    if f_init: f_init(None)
    for c in result.connections:
        if f_add: f_add(c)

    timetable = result.connections

    while timetable[-1].arr_time < travelData.arr_time:
        f_log('Run query...')
        travelData.dep_time = timetable[-1].dep_time

        f_log('Resolve query...')
        result = request_timetable_page(travelData)
        #show_resolved_yourtimetable_page(result)

        try:
            pos = result.connections.index(timetable[-1]) + 1
        except ValueError:
            pos = 0

        conn = result.connections[pos:]

        timetable.extend(conn)
        result = get_resolved_timetable_page(result)

        for c in conn:
            if f_add: f_add(c)

# ----------------- command line interface starts here ------------------------

testTravellers = [
        Traveller('Homer', age = 45, bahncard = 4)
        ]

testTravelData0 = TravelData(
        'Berlin',
        'Hamburg',
        (datetime.date.today()+datetime.timedelta(14)).strftime('%d.%m.%Y'),
        '08:00',
        (datetime.date.today()+datetime.timedelta(14)).strftime(''),
        '14:00',
        travellers = testTravellers
        )

# test dataset with mismatching bahncard/class.
testTravelData1 = TravelData(
        'Berlin',
        'Hamburg',
        (datetime.date.today()+datetime.timedelta(14)).strftime('%d.%m.%Y'),
        '08:00',
        (datetime.date.today()+datetime.timedelta(14)).strftime('%d.%m.%Y'),
        '14:00',
        travellers = testTravellers,
        clazz = 1
        )

# test dataset with mismatching/unknown station name.
testTravelData2 = TravelData(
        'Fulda Bf',
        'Hamburg',
        (datetime.date.today()+datetime.timedelta(14)).strftime('%d.%m.%Y'),
        '08:00',
        (datetime.date.today()+datetime.timedelta(14)).strftime('%d.%m.%Y'),
        '14:00',
        travellers = testTravellers,
        clazz = 1
        )


def _log_status(s):
    logging.info(s)

def _add_connection(c):
    sys.stdout.write(c.to_csv().encode('utf-8') + '\n')
    db.add(c)

def main():
    log_level = logging.INFO

    opts, args = getopt.getopt(sys.argv[1:], 'abdq', (
            'db',
            ))

    for o, v in opts:
        if o == '-a':
            global archive_pages
            archive_pages = True
        elif o == '-b':
            global browse_results
            browse_results = True
        elif o == '--db':
            db.dump()
            sys.exit()
        elif o == '-d':
            log_level = logging.DEBUG
        elif o == '-q':
            log_level = logging.WARN

    init_logger(log_level)

    if len(args) == 0:
        logging.info('No travel data given - using test data')
        travelData = testTravelData0
    else:
        travelData = TravelData(*args)

    try:
        query(travelData, _log_status, None, _add_connection)
    except UnexpectedPage, e:
        logging.error(e)
        open_browser(e.url)
    except KeyboardInterrupt:
        sys.exit('Keyboard interrupt')


if __name__ == '__main__':
    main()


