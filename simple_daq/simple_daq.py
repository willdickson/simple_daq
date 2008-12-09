#!/usr/bin/env python
"""
simple_daq
Copyright (C) William Dickson, 2008.

wbd@caltech.edu
www.willdickson.com

This file is part of simple_daq.

simple_daq is free software: you can redistribute it and/or modify it
under the terms of the GNU Lesser General Public License as published
by the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.
    
simple_daq is distributed in the hope that it will be useful, but
WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
Lesser General Public License for more details.

You should have received a copy of the GNU Lesser General Public
License along with simple_daq.  If not, see
<http://www.gnu.org/licenses/>.  

---------------------------------------------------------------------

Purpose: A simple module for capturing data from comedi supported data
acquisition cards. Includes functions which support the daq_acquire
command-line data acquisition program. In particular, in addition the
basic data acquisition function "acquire_data" there are functions for
parsing text based configuration files and handling command-line
options.
 
 William Dickson 02/20/2007

"""
import sys
import os
import os.path
import time
import numpy 
import comedi as c
import optparse

PROG_NAME = os.path.basename(sys.argv[0])

# Constants
MIN_GAIN = 0
MAX_GAIN = 3

# Default options
DEFAULT_DEVICE = '/dev/comedi0'
DEFAULT_SAMPLE_NUM = 1000
DEFAULT_SAMPLE_FREQ = 1000
DEFAULT_CHANNELS = '0 1 2 3 4 5 6 7'
DEFAULT_GAINS = '0'
DEFAULT_SUBDEV = 0
DEFAULT_OUTPUT_FILE = None
DEFAULT_CONFIG_FILE = None
DEFAULT_VERBOSE = False
DEFAULT_PLOT = False
DEFAULT_AREF = 'ground'

# Comedi command Defaults
DEFAULT_CMD_FLAGS = 0
DEFAULT_CMD_SART_ARG = 0
DEFAULT_CMD_CONVERT_ARG = 5000
DEFAULT_CMD_TEST_NUM = 4

# Configuration files
CURR_DIR_CONFIG = 'daq-config'
HOME_DIR_CONFIG = '.daq-acquire'

# Command test messages
CMD_TEST_MSG = [
    "success",
    "invalid source",
    "source conflict",
    "invalid argument",
    "argument conflict",
    "invalid chanlist",
    ]
NANO_SEC = 1.0e9

def parse_config_file(filename):
    """
    Parse configuration file
    """
    config = {}
    fid = open(filename)
    for line in fid.readlines():
        line = line.split()
        if len(line) == 0:
            continue
        if line[0] == '#':
            continue
        config[line[0].lower()] = reduce(lambda x,y:x+' '+y, line[1:])
    fid.close()
    return config


def process_options():
    """
    Process command line options using options parser. Returns a dictionary
    of the configurations options selected on the command line. 

    This function is used in daq_acquire command-line program
    """

    # Setup input option parser
    usage = """%prog [OPTION]...

    %prog acquires data from a an acquisition device such a PCI
    DAQ card. Command line options can be used to configure aspects of the
    data acquisition such as the device, the number of samples acquired,
    the sample rate, etc. If a given command line options is not present the
    program looks first for a configuration file with the name daq-config
    in the current directory. If this file cannot be found the program will
    look for a configuration file named .daq-acquire in the users home
    directory. If neither of these files are present the program defaults
    are used. If an output file is not specified the samples acquired by the
    program are sent to stdout. """


    # Set up command line option parser 
    parser = optparse.OptionParser(usage=usage)

    parser.add_option('-v', '--verbose',
                      action='store_true',
                      dest='verbose',
                      help='verbose mode - print addition information',
                      default=DEFAULT_VERBOSE
                      )
    parser.add_option('-p', '--plot',
                      action='store_true',
                      dest='plot',
                      help='plot samples upon completion of acquisition',
                      default=DEFAULT_PLOT
                      )

    parser.add_option('-d', '--device',
                      type='string',
                      dest='device',
                      help='select comedi device (e.g. /dev/comedi0)',
                      default=None
                      )

    parser.add_option('-n', '--sample_num',
                      type='int',
                      dest='sample_num',
                      help='number of samples to acquire',
                      default=None
                      )

    parser.add_option('-f', '--sample_freq',
                      type='int',
                      dest='sample_freq',
                      help='sampling frequency (Hz)',
                      default=None
                      )

    parser.add_option('-c', '--channels',
                      type='string',
                      dest='channels',
                      help='select data acquisition channels',
                      default= None
                      )

    parser.add_option('-g', '--gains',
                      type='string',
                      dest='gains',
                      help ='select channel gain',
                      default=None
                      )

    parser.add_option('-s', '--sub_device',
                      type='int',
                      dest='subdev',
                      help='select subdevice of data acquisition device',
                      default=None
                      )

    parser.add_option('-o', '--output',
                      type='string',
                      dest='output_file',
                      help='select output file (default = stdout)',
                      default=None
                      )

    parser.add_option('-i', '--configuration', type='string', dest='config_file',
                      help='select configuration file', default=None) 

    parser.add_option('-a', '--aref',
                      type='string',
                      dest='aref',
                      help='select reference mode (ground,diff,common)',
                      default=None
                      )

    # Parse input options 
    options, args = parser.parse_args()

    # Remove options with None
    for key in options.__dict__.keys():
        if options.__dict__[key] == None:
            del options.__dict__[key]

    return options.__dict__
    

