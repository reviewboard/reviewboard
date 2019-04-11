"""Management command for resetting GitHub auth tokens."""

from __future__ import unicode_literals

import getpass

from django.utils.six.moves import input
from django.utils.translation import ugettext as _
from djblets.util.compat.django.core.management.base import BaseCommand

from reviewboard.hostingsvcs.errors import (AuthorizationError,
                                            TwoFactorAuthCodeRequiredError)
from reviewboard.hostingsvcs.models import HostingServiceAccount


class Command(BaseCommand):
    """Management command for resetting GitHub auth tokens."""

    help = _('Resets associated GitHub tokens.')

    def add_arguments(self, parser):
        """Add arguments to the command.

        Args:
            parser (argparse.ArgumentParser):
                The argument parser for the command.
        """
        parser.add_argument(
            'usernames',
            metavar='USERNAME',
            nargs='*',
            help=_('Specific GitHub account users to reset. If not '
                   'provided, all users will be reset.'))

        parser.add_argument(
            '--yes',
            action='store_true',
            default=False,
            dest='force_yes',
            help=_('Answer yes to all questions'))
        parser.add_argument(
            '--local-sites',
            action='store',
            dest='local_sites',
            help=_('Comma-separated list of Local Sites to filter by'))

    def handle(self, *usernames, **options):
        """Handle the command.

        Args:
            *usernames (tuple):
                A list of usernames containing tokens to reset.

            **options (dict, unused):
                Options parsed on the command line. For this command, no
                options are available.

        Raises:
            django.core.management.CommandError:
                There was an error with arguments or disabling the extension.
        """
        force_yes = options['force_yes']
        local_sites = options['local_sites']

        accounts = HostingServiceAccount.objects.filter(service_name='github')

        if usernames:
            accounts = accounts.filter(username__in=usernames)

        if local_sites:
            local_site_names = local_sites.split(',')

            if local_site_names:
                accounts = accounts.filter(
                    local_site__name__in=local_site_names)

        for account in accounts:
            if force_yes:
                reset = 'y'
            else:
                if account.local_site:
                    reset_msg = _('Reset token for %(site_name)s '
                                  '(%(username)s) [Y/n] ') % {
                        'site_name': account.local_site.name,
                        'username': account.username,
                    }
                else:
                    reset_msg = _('Reset token for %s [Y/n] ') % (
                        account.username)

                reset = input(reset_msg)

            if reset != 'n':
                self._reset_token(account)

    def _reset_token(self, account):
        """Reset the token for an account.

        Args:
            account (reviewboard.hostingsvcs.tests.HostingServiceAccount):
                The account containing a token to reset.
        """
        service = account.service
        password = None
        auth_token = None

        while True:
            if (not password and
                service.get_reset_auth_token_requires_password()):
                password = getpass.getpass(_('Password for %s: ')
                                           % account.username)
                auth_token = None

            try:
                service.reset_auth_token(password, auth_token)

                self.stdout.write(_('Successfully reset token for %s\n')
                                  % account.username)
                break
            except TwoFactorAuthCodeRequiredError:
                auth_token = input('Enter your two-factor auth token: ')
            except AuthorizationError as e:
                self.stderr.write('%s\n' % e)
                password = None
            except Exception as e:
                self.stderr.write(_('Unexpected error: %s\n') % e)
                raise
