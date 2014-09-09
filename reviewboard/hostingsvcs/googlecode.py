from __future__ import unicode_literals

import json
import logging
from collections import defaultdict

from django import forms
from django.conf.urls import patterns, url
from django.http import HttpResponse
from django.utils.translation import ugettext_lazy as _
from django.views.decorators.http import require_POST

from reviewboard.hostingsvcs.forms import HostingServiceForm
from reviewboard.hostingsvcs.hook_utils import (close_all_review_requests,
                                                get_review_request_id,
                                                get_server_url)
from reviewboard.hostingsvcs.service import HostingService


class GoogleCodeForm(HostingServiceForm):
    googlecode_project_name = forms.CharField(
        label=_('Project name'),
        max_length=64,
        required=True,
        widget=forms.TextInput(attrs={'size': '60'}))


class GoogleCode(HostingService):
    name = 'Google Code'
    form = GoogleCodeForm
    supported_scmtools = ['Mercurial', 'Subversion']
    supports_repositories = True
    supports_bug_trackers = True

    repository_url_patterns = patterns(
        '',

        url(r'^hooks/close-submitted/$',
            'reviewboard.hostingsvcs.googlecode'
            '.post_receive_hook_close_submitted',
            name='googlecode-hooks-close-submitted'),
    )

    repository_fields = {
        'Mercurial': {
            'path': 'http://%(googlecode_project_name)s'
                    '.googlecode.com/hg',
            'mirror_path': 'https://%(googlecode_project_name)s'
                           '.googlecode.com/hg',
        },
        'Subversion': {
            'path': 'http://%(googlecode_project_name)s'
                    '.googlecode.com/svn',
            'mirror_path': 'https://%(googlecode_project_name)s'
                           '.googlecode.com/svn',
        },
    }
    bug_tracker_field = 'http://code.google.com/p/' \
                        '%(googlecode_project_name)s/' \
                        'issues/detail?id=%%s'


@require_POST
def post_receive_hook_close_submitted(request, local_site_name=None,
                                      repository_id=None,
                                      hosting_service_id=None):
    """Closes review requests as submitted automatically after a push."""
    try:
        payload = json.loads(request.body)
    except KeyError as e:
        logging.error('There is no JSON payload in the POST request: %s', e,
                      exc_info=1)
        return HttpResponse(status=400)
    except ValueError as e:
        logging.error('The payload is not in JSON format: %s', e,
                      exc_info=1)
        return HttpResponse(status=400)

    server_url = get_server_url(request)
    review_request_id_to_commits_map = \
        close_review_requests(payload, server_url)

    if review_request_id_to_commits_map:
        close_all_review_requests(review_request_id_to_commits_map,
                                  local_site_name, repository_id,
                                  hosting_service_id)

    return HttpResponse()


def close_review_requests(payload, server_url):
    """Closes all review requests for the Google Code repository."""
    # The Google Code payload is the same for SVN and Mercurial
    # repositories. There is no information in the payload as to
    # which SCM tool was used for the commit. That's why the only way
    # to close a review request through this hook is by adding the review
    # request id in the commit message.
    review_request_id_to_commits_map = defaultdict(list)
    branch_name = payload.get('repository_path')

    if not branch_name:
        return review_request_id_to_commits_map

    revisions = payload.get('revisions', [])

    for revision in revisions:
        revision_id = revision.get('revision')

        if len(revision_id) > 7:
            revision_id = revision_id[:7]

        commit_message = revision.get('message')
        review_request_id = get_review_request_id(commit_message, server_url,
                                                  None)
        review_request_id_to_commits_map[review_request_id].append(
            '%s (%s)' % (branch_name, revision_id))

    return review_request_id_to_commits_map
