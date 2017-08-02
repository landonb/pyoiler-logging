# File: pyoiler_logging/__init__.py
#  /coding: utf-8
#  vim:tw=0:ts=4:sw=4:et
# Last Modified: 2017.08.02
# Author: Landon Bouma (landonb &#x40; retrosoft &#x2E; com)
# Project: https://github.com/landonb/pyoiler-logging
# Summary: Python logging wrapper.
# Copyright: © 2008, 2015-2017 Landon Bouma.
# License: GPLv3. See LICENSE.txt.
# -------------------------------------------------------------------
# Summary: Wrap Python logging facility:
# - Print timestamp.
# - Print facility.
# - Wrap and columnize wide (long) lines.
# - Add convenience fcns., e.g., log.info(), etc.

# See: /usr/lib/python2.7/logging/__init__.py
#      /usr/lib/python3.5/logging/__init__.py
#      etc.

# Sample usage:
#   $ py3

example_usage="""

# 

Running the command:


    python3 -c "\
from pyoiler_logging import *
init_logging(log_level=0)
debug('A message')
warngng('A warning')
fatal('Goodbye')
"



    python3 -c "\

import logging
import logging2
logging2.init_logging(
    logging.DEBUG,
    show_logger_name=True,
    show_mod_func_line=False,
)
log = logging.getLogger('filename-or-service')
log.debug('A message')
log.warn('A warning')
log.fatal('Goodbye')
"

Prints:

    DEBG|2016-Oct-13|Thu|11:42:33|filename-or-service | A message
    WARN|2016-Oct-13|Thu|11:42:33|filename-or-service | A warning
    CRIT|2016-Oct-13|Thu|11:42:33|filename-or-service | Goodbye

"""

fixme_mod_name="""

cat > logging2_test.py << EOF
#!/usr/bin/env python3
import logging
import logging2
logging2.init_logging(logging.DEBUG)
log = logging.getLogger('filename-or-service')
log.debug('A message')
EOF

chmod 775 logging2_test.py
./logging2_test.py

DEBG|2016-Oct-13|Thu|11:31:26|__init__.debug:1262| A message

FIXME: The logging module name is used (__init__.debug)
    i.e., from /usr/lib/python3.4/logging/__init__.py
    see: target_frame, below.

"""

import os
import sys

import logging
import logging.handlers

import inspect
#import string
import threading
import traceback

try:
    import wx
    import wx.lib.newevent
    # Create wxPython event type.
    wxLogEvent, EVT_WX_LOG_EVENT = wx.lib.newevent.NewEvent()
except ImportError:
    pass

__all__ = [
    #'My_Logger',
    #'My_Handler',
    'init_logging',
    # SYNC_ME: Log levels.
    'log',
    'fatal',
    'critical',
    'error',
    'warning',
    'notice',
    'debug',
    'trace',
    'verbose1',
    'verbose2',
    'verbose3',
    'verbose4',
    'verbose5',
    'verbose',
    'info',
    #
    'assert_soft',
]

"""

The Python logging library defines the following levels:

---Level---  ---Value---
 CRITICAL         50
 FATAL            50 [*aliases CRITICAL]
 ERROR            40
 WARNING          30 [*also WARN]
 INFO             20
 DEBUG            10
 NOTSET            0

Some other loggers are more expressible and include additional
levels, such as 'notice' and 'verbose'. We add those levels to
the logger, as well as a handful of verbose sublevels. You can
feel comfortable adding lots of logging without worrying about
noise, since it's easily turned off.

---Level---  ---Value---
 NOTICE           25
 VERBOSE1          9
 VERBOSE2          8
 VERBOSE3          7
 VERBOSE4          6
 VERBOSE5          5
 VERBOSE           5

# SYNC_ME: Log levels.
---Level---  ---Value---
 TERMINAL         186
 CRITICAL         50
 FATAL            50 [*aliases CRITICAL]
 ERROR            40
 WARNING          30 [*also WARN]
 NOTICE           25 ** NEW
 INFO             20
 TRACE            15 ** NEW
 DEBUG            10
 VERBOSE1          9 ** NEW
 VERBOSE2          8 ** NEW
 VERBOSE3          7 ** NEW
 VERBOSE4          6 ** NEW
 VERBOSE5          5 ** NEW
 VERBOSE           5 ** NEW
 NOTSET            0


Also, this script splits long messages into multiple lines and prefixes 
each line except the first with a bunch of spaces, so that messages are 
right-justified and don't fill the columns on the left, which are used to 
show the timestamp, debug level, and logger name.

E.g.,

12:24:36  DEBUG  item_user_access  #  A one-line message
12:34:56  DEBUG     grax.grac_mgr  #  This is an example of a log message
                                   #  that spans two lines.
"""

