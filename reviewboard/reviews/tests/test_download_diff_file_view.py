"""Unit tests for reviewboard.reviews.views.DownloadDiffFileView."""

from __future__ import annotations

from reviewboard.hostingsvcs.base import hosting_service_registry
from reviewboard.hostingsvcs.models import HostingServiceAccount
from reviewboard.scmtools.core import PRE_CREATION
from reviewboard.site.urlresolvers import local_site_reverse
from reviewboard.testing import TestCase
from reviewboard.testing.hosting_services import TestService


class DownloadDiffFileViewTests(TestCase):
    """Unit tests for reviewboard.reviews.views.DownloadDiffFileView."""

    fixtures = ['test_users', 'test_scmtools']

    @classmethod
    def setUpClass(cls) -> None:
        """Set up the test case class."""
        super().setUpClass()

        hosting_service_registry.register(TestService)

    @classmethod
    def tearDownClass(cls) -> None:
        """Tear down the test case class."""
        super().tearDownClass()

        hosting_service_registry.unregister(TestService)

    def setUp(self) -> None:
        """Set up the test case."""
        super().setUp()

        self.account = HostingServiceAccount.objects.create(
            service_name=TestService.hosting_service_id,
            hosting_url='http://example.com/',
            username='foo')

        self.repository = self.create_repository(hosting_account=self.account)
        self.review_request = self.create_review_request(
            repository=self.repository, publish=True)
        self.diffset = self.create_diffset(review_request=self.review_request)
        self.filediff = self.create_filediff(self.diffset,
                                             source_file='/invalid-path',
                                             dest_file='/invalid-path')

    def testing_download_orig_file_404(self) -> None:
        """Testing DownloadDiffFileView with original file when the file
        cannot be found upstream
        """
        rsp = self.client.get(
            local_site_reverse('download-orig-file', kwargs={
                'review_request_id': self.review_request.display_id,
                'revision': self.diffset.revision,
                'filediff_id': self.filediff.pk,
            }))

        self.assertEqual(rsp.status_code, 404)

    def testing_download_modified_file_404(self) -> None:
        """Testing DownloadDiffFileView with modified file when the file
        cannot be found upstream
        """
        rsp = self.client.get(
            local_site_reverse('download-modified-file', kwargs={
                'review_request_id': self.review_request.display_id,
                'revision': self.diffset.revision,
                'filediff_id': self.filediff.pk,
            }))

        self.assertEqual(rsp.status_code, 404)

    def test_download_modified_file_patch_error(self) -> None:
        """Testing DownloadDiffFileView with modified file when patching
        fails
        """
        # Create a filediff with a diff that won't apply to the original
        # file contents. The source revision of PRE_CREATION means the
        # original file is empty, but the diff references non-empty
        # content, which will cause a PatchError.
        bad_diff = (
            b'--- /new-file\n'
            b'+++ /new-file\n'
            b'@@ -1,3 +1,3 @@\n'
            b' line 1\n'
            b'-line 2\n'
            b'+line 2 modified\n'
            b' line 3\n'
        )

        filediff = self.create_filediff(
            self.diffset,
            source_file='/new-file',
            dest_file='/new-file',
            source_revision=PRE_CREATION,
            dest_detail='',
            diff=bad_diff)

        rsp = self.client.get(
            local_site_reverse('download-modified-file', kwargs={
                'review_request_id': self.review_request.display_id,
                'revision': self.diffset.revision,
                'filediff_id': filediff.pk,
            }))

        self.assertEqual(rsp.status_code, 404)
