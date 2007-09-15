#!/usr/bin/env python2.4

import getopt
import logging
import os
import os.path
import random
import re
import time
import sys
import urllib2

sitepackages = os.path.join(os.path.dirname(__file__), 'site-packages')
sys.path.insert(0, sitepackages)

import ClientForm
from BeautifulSoup import BeautifulSoup




re_eur = re.compile(r'([0-9]+,[0-9]+)&nbsp;EUR')


def init_logger(debug = False):
    if debug:
        level  = logging.DEBUG
    else:
        level  = logging.INFO
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


class Price:
    def __init__(self, price=None):
        if price:
            # FIXME: test for string type
            price = float(price.replace(',', '.'))

        self.price = price
        
    def __str__(self):
        if self.price:
            return '%6.2f' % (self.price)
        return '-.- '
        

class TravelData:
    def __init__(self, fr0m, to, date, time):
        self.fr0m = fr0m
        self.to = to
        self.date = date
        self.time = time


class Connection:
    def __init__(self, 
            st_dep, st_arr, dt_dep, tm_dep, dt_arr, tm_arr, duration, changes, trains
            ):
        self.st_dep = st_dep
        self.st_arr = st_arr

        self.time_dep = time.strptime(dt_dep + ' ' + tm_dep, '%d.%m.%y %H:%M')
        self.time_arr = time.strptime(dt_arr + ' ' + tm_arr, '%d.%m.%y %H:%M')
        
        self.duration = duration
        self.changes = changes
        self.trains = trains

        self.price_n = Price()
        self.price_s = Price()

    def __str__(self):
        return '%-20s %s  %s\n%-20s %s   %5s %-2s  %6s  %6s' % (
            self.st_dep, 
            time.strftime('%d.%m.%y %H:%M', self.time_dep),
            self.trains, 
            self.st_arr,
            time.strftime('%d.%m.%y %H:%M', self.time_arr),
            self.duration, self.changes,
            self.price_n, self.price_s,
            )


class UnexpectedPage:
    def __init__(self, url):
        self.url = url
    

class FindConnectionPage:
    def __init__(self):
        response = urlopen("http://reiseauskunft.bahn.de/bin/query.exe/d")
        forms = ClientForm.ParseResponse(response)

        for form in forms:
            logging.debug('form:\n' + str(form))

        self.form = forms[1]

        logging.debug('selected form:\n' + str(self.form))

    def fill_form(self, travelData):
        self.form['REQ0JourneyStopsSG'] = travelData.fr0m
        self.form['REQ0JourneyStopsZG'] = travelData.to
        self.form['REQ0JourneyDate'] = travelData.date
        self.form['REQ0JourneyTime'] = travelData.time
        # it's a BC 50, 2. Kl
        self.form['REQ0Tariff_TravellerReductionClass.1'] = ['4']
        # 2. Kl
        self.form['REQ0Tariff_Class'] = ['2']
        

    def submit(self):
        logging.info('submit form...')
        response = self.form.click('start')
        return urlopen(response)



class TimetablePage:
    def __init__(self, response):
        self.url = response.geturl()
        self.links_check_availability = []
        self.link_later = None
        self.connections = []

        self.soup = BeautifulSoup(response.read())

        for incident in self.soup('span'):
            try:
                tag_class = incident['class']
            except KeyError:
                continue
            if tag_class == 'progress_digit_active':
                self.ok = incident.contents[0] == '2'

        if not self.ok:
            raise UnexpectedPage(self.url)

        for incident in self.soup('a'):
            if incident.contents[0] == u'Verf&#252;gbarkeit pr&#252;fen':
                link = incident['href']
                self.links_check_availability.append(link)
            if incident.contents[0] == u'Sp&#228;ter':
                if not self.link_later:
                    self.link_later = incident['href']

        table = self.soup.findAll('table', attrs={'class':'result', 'cellspacing':'0'})
        table = table[0]
        for row in table.findAll('tr', recursive=False):
            colums = row.findAll('td', recursive=False)
            #print '---', colums
            if len(colums) < 2 or colums[2].contents[0] != u'ab':
                continue

            conn = (
                # st_dep
                colums[0].a.contents[0],
                # st_arr
                colums[0].a.contents[2],
                # dt_dep
                colums[1].contents[0].split()[1],
                # tm_dep
                colums[3].contents[0],
                # dt_arr
                colums[1].contents[2].split()[1],
                # tm_arr
                colums[3].contents[2],
                # duration
                colums[4].string,
                # changes
                colums[5].string,
                # trains
                colums[6].a.contents[-1],
                )
            conn = [i.strip() for i in conn]
            conn = Connection(*conn)
            conn.price_n = self.parse_price(str(colums[7]))
            conn.price_s = self.parse_price(str(colums[8]))
            
            self.connections.append(conn)
    
    def __str__(self):
        return '\n\n'.join([str(c) for c in self.connections])

    def parse_price(self, s):
        m = re_eur.search(s)
        if m:
            return Price(m.group(1))
        return Price()
        
    def follow_link_later(self):
        logging.info('follow link <Spaeter>...')
        # return self.url + self.link_later
        return urlopen('http://reiseauskunft.bahn.de' + self.link_later)
        


class AvailabilityPage:
    def __init__(self, response):
        self.url = response.geturl()
        self.link_back = None

        self.soup = BeautifulSoup(response.read())

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
            if incident.contents[0] == u'Zur&#252;ck':
                if not self.link_back:
                    self.link_back = incident['href']

        
    def follow_link_back(self):
        logging.info('follow link <Zurueck>...')
        return urlopen(self.link_back)
        
        


################################################################################

def request_timetable_page(travelData, complete=True):
    logging.info('request_timetable_page...')

    find_page = FindConnectionPage()
    find_page.fill_form(travelData)
    
    timetable_page = TimetablePage(find_page.submit())
    print timetable_page

    if not timetable_page.ok:
        open_browser_and_exit(timetable_page.url)

    if complete:
        while timetable_page.link_later:
            response = timetable_page.follow_link_later()
            timetable_page = TimetablePage(response)
            print timetable_page
    
    return timetable_page


def show_all_availability_pages(timetable_page):
    logging.info('show_all_availability_pages...')

    for link in timetable_page.links_check_availability:
        open_browser(link)
        sleep()

    
def show_resolved_yourtimetable_page(timetable_page):
    logging.info('show_resolved_yourtimetable_page...')

    if len(timetable_page.links_check_availability) == 0:
        open_browser(timetable_page.url)
        return

    first_link = timetable_page.links_check_availability[0]

    page = AvailabilityPage(urlopen(first_link))
    response = page.follow_link_back()

    timetable_page = TimetablePage(response)
    if len(timetable_page.links_check_availability):
        show_resolved_yourtimetable_page(timetable_page)
    else:
        open_browser(response.geturl())

            

def main():
    debug = False

    opts, args = getopt.getopt(sys.argv[1:], 'd', [])

    for o, v in opts:
        if o == '-d':
            debug = True

    init_logger(debug)

    if len(args) == 0:
        args = ('Frankfurt am Main', 'Berlin hbf', '30.10.2007', '08:00')

    travelData = TravelData(*args)

    try:
        #show_all_availability_pages(request_timetable_page(travelData))
        show_resolved_yourtimetable_page(request_timetable_page(travelData))
        #page = request_timetable_page(travelData, complete=False)
        #open_browser(page.url)

    except UnexpectedPage, e:
        logging.error('UnexpectedPage')
        open_browser(e.url)

################################################################################

if __name__ == "__main__":
    main()