# *** 

# SYNC_ME: Log levels.
TERMINAL = 186
CRITICAL = logging.CRITICAL
FATAL = logging.FATAL
ERROR = logging.ERROR
WARNING = logging.WARNING
WARN = logging.WARN
NOTICE = 25
INFO = logging.INFO
TRACE = 15
DEBUG = logging.DEBUG
VERBOSE1 = 9
VERBOSE2 = 8
VERBOSE3 = 7
VERBOSE4 = 6
VERBOSE5 = 5
VERBOSE = 5
NOTSET = logging.NOTSET

# ***

APACHE_REQUEST = None

# *** 

def config_line_format(frmat_len, frmat_postfix, line_len=None, add_tid=False):
    global msg_continuation_prefix
    global line_len_log
    global line_len_msg
    global include_thread_id
    if line_len == 0:
        # Most terminals' widths are 80 chars, right?
        line_len = 80
    msg_continuation_prefix = (' ' * frmat_len) + frmat_postfix
    line_len_log = line_len
    include_thread_id = add_tid
    if line_len_log is not None:
        line_len_msg = line_len_log - len(msg_continuation_prefix)
    else:
        line_len_msg = None

# *** 

if sys.version_info.major == 2:
    make_string = lambda s: unicode(s)
else:
    make_string = lambda s: str(s)

class My_Logger(logging.Logger):

    def __init__(self, name, level=logging.NOTSET):
        logging.Logger.__init__(self, name, level)

    # C.f., e.g., /usr/lib64/python2.7/logging/__init__.py

    def _log(self, level, msg, args, exc_info=None, extra=None):
        global APACHE_REQUEST
        global include_thread_id
        global show_logger_name_
        global show_mod_func_line_
        # For multi-threaded apps, including the thread ID.
        if include_thread_id:
            # FIXME/MAYBE: Use Formatter's %(thread)s.
            if APACHE_REQUEST is not None:
                # You'll see the same parent process ID (and it's not 1)
                # for all apache request threads (os.getppid()).
                # You'll see lots of unique process IDs for each request,
                # but some processes appear to handle multiple connections
                # per process (os.getpid()).
                # You'll find that each thread has a unique identifier. It
                # doesn't matter if we use the cooked-in get_ident() value,
                # or if we use the object id, id(threading.currentThread()).
                msg = '%8d-%3d: %s' % (
                    threading.currentThread().ident,
                    int(APACHE_REQUEST.connection.id),
                    msg,
                )
            else:
                msg = '%8d: %s' % (threading.currentThread().ident, msg,)
