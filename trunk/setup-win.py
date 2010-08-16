#!/usr/bin/env python

# $HeadURL: https://casualcoding@svn.berlios.de/svnroot/repos/ghafas/trunk/setup.py $
# $Id: setup.py 131 2008-01-13 12:12:45Z tomfuks $

import os

from distutils.core import setup, Extension
from py2exe.build_exe import py2exe
from glob import glob

ms_data_files = ("Microsoft.VC90.CRT", glob(r'f:\dev\ms-vc-runtime\*.*'))

def capture(cmd):
    return os.popen(cmd).read().strip()

setup(name='GHAFAS',
        version='0.1',
        description='GHAFAS, a GTK+ client to query train connections & fares.',
        author='tomfuks',
        author_email='casualcoding@gmail.com',
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
                    ('ghafaslib', glob('ghafaslib/*.py*')),
					ms_data_files,
                    ],
		console=["ghafas"],
		
		options = {
			'py2exe': {
				'packages':'encodings',
				'includes': 'cairo, gobject, atk, pango, pangocairo, gio, ghafaslib.BeautifulSoup, ghafaslib.ClientForm',
				}
			},
        )