def process_config(config, src_str):
    """
    Process a configration dictionary so the values can be used in the
    propram.  Strings from the configuration files and command line
    arguments are cast to the appropriate values. Also, the configuration
    is checked for possible problems.

    This function is used when initial configuration dictionary is read from 
    a text based configuration file. 

    Note: the error checking here is really poor. In a better world I would
    query the daq card and check the options versus what I find there.

    """
    
    if 'sample_num' in config:
        # Convert and check sample_num
        try:
            config['sample_num'] = int(config['sample_num'])
        except ValueError:
            err_msg = '%s: error: %s: invalid sample number value\n'%(PROG_NAME,src_str)
            sys.stderr.write(err_msg)
            sys.exit(1)
        if config['sample_num'] <= 0:
            err_msg = '%s: error: %s: number of sample must be > 0\n'%(PROG_NAME,src_str)
            sys.stderr.write(err_msg)
            sys.exit(1)
    
    if 'sample_freq' in config:
        # Convert and check sample frequency
        try:
            config['sample_freq'] = int(config['sample_freq'])
        except ValueError:
            err_msg = '%s: error: %s: invalid sample frequency value\n'%(PROG_NAME,src_str)
            sys.stderr.write(err_msg)
            sys.exit(1)
        if config['sample_freq'] <= 0:
            err_msg = '%s: error: %s: sample frequency must be > 0\n'%(PROG_NAME,src_str)
            sys.stderr.write(err_msg)
            sys.exit(1)
    
    if 'channels' in config:
        # Convert and Check channel numbers
        if not type(config['channels']) == list:
            try:
                config['channels'] = [int(x) for x in config['channels'].split()]
            except ValueError:
                err_msg = '%s: error: %s: invalid channel values\n'%(PROG_NAME,src_str)
                sys.stderr.write(err_msg)
                sys.exit(1)
    
        # Really need to query card and get number of channel for this subdevice
        fail = False
        for x in config['channels']:
            if x < 0:
                fail = True
        if fail:
            err_msg = '%s: error: %s: channel values must be >= 0\n'%(PROG_NAME,src_str)
            sys.stderr.write(err_msg)
            sys.exit(1)

    if 'gains' in config:
        if not type(config['gains']) == list:
            try:
                # Convert and check gains 
                config['gains'] = [int(x) for x in config['gains'].split()]
            except ValueError:
                err_msg = '%s: error: %s: invalid gain values %s\n'%(PROG_NAME,src_str,config['gains'])
                sys.stderr.write(err_msg)
                sys.exit(1)
        fail = False
        for x in config['gains']:
            if x < MIN_GAIN or x > MAX_GAIN:
                fail = True
        if fail:
            err_msg = '%s: error: %s: gains must be between 0 and 3\n'%(PROG_NAME,src_str)
            sys.stderr.write(err_msg)
            sys.exit(1)


    if ('gains' in config) and ('channels' in config):
        # Make sure we have one gain or enough for each channel
        ngains = len(config['gains'])
        nchans = len(config['channels'])         
        if not (ngains == nchans or ngains == 1):
            err_msg = '\n \tchannels: %s\n'%(config['channels'],)
            err_msg += '\tgains: %s\n\n'%(config['gains'],)
            err_msg += '%s: error: %s: the number of gain values be equal '%(PROG_NAME,src_str)
            err_msg += 'to 1 or to the number of channels\n'
            sys.stderr.write(err_msg)
            sys.exit(1)
        if ngains == 1:
            config['gains'] = config['gains']*nchans        


    if 'subdev' in config:
        # Convert and check subdevice number
        try:
            config['subdev'] = int(config['subdev'])
        except ValueError:
            err_msg = "%s: error: %s: invalid subdevice value '%s'"%(PROG_NAME,src_str,config['subdev'])
            sys.stderr.write(err_msg)
            sys.exit(1)

    if 'aref' in config:
        if not config['aref'] in ('diff', 'ground', 'common'):
            err_msg = "%s: error: %s: invalid reference mode '%s'"%(PROG_NAME,src_str,config['aref'])
            sys.stderr.write(err_msg)
            sys.exit(1)
    