#
        if False and show_mod_func_line_:
            # Grab the frame so we can spit the fcn., file, and line number.
            # (We cannot use Formatter's %()s options because wrappered.)
            frame = inspect.currentframe().f_back
            #frame = frame.f_back
            mod = make_string(inspect.getmodulename(frame.f_code.co_filename))
            func = frame.f_code.co_name + '()'
            linen = make_string(frame.f_lineno)
            mod_func_line = '%s.%s:%s' % (mod, func, linen)
            ##template = string.Template(msg)
            ##template.substitute({'mod_func_line': mod_func_line,})
            #msg = msg.replace('${mod_func_line}', mod_func_line)
            msg = '%s # %s' % (mod_func_line, msg,)
        logging.Logger._log(self, level, msg, args, exc_info, extra)

    # NOTE: Old source used apply, which is deprecated. E.g.,:
    #         apply(self._log, (NOTICE, msg, args), kwargs)
    #       The new source uses the extended call syntax instead.

    def notice(self, msg, *args, **kwargs):
        """
        Log 'msg % args' with severity 'NOTICE'.

        To pass exception information, use the keyword argument exc_info with
        a true value, e.g.

        logger.notice("Houston, we have a %s", "interesting problem", exc_info=1)
        """
        global NOTICE
        if self.isEnabledFor(NOTICE):
            # NOTE: We don't repackages args. I.e., you'll get
            #   TypeError: _log() takes at least 4 arguments (3 given)
            # if you try: self._log(NOTICE, msg, *args, **kwargs)
            self._log(NOTICE, msg, args, **kwargs)

    def trace(self, msg, *args, **kwargs):
        global TRACE
        if self.isEnabledFor(TRACE):
            self._log(TRACE, msg, args, **kwargs)

    def verbose1(self, msg, *args, **kwargs):
        global VERBOSE1
        if self.isEnabledFor(VERBOSE1):
            self._log(VERBOSE1, msg, args, **kwargs)

    def verbose2(self, msg, *args, **kwargs):
        global VERBOSE2
        if self.isEnabledFor(VERBOSE2):
            self._log(VERBOSE2, msg, args, **kwargs)

    def verbose3(self, msg, *args, **kwargs):
        global VERBOSE3
        if self.isEnabledFor(VERBOSE3):
            self._log(VERBOSE3, msg, args, **kwargs)

    def verbose4(self, msg, *args, **kwargs):
        global VERBOSE4
        if self.isEnabledFor(VERBOSE4):
            self._log(VERBOSE4, msg, args, **kwargs)

    def verbose5(self, msg, *args, **kwargs):
        global VERBOSE5
        if self.isEnabledFor(VERBOSE5):
            self._log(VERBOSE5, msg, args, **kwargs)

    def verbose(self, msg, *args, **kwargs):
        """
        Log 'msg % args' with severity 'VERBOSE'.

        To pass exception information, use the keyword argument exc_info with
        a true value, e.g.

        logger.notice("Houston, we have a %s", "loud problem", exc_info=1)
        """
        global VERBOSE
        # Pre-Python 2.7:
        #if self.manager.disable >= VERBOSE:
        #   return
        #if VERBOSE >= self.getEffectiveLevel():
        #   apply(self._log, (VERBOSE, msg, args), kwargs)
        # FIXME: This works in Python 2.7, but hasn't been tested on other
        # releases.
        if self.isEnabledFor(VERBOSE):
            self._log(VERBOSE, msg, args, **kwargs)

    # NOTE: This overrides the Python's Logger.fatal which is Logger.critical.
    def fatal(self, msg, *args, **kwargs):
        global FATAL
        if self.isEnabledFor(FATAL):
            self._log(FATAL, msg, args, **kwargs)

# *** 

class My_StreamHandler(logging.StreamHandler):

    def __init__(self, stream=None):
        logging.StreamHandler.__init__(self, stream)

    def format(self, record):
        return My_Handler.format(self, record)

class My_FileHandler(logging.FileHandler):

    def __init__(self, filename, mode='a'):
        logging.FileHandler.__init__(self, filename, mode)

    def format(self, record):
        return My_Handler.format(self, record)

# MAYBE: Mehhhhhhhh. 2016-06-27: Untested/could not get basic wxPython test to work
#                     (it's my first day using wxPython -- ever! -- so I'll worry/care/
#                     not care about this later since I got normal console working).
class My_wxPythonHandler(logging.StreamHandler):

    def __init__(self, wx_dest=None):
        """
        Initialize handler.
        @param wx_dest: destination object to which to post event
        @type wx_dest: wx.Window
        """
        logging.StreamHandler.__init__(self)
        self.wx_dest = wx_dest
        #self.level = logging.DEBUG

    def format(self, record):
        return My_Handler.format(self, record)

    def flush(self):
        """
        does nothing for this handler
        """
        pass

    def emit(self, record):
        """
        Emit a record.

        """
        try:
            msg = self.format(record)
            evt = wxLogEvent(message=msg, levelname=record.levelname)
            wx.PostEvent(self.wx_dest, evt)
        except (KeyboardInterrupt, SystemExit):
            raise
        except:
            self.handleError(record)

