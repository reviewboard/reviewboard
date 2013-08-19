import logging

from django import template
from django.core.exceptions import MultipleObjectsReturned, ObjectDoesNotExist

from reviewboard.attachments.models import FileAttachment


register = template.Library()


@register.assignment_tag(takes_context=True)
def get_diff_file_attachment(context, filediff, use_modified=True):
    """Fetch the FileAttachment associated with a FileDiff.

    This will query for the FileAttachment based on the provided filediff,
    and set the retrieved diff file attachment to a variable whose name is
    provided as an argument to this tag.

    If 'use_modified' is True, the FileAttachment returned will be from the
    modified version of the new file. Otherwise, it's the original file that's
    being modified.

    If no matching FileAttachment is found or if there is more than one
    FileAttachment associated with one FileDiff, None is returned. An error
    is logged in the latter case.
    """
    if not filediff:
        return None

    try:
        return FileAttachment.objects.get_for_filediff(filediff, use_modified)
    except ObjectDoesNotExist:
        return None
    except MultipleObjectsReturned:
        # Only one FileAttachment should be associated with a FileDiff
        logging.error('More than one FileAttachments associated with '
                      'FileDiff %s',
                      filediff.pk,
                      exc_info=1)
        return None
