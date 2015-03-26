from __future__ import unicode_literals

import logging
import os

from django.conf import settings
from django.core.files.base import ContentFile
from django.core.files.storage import FileSystemStorage
from django.utils import six
from django.utils.six.moves.urllib.error import HTTPError
from django.utils.six.moves.urllib.request import urlopen
from django.utils.translation import ngettext
from django.utils.translation import ugettext_lazy as _

from reviewboard.admin.server import build_server_url


_security_checks = {}


class BaseSecurityCheck(object):
    """Base class for a security check."""

    name = None
    desc = None
    fix_info = None

    def setUp(self):
        """Set up the security check."""
        pass

    def execute(self):
        """Execute the security check.

        This must be implemented by subclasses.
        """
        raise NotImplementedError

    def tearDown(self):
        """Tear down the security check."""
        pass


class ExecutableCodeCheck(BaseSecurityCheck):
    """Check that uploaded files don't get executed.

    Web servers like to run code in files named things like .php or .shtml.
    This check makes sure that user-uploaded files do not get executed when
    loading them via their URL.
    """

    name = _("Checking that uploaded files won't be executed by the server")
    desc = _('A misconfiguration in the web server can cause files attached '
             'to review requests to be executed as code. The file types '
             'checked in this test are: .html, .htm, .shtml, .php, .php3, '
             '.php4, .php5, .phps, .asp, .pl, .py, .fcgi, .cgi, .phtml, '
             '.phtm, .pht, .jsp, .sh, and .rb.')
    fix_info = _('For instructions on how to fix this problem, please visit '
                 '<a href="http://support.beanbaginc.com/support/solutions/'
                 'articles/110173-securing-file-attachments">'
                 'http://support.beanbaginc.com/support/solutions/articles/'
                 '110173-securing-file-attachments</a>')

    def __init__(self):
        """Initialize the security check."""
        loc = os.path.join(settings.MEDIA_ROOT, 'uploaded', 'files')
        self.storage = FileSystemStorage(location=loc)
        self.directory = settings.MEDIA_URL + 'uploaded/files/'

        self.file_checks = [
            (
                ['.php', '.php3', '.php4', '.php5', '.phps', '.phtml',
                 '.phtm'],
                '<?php echo "Hello, World!"; ?>'
            ),
            (
                ['.pl', '.py'],
                'print "Hello, World!"'
            ),
            (
                ['.html', '.htm', '.shtml', '.pht'],
                ('<HTML>\n'
                 '<HEAD>\n'
                 '<TITLE>Hello, world!</TITLE>\n'
                 '</HEAD>\n'
                 '<BODY>\n'
                 '<H1>Hello, world!</H1>\n'
                 '<!--#echo var="LAST_MODIFIED" -->\n'
                 '<!--#exec cmd="echo HI!" -->\n'
                 '</BODY>\n'
                 '</HTML>')
            ),
            (
                ['.jsp'],
                '<%= new String("Hello!") %>'
            ),
            (
                ['.asp'],
                '<%="Hello World!"%>'
            ),
            (
                ['.fcgi', '.cgi', '.sh'],
                ('#!/bin/sh\n'
                 'echo "Hello World!"')
            ),
            (
                ['.rb'],
                'puts "Hello world!"'
            )
        ]

    def setUp(self):
        """Set up the security check.

        This will go through the various file extensions that we intend to
        check and create file attachments with the given content.
        """
        if self._using_default_storage():
            for i, file_check in enumerate(self.file_checks):
                extensions_list, content = file_check
                bad_extensions = []

                for ext in extensions_list:
                    try:
                        self.storage.save('exec_check' + ext,
                                          ContentFile(content))
                    except OSError:
                        # Some web server configurations prevent even saving
                        # files with certain extensions. In this case, things
                        # will definitely succeed.
                        bad_extensions.append(ext)

                # Filter out any extensions that we failed to save, because we
                # don't need to check that they downloaded properly.
                extensions_list = [ext for ext in extensions_list
                                   if ext not in bad_extensions]
                self.file_checks[i] = extensions_list, content

    def execute(self):
        """Execute the security check.

        This will download each file that was created in ``setUp`` and check
        that the content matches what we expect.
        """
        error_msg = ''
        ext_result = True
        final_result = True
        failed_exts = []

        if self._using_default_storage():
            for extensions_list, content in self.file_checks:
                for ext in extensions_list:
                    try:
                        ext_result = self.download_and_compare(
                            'exec_check' + ext)
                        if final_result and not ext_result:
                            final_result = False
                    except Exception as e:
                        return (False,
                                _('Uncaught exception during test: %s') % e)

                    if not ext_result:
                        failed_exts.append(ext)

        if not final_result:
            error_msg = _(
                ngettext(
                    'The web server incorrectly executed these file types: %s',
                    'The web server incorrectly executed this file type: %s',
                    len(failed_exts))
                % ', '.join(failed_exts))

        return final_result, error_msg

    def tearDown(self):
        """Tear down the security check.

        This will delete all of the files created in ``setUp``.
        """
        if self._using_default_storage():
            for extensions_list, content in self.file_checks:
                for ext in extensions_list:
                    self.storage.delete('exec_check' + ext)

    def download_and_compare(self, to_download):
        """Download a file and compare the resulting response to the file.

        This makes sure that when we fetch a file via its URL, the returned
        contents are identical to the file contents. This returns True if the
        file contents match, and False otherwise.
        """
        try:
            data = urlopen(build_server_url(self.directory,
                                            to_download)).read()
        except HTTPError as e:
            # An HTTP 403 is also an acceptable response
            if e.code == 403:
                return True
            else:
                raise e

        with self.storage.open(to_download, 'r') as f:
            return data == f.read()

    def _using_default_storage(self):
        """Return whether the server is using the built-in file storage."""
        return (settings.DEFAULT_FILE_STORAGE ==
                'django.core.files.storage.FileSystemStorage')