def set_config():
    """
    Determine the configuration to use from the command line options, the
    command line specified configuration file (if it exists), the current
    directory configuration file (daq-config), and the home directory
    configuration file (daq-acquire).

    The order a precedence is command line options, command line configuration
    file, current directory configuration file, home directory configuration
    file. 
    """

    # Set confguration to default values
    config = {
        'device': DEFAULT_DEVICE,
        'sample_num' : DEFAULT_SAMPLE_NUM,
        'sample_freq' : DEFAULT_SAMPLE_FREQ,
        'channels' : DEFAULT_CHANNELS,
        'gains' : DEFAULT_GAINS,
        'subdev' : DEFAULT_SUBDEV,
        'output_file' : DEFAULT_OUTPUT_FILE,
        'config_file' : DEFAULT_CONFIG_FILE,
        'verbose': DEFAULT_VERBOSE,
        'plot' : DEFAULT_PLOT, 
        'aref' : DEFAULT_AREF
        }
    process_config(config, 'default config')

    # Get configuration information from command line options
    options_config = process_options()
    process_config(options_config, 'command line config')
    config.update(options_config)
    used_config_keys = options_config.keys()

    # Look for configuration files 
    curr_dir = os.getcwd()
    home_dir = os.environ['HOME']
    curr_dir_config_file = os.path.join(curr_dir, CURR_DIR_CONFIG)
    home_dir_config_file = os.path.join(home_dir, HOME_DIR_CONFIG)
    curr_config_exists =  os.path.exists(curr_dir_config_file)
    home_config_exists =  os.path.exists(home_dir_config_file)


    # If there is a configuration file specified on the command line 
    if  'config_file' in options_config:
        config_file_exists = os.path.exists(options_config['config_file']) 
        if config_file_exists: 
            try:
                # Read custom config file and update config 
                file_config = parse_config_file(options_config['config_file'])

            except IOError:
                msg_data = (PROG_NAME, options_config['config_file'],)
                err_msg = "%s: error: option -i: unable to parse configuration file '%s'"%msg_data
                sys.stderr.write(err_msg)
                sys.exit(1)

            # Remove items from file config which are already in options config 
            for key in used_config_keys:
                try:
                    del file_config[key]
                except:
                    pass
            process_config(file_config, 'file config option -i')
            config.update(file_config)
            used_config_keys+=file_config.keys()
        else:
            msg_data = (PROG_NAME, options_config['config_file'],)
            err_msg = "%s: error: option -i: configuration file '%s' not found"%msg_data
            sys.stderr.write(err_msg)
            sys.exit(1)
            
    if config['verbose']:
        print 
        print 'configuration files'
        print
        print '\t-i  config_file:',
        if 'config_file' in options_config:
            print '%s, exists: %s'%(options_config['config_file'], config_file_exists)
        else:
            print 'none'
        print '\tcurr_dir_config: %s, exists: %s'%(curr_dir_config_file, curr_config_exists)
        print '\thome_dir_config: %s, exists: %s'%(home_dir_config_file,home_config_exists)
        print


    # If there are unused configuration options try loading daq_config
    if (not len(used_config_keys)==len(config.keys())) and curr_config_exists:
        curr_dir_config = parse_config_file(curr_dir_config_file)

        # Remove item from config which have already been used
        for key in used_config_keys:
            try:
                del curr_dir_config[key]
            except:
                pass
        process_config(curr_dir_config, 'daq_config')
        config.update(curr_dir_config)
        used_config_keys+=curr_dir_config.keys()


    # If there are still unused configuration options try loading $HOME/.daq_acquire
    if (not len(used_config_keys)==len(config.keys())) and home_config_exists:
        home_dir_config = parse_config_file(home_dir_config_file)

        # Remove item from config which have already been used
        for key in used_config_keys:
            try:
                del home_dir_config[key]
            except:
                pass
        process_config(home_dir_config, '.daq_acquire')
        config.update(home_dir_config)
        used_config_keys+=home_dir_config.keys()

    # Process combined configuration to check for errors
    process_config(config, 'combined config')
    return config

