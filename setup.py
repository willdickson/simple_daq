#!/usr/bin/env python
from setuptools import setup, find_packages

setup(name='simple_daq',
      version='0.1',
      description='simple data capture for data acquisition cards supported by comedi',
      author='William Dickson',
      author_email='wbd@caltech.edu',
      packages=find_packages(),
      entry_points = {
        'console_scripts': [
            'daq-acquire = simple_daq:daq_acquire_main',
            'plot-daq = simple_daq:plot_daq_main',
            ]
        }
     )


