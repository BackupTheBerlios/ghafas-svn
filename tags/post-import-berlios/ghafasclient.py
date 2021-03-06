#!/usr/bin/env python2.5

# coding=utf-8
# $HeadURL$
# $Id$

__version__ = "0.1"

__license__ = """
GHAFAS, a GTK+ client to query train connections & fares
Copyright 2007 tomfuks <casualcoding@gmail.com>

This file is part of GHAFAS.

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

ghafaslib_path = os.path.join(os.path.dirname(__file__), 'ghafaslib')
sys.path.insert(0, ghafaslib_path)

import ClientForm
from BeautifulSoup import BeautifulSoup


MARK_LINK_LATER = u'Sp&#228;ter'
MARK_LINK_CHECK_AVAILABILTY = u'Verf&#252;gbarkeit pr&#252;fen'
MARK_BUTTON_SHOW_AVAILABILTY = u'Verf&#252;gbarkeit f&#252;r alle anzeigen'
MARK_LINK_BOOKING = u'Zur&nbsp;Buchung'
MARK_LINK_BACK = u'Zur&#252;ck'
MARK_TEXT_FROM = u'ab'

BAHN_BASE_URL = 'http://reiseauskunft.bahn.de'
BAHN_QUERY_URL = BAHN_BASE_URL + "/bin/query.exe/d"

re_eur = re.compile(r'([0-9]+,[0-9]+)&nbsp;EUR')



def init_logger(level):
    format = '%(asctime)s %(levelname)s %(message)s'
    format = '%(levelname)s: %(message)s'

    logging.basicConfig(level=level, format=format, stream=sys.stderr)
    #filename='/tmp/myapp.log', filemode='w'



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
    os.system('open "%s"' % link)

def open_browser_and_exit(link):
    open_browser(link)
    sys.exit(1)

def urlopen(url):
    logging.debug('open url: %s' % url)
    return urllib2.urlopen(url)

def parse_time(d, t):
    return time.mktime(time.strptime('%s %s' % (d, t), '%d.%m.%Y %H:%M'))

def format_time(f, t):
    return time.strftime(f, time.localtime(t))


class Fare:
    def __init__(self, fare=None, unknown=False, url=None):
        if fare:
            # FIXME: test for string type
            fare = float(fare.replace(',', '.'))

        self.fare = fare
        self.unknown = unknown # unknown availability
        self.url = url

    def __str__(self):
        if self.unknown == True:
            return '?'
        if self.fare:
            return '%6.2f' % (self.fare)
        return '-.- '


class TravelData:
    def __init__(
            self,
            fr0m, to, dep_date, dep_time, arr_date=None, arr_time=None,
            bahncard=0, clazz=1
            ):
        self.fr0m = fr0m
        self.to = to
        self.dep_time = parse_time(dep_date, dep_time)
        if not arr_date:
            arr_date = dep_date
        if not arr_time:
            arr_time = dep_time
        self.arr_time = parse_time(arr_date, arr_time)
        self.bahncard = bahncard
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


testTravelData = TravelData(
        'Berlin',
        'Hamburg',
        (datetime.date.today()+datetime.timedelta(14)).strftime("%d.%m.%Y"),
        '08:00',
        (datetime.date.today()+datetime.timedelta(14)).strftime("%d.%m.%Y"),
        '14:00',
        bahncard = 3
        )



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
        self.trains = trains

        self.fare_n = Fare()
        self.fare_s = Fare()

        self.url = None

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
            self.trains,
            self.changes,
            format_time('%d.%m.%y', self.dep_time),
            time_f % format_time('%H:%M', self.dep_time),
            format_time('%d.%m.%y', self.arr_time),
            time_f % format_time('%H:%M', self.arr_time),
            self.duration,
            )

    def __str__(self):
        return '%-20s %s  %s\n%-20s %s   %5s %-2s  %6s  %6s' % (
            self.st_dep,
            format_time('%d.%m.%y %H:%M', self.dep_time),
            self.trains,
            self.st_arr,
            format_time('%d.%m.%y %H:%M', self.arr_time),
            self.duration, self.changes,
            self.fare_n, self.fare_s,
            )


class HtmlPage:
    def __init__(self, url):
        self.response = urlopen(url)
        self.content = self.response.read()
        self.soup = BeautifulSoup(self.content)

    def get_stream(self):
        return StringIO.StringIO(self.content)

    def get_forms(self):
        file = StringIO.StringIO(self.content)
        return ClientForm.ParseFile(file, self.response.geturl())


class UnexpectedPage:
    def __init__(self, url):
        self.url = url


def convert_encoding(s, src='utf-8', dst='iso-8859-1'):
    return s.decode(src).encode(dst)

class FindConnectionPage(HtmlPage):
    def __init__(self, url):
        HtmlPage.__init__(self, url)
        forms = self.get_forms()
        for form in forms:
            logging.debug('form:\n' + str(form))
        self.form = forms[1]

        logging.debug('selected form:\n' + str(self.form))

    def fill_form(self, travelData):
        self.form['REQ0JourneyStopsSG'] = convert_encoding(travelData.fr0m)
        self.form['REQ0JourneyStopsZG'] = convert_encoding(travelData.to)
        self.form['REQ0JourneyDate'] = travelData.get_departure_date()
        self.form['REQ0JourneyTime'] = travelData.get_departure_time()
        # it's a BC 50, 2. Kl
        self.form['REQ0Tariff_TravellerReductionClass.1'] = [str(travelData.bahncard+1)]
        # 2. Kl
        self.form['REQ0Tariff_Class'] = [str(travelData.clazz+1)]


    def submit(self):
        logging.info('submit form...')
        return self.form.click('start')



class TimetablePage(HtmlPage):
    def __init__(self, url):
        HtmlPage.__init__(self, url)

        self.form = self.get_forms()[0]
        logging.debug('form:\n' + str(self.form))

        self.links_check_availability = []
        self.link_later = None
        self.connections = []

        for incident in self.soup('span'):
            try:
                tag_class = incident['class']
            except KeyError:
                continue
            if tag_class == 'progress_digit_active':
                self.ok = incident.contents[0] == '2'

        if not self.ok:
            raise UnexpectedPage(self.response.geturl())

        for incident in self.soup('a'):
            if incident.contents[0] == MARK_LINK_LATER:
                if not self.link_later:
                    self.link_later = incident['href']

        table = self.soup.findAll(
                'table',
                attrs={'class':'result', 'cellspacing':'0'}
                )
        table = table[0]
        departurerow = None
        for row in table.findAll('tr', recursive=False):
            for incident in row.findAll('a'):
                if incident.contents[0] == MARK_LINK_CHECK_AVAILABILTY:
                    link = incident['href']
                    self.links_check_availability.append(link)

            #colums = row.findAll('td', recursive=False)
            #if len(colums) < 2 or colums[2].contents[0] != MARK_TEXT_FROM:
            #    continue
            
            try:
                row_class = row['class']
            except KeyError:
                continue
            
            if not (row_class.startswith('light') or row_class.startswith('dark')):
                continue

            if row.td['class'].find('departurerow') != -1:
                departurerow = row
                continue

            arrivalrow = row

            conn = self.parse_connection(departurerow, arrivalrow)
            self.connections.append(conn)

            departurerow = None
            arrivalrow = None

    def __str__(self):
        return '\n\n'.join([str(c) for c in self.connections])

    def parse_connection(self, departure_row, arrival_row):                
        departure_cols = departure_row.findAll('td', recursive=False)
        arrival_cols = arrival_row.findAll('td', recursive=False)
        
        conn = (
            # st_dep
            departure_cols[0].a.contents[0],
            # st_arr
            arrival_cols[0].a.contents[0],
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
        conn = [urllib2.unquote(i.strip()) for i in conn]
        conn = Connection(*conn)
        conn.fare_n = self.parse_fare(departure_cols[7])
        conn.fare_s = self.parse_fare(departure_cols[8])
        conn.url = self.response.geturl()
        return conn

    def has_availability_button(self):
        try:
            self.form['immediateAvail=ON&action']
        except:
            return False
        return True

    def submit(self):
        logging.info('submit form...')
        return self.form.click('immediateAvail=ON&action')

    def parse_fare(self, content):
        url = None
        for incident in content.findAll('a'):
            if incident.contents[0] == MARK_LINK_CHECK_AVAILABILTY:
                return Fare(unknown=True)
            if incident.contents[0] == MARK_LINK_BOOKING:
                url = incident['href']

        m = re_eur.search(str(content.contents[0]))
        if not m and content.a:
            m = re_eur.search(str(content.a.contents[0]))

        if m:
            return Fare(m.group(1), url=url)
        return Fare()

    def get_link_later(self):
        logging.info('get_link_later...')
        return BAHN_BASE_URL + self.link_later



class AvailabilityPage(HtmlPage):
    def __init__(self, url):
        HtmlPage.__init__(self, url)
        self.link_back = None

        for incident in self.soup('span'):
            try:
                tag_class = incident['class']
            except KeyError:
                continue
            if tag_class == 'progress_digit_active':
                self.ok = incident.contents[0] == '3'

        #if not self.ok:
        #    raise UnexpectedPage(self.url)

        for incident in self.soup('a'):
            if incident.contents[0] == MARK_LINK_BACK:
                if not self.link_back:
                    self.link_back = incident['href']


    def get_link_back(self):
        logging.info('get_link_back...')
        return self.link_back



def request_timetable_page(travelData, complete=True):
    logging.info('request_timetable_page...')

    find_page = FindConnectionPage(BAHN_QUERY_URL)
    find_page.fill_form(travelData)

    timetable_page = TimetablePage(find_page.submit())
    logging.info(timetable_page)

    if timetable_page.has_availability_button():
        timetable_page = TimetablePage(timetable_page.submit())

    if not timetable_page.ok:
        open_browser_and_exit(timetable_page.response.geturl())

    if complete:
        while timetable_page.connections[-1].arr_time < travelData.arr_time:
            if not timetable_page.link_later:
                break
            response = timetable_page.get_link_later()
            timetable_page = TimetablePage(response)
            print timetable_page

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


# command line interface starts here:
def main():
    log_level = logging.INFO

    opts, args = getopt.getopt(sys.argv[1:], 'd', [])

    for o, v in opts:
        if o == '-d':
            log_level = logging.DEBUG

    init_logger(log_level)

    if len(args) == 0:
        travelData = testTravelData
    else:
        travelData = TravelData(*args)

    try:
        result = request_timetable_page(travelData)
        show_resolved_yourtimetable_page(result)

        #show_all_availability_pages(request_timetable_page(travelData))
        #page = request_timetable_page(travelData, complete=False)
        #open_browser(page.response.geturl())

    except UnexpectedPage, e:
        logging.error('UnexpectedPage')
        open_browser(e.url)


if __name__ == "__main__":
    main()


