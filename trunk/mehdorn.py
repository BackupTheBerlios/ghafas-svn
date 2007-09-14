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
        logging.info('submit...')
        response = self.form.click('submitButton')
        return urlopen(response)



class ConnectionOverviewPage(SGMLParser):
    def __init__(self, response):
        SGMLParser.__init__(self)

        self.url = response.geturl()
        self.links_verfuegbarkeit = []
        self.link_spaeter = None

        self.feed(response.read())
        
    def follow_spaeter(self):
        logging.info('follow link <Spaeter>...')
        # return self.url + self.link_spaeter
        return urlopen('http://reiseauskunft.bahn.de' + self.link_spaeter)
        
    def start_a(self, attrs):
        attrs = tuples2dict(attrs)
        #print attrs
        
        marker = 'Es gelten besondere Nutzungs- und Stornobedingungen.'
        if 'title' in attrs and attrs['title'] == marker:
            self.links_verfuegbarkeit.append(attrs['href'])

        marker = 'arrowlink arrowlinkbottom'
        if 'class' in attrs and attrs['class'] == marker:
            self.link_spaeter = attrs['href']

    def start_span(self, attrs):
        self.span_tag = tuples2dict(attrs)

    def handle_data(self, data):
        try:
            self.span_tag
        except:
            return
        if 'class' in self.span_tag and self.span_tag['class'] == 'progress_digit_active':
            self.ok = data == '2'
        self.span_tag = {}



class ConnectionAvailabilityPage(SGMLParser):
    def __init__(self, response):
        SGMLParser.__init__(self)

        self.url = response.geturl()
        self.link_zurueck = None

        self.feed(response.read())
        
    def follow_zurueck(self):
        logging.info('follow link <Zurueck>...')
        return urlopen(self.link_zurueck)
        
    def start_a(self, attrs):
        attrs = tuples2dict(attrs)
        #print attrs
        
        marker = 'arrowlink'
        if 'class' in attrs and attrs['class'] == marker:
            self.link_zurueck = attrs['href']



################################################################################

def get_overview(travelData):
    startPage = StartPage()
    startPage.fill_form(travelData)
    
    overview = ConnectionOverviewPage(startPage.submit())
    if not overview.ok:
        open_browser_and_exit(overview.url)

    while overview.link_spaeter:
        response = overview.follow_spaeter()
        overview = ConnectionOverviewPage(response)
    
    return overview

def check_all_availabilities(overview):
    logging.info('check all availabilities...')

    for link in overview.links_verfuegbarkeit:
        open_browser(link)
        sleep()
    
def show_availability_overview(overview):
    logging.info('show availability...')

    first_link = overview.links_verfuegbarkeit[0]
    page = ConnectionAvailabilityPage(urlopen(first_link))
    response = page.follow_zurueck()
    open_browser(response.geturl())

            


def main():
    opts, args = getopt.getopt(sys.argv[1:], '', [])

    if len(args) == 0:
        args = ('Frankfurt am Main', 'Berlin hbf', '30.10.2007', '08:00')

    travelData = TravelData(*args)

    #check_all_availabilities(get_overview(travelData))
    show_availability_overview(get_overview(travelData))



if __name__ == "__main__":
    main()


################################################################################

#forms = ParseResponse(response2)
#for form in forms:
#    print form
#f = open('out.html', 'w')
#f.write(html)
#f.close()


