#!/usr/bin/env python

# $HeadURL$
# $Id$

import os

from distutils.core import setup, Extension

def capture(cmd):
    return os.popen(cmd).read().strip()

setup(name='GHAFAS',
        version='0.1',
        description='GHAFAS, a GTK+ client to query train connections & fares.',
        author='tomfuks',
        author_email='xxxxxxxxxxxxxxxx',
        url='http://ghafas.berlios.de',
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
        py_modules = ['ghafas', 'ghafasclient', 'ghafaslib/BeautifulSoup', 'ghafaslib/ClientForm', 'ghafaslib/sgmllib'],
        ext_modules=[],
        scripts = ['ghafas'],
        data_files=[
                    ('share/ghafas', ['README', 'CHANGELOG', 'TODO']),
                    ('share/ghafas/stations', ['stations/ice-only.txt', ]),
                    #('share/applications', ['ghafas.desktop']),
                    ('share/pixmaps', ['pixmaps/ghafas.png']),
                    ],
        )
