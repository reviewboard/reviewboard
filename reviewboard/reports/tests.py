from django.test import TestCase

from djblets.siteconfig.models import SiteConfiguration


class ViewTests(TestCase):
    """Tests for views in reviewboard.reports.views"""
    fixtures = ['test_users', 'test_reviewrequests', 'test_scmtools']

    def setUp(self):
        siteconfig = SiteConfiguration.objects.get_current()
        siteconfig.set("auth_require_sitewide_login", False)

    def testReviewRequestReport(self):
        """Testing review_request report"""
        response = self.client.get("/reports/admin/review_request/moinmoin/")
        self.assertEqual(response.status_code, 200)

        response = self.client.get("/reports/admin/review_request/text/")
        self.assertEqual(response.status_code, 200)

        response = self.client.get("/reports/admin/review_request/abc/")
        self.assertEqual(response.status_code, 404)

    def testReviewReport(self):
        """Testing review report"""
        response = self.client.get("/reports/admin/review/moinmoin/")
        self.assertEqual(response.status_code, 200)

        response = self.client.get("/reports/admin/review/text/")
        self.assertEqual(response.status_code, 200)

        response = self.client.get("/reports/admin/review/abc/")
        self.assertEqual(response.status_code, 404)

    def testStatusReport(self):
        """Testing status_report"""
        response = self.client.get("/reports/admin/status_report/moinmoin/")
        self.assertEqual(response.status_code, 200)

        response = self.client.get("/reports/admin/status_report/text/")
        self.assertEqual(response.status_code, 200)

        response = self.client.get("/reports/admin/status_report/abc/")
        self.assertEqual(response.status_code, 404)

    def testReportList(self):
        """Testing report_list"""
        response = self.client.get("/reports/")
        self.assertEqual(response.status_code, 200)
