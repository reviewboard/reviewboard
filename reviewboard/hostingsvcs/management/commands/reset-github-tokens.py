from __future__ import unicode_literals

import getpass
from optparse import make_option

from django.core.management.base import BaseCommand
from django.utils.six.moves import input
from django.utils.translation import ugettext_lazy as _

from reviewboard.hostingsvcs.errors import (AuthorizationError,
                                            TwoFactorAuthCodeRequiredError)
from reviewboard.hostingsvcs.models import HostingServiceAccount


class Command(BaseCommand):
    help = _('Resets associated GitHub tokens')

    option_list = BaseCommand.option_list + (
        make_option('--yes',
                    action='store_true',
                    default=False,
                    dest='force_yes',
                    help=_('Answer yes to all questions')),
        make_option('--local-sites',
                    action='store',
                    dest='local_sites',
                    help=_('Comma-separated list of Local Sites to '
                           'filter by')),
    )

    def handle(self, *usernames, **options):
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
                break
