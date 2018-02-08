"""RawFileDiffData model definition."""

from __future__ import unicode_literals

import bz2
import logging

from django.db import models
from django.utils.translation import ugettext_lazy as _
from djblets.db.fields import JSONField

from reviewboard.diffviewer.errors import DiffParserError
from reviewboard.diffviewer.managers import RawFileDiffDataManager


class RawFileDiffData(models.Model):
    """Stores raw diff data as binary content in the database.

    This is the class used in Review Board 2.5+ to store diff content.
    Unlike in previous versions, the content is not base64-encoded. Instead,
    it is stored either as bzip2-compressed data (if the resulting
    compressed data is smaller than the raw data), or as the raw data itself.
    """

    COMPRESSION_BZIP2 = 'B'

    COMPRESSION_CHOICES = (
        (COMPRESSION_BZIP2, _('BZip2-compressed')),
    )

    binary_hash = models.CharField(_("hash"), max_length=40, unique=True)
    binary = models.BinaryField()
    compression = models.CharField(max_length=1, choices=COMPRESSION_CHOICES,
                                   null=True, blank=True)
    extra_data = JSONField(null=True)

    objects = RawFileDiffDataManager()

    @property
    def content(self):
        """Return the content of the diff.

        The content will be uncompressed (if necessary) and returned as the
        raw set of bytes originally uploaded.
        """
        if self.compression == self.COMPRESSION_BZIP2:
            return bz2.decompress(self.binary)
        elif self.compression is None:
            return bytes(self.binary)
        else:
            raise NotImplementedError(
                'Unsupported compression method %s for RawFileDiffData %s'
                % (self.compression, self.pk))

    @property
    def insert_count(self):
        return self.extra_data.get('insert_count')

    @insert_count.setter
    def insert_count(self, value):
        self.extra_data['insert_count'] = value

    @property
    def delete_count(self):
        return self.extra_data.get('delete_count')

    @delete_count.setter
    def delete_count(self, value):
        self.extra_data['delete_count'] = value

    def recalculate_line_counts(self, tool):
        """Recalculates the insert_count and delete_count values.

        This will attempt to re-parse the stored diff and fetch the
        line counts through the parser.
        """
        logging.debug('Recalculating insert/delete line counts on '
                      'RawFileDiffData %s' % self.pk)

        try:
            files = tool.get_parser(self.content).parse()

            if len(files) != 1:
                raise DiffParserError(
                    'Got wrong number of files (%d)' % len(files))
        except DiffParserError as e:
            logging.error('Failed to correctly parse stored diff data in '
                          'RawFileDiffData ID %s when trying to get '
                          'insert/delete line counts: %s',
                          self.pk, e)
        else:
            file_info = files[0]
            self.insert_count = file_info.insert_count
            self.delete_count = file_info.delete_count

            if self.pk:
                self.save(update_fields=['extra_data'])

    class Meta:
        app_label = 'diffviewer'
        db_table = 'diffviewer_rawfilediffdata'
        verbose_name = _('Raw File Diff Data')
        verbose_name_plural = _('Raw File Diff Data Blobs')
