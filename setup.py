#!/usr/bin/env python
# - coding: utf-8 -
from setuptools import setup

setup(
    name='django-sakkada',
    version='1.11.0',

    description = (u'Collection of custom extensions'
                   u' for the Django Framework'.encode('utf8')),
    long_description = (open('README.rst').read().decode('utf8')
                        + open('CHANGES.rst').read().decode('utf8')),

    author='Guchetl Murat',
    author_email='gmurka@gmail.com',

    url='https://bitbucket.org/sakkada/django-sakkada/',

    packages=['sakkada',],
    license = 'MIT license',

    requires=['django (>= 1.11)'],

    classifiers=(
        'Development Status :: 4 - Beta',
        'Environment :: Web Environment',
        'Framework :: Django',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: MIT License',
        'Natural Language :: English',
        'Programming Language :: Python',
        'Programming Language :: Python :: 2',
        'Programming Language :: Python :: 2.6',
        'Programming Language :: Python :: 2.7',
        'Topic :: Software Development :: Libraries :: Python Modules',
    ),
)
