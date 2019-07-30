"""Unit tests for reviewboard.reviews.views.DownloadDiffFileView."""

from __future__ import unicode_literals

from reviewboard.extensions.tests import TestService
from reviewboard.hostingsvcs.models import HostingServiceAccount
from reviewboard.hostingsvcs.service import (register_hosting_service,
                                             unregister_hosting_service)
from reviewboard.site.urlresolvers import local_site_reverse
from reviewboard.testing import TestCase


class DownloadDiffFileViewTests(TestCase):
    """Unit tests for reviewboard.reviews.views.DownloadDiffFileView."""

    fixtures = ['test_users', 'test_scmtools']

    @classmethod
    def setUpClass(cls):
        super(DownloadDiffFileViewTests, cls).setUpClass()

        register_hosting_service(TestService.hosting_service_id, TestService)

    @classmethod
    def tearDownClass(cls):
        super(DownloadDiffFileViewTests, cls).tearDownClass()

        unregister_hosting_service(TestService.hosting_service_id)

    def setUp(self):
        super(DownloadDiffFileViewTests, self).setUp()

        self.account = HostingServiceAccount.objects.create(
            service_name=TestService.name,
            hosting_url='http://example.com/',
            username='foo')

        self.repository = self.create_repository(hosting_account=self.account)
        self.review_request = self.create_review_request(
            repository=self.repository, publish=True)
        self.diffset = self.create_diffset(review_request=self.review_request)
        self.filediff = self.create_filediff(self.diffset,
                                             source_file='/invalid-path',
                                             dest_file='/invalid-path')

    def testing_download_orig_file_404(self):
        """Testing DownloadDiffFileView with original file when the file
        cannot be found upstream
        """
        rsp = self.client.get(
            local_site_reverse('download-orig-file', kwargs={
                'review_request_id': self.review_request.display_id,
                'revision': self.diffset.revision,
                'filediff_id': self.filediff.pk,
            }))

        self.assertEquals(rsp.status_code, 404)

    def testing_download_modified_file_404(self):
        """Testing DownloadDiffFileView with modified file when the file
        cannot be found upstream
        """
        rsp = self.client.get(
            local_site_reverse('download-modified-file', kwargs={
                'review_request_id': self.review_request.display_id,
                'revision': self.diffset.revision,
                'filediff_id': self.filediff.pk,
            }))

        self.assertEquals(rsp.status_code, 404)