class My_Handler(object):

    @staticmethod
    def format(handler, record):
        """
        Format the specified record. If a formatter is set, use it.
        Otherwise, use the default formatter for the module.
        """
        global msg_continuation_prefix
        global line_len_log
        global line_len_msg

        if handler.formatter:
            fmt = handler.formatter
        else:
            fmt = logging._defaultFormatter

        if False:
            # I cannot get inspect to work as expected.
            # Grab the frame so we can spit the fcn., file, and line number.
            # (We cannot use Formatter's %()s options because wrappered.)
            frame = inspect.currentframe().f_back
            #frame = frame.f_back
            mod = make_string(inspect.getmodulename(frame.f_code.co_filename))
            func = frame.f_code.co_name + '()'
            linen = make_string(frame.f_lineno)
            #mod_func_line = '%s.%s:%s' % (mod, func, linen)
        else:
            stack = traceback.extract_stack()
            target_frame = None
            for frame in stack:
                # __name__ is, e.g., 'retrosoft.logging2'
                pathname = __name__.replace('.', os.path.sep) + '.py'
                if frame[0].endswith(pathname):
                    break
                target_frame = frame
            if target_frame is not None:
                mod = os.path.splitext(os.path.basename(target_frame[0]))[0]
                func = target_frame[2]
                linen = target_frame[1]
            # else, MAYBE: complain?
        #
        # HACK!!
        try:
            record.module = mod
            record.funcName = func
            record.lineno = linen
        except NameError:
            pass

        # Fix problem is message is unicode:
        #     File "/usr/lib/python2.7/logging/__init__.py", line 467, in format
        #       s = self._fmt % record.__dict__
        #   UnicodeDecodeError: 'ascii' codec can't decode byte 0xe2 in position 35: ordinal not in range(128)
        record.msg = str(record.msg)

        msg = fmt.format(record)

        if (line_len_log is None) or (msg.find('\n') != -1):
            verbatim = True
        else:
            verbatim = False
        #msg = msg % (('\n' if verbatim else ''),)
        if verbatim:
            # FIXME: This is completely correct. The msg is printed verbatim --
            # including newlines -- but the first part of the message still
            # follows the date and names; ideally, there'd be a newline after the
            # date and names, but before the message. Well, not when line_len_log
            # is None, but when the message already has newlines.
            formatted = '%s' % msg.strip()
        else:
            first = True
            multi_line = []
            while len(msg) > 0:
                # BUG nnnn: Only split (insert newlines) on whitespace, otherwise
                # if you are searching a trace your keyword may miss a hit.
                if not first:
                    snip = msg_continuation_prefix
                    snip += msg[0:line_len_msg]
                    msg = msg[line_len_msg:]
                else:
                    snip = msg[0:line_len_log]
                    msg = msg[line_len_log:]
                    first = False
                # FIXME: Newlines mess up formatting. If there's a newline in snip,
                #        you should back up to the newline and put the remainder   
                #        back in msg.
                snip += '\n'
                multi_line.append(snip)
            multi_line[-1] = multi_line[-1].strip('\n')
            formatted = ''.join(multi_line)

        return formatted

# *** 

logging_inited = False
logging_handlers = []
root_logger = None

def init_logging(
    log_level=logging.INFO, 
    log_fname=None, 
    log_frmat=None, 
    log_dfmat=None,
    log_to_file=False,
    log_to_console=False,
    log_to_stderr=False,
    log_to_wx=False,
    log_frmat_len=0,
    #log_frmat_postfix='#',
    log_frmat_postfix='| ',
    log_line_len=None,
    add_thread_id=False,
    show_logger_name=False,
    show_mod_func_line=False,
):
    global logging_inited
    if not logging_inited:
        init_logging_impl(
            log_level,
            log_fname,
            log_frmat,
            log_dfmat,
            log_to_file,
            log_to_console,
            log_to_stderr,
            log_to_wx,
            log_frmat_len,
            log_frmat_postfix,
            log_line_len,
            add_thread_id,
            show_logger_name,
            show_mod_func_line,
        )
        logging_inited = True
    # else, MAYBE: complain? warn-tell user?

