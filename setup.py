"""
simple_daq
Copyright (C) William Dickson, 2008.

wbd@caltech.edu
www.willdickson.com

This file is part of simple_daq.

simple_step is free software: you can redistribute it and/or modify it
under the terms of the GNU Lesser General Public License as published
by the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.
    
simple_step is distributed in the hope that it will be useful, but
WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
Lesser General Public License for more details.

You should have received a copy of the GNU Lesser General Public
License along with simple_step.  If not, see
<http://www.gnu.org/licenses/>.  
from setuptools import setup, find_packages

"""

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


