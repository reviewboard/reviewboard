"""Management command to clean up orphaned data.

Version Added:
    7.0
"""

from __future__ import annotations

import gc
import sys
from typing import Iterator, Optional, TYPE_CHECKING

import tqdm
from django.core.management.base import BaseCommand
from django.db import reset_queries
from django.utils.translation import (
    gettext as _,
    ngettext as N_)

from reviewboard.attachments.models import (FileAttachment,
                                            FileAttachmentHistory)
from reviewboard.changedescs.models import ChangeDescription
from reviewboard.diffviewer.models import DiffSet, DiffSetHistory
from reviewboard.reviews.models import Screenshot

if TYPE_CHECKING:
    from argparse import ArgumentParser

    from django.db.models import Model, QuerySet
    from typing_extensions import TypeVar

    _ModelT = TypeVar('_ModelT', bound=Model)


class Command(BaseCommand):
    """Management command to clean up orphaned data.

    Version Added:
        7.0
    """

    help = _('Deletes orphaned file attachments')

    def add_arguments(
        self,
        parser: ArgumentParser,
    ) -> None:
        """Add arguments to the command.

        Args:
            parser (argparse.ArgumentParser):
                The argument parser for the command.
        """
        parser.add_argument(
            '--show-counts-only',
            action='store_true',
            dest='show_counts',
            default=False,
            help=_('Show the number of orphaned items expected to be '
                   'deleted, but do not actually delete any data.'))
        parser.add_argument(
            '--no-progress',
            action='store_false',
            dest='show_progress',
            default=True,
            help=_("Don't show progress information or totals while "
                   "performing the clean up."))

    def handle(
        self,
        *,
        show_counts: bool = False,
        show_progress: bool = True,
        **options,
    ) -> None:
        """Handle the command.

        Args:
            show_counts (bool):
                Whether to only show the counts of objects.

            show_progress (bool):
                Whether to show progress information.

            **options (dict, unused):
                Any additional parsed command-line options.

        Raises:
            django.core.management.CommandError:
                An error occurred while cleaning up file attachments.
        """
        attachments = FileAttachment.objects.filter(
            user=None,
            drafts=None,
            inactive_drafts=None,
            review_request=None,
            inactive_review_request=None)

        attachment_histories = FileAttachmentHistory.objects.filter(
            review_request=None)

        screenshots = Screenshot.objects.filter(
            drafts=None,
            inactive_drafts=None,
            review_request=None,
            inactive_review_request=None)

        changedescs = ChangeDescription.objects.filter(
            review_request=None,
            review_request_draft=None)

        diffset_histories = DiffSetHistory.objects.filter(
            review_request=None)

        diffsets = DiffSet.objects.filter(
            history_id=None,
            review_request_draft=None)

        n_attachments = attachments.count()
        n_attachment_histories = attachment_histories.count()
        n_screenshots = screenshots.count()
        n_changedescs = changedescs.count()
        n_diffset_histories = diffset_histories.count()
        n_diffsets = diffsets.count()

        if (n_attachments == 0 and
            n_attachment_histories == 0 and
            n_screenshots == 0 and
            n_changedescs == 0 and
            n_diffset_histories == 0 and
            n_diffsets == 0):
            self.stdout.write(_('No orphaned data found.\n'))
            return

        if show_counts:
            self.stdout.write(
                N_('%d FileAttachment object\n',
                   '%d FileAttachment objects\n',
                   n_attachments)
                % n_attachments)
            self.stdout.write(
                N_('%d FileAttachmentHistory object\n',
                   '%d FileAttachmentHistory object\n',
                   n_attachment_histories)
                % n_attachment_histories)
            self.stdout.write(
                N_('%d Screenshot object\n',
                   '%d Screenshot objects\n',
                   n_screenshots)
                % n_screenshots)
            self.stdout.write(
                N_('%d ChangeDescription object\n',
                   '%d ChangeDescription objects\n',
                   n_changedescs)
                % n_changedescs)
            self.stdout.write(
                N_('%d DiffSetHistory object\n',
                   '%d DiffSetHistory objects\n',
                   n_diffset_histories)
                % n_diffset_histories)
            self.stdout.write(
                N_('%d DiffSet object\n',
                   '%d DiffSet objects\n',
                   n_diffsets)
                % n_diffsets)
            return

        if show_progress:
            self.stdout.write(_('Deleting orphaned objects:\n'))

        # We explicitly delete file attachments before file attachment
        # histories. Deleting the histories would cause the file attachments to
        # get deleted in a cascade, which might theoretically put more load on
        # the DB than we want. This does mean we end up with some extra queries
        # to update the histories as file attachments get deleted, but that's
        # better than potentially timing out on a giant cascade.

        self._delete_in_batches(
            queryset=attachments,
            total_objects=n_attachments,
            show_progress=show_progress,
            description=_('FileAttachment'))

        self._delete_in_batches(
            queryset=attachment_histories,
            total_objects=n_attachment_histories,
            show_progress=show_progress,
            description=_('FileAttachmentHistory'))

        self._delete_in_batches(
            queryset=screenshots,
            total_objects=n_screenshots,
            show_progress=show_progress,
            description=_('Screenshot'))

        self._delete_in_batches(
            queryset=changedescs,
            total_objects=n_changedescs,
            show_progress=show_progress,
            description=_('ChangeDescription'))

        self._delete_in_batches(
            queryset=diffset_histories,
            total_objects=n_diffset_histories,
            show_progress=show_progress,
            description=_('DiffSetHistory'))

        self._delete_in_batches(
            queryset=diffsets,
            total_objects=n_diffsets,
            show_progress=show_progress,
            description=_('DiffSet'))

        if show_progress:
            self.stdout.write(_('Done.\n'))

    def _delete_in_batches(
        self,
        *,
        queryset: QuerySet[_ModelT],
        total_objects: int,
        show_progress: bool,
        description: str,
    ) -> None:
        """Delete the given objects in batches.

        Args:
            queryset (django.db.models.QuerySet):
                The queryset of objects to delete.

            total_objects (int):
                The total number of objects in the queryset.

            show_progress (bool):
                Whether to show progress.

            description (str):
                The description to show, when showing progress.
        """
        if total_objects == 0:
            # Skip the output entirely.
            return

        # If we're operating with a real stdout, we want to let tqdm connect
        # directly to it, rather than using django's OutputWrapper.
        if self.stdout._out is sys.stdout:
            file = None
        else:
            file = self.stdout

        t = tqdm.tqdm(
            desc=description,
            disable=not show_progress,
            file=file,
            total=total_objects,
            bar_format='{desc} {bar} [{n_fmt}/{total_fmt}]',
            ncols=80)

        for batch in self._iter_batches(queryset, total_objects=total_objects):
            n = batch.count()

            batch.delete()

            t.update(n)

        t.close()

    def _iter_batches(
        self,
        queryset: QuerySet[_ModelT],
        *,
        total_objects: Optional[int] = None,
        batch_size: int = 50,
    ) -> Iterator[QuerySet[_ModelT]]:
        """Iterate through items in a queryset, yielding batches.

        This will gather up to a specified number of items from a queryset
        at a time, process them into batches of a specified size, and yield
        them.

        After each set of objects is fetched from the database, garbage
        collection will be forced and stored queries reset, in order to
        reduce memory usage.

        Args:
            queryset (django.db.models.query.QuerySet):
                The queryset to execute for fetching objects.

            total_objects (int, optional):
                The total number of objects. If this is ``None``, it will be
                determined from ``queryset.count()``.

            batch_size (int, optional):
                The maximum number of objects to yield per batch.

        Yields:
            django.db.models.query.QuerySet:
            A QuerySet containing a batch of items to process. This will never
            be larger than ``batch_size``.
        """
        if total_objects is None:
            total_objects = queryset.count()

        object_pks = list(queryset.values_list('pk', flat=True))

        for i in range(0, total_objects, batch_size):
            batch_pks = object_pks[i:i + batch_size]
            yield queryset.model.objects.filter(pk__in=batch_pks)

            # Do all we can to limit the memory usage by resetting any
            # stored queries (if DEBUG is True), and force garbage
            # collection of anything we may have from processing an object.
            reset_queries()
            gc.collect()