def init_logging_impl(
    log_level,
    log_fname,
    log_frmat,
    log_dfmat,
    log_to_file,
    log_to_console,
    log_to_stderr,
    log_to_wx,
    log_frmat_len,
    log_frmat_postfix,
    log_line_len,
    add_thread_id,
    show_logger_name,
    show_mod_func_line,
):
    global include_thread_id
    global show_logger_name_
    global show_mod_func_line_

    config_line_format(
        log_frmat_len,
        log_frmat_postfix,
        log_line_len, 
        add_thread_id,
    )

    if (not show_logger_name) and (not show_mod_func_line):
        show_mod_func_line = True
    show_logger_name_ = show_logger_name
    show_mod_func_line_ = show_mod_func_line

    if not log_frmat:
        # See class Formatter in /usr/lib/python2.7/logging/__init__.py for options.
        #
        # NOTE: Skipping:
        #
        #   %(asctime)s -- Textual time when the LogRecord was created
        #                   See: log_dfmat (next!)
        #   %(created)s -- time.time() when LogRecord was created
        #   %(msecs)s   -- silly. just the msec. portion of %(created)s
        #   %(relativeCreated)s -- since start of logger;
        #                           could be interesting for niche applications
        #
        #   %(module)s   --   We cannot use Formatter's special variables to
        #   %(funcName)s --    show the fcn. name and line, e.g.,
        #   %(lineno)s   --     %(module)s.%(funcName)s:%(lineno)s
        #                --    because that's us! E.g.,
        #                --     logging2.notice:199
        # so we'll override log() and mess around there.
        #
        log_frmat = (
            #'%%(asctime)s %%(levelname)-4s %s%s%s %%(message)s'
            '%%(levelname)-4s|%%(asctime)s|%s%s%s%%(message)s'
            % (
                '%(name)-11s ' if show_logger_name_ else '',
                #'%(name)-11s|' if show_logger_name_ else '',
                #'${mod_func_line} ' if show_mod_func_line_ else '',
                #'%(module)s.%(funcName)s:%(lineno)s ' if show_mod_func_line_ else '',
                '%(module)s.%(funcName)s:%(lineno)s' if show_mod_func_line_ else '',
                log_frmat_postfix,
            )
        )

# FIXME: UNTESTED:
    if include_thread_id:
      # FIXME: 2016-06-27: this code is Untested.
      # FIXME: See My_Logger._log, which maybe doesn't need to use threading.
      log_frmat = '%%(thread)8d %s' % (log_frmat,)

    if not log_dfmat:
        # See strftime() for the meaning of these directives.
        # Too loquacious:
        #    log_dfmat = '%a, %d %b %Y %H:%M:%S'
        #    E.g., "Mon, 27 Jun 2016 20:39:21"
        log_dfmat = '%Y-%b-%d|%a|%H:%M:%S'

    #logging.basicConfig(
    #   level=log_level,
    #   filename=log_fname,
    #   format=log_frmat,
    #   datefmt=log_dfmat)

    formatter = logging.Formatter(log_frmat, log_dfmat)

    logging.setLoggerClass(My_Logger)

    global root_logger
    root_logger = logging.getLogger('')

    root_logger.setLevel(log_level)

    # SYNC_ME: Log levels.
    logging.addLevelName(        FATAL,     'FATL') # 186
    logging.addLevelName(logging.CRITICAL,  'CRIT') # 50
    #logging.addLevelName(logging.FATAL,     'CRIT') # 50 [*aliases CRITICAL]
    logging.addLevelName(logging.ERROR,     'ERRR') # 40
    logging.addLevelName(logging.WARNING,   'WARN') # 30
    logging.addLevelName(        NOTICE,    'NTCE') # 25
    logging.addLevelName(logging.INFO,      'INFO') # 20
    logging.addLevelName(        TRACE,     'TRCE') # 15
    logging.addLevelName(logging.DEBUG,     'DEBG') # 10
    logging.addLevelName(        VERBOSE1,  'VRB1') # 09
    logging.addLevelName(        VERBOSE2,  'VRB2') # 08
    logging.addLevelName(        VERBOSE3,  'VRB3') # 07
    logging.addLevelName(        VERBOSE4,  'VRB4') # 06
    logging.addLevelName(        VERBOSE5,  'VRB5') # 05
    logging.addLevelName(        VERBOSE,   'VRBS') # 05

    global logging_handlers
    if (True
        and not log_to_file
        and not log_to_console
        and not log_to_stderr
        and not log_to_wx
    ):
      log_to_console = True
    if log_to_file:
        assert(log_fname)
        logging_handlers.append(My_FileHandler(log_fname))
    if log_to_console:
        logging_handlers.append(My_StreamHandler())
    #if log_to_stdout:
    #    # Should be same as not specifying stream.
    #    logging_handlers.append(My_StreamHandler(sys.stdout))
    if log_to_stderr:
        logging_handlers.append(My_StreamHandler(sys.stderr))
    if log_to_wx:
        logging_handlers.append(My_wxPythonHandler())
    for handler in logging_handlers:
        handler.setLevel(log_level)
        handler.setFormatter(formatter)
        root_logger.addHandler(handler)

