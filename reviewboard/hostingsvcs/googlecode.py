from __future__ import unicode_literals

import json
import logging
from collections import defaultdict

from django import forms
from django.conf.urls import patterns, url
from django.http import HttpResponse, HttpResponseBadRequest
from django.template import RequestContext
from django.template.loader import render_to_string
from django.utils.translation import ugettext_lazy as _
from django.views.decorators.http import require_POST

from reviewboard.admin.server import build_server_url, get_server_url
from reviewboard.hostingsvcs.forms import HostingServiceForm
from reviewboard.hostingsvcs.hook_utils import (close_all_review_requests,
                                                get_repository_for_hook,
                                                get_review_request_id)
from reviewboard.hostingsvcs.service import HostingService
from reviewboard.site.urlresolvers import local_site_reverse


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
    has_repository_hook_instructions = True

    repository_url_patterns = patterns(
        '',

        url(r'^hooks/(?P<hooks_uuid>[a-z0-9]+)/close-submitted/$',
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

    def get_repository_hook_instructions(self, request, repository):
        """Returns instructions for setting up incoming webhooks."""
        webhook_endpoint_url = build_server_url(local_site_reverse(
            'googlecode-hooks-close-submitted',
            local_site=repository.local_site,
            kwargs={
                'repository_id': repository.pk,
                'hosting_service_id': repository.hosting_account.service_name,
                'hooks_uuid': repository.get_or_create_hooks_uuid(),
            }))
        add_webhook_url = (
            'https://code.google.com/p/%s/adminSource'
            % repository.extra_data['googlecode_project_name'])

        example_id = 123
        example_url = build_server_url(local_site_reverse(
            'review-request-detail',
            local_site=repository.local_site,
            kwargs={
                'review_request_id': example_id,
            }))

        return render_to_string(
            'hostingsvcs/googlecode/repo_hook_instructions.html',
            RequestContext(request, {
                'example_id': example_id,
                'example_url': example_url,
                'repository': repository,
                'server_url': get_server_url(),
                'add_webhook_url': add_webhook_url,
                'webhook_endpoint_url': webhook_endpoint_url,
            }))


@require_POST
def post_receive_hook_close_submitted(request, local_site_name=None,
                                      repository_id=None,
                                      hosting_service_id=None,
                                      hooks_uuid=None):
    """Closes review requests as submitted automatically after a push."""
    repository = get_repository_for_hook(repository_id, hosting_service_id,
                                         local_site_name, hooks_uuid)

    try:
        payload = json.loads(request.body)
    except ValueError as e:
        logging.error('The payload is not in JSON format: %s', e, exc_info=1)
        return HttpResponseBadRequest('Invalid payload format')

    server_url = get_server_url(request=request)
    review_request_id_to_commits_map = \
        close_review_requests(payload, server_url)

    if review_request_id_to_commits_map:
        close_all_review_requests(review_request_id_to_commits_map,
                                  local_site_name, repository,
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
        review_request_id = get_review_request_id(commit_message, server_url)
        review_request_id_to_commits_map[review_request_id].append(
            '%s (%s)' % (branch_name, revision_id))

    return review_request_id_to_commits_map
