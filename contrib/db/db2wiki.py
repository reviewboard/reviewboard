#!/usr/bin/env python
#
# Database to Wiki script
#
# This pretty-prints the database in a format compatible with the Google Code
# wiki. It's intended for dumping data from the test fixtures in order to
# present documentation for contributors, and is not recommended for large
# databases.
#
# This must be run from the top-level Review Board directory containing
# manage.py
#
# Example:
#
#   $ ./contrib/db/db2wiki.py > db.wiki

import os
import sys

sys.path.append(os.getcwd())

try:
    import settings
except ImportError:
    sys.stderr.write(("Error: Can't find the file 'settings.py' in the " +
                      "directory containing %r. Make sure you're running " +
                      "from the root reviewboard directory.") % __file__)
    sys.exit(1)

# This must be done before we import any models
from django.core.management import setup_environ
setup_environ(settings)

from django.contrib.auth.models import User

from reviewboard.diffviewer.models import DiffSet, DiffSetHistory
from reviewboard.reviews.models import Group, ReviewRequest, Review, Comment
from reviewboard.scmtools.models import Repository
from reviewboard.reviews.json import ReviewBoardJSONEncoder


def get_object_info(o):
    if isinstance(o, User):
        info = [
            ('username', o.username),
            ('password', o.username),
            ('first_name', o.first_name),
            ('last_name', o.last_name),
            ('email', o.email),
        ]

        if o.is_staff:
            info.append(('is_staff', True),)

        if o.is_superuser:
            info.append(('is_superuser', True),)

        if o.user_permissions.count() > 0:
            info.append(('permissions',
                ["%s.%s" % (perm.content_type.app_label, perm.codename)
                 for perm in o.user_permissions.all()]),)

    elif isinstance(o, Group):
        info = [
            ('name', o.name),
            ('mailing_list', o.mailing_list),
        ]

        info.append(('users', [u.username for u in o.users.all()]),)
    elif isinstance(o, Repository):
        info = [
            ('name', o.name),
            ('path', o.path),
            ('bug_tracker', o.bug_tracker),
            ('tool', o.tool.name),
        ]
    elif isinstance(o, ReviewRequest):
        info = [
            ('submitter', o.submitter.username),
            ('summary', o.summary),
            ('description', o.description),
            ('testing_done', o.testing_done),
            ('target_groups', [g.name for g in o.target_groups.all()]),
            ('target_people', [u.username for u in o.target_people.all()]),
            ('bugs_closed', o.get_bug_list()),
            ('public', o.public),
            ('status', o.status),
            ('diff', o.diffset_history.diffset_set.latest().name),
            ('reviews', [(review.user.username, get_object_info(review))
                         for review in o.review_set.all()]),
        ]
    elif isinstance(o, Review):
        info = [
            ('user', o.user.username),
        ]

        if o.ship_it:
            info.append(('ship_it', True),)

        if o.body_top != "":
            info.append(('body_top', o.body_top),)

        if o.body_bottom != "":
            info.append(('body_bottom', o.body_bottom),)

        if o.comments.count() > 0:
            info.append(('comments', [(comment.text, get_object_info(comment))
                                      for comment in o.comments.all()]))
    elif isinstance(o, Comment):
        info = [
            ('text', o.text),
            ('first_line', o.first_line),
            ('num_lines', o.num_lines),
            ('file', o.filediff.source_file),
        ]
    else:
        info = None

    return info


def dump_object_info(key, info, indent_level=1):
    if isinstance(info, list) and len(info) > 0 and \
       isinstance(info[0], tuple):
        print "%s* *%s:*" % ("  " * indent_level, key)

        for key, value in info:
            print '%s* *"%s"*' % ("  " * (indent_level + 1), key)
            for inner_key, inner_value in value:
                dump_object_info(inner_key, inner_value, indent_level + 2)
    else:
        if isinstance(info, str):
            info = '"%s"' % info

        print '%s* *%s:* %s' % ("  " * indent_level, key, info)

def dump_wiki(name, query_list):
    print
    print "== %s ==" % name

    for model_name, queryset in query_list:
        print
        print "=== %s entries ===" % model_name

        for obj in queryset:
            info = get_object_info(obj)

            if info:
                print
                print "==== %s ====" % obj
                print

                for key, value in info:
                    dump_object_info(key, value)

if __name__ == "__main__":

    print "= Fixture Details ="

    dump_wiki("test_users.json", [
        ("User", User.objects.all())
    ])

    dump_wiki("test_reviewrequests.json", [
        ("Group", Group.objects.all()),
        ("ReviewRequest", ReviewRequest.objects.all()),
    ])

    dump_wiki("test_scmtools.json", [
        ("Repository", Repository.objects.all())
    ])