def setLevel(log_level):
    global root_logger
    root_logger.setLevel(log_level)
    global logging_handlers
    for handler in logging_handlers:
        handler.setLevel(level=log_level)

# ***

# SYNC_ME: Log levels.

# NOTE: The unnamed '' logger is the root logger, not My_Logger. So,
#            logging.getLogger('%')
#         and not
#            logging.getLogger('')

def critical(*args, **kwargs):
    logging.getLogger('%').critical(*args, **kwargs)

def fatal(*args, **kwargs):
    logging.getLogger('%').fatal(*args, **kwargs)

def error(*args, **kwargs):
    logging.getLogger('%').error(*args, **kwargs)

def warning(*args, **kwargs):
    logging.getLogger('%').warning(*args, **kwargs)

def warn(*args, **kwargs):
    logging.getLogger('%').warn(*args, **kwargs)

def notice(*args, **kwargs):
    logging.getLogger('%').notice(*args, **kwargs)

def log(*args, **kwargs):
    logging.getLogger('%').info(*args, **kwargs)

def info(*args, **kwargs):
    logging.getLogger('%').info(*args, **kwargs)

def trace(*args, **kwargs):
    logging.getLogger('%').trace(*args, **kwargs)

def debug(*args, **kwargs):
    logging.getLogger('%').debug(*args, **kwargs)

def verbose1(*args, **kwargs):
    logging.getLogger('%').verbose1(*args, **kwargs)

def verbose2(*args, **kwargs):
    logging.getLogger('%').verbose2(*args, **kwargs)

def verbose3(*args, **kwargs):
    logging.getLogger('%').verbose3(*args, **kwargs)

def verbose4(*args, **kwargs):
    logging.getLogger('%').verbose4(*args, **kwargs)

def verbose5(*args, **kwargs):
    logging.getLogger('%').verbose5(*args, **kwargs)

def verbose(*args, **kwargs):
    logging.getLogger('%').verbose(*args, **kwargs)

# ***

# A soft assert complains about non-exception-worthy unexpected states.
# DEV-TIPs: Enable breakpoints easily with assert_soft(False) by setting
#           ON_ASSERT_TRACE=True environment variable.
ON_ASSERT_TRACE = False
#ON_ASSERT_TRACE = True
def assert_soft(condition, *args, **kwargs):
    # MAYBE: There's a way to print out the source code for a failed condition
    # and also the value(s) that were used, but [lb] doesn't know it and I don't
    # want to spend time searching. See py.test's asserts for an example.
    # MAYBE: Use logcheck and email the developers when this happens.
    if not condition:
        if not args:
            kwargs.setdefault('msg', 'Assertion failed.')
        fatal(*args, **kwargs)
        do_break = False
        if ON_ASSERT_TRACE:
            do_break = True
        else:
            try:
                do_break = os.environ['ON_ASSERT_TRACE']
            except KeyError:
                pass
        if do_break:
            if threading.current_thread().name == 'MainThread':
                import pdb; pdb.set_trace()
            else:
                import pydevd; pydevd.settrace()

# *** 

# FIXME: Check that logging is inited in all the calls above?
#        I.e., so user can start using module without calling init_logging?
#        Here's my old comment:
# To initialize the logger when this module is loaded, uncomment the following:
#  init_logging()
# Note: Usually, you'll deliberately call init_logging from your own code
#       so you can set the logfile, console width, and default log level.

if __name__ == '__main__':
    pass