def acquire_data(config):
    """
    Acquire data from data acquisition device. 
    """
    
    #Open a comedi device
    dev=c.comedi_open(config['device'])
    if not dev:
        err_msg = "%s: error: unable to open openning Comedi device"%(PROG_NAME,)
        sys.stderr.write(err_msg)
        sys.exit(1)

    # Get a file-descriptor to access data
    fd = c.comedi_fileno(dev)

    # Setup channels
    nchans = len(config['channels'])
    aref_str = config['aref'].lower()
    if aref_str == 'diff':
        aref =[c.AREF_DIFF]*nchans
    elif aref_str == 'common':
        aref =[c.AREF_COMMON]*nchans
    elif aref_str == 'ground':
        aref =[c.AREF_GROUND]*nchans
    else:
        raise ValueError, 'unknown aref'

    #nchans = len(config['channels'])
    #aref =[c.AREF_GROUND]*nchans

    # Pack the channel, gain and reference information into the chanlist object
    channel_list = c.chanlist(nchans)
    for i in range(nchans):
	channel_list[i]=c.cr_pack(config['channels'][i], config['gains'][i], aref[i])

    # Construct a comedi command 
    cmd = c.comedi_cmd_struct()
    cmd.subdev = config['subdev']
    cmd.flags = DEFAULT_CMD_FLAGS
    cmd.start_src = c.TRIG_NOW
    cmd.sart_arg = DEFAULT_CMD_SART_ARG
    cmd.scan_begin_src = c.TRIG_TIMER
    cmd.scan_begin_arg = int(NANO_SEC/config['sample_freq'])
    cmd.convert_src = c.TRIG_TIMER
    cmd.convert_arg = DEFAULT_CMD_CONVERT_ARG
    cmd.scan_end_src = c.TRIG_COUNT
    cmd.scan_end_arg = nchans
    cmd.stop_src = c.TRIG_COUNT
    cmd.stop_arg = config['sample_num']
    cmd.chanlist = channel_list
    cmd.chanlist_len = nchans

    # Test comedi command
    if config['verbose']:
        print 'Testing comedi command'
        print 
    for i in range(0,DEFAULT_CMD_TEST_NUM):
        if config['verbose']:
            print_cmd(cmd)
        ret = c.comedi_command_test(dev,cmd)
        if config['verbose']:
            print 
            print '\t*** test %d returns %s'%(i, CMD_TEST_MSG[ret])
            print 
    if not ret==0:
        msg_data = (PROG_NAME, CMD_TEST_MSG[ret])
        err_msg = '%s: error: unable to configure daq device - %s'%msg_data
        sys.stderr.write(err_msg)

    # Acquire data
    if config['verbose']:
        print 'acquiring data'
        print 
        sys.stdout.flush()
    ret = c.comedi_command(dev,cmd) # non blocking
    if not ret == 0:
        err_msg = '%s: error: unable to execute comedi command'%(PROG_NAME,)
        sys.stderr.write(err_msg)
        sys.exit(1)

    # Read data from buffer - may want to add a timeout here
    read_done = False
    bytes_total = 2*config['sample_num']*nchans
    bytes_read = 0
    datastr = ''
    while not read_done:
        try:
            buffstr = os.read(fd,bytes_total)
        except OSError, err:
            if err.args[0]==4:
                continue
            raise                
        datastr += buffstr
        bytes_read += len(buffstr)
        if config['verbose']:
            print '\tread:', bytes_read, 'of', 2*config['sample_num']*nchans, 'bytes'
        if bytes_read == bytes_total:
            read_done = True
        
    # Convert from string to integers
    dataarray = numpy.fromstring(datastr, numpy.uint16)

    # Unpack data from long array and convert to volts
    array_list = []
    for i in range(0,nchans):

        # Get channel information
        channel = config['channels'][i]
        gain = config['gains'][i]
        subdev = config['subdev']
        maxdata = c.comedi_get_maxdata(dev,subdev, channel)
        cr = c.comedi_get_range(dev,subdev,channel,gain)

        # Convert to voltages
        temp_array = dataarray[i::nchans]
        temp_array = numpy.array([c.comedi_to_phys(int(x),cr,maxdata)for x in temp_array])
        temp_array = numpy.reshape(temp_array,(temp_array.shape[0],1))
        array_list.append(temp_array)

    # Form sample_num x nchans array
    samples = numpy.concatenate(tuple(array_list),1)
    n,m = samples.shape

    if config['verbose']:
        print 
        print 'acquired data array w/ size: %dx%d'%(n,m)

    # Create time array
    sample_t = (1.0/float(config['sample_freq']))
    sample_t_true = cmd.scan_begin_arg/NANO_SEC
    if config['verbose']:
        print
        print 'sample frequencies'
        print 
        print '\tdesired sample freq: ', 1.0/sample_t
        print '\tactual sample freq: ', 1.0/sample_t_true
        print 
    
    t = numpy.linspace(0,n*sample_t_true, n)

    # Close acquisition device
    ret = c.comedi_close(dev)
        
    return t,samples

