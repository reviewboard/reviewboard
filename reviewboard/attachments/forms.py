from __future__ import unicode_literals

from uuid import uuid4
import os
import subprocess

from django import forms
from django.utils import timezone
from djblets.util.filesystem import is_exe_in_path

from reviewboard.attachments.models import FileAttachment
from reviewboard.reviews.models import (ReviewRequestDraft,
                                        FileAttachmentComment)


class UploadFileForm(forms.Form):
    """A form that handles uploading of new files.

    A file takes a path argument and optionally a caption.
    """
    DEFAULT_MIMETYPE = 'application/octet-stream'
    READ_BUF_SIZE = 1024

    caption = forms.CharField(required=False)
    path = forms.FileField(required=True)

    def create(self, file, review_request, filediff=None):
        caption = self.cleaned_data['caption'] or file.name

        # There are several things that can go wrong with browser-provided
        # mimetypes. In one case (bug 3427), Firefox on Linux Mint was
        # providing a mimetype that looked like 'text/text/application/pdf',
        # which is unparseable. IE also has a habit of setting any unknown file
        # type to 'application/octet-stream', rather than just choosing not to
        # provide a mimetype. In the case where what we get from the browser
        # is obviously wrong, try to guess.
        if (file.content_type and
            len(file.content_type.split('/')) == 2 and
            file.content_type != 'application/octet-stream'):
            mimetype = file.content_type
        else:
            mimetype = self._guess_mimetype(file)

        filename = '%s__%s' % (uuid4(), file.name)

        attachment_kwargs = {
            'caption': '',
            'draft_caption': caption,
            'orig_filename': os.path.basename(file.name),
            'mimetype': mimetype,
        }

        if filediff:
            file_attachment = FileAttachment.objects.create_from_filediff(
                filediff,
                save=False,
                **attachment_kwargs)
        else:
            file_attachment = FileAttachment(**attachment_kwargs)

        file_attachment.file.save(filename, file, save=True)

        draft = ReviewRequestDraft.create(review_request)
        draft.file_attachments.add(file_attachment)
        draft.save()

        return file_attachment

    def _guess_mimetype(self, file):
        """Guess the mimetype of an uploaded file.

        Uploaded files don't necessarily have valid mimetypes provided,
        so attempt to guess them when they're blank.

        This only works if `file` is in the path. If it's not, or guessing
        fails, we fall back to a mimetype of application/octet-stream.
        """
        if not is_exe_in_path('file'):
            return self.DEFAULT_MIMETYPE

        # The browser didn't know what this was, so we'll need to do
        # some guess work. If we have 'file' available, use that to
        # figure it out.
        p = subprocess.Popen(['file', '--mime-type', '-b', '-'],
                             stdout=subprocess.PIPE,
                             stderr=subprocess.PIPE,
                             stdin=subprocess.PIPE)

        # Write the content from the file until file has enough data to
        # make a determination.
        for chunk in file.chunks():
            try:
                p.stdin.write(chunk)
            except IOError:
                # file closed, so we hopefully have an answer.
                break

        p.stdin.close()
        ret = p.wait()

        if ret == 0:
            mimetype = p.stdout.read().strip()
        else:
            mimetype = None

        # Reset the read position so we can properly save this.
        file.seek(0)

        return mimetype or self.DEFAULT_MIMETYPE


class CommentFileForm(forms.Form):
    """A form that handles commenting on a file."""
    review = forms.CharField(widget=forms.Textarea(attrs={
        'rows': '8',
        'cols': '70'
    }))

    def create(self, file_attachment, review_request):
        comment = FileAttachmentComment(text=self.cleaned_data['review'],
                                        file_attachment=file_attachment)

        comment.timestamp = timezone.now()
        comment.save(save=True)

        draft = ReviewRequestDraft.create(review_request)
        draft.file_attachment_comments.add(comment)
        draft.save()

        return comment
