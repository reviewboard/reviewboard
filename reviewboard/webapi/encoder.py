from __future__ import unicode_literals

from django.template.defaultfilters import timesince
from djblets.webapi.encoders import WebAPIEncoder

from reviewboard.diffviewer.models import FileDiff, DiffSet
from reviewboard.reviews.models import (ReviewRequest, Review, Group, Comment,
                                        ReviewRequestDraft, Screenshot,
                                        ScreenshotComment)
from reviewboard.scmtools.models import Repository


def status_to_string(status):
    if status == "P":
        return "pending"
    elif status == "S":
        return "submitted"
    elif status == "D":
        return "discarded"
    elif status is None:
        return "all"
    else:
        raise Exception("Invalid status '%s'" % status)


def string_to_status(status):
    if status == "pending":
        return "P"
    elif status == "submitted":
        return "S"
    elif status == "discarded":
        return "D"
    elif status == "all":
        return None
    else:
        raise Exception("Invalid status '%s'" % status)


class DeprecatedReviewBoardAPIEncoder(WebAPIEncoder):
    def encode(self, o, *args, **kwargs):
        if isinstance(o, Group):
            return {
                'id': o.id,
                'name': o.name,
                'display_name': o.display_name,
                'mailing_list': o.mailing_list,
                'url': o.get_absolute_url(),
            }
        elif isinstance(o, ReviewRequest):
            if o.bugs_closed:
                bugs_closed = [b.strip() for b in o.bugs_closed.split(',')]
            else:
                bugs_closed = ''

            return {
                'id': o.id,
                'submitter': o.submitter,
                'time_added': o.time_added,
                'last_updated': o.last_updated,
                'status': status_to_string(o.status),
                'public': o.public,
                'changenum': o.changenum,
                'commit_id': o.commit,
                'repository': o.repository,
                'summary': o.summary,
                'description': o.description,
                'testing_done': o.testing_done,
                'bugs_closed': bugs_closed,
                'branch': o.branch,
                'target_groups': o.target_groups.all(),
                'target_people': o.target_people.all(),
            }
        elif isinstance(o, ReviewRequestDraft):
            if o.bugs_closed != "":
                bugs_closed = [b.strip() for b in o.bugs_closed.split(',')]
            else:
                bugs_closed = []

            return {
                'id': o.id,
                'review_request': o.review_request,
                'last_updated': o.last_updated,
                'summary': o.summary,
                'description': o.description,
                'testing_done': o.testing_done,
                'bugs_closed': bugs_closed,
                'branch': o.branch,
                'target_groups': o.target_groups.all(),
                'target_people': o.target_people.all(),
            }
        elif isinstance(o, Review):
            return {
                'id': o.id,
                'user': o.user,
                'timestamp': o.timestamp,
                'public': o.public,
                'ship_it': o.ship_it,
                'body_top': o.body_top,
                'body_bottom': o.body_bottom,
                'comments': o.comments.all(),
            }
        elif isinstance(o, Comment):
            review = o.review.get()
            return {
                'id': o.id,
                'filediff': o.filediff,
                'interfilediff': o.interfilediff,
                'text': o.text,
                'timestamp': o.timestamp,
                'timesince': timesince(o.timestamp),
                'first_line': o.first_line,
                'num_lines': o.num_lines,
                'public': review.public,
                'user': review.user,
            }
        elif isinstance(o, ScreenshotComment):
            review = o.review.get()
            return {
                'id': o.id,
                'screenshot': o.screenshot,
                'text': o.text,
                'timestamp': o.timestamp,
                'timesince': timesince(o.timestamp),
                'public': review.public,
                'user': review.user,
                'x': o.x,
                'y': o.y,
                'w': o.w,
                'h': o.h,
            }
        elif isinstance(o, Screenshot):
            return {
                'id': o.id,
                'caption': o.caption,
                'title': 'Screenshot: %s' % (o.caption or o.image.name),
                'image_url': o.get_absolute_url(),
                'thumbnail_url': o.get_thumbnail_url(),
            }
        elif isinstance(o, FileDiff):
            return {
                'id': o.id,
                'diffset': o.diffset,
                'source_file': o.source_file,
                'dest_file': o.dest_file,
                'source_revision': o.source_revision,
                'dest_detail': o.dest_detail,
            }
        elif isinstance(o, DiffSet):
            return {
                'id': o.id,
                'name': o.name,
                'revision': o.revision,
                'timestamp': o.timestamp,
                'repository': o.repository,
            }
        elif isinstance(o, Repository):
            return {
                'id': o.id,
                'name': o.name,
                'path': o.path,
                'tool': o.tool.name
            }
        else:
            return super(DeprecatedReviewBoardAPIEncoder, self).encode(
                o, *args, **kwargs)
