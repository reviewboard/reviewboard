"""Unit tests for reviewboard.diffviewer.views.DownloadPatchErrorBundleView."""

import kgb
from django.http import HttpResponse

from reviewboard.diffviewer.errors import PatchError
from reviewboard.diffviewer.renderers import DiffRenderer
from reviewboard.site.urlresolvers import local_site_reverse
from reviewboard.testing import TestCase


class DownloadPatchErrorBundleViewTests(kgb.SpyAgency, TestCase):
    """Unit tests for DownloadPatchErrorBundleView."""

    fixtures = ['test_users', 'test_scmtools']

    def test_sends_404_when_no_patch_error(self):
        """Testing DownloadPatchErrorBundleView returns 404 when
        no patch error is raised by the renderer.
        """
        review_request = self.create_review_request(publish=True,
                                                    create_repository=True)
        diffset = self.create_diffset(review_request=review_request)
        self.create_diffcommit(diffset=diffset)
        filediff_id = diffset.files.all()[0].pk

        # This does not raise a PatchError, so there is no patch error bundle.
        self.spy_on(DiffRenderer.render_to_response,
                    op=kgb.SpyOpReturn(HttpResponse()))

        response = self.client.get(
            local_site_reverse(
                'patch-error-bundle',
                kwargs={
                    'review_request_id': review_request.pk,
                    'revision': diffset.revision,
                    'filediff_id': filediff_id,
                }))

        self.assertEqual(response.status_code, 404)

    def test_sends_bundle_when_patch_error(self):
        """Testing DownloadPatchErrorBundleView sends a patch error bundle
        when a PatchError is raised by the renderer.
        """
        review_request = self.create_review_request(publish=True,
                                                    create_repository=True)
        diffset = self.create_diffset(review_request=review_request)
        self.create_diffcommit(diffset=diffset)
        filediff_id = diffset.files.all()[0].pk

        patch_error = PatchError(filename='filename',
                                 error_output='error_output',
                                 orig_file=b'orig_file',
                                 new_file=b'new_file',
                                 diff=b'diff',
                                 rejects=b'rejects')
        self.spy_on(DiffRenderer.render_to_response,
                    op=kgb.SpyOpRaise(patch_error))

        response = self.client.get(
            local_site_reverse(
                'patch-error-bundle',
                kwargs={
                    'review_request_id': review_request.pk,
                    'revision': diffset.revision,
                    'filediff_id': filediff_id,
                }))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'application/zip')
