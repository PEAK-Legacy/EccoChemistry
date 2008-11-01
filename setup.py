#!/usr/bin/env python
"""Distutils setup file"""
import sys, ez_setup
ez_setup.use_setuptools()
from setuptools import setup

# Metadata
PROJECT = 'EccoChemistry'
VERSION = '0.4a1'
TAGLINE = 'SQLAlchemy-like interface for import/export/sync with the Ecco PIM'
MODULES = ['ecco_chemistry']
REQUIRES, LINKS = ['EccoDDE','DecoratorTools'], []
if sys.version<"2.4":
    REQUIRES.append("decimal")
    LINKS.append("http://sourceforge.net/project/showfiles.php?group_id=104148&package_id=130611")

def get_description():
    # Get our long description from the documentation
    f = file('README.txt')
    lines = []
    for line in f:
        if not line.strip():
            break     # skip to first blank line
    for line in f:
        if line.startswith('.. contents::'):
            break     # read to table of contents
        lines.append(line)
    f.close()
    return ''.join(lines)

setup(
    name=PROJECT, version=VERSION, description=TAGLINE,
    url = "http://cheeseshop.python.org/pypi/" + PROJECT,
    download_url = "http://peak.telecommunity.com/snapshots/",
    long_description = file('README.txt').read(), #get_description(),
    author="Phillip J. Eby", author_email="peak@eby-sarna.com",
    license="PSF or ZPL", test_suite = 'ecco_chemistry',
    py_modules=['ecco_chemistry'], include_package_data = True,
    install_requires = REQUIRES, dependency_links=LINKS,
)
