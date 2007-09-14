
import logging, os, random, time, sys, urllib2

from ClientForm import ParseResponse
from sgmllib import SGMLParser


LOGLEVEL  = logging.INFO
LOGLEVEL  = logging.DEBUG
LOGFORMAT = '%(asctime)s %(levelname)s %(message)s'
LOGFORMAT = '%(levelname)s: %(message)s'


#                    filename='/tmp/myapp.log',
#                    filemode='w')
logging.basicConfig(level=LOGLEVEL, format=LOGFORMAT, stream=sys.stderr)


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
    #os.system('open "%s"' % link)

def urlopen(url):
    logging.debug('open url: %s' % url)
    return urllib2.urlopen(url)

class ConnectionOverviewPage(SGMLParser):
    def __init__(self, response):
        SGMLParser.__init__(self)

        self.links_verfuegbarkeit = []
        self.link_spaeter = None

        self.feed(response.read())
        
    def start_a(self, attrs):
        attrs = tuples2dict(attrs)
        #print attrs
        
        marker = 'Es gelten besondere Nutzungs- und Stornobedingungen.'
        if 'title' in attrs and attrs['title'] == marker:
            self.links_verfuegbarkeit.append(attrs['href'])

        if 'class' in attrs and attrs['class'] == 'arrowlink arrowlinkbottom':
            self.link_spaeter = attrs['href']


class StartPage(SGMLParser):
    def __init__(self):
        response = urlopen("http://www.bahn.de/p/view/index.shtml")
        forms = ParseResponse(response)

        for form in forms:
            logging.debug('form:\n' + str(form))

        self.form = forms[2]

        logging.debug('selected form:\n' + str(self.form))

    def fill(self):
        self.form['S'] = 'Berlin Ostbahnhof'
        self.form['Z'] = 'Frankfurt am Main'
        self.form['S'] = 'Fulda'
        self.form['Z'] = 'Hof'
        self.form['date'] = '1.12.2007'
        self.form['time'] = '08:00'
        self.form['REQ0Tariff_TravellerReductionClass.1'] = ['4']

    def submit(self):
        logging.info('submit...')
        return urlopen(self.form.click('submitButton'))


################################################################################

startPage = StartPage()

startPage.fill()

overview = ConnectionOverviewPage(startPage.submit())

while overview.link_spaeter:
    logging.info('follow link: Spaeter')
    response = urlopen('http://reiseauskunft.bahn.de' + overview.link_spaeter)
    overview = ConnectionOverviewPage(response)


for link in overview.links_verfuegbarkeit:
    open_browser(link)
    sleep()
    


#forms = ParseResponse(response2)
#for form in forms:
#    print form
#f = open('out.html', 'w')
#f.write(html)
#f.close()