class AllowedHostsCheck(BaseSecurityCheck):
    """Check that the ALLOWED_HOSTS setting is configured.

    In order to prevent URL inejections, Django requires that ALLOWED_HOSTS be
    configured with a list of hostnames for which Review Board will answer.
    People upgrading from previous versions will have this set to a wildcard.
    """

    name = _('Checking ALLOWED_HOSTS setting')
    desc = _('ALLOWED_HOSTS is a list containing the host/domain names that '
             'Review Board will consider valid for this server to serve. '
             'This is a security measure to prevent an attacker from '
             'poisoning cache and password reset e-mails with links to '
             'malicious hosts by submitting requests with a fake HTTP Host '
             'header, which is possible even under many seemingly-safe web '
             'server configurations.')
    fix_info = _("To fix this, edit the settings_local.py in the site's conf "
                 "directory and add a line like this with your site's URL: "
                 "<pre>ALLOWED_HOSTS = ['example.com']</pre>")

    def execute(self):
        """Execute the security check.

        This checks the value of the ALLOWED_HOSTS setting to make sure that it
        contains one or more hostnames.
        """
        result = True
        error_msg = ''

        if len(settings.ALLOWED_HOSTS) < 1:
            result = False
            error_msg = _('ALLOWED_HOSTS is empty.')

        if '*' in settings.ALLOWED_HOSTS:
            result = False
            error_msg = _("ALLOWED_HOSTS contains '*', which means that the "
                          "server will respond to any host.")

        return result, error_msg


class SecurityCheckRunner(object):
    """This is a runner to execute the security checks defined above.

    In order for a check to be run in this runner it needs to be added
    to the _security_checks list.

    The information that comes back from a single check is the following:
    - name: User-friendly name used to describe the check.
    - desc: A more detailed description to provide information about the check.
    - result: True if the check passed, or False if it failed or there was
              an excetion during its execution.
    - error_msg: A description of what failed. This will be blank if the test
                 passes.
    - fix_info: Instructions containing what a user should do if a check fails.
    """

    def __init__(self):
        """Initialize the security check runner."""
        pass

    def run(self):
        """Run all security checks and return the results."""
        all_test_results = []
        checks = get_security_checks()

        for name, cls in six.iteritems(checks):
            check = cls()

            check.setUp()
            current_test_result, error_msg = check.execute()
            check.tearDown()

            all_test_results.append({
                'name': check.name,
                'desc': check.desc,
                'result': current_test_result,
                'error_msg': error_msg,
                'fix_info': check.fix_info,
            })

        return all_test_results


def _populate_security_checks():
    """Populate a list of existing security checks."""
    if not _security_checks:
        _security_checks['executable_check'] = ExecutableCodeCheck
        _security_checks['hosts_check'] = AllowedHostsCheck


def get_security_checks():
    """Return the list of security checks."""
    _populate_security_checks()

    return _security_checks


def register_security_check(name, cls):
    """Register a custom security check."""
    _populate_security_checks()

    if name in _security_checks:
        raise KeyError('"%s" is already a registered security check' % name)

    _security_checks[name] = cls


def unregister_security_check(name):
    """Unregister a previously registered security check."""
    _populate_security_checks()

    try:
        del _security_checks[name]
    except KeyError:
        logging.error('Failed to unregister unknown security check "%s"' %
                      name)
        raise KeyError('"%s" is not a registered security check' % name)
