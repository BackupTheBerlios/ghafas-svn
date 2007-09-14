#!/usr/bin/env python

import getopt, logging, os, random, time, sys, urllib2

import ClientForm
import TableParse
from sgmllib import SGMLParser
from BeautifulSoup import BeautifulSoup


LOGLEVEL  = logging.INFO
#LOGLEVEL  = logging.DEBUG
LOGFORMAT = '%(asctime)s %(levelname)s %(message)s'
LOGFORMAT = '%(levelname)s: %(message)s'


logging.basicConfig(level=LOGLEVEL, format=LOGFORMAT, stream=sys.stderr)
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


class TravelData:
    def __init__(self, fr0m, to, date, time):
        self.fr0m = fr0m
        self.to = to
        self.date = date
        self.time = time


class UnexpectedPage:
    def __init__(self, url):
        self.url = url
    

class StartPage:
    def __init__(self):
        response = urlopen("http://www.bahn.de/p/view/index.shtml")
        forms = ClientForm.ParseResponse(response)

        for form in forms:
            logging.debug('form:\n' + str(form))

        self.form = forms[2]

        logging.debug('selected form:\n' + str(self.form))

    def fill_form(self, travelData):
        self.form['S'] = travelData.fr0m
        self.form['Z'] = travelData.to
        self.form['date'] = travelData.date
        self.form['time'] = travelData.time
        # it's a BC 50, 2. Kl
        self.form['REQ0Tariff_TravellerReductionClass.1'] = ['4']

    def submit(self):
        logging.info('submit form...')
        response = self.form.click('submitButton')
        return urlopen(response)



class TimetablePage:
    def __init__(self, response):
        self.url = response.geturl()
        self.links_check_availability = []
        self.link_later = None

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

def request_timetable_page(travelData):
    logging.info('request_timetable_page...')

    startPage = StartPage()
    startPage.fill_form(travelData)
    
    overview = TimetablePage(startPage.submit())

    if not overview.ok:
        open_browser_and_exit(overview.url)

    while overview.link_later:
        response = overview.follow_link_later()
        overview = TimetablePage(response)
    
    return overview

def show_all_availability_pages(overview):
    logging.info('show_all_availability_pages...')

    for link in overview.links_check_availability:
        open_browser(link)
        sleep()
    
def show_resolved_yourtimetable_page(overview):
    logging.info('show_resolved_yourtimetable_page...')

    first_link = overview.links_check_availability[0]
    print first_link
    open_browser(first_link)
    page = AvailabilityPage(urlopen(first_link))
    response = page.follow_link_back()
    open_browser(response.geturl())

            


def main():
    opts, args = getopt.getopt(sys.argv[1:], '', [])

    if len(args) == 0:
        args = ('Frankfurt am Main', 'Berlin hbf', '30.10.2007', '08:00')

    travelData = TravelData(*args)

    try:
        #show_all_availability_pages(request_timetable_page(travelData))

        show_resolved_yourtimetable_page(request_timetable_page(travelData))
    except UnexpectedPage, e:
        open_browser(e.url)


if __name__ == "__main__":
    main()


################################################################################

#forms = ParseResponse(response2)
#for form in forms:
#    print form
#f = open('out.html', 'w')
#f.write(html)
#f.close()


