#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""The setup script."""

from setuptools import setup, find_packages
from os import path 
import re, io


__version__ = re.search(
    r'__version__\s*=\s*[\'"]([^\'"]*)[\'"]',  # It excludes inline comment too
    io.open('wod_prof_db/__init__.py', encoding='utf_8_sig').read()
    ).group(1)

here = path.abspath(path.dirname(__file__))

with open('README.rst') as readme_file:
    readme = readme_file.read()

# get the dependencies and installs
with open(path.join(here, 'requirements.txt'), encoding='utf-8') as f:
    all_reqs = f.read().split('\n')

# install_requires = [x.strip() for x in all_reqs if 'git+' not in x]
install_requires = [x.strip() for x in all_reqs]
# dependency_links = [x.strip().replace('git+', '') for x in all_reqs if x.startswith('git+')]
dependency_links = []
# install_requires.extend([x.strip().replace('git+', '') for x in all_reqs if x.startswith('git+')])

tests_requirements = ['pytest'],
setup_requirements = ['pytest-runner']
requirements = [
    # package requirements go here
]

setup(
    name='wod_prof_db',
    version=__version__,
    description="Assemble searchable data/meta-data base of WOD profiles",
    long_description=readme,
    author="Saulo M Soares",
    author_email='ocesaulo@gmail.com',
    url='https://github.com/ocesaulo/wod_prof_db',
    packages=find_packages(include=['wod_prof_db'],
                           exclude=('docs', 'tests*',)),
    license="MIT license",

    install_requires=install_requires,
    dependency_links=dependency_links,
    setup_requires=setup_requirements,
    test_suite='tests',
    tests_require=tests_requirements,
    keywords='wod_prof_db',
    classifiers=[
        'Programming Language :: Python :: 3.6',
    ]
)
