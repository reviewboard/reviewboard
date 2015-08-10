#
# __init__.py -- Basic utilities for the log app
#
# Copyright (c) 2008-2009  Christian Hammond
# Copyright (c) 2008-2009  David Trowbridge
#
# Permission is hereby granted, free of charge, to any person obtaining
# a copy of this software and associated documentation files (the
# "Software"), to deal in the Software without restriction, including
# without limitation the rights to use, copy, modify, merge, publish,
# distribute, sublicense, and/or sell copies of the Software, and to
# permit persons to whom the Software is furnished to do so, subject to
# the following conditions:
#
# The above copyright notice and this permission notice shall be included
# in all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
# EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
# MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT.
# IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY
# CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT,
# TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE
# SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
#

from __future__ import unicode_literals

from datetime import datetime
import logging
import os
import sys

from django.conf import settings


_logging_setup = False
_profile_log = None

DEFAULT_LOG_LEVEL = "DEBUG"
DEFAULT_LINE_FORMAT = \
    "%(asctime)s - %(levelname)s - %(request_info)s - %(message)s"
DEFAULT_REQUEST_FORMAT = '%(user)s - %(path)s'


class TimedLogInfo(object):
    """
    A utility class created by ``log_timed`` that handles the timed logging
    functionality and provides a way to end the timed logging operation.
    """
    def __init__(self, message, warning_at, critical_at, default_level,
                 log_beginning, request):
        self.message = message
        self.warning_at = warning_at
        self.critical_at = critical_at
        self.default_level = default_level
        self.start_time = datetime.utcnow()
        self.request = request

        if log_beginning:
            logging.log(self.default_level, "Begin: %s" % self.message,
                        request=self.request)

    def done(self):
        """
        Stops the timed logging operation. The resulting time of the
        operation will be written to the log file. The log level depends
        on how long the operation takes.
        """
        delta = datetime.utcnow() - self.start_time
        level = self.default_level

        if delta.seconds >= self.critical_at:
            level = logging.CRITICAL
        elif delta.seconds >= self.warning_at:
            level = logging.WARNING

        logging.log(self.default_level, "End: %s" % self.message,
                    request=self.request)
        logging.log(level, '%s took %d.%06d seconds' % (self.message,
                                                        delta.seconds,
                                                        delta.microseconds),
                    request=self.request)


class RequestLogFormatter(logging.Formatter):
    def __init__(self, request_fmt, *args, **kwargs):
        logging.Formatter.__init__(self, *args, **kwargs)
        self.request_fmt = request_fmt

    def format(self, record):
        record.request_info = self.format_request(
            getattr(record, 'request', None))

        return logging.Formatter.format(self, record)

    def format_request(self, request):
        if request:
            return self.request_fmt % request.__dict__
        else:
            return ''


def _wrap_logger(logger):
    """Wraps a logger, providing an extra 'request' argument."""
    def _log_with_request(self, *args, **kwargs):
        extra = kwargs.pop('extra', {})
        request = kwargs.pop('request', None)

        if request:
            extra['request'] = request

        kwargs['extra'] = extra

        old_log(self, *args, **kwargs)

    if not hasattr(logger, '_djblets_wrapped'):
        # This should be a good assumption on all supported versions of Python.
        assert hasattr(logger, '_log')
        old_log = logger._log
        logger._log = _log_with_request
        logger._djblets_wrapped = True


# Regardless of whether we have logging enabled, we'll want this to be
# set so that logging calls don't fail when passing request.
root = logging.getLogger('')
_wrap_logger(root)


def init_logging():
    """
    Sets up the main loggers, if they haven't already been set up.
    """
    global _logging_setup

    if _logging_setup:
        return

    enabled = getattr(settings, 'LOGGING_ENABLED', False)
    log_directory = getattr(settings, 'LOGGING_DIRECTORY', None)
    log_name = getattr(settings, 'LOGGING_NAME', None)

    if not enabled or not log_directory or not log_name:
        return

    log_level_name = getattr(settings, 'LOGGING_LEVEL',
                             DEFAULT_LOG_LEVEL)
    log_level = logging.getLevelName(log_level_name)
    request_format_str = getattr(settings, 'LOGGING_REQUEST_FORMAT',
                                 DEFAULT_REQUEST_FORMAT)
    format_str = getattr(settings, 'LOGGING_LINE_FORMAT',
                         DEFAULT_LINE_FORMAT)

    log_path = os.path.join(log_directory, log_name + ".log")

    formatter = RequestLogFormatter(request_format_str, format_str)
    logging_to_stderr = False

    if log_path:
        try:
            if sys.platform == 'win32':
                handler = logging.FileHandler(log_path)
            else:
                handler = logging.handlers.WatchedFileHandler(log_path)

            logging_to_stderr = False
        except IOError:
            handler = logging.StreamHandler()
            logging_to_stderr = True

        handler.setLevel(log_level)
        handler.setFormatter(formatter)

        root.addHandler(handler)
        root.setLevel(log_level)

    if logging_to_stderr:
        logging.warning("Could not open logfile %s. Logging to stderr",
                        log_path)

    if settings.DEBUG and not logging_to_stderr:
        # In DEBUG mode, log to the console as well.
        console_log = logging.StreamHandler()
        console_log.setLevel(log_level)
        console_log.setFormatter(formatter)
        root.addHandler(console_log)

        logging.debug("Logging to %s with a minimum level of %s",
                      log_path, log_level_name)

    _logging_setup = True


def init_profile_logger():
    """
    Sets up the profiling logger, if it hasn't already been set up.
    """
    global _profile_log

    enabled = getattr(settings, 'LOGGING_ENABLED', False)
    log_directory = getattr(settings, 'LOGGING_DIRECTORY', None)
    log_name = getattr(settings, 'LOGGING_NAME', None)

    if (enabled and log_directory and log_name and not _profile_log and
        getattr(settings, "LOGGING_ALLOW_PROFILING", False)):

        filename = os.path.join(log_directory, log_name + ".prof")

        if sys.platform == 'win32':
            handler = logging.handlers.FileHandler(filename)
        else:
            handler = logging.handlers.WatchedFileHandler(filename)

        handler.setLevel(logging.INFO)
        handler.setFormatter(logging.Formatter("%(asctime)s %(message)s"))

        _profile_log = logging.getLogger("profile")
        _profile_log.addHandler(handler)


def restart_logging():
    """
    Restarts the logging. The next page view will set up the loggers
    based on any new settings.
    """
    global _logging_setup

    logging.log(logging.INFO, "Reloading logging settings")

    for logger_id in ('profile', ''):
        logger = logging.getLogger(logger_id)

        while logger.handlers:
            handler = logger.handlers[0]
            handler.flush()
            logger.removeHandler(handler)

    _logging_setup = False

    init_logging()


def log_timed(message, warning_at=5, critical_at=15,
              log_beginning=True, default_level=logging.DEBUG,
              request=None):
    """
    Times an operation, displaying a log message before and after the
    operation. The log level for the final log message containing the
    operation runtime will be based on the runtime, the ``warning_at`` and
    the ``critical_at`` parameters.
    """
    return TimedLogInfo(message, warning_at, critical_at, default_level,
                        log_beginning, request)
