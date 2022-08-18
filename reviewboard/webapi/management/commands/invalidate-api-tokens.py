"""Management command to invalidate API tokens.

Version Added:
    5.0
"""

import sys

from django.contrib.auth.models import User
from django.core.management.base import BaseCommand, CommandError
from django.utils.translation import gettext_lazy as _

from reviewboard.cmdline.utils.console import get_console
from reviewboard.webapi.models import WebAPIToken


class Command(BaseCommand):
    """Management command to invalidate API tokens.

    Version Added:
        5.0
    """

    help = _('Invalidate API tokens for users.')

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
            help=_('The usernames of users whose tokens will be invalidated.'))

        parser.add_argument(
            '-r',
            '--reason',
            default='',
            help=_('A message indicating why the tokens are no longer valid.'))

        parser.add_argument(
            '-a',
            '--all',
            action='store_true',
            default=False,
            help=_('Invalidate tokens for all users.'))

    def handle(self, *args, **options):
        """Handle the command.

        Args:
            *args (tuple, unused):
                Arguments parsed on the command line.

            **options (dict):
                Options parsed on the command line.

        Raises:
            django.core.management.CommandError:
                There was an error with the supplied arguments.
        """
        console = get_console()
        invalid_reason = options.get('reason')
        invalidate_all = options.get('all')
        usernames = set(options.get('usernames'))

        if usernames and invalidate_all:
            raise CommandError(
                _('--all cannot be used when supplying usernames.'))
        elif invalidate_all:
            invalidate = console.prompt_input(
                _('Are you sure you want to invalidate tokens for all users?'),
                prompt_type=console.PROMPT_TYPE_YES_NO)

            if not invalidate:
                self.stdout.write(_('Cancelling token invalidation.'))
                sys.exit(1)

            WebAPIToken.objects.invalidate_tokens(
                users=None,
                invalid_reason=invalid_reason)

            self.stdout.write(_('Invalidated tokens for all users.'))
        elif usernames:
            try:
                found_user_ids, found_usernames = zip(
                    *User.objects
                    .filter(username__in=usernames)
                    .values_list('pk', 'username')
                )
            except ValueError:
                raise CommandError(
                    _('Cancelling token invalidation because the following '
                      'users do not exist: %s.')
                    % ', '.join(sorted(usernames))
                )

            found_usernames = set(found_usernames)

            if usernames != found_usernames:
                raise CommandError(
                    _('Cancelling token invalidation because the following '
                      'users do not exist: %s.')
                    % ', '.join(sorted(usernames - found_usernames))
                )

            WebAPIToken.objects.invalidate_tokens(
                users=found_user_ids,
                invalid_reason=invalid_reason)

            self.stdout.write(_('Invalidated tokens for users: %s.')
                              % ', '.join(sorted(usernames)))
        else:
            raise CommandError(
                _('Either --all must be set or at least one username '
                  'must be supplied.'))
