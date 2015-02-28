from __future__ import unicode_literals

from django.utils import six

from reviewboard.diffviewer.models import DiffCommit
from reviewboard.webapi.resources import resources
from reviewboard.webapi.tests.base import BaseWebAPITestCase
from reviewboard.webapi.tests.mimetypes import (diff_commit_item_mimetype,
                                                diff_commit_list_mimetype)
from reviewboard.webapi.tests.mixins import (BasicTestsMetaclass,
                                             ReviewRequestChildItemMixin,
                                             ReviewRequestChildListMixin)
from reviewboard.webapi.tests.mixins_extra_data import (ExtraDataItemMixin)
from reviewboard.webapi.tests.urls import (get_diff_commit_item_url,
                                           get_diff_commit_list_url)


def compare_item(self, item_rsp, commit):
    self.assertEqual(item_rsp['id'], commit.pk)
    self.assertEqual(item_rsp['name'], commit.name)
    self.assertEqual(item_rsp['commit_id'], commit.commit_id)
    self.assertEqual(item_rsp['parent_id'], commit.parent_id)
    self.assertEqual(item_rsp['description'], commit.description)
    self.assertEqual(item_rsp['author_name'], commit.author_name)
    self.assertEqual(item_rsp['author_email'], commit.author_email)
    self.assertEqual(item_rsp['author_date'],
                     commit.author_date.strftime(DiffCommit.DATE_FORMAT))
    self.assertEqual(item_rsp['committer_name'], commit.committer_name)
    self.assertEqual(item_rsp['committer_email'], commit.committer_email)

    if item_rsp['committer_date'] or commit.committer_date:
        self.assertEqual(
            item_rsp['committer_date'],
            commit.committer_date.strftime(DiffCommit.DATE_FORMAT))

    self.assertDictEqual(item_rsp['extra_data'], commit.extra_data)

    commit_ids = set(commit.merge_parent_ids.all())
    item_ids = set(item_rsp['merge_parent_ids'])
    self.assertSetEqual(set(commit_ids), item_ids)
    self.assertEqual(len(commit_ids), commit.merge_parent_ids.count())
    self.assertEqual(len(item_ids), len(item_rsp['merge_parent_ids']))

    self.assertIn(commit.commit_type, ('C', 'M'))
    self.assertIn(item_rsp['commit_type'], ('change', 'merge'))

    if commit.commit_type == 'C':
        self.assertEqual(item_rsp['commit_type'], 'change')
    elif commit.commit_type == 'M':
        self.assertEqual(item_rsp['commit_type'], 'merge')


@six.add_metaclass(BasicTestsMetaclass)
class ResourceListTests(ReviewRequestChildListMixin, BaseWebAPITestCase):
    resource = resources.diff_commit
    sample_api_url = 'review-requests/<id>/diffs/<id>/commits/'
    fixtures = ['test_users', 'test_scmtools']

    test_http_methods = ('GET', )

    compare_item = compare_item

    def setup_basic_get_test(self, user, with_local_site, local_site_name,
                             populate_items):
        repository = self.create_repository(tool_name='Test')
        review_request = self.create_review_request(
            repository=repository,
            with_local_site=with_local_site,
            submitter=user,
            publish=True)

        diffset = self.create_diffset(review_request=review_request,
                                      repository=repository)

        items = []

        if populate_items:
            commit = self.create_diff_commit(diffset=diffset,
                                             repository=repository,
                                             commit_id='r1',
                                             parent_id='r0')

            items.append(commit)

        return (get_diff_commit_list_url(review_request, diffset,
                                         local_site_name),
                diff_commit_list_mimetype,
                items)

    def check_post_result(self, user, rsp, review_request, diffset):
        self.assertIn('diff_commit', rsp)
        item_rsp = rsp['diff_commit']

        draft = review_request.get_draft()
        self.assertIsNotNone(draft)

        commit = DiffCommit.objects.get(pk=item_rsp['id'])
        self.assertEqual(diffset, commit.diffset)
        self.compare_item(item_rsp, commit)

    def setup_review_request_child_test(self, review_request):
        if not review_request.repository:
            review_request.repository = self.create_repository(
                tool_name='Test')
            review_request.save()

        diffset = self.create_diffset(review_request=review_request)

        self.create_diff_commit(diffset=diffset,
                                repository=review_request.repository,
                                commit_id='r1',
                                parent_id='r0')

        return (get_diff_commit_list_url(review_request, diffset),
                diff_commit_list_mimetype)


@six.add_metaclass(BasicTestsMetaclass)
class ResourceItemTests(BaseWebAPITestCase, ExtraDataItemMixin,
                        ReviewRequestChildItemMixin):
    resource = resources.diff_commit
    sample_api_url = 'review-requests/<id>/draft/diffs/<id>/commits/<commit>/'
    fixtures = ['test_users', 'test_scmtools']
    test_http_methods = ('GET', 'PUT')
    basic_put_use_admin = False

    compare_item = compare_item

    def setup_review_request_child_test(self, review_request):
        if not review_request.repository:
            review_request.repository = self.create_repository()
            review_request.save()

        diffset = self.create_diffset(review_request=review_request)

        commit = self.create_diff_commit(
            diffset=diffset,
            repository=review_request.repository,
            commit_id='r1',
            parent_id='r0')

        return (get_diff_commit_item_url(review_request, diffset, commit),
                diff_commit_item_mimetype)

    def setup_basic_get_test(self, user, with_local_site, local_site_name):
        repository = self.create_repository(tool_name='Test')
        review_request = self.create_review_request(
            repository=repository,
            with_local_site=with_local_site,
            submitter=user,
            publish=True)

        diffset = self.create_diffset(review_request=review_request,
                                      repository=repository)

        commit = self.create_diff_commit(diffset=diffset,
                                         repository=repository,
                                         commit_id='r1',
                                         parent_id='r2')

        return (get_diff_commit_item_url(review_request, diffset,
                                         commit, local_site_name),
                diff_commit_item_mimetype,
                commit)

    def setup_basic_put_test(self, user, with_local_site, local_site_name,
                             put_valid_data):
        repository = self.create_repository(tool_name='Test')
        review_request = self.create_review_request(
            repository=repository,
            with_local_site=with_local_site,
            submitter=user,
            publish=True)

        diffset = self.create_diffset(review_request)

        commit = self.create_diff_commit(diffset=diffset,
                                         repository=repository,
                                         commit_id='r1',
                                         parent_id='r2')

        return (get_diff_commit_item_url(review_request, diffset,
                                         commit, local_site_name),
                diff_commit_item_mimetype,
                {},
                commit,
                [])

    def check_put_result(self, user, item_rsp, commit):
        self.compare_item(item_rsp, commit)
