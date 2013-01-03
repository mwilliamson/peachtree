#!/usr/bin/env python

import os
from distutils.core import setup

def read(fname):
    return open(os.path.join(os.path.dirname(__file__), fname)).read()

setup(
    name='peachtree',
    version='0.1.0',
    description='Library for starting and interacting with qemu/kvm',
    long_description=read("README"),
    author='Michael Williamson',
    url='http://github.com/mwilliamson/peachtree',
    packages=['peachtree'],
    install_requires=["spur>=0.1.5", "starboard>=0.1.0"],
)
