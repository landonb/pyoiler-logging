#!/usr/bin/env python
# Last Modified: 2016.11.19 /coding: utf-8
# Copyright: © 2016 Landon Bouma.
#  vim:tw=0:ts=4:sw=4:et

# FIXME/2016-11-19: Wire this into a automated test tool.

from pyoiler_logging import *
init_logging(log_level=0)

def test_from_fcn():
    debug('from fcn')

def test_empties():
    log()
    fatal()
    critical()
    error()
    warning()
    notice()
    debug()
    trace()
    verbose1()
    verbose2()
    verbose3()
    verbose4()
    verbose5()
    verbose()
    info()

def test_pangram():
    # https://en.wikipedia.org/wiki/Pangram
    log('Pack')
    fatal('my')
    critical('box')
    error('with')
    warning('five')
    notice('dozen')
    debug('liquor')
    trace('jugs')
    verbose1('dozy')
    verbose2('fowl')
    verbose3('quack')
    verbose4('bright')
    verbose5('vixens')
    verbose('jump')
    info('vixens')

if __name__ == '__main__':
    #test_from_fcn()
    #test_empties()
    test_pangram()

