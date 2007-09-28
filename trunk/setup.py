#!/usr/bin/env python

# $HeadURL$
# $Id$

import os

from distutils.core import setup, Extension

def capture(cmd):
    return os.popen(cmd).read().strip()

setup(name='GnaKB',
        version='0.1',
        description='GnaKB, a GTK+ client to query train connections & fares.',
        author='tomfuks',
        author_email='xxxxxxxxxxxx',
        url='http://gnakb.berlios.de',
        classifiers=[
            'Development Status :: 4 - Beta',
            'Environment :: X11 Applications',
            'Intended Audience :: End Users/Desktop',
            'License :: GNU General Public License (GPL)',
            'Operating System :: Linux',
            'Operating System :: MacOS :: MacOS X',
            'Programming Language :: Python',
            'Topic :: Office/Business :: Utilities',
            ],
        py_modules = ['gnakb', 'kbclient', 'gnakblib/BeautifulSoup', 'gnakblib/ClientForm', 'gnakblib/sgmllib'],
        ext_modules=[],
        scripts = ['gnakb'],
        data_files=[('share/gnakb', ['README', 'CHANGELOG', 'TODO', 'stations.txt']),
                    #('share/applications', ['gnakb.desktop']),
                    ('share/pixmaps', ['pixmaps/gnakb.png']),
                    ],
        )