def print_cmd(cmd):
    """
    Display contents of command structure 
    """
    print '\tsubdev:', cmd.subdev
    print '\tflags:', cmd.flags
    print '\tstart_src:', cmd.start_src
    print '\tstart_arg:', cmd.start_arg
    print '\tscan_begin_src:', cmd.scan_begin_src
    print '\tscan_begin_arg:', cmd.scan_begin_arg
    print '\tconvert_src:', cmd.convert_src
    print '\tconvert_arg:', cmd.convert_arg
    print '\tscan_end_src:', cmd.scan_end_src
    print '\tstop_src:', cmd.stop_src
    print '\tstop_arg:', cmd.stop_arg
    print '\tchanlist:', cmd.chanlist
    print '\tchanlist_len:',cmd.chanlist_len 


def write_samples(fid, t, samples):
    """
    Write time and samples to output file.
    """
    for i in xrange(0,t.shape[0]):
        fid.write('%f '%(t[i],))
        for j in range(0,samples.shape[1]):
            fid.write('%f '%(samples[i,j],))
        fid.write('\n') 


# Functions for console scripts --------------------------------------------
def daq_acquire_main():
    """
    main function for daq_acquire command-line program. Called by
    daq_acquire script.
    """

    # Get configuration 
    config = set_config()

    if config['verbose']:
        print
        print 'Configuration options'
        print
        for key in config.keys():
            print '\t%s'%(key,),  config[key]
        print
    
    # Acquire data
    t, samples = acquire_data(config)    

    # Save data to output file or write to stdout
    if config['output_file'] == None:
        # Print data to stdout
        outfile_fid = sys.stdout
        write_samples(sys.stdout, t, samples)
    else:
        # Write data to output file
        outfile_fid = open(config['output_file'],'w')
        write_samples(outfile_fid, t, samples)
        outfile_fid.close()

    # Plot data
    if config['plot']:
    
        import matplotlib.pylab as pylab

        n,m = samples.shape
        for i in range(0,m):
            pylab.figure(config['channels'][i])
            pylab.plot(t,samples[:,i])
            pylab.xlabel('t (sec)')
            pylab.ylabel('(V)')
            pylab.title('channel %d'%(config['channels'][i],))
        pylab.show()


def plot_daq_main():
    """
    main function for plot_daq command-line program
    """
    
    import matplotlib.pylab as pylab


    # Setup input option parser
    usage = """%prog [OPTION]...

    %prog simple script for plotting data captured by daq_acquire
     commmand-line program. """

    # Set up command line option parser 
    parser = optparse.OptionParser(usage=usage)
    options, args = parser.parse_args()

    datafile = sys.argv[1]
    data = pylab.load(datafile)

    t = data[:,0]
    samples = data[:,1:]

    for i in range(samples.shape[1]):
        pylab.figure(i)
        pylab.plot(t,samples[:,i])
        pylab.xlabel('t (sec)')
        pylab.ylabel('(V)')
        pylab.title('channel %d'%(i,))
    pylab.show()

# ---------------------------------------------------------------------
if __name__=="__main__":
    
    daq_acquire_main()
    
    #plot_daq_main()
