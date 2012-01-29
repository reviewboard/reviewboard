import logging
import os

from django.contrib.auth.models import AnonymousUser, User
from django.core.urlresolvers import reverse
from django.template import Context, Template
from django.test import TestCase

from djblets.siteconfig.models import SiteConfiguration

from reviewboard.accounts.models import Profile, LocalSiteProfile
from reviewboard.reviews.forms import DefaultReviewerForm, GroupForm
from reviewboard.reviews.models import DefaultReviewer, \
                                       Group, \
                                       ReviewRequest, \
                                       ReviewRequestDraft, \
                                       Review
from reviewboard.scmtools.models import Repository, Tool
from reviewboard.site.models import LocalSite
from reviewboard.site.urlresolvers import local_site_reverse


class DbQueryTests(TestCase):
    """Tests review request query utility functions."""
    fixtures = ['test_users', 'test_reviewrequests', 'test_scmtools',
                'test_site']

    def testAllReviewRequests(self):
        """Testing get_all_review_requests"""
        self.assertValidSummaries(
            ReviewRequest.objects.public(
                User.objects.get(username="doc")), [
            "Comments Improvements",
            "Update for cleaned_data changes",
            "Add permission checking for JSON API",
            "Made e-mail improvements",
            "Error dialog",
            "Interdiff Revision Test",
        ])

        self.assertValidSummaries(
            ReviewRequest.objects.public(status=None), [
            "Update for cleaned_data changes",
            "Add permission checking for JSON API",
            "Made e-mail improvements",
            "Error dialog",
            "Improved login form",
            "Interdiff Revision Test",
        ])

        self.assertValidSummaries(
            ReviewRequest.objects.public(
                User.objects.get(username="doc"), status=None), [
            "Comments Improvements",
            "Update for cleaned_data changes",
            "Add permission checking for JSON API",
            "Made e-mail improvements",
            "Error dialog",
            "Improved login form",
            "Interdiff Revision Test",
        ])

    def testReviewRequestsToGroup(self):
        """Testing get_review_requests_to_group"""
        self.assertValidSummaries(
            ReviewRequest.objects.to_group("privgroup", None),
            ["Add permission checking for JSON API"])

        self.assertValidSummaries(
            ReviewRequest.objects.to_group("privgroup", None, status=None),
            ["Add permission checking for JSON API"])

    def testReviewRequestsToUserGroups(self):
        """Testing get_review_requests_to_user_groups"""
        self.assertValidSummaries(
            ReviewRequest.objects.to_user_groups("doc", local_site=None),
            ["Update for cleaned_data changes",
             "Add permission checking for JSON API"])

        self.assertValidSummaries(
            ReviewRequest.objects.to_user_groups("doc", status=None,
                local_site=None),
            ["Update for cleaned_data changes",
             "Add permission checking for JSON API"])

        self.assertValidSummaries(
            ReviewRequest.objects.to_user_groups("doc",
                User.objects.get(username="doc"), local_site=None),
            ["Comments Improvements",
             "Update for cleaned_data changes",
             "Add permission checking for JSON API"])

    def testReviewRequestsToUserDirectly(self):
        """Testing get_review_requests_to_user_directly"""
        self.assertValidSummaries(
            ReviewRequest.objects.to_user_directly("doc", local_site=None),
            ["Add permission checking for JSON API",
             "Made e-mail improvements"])

        self.assertValidSummaries(
            ReviewRequest.objects.to_user_directly("doc", status=None),
            ["Add permission checking for JSON API",
             "Made e-mail improvements",
             "Improved login form"])

        self.assertValidSummaries(
            ReviewRequest.objects.to_user_directly("doc",
                User.objects.get(username="doc"), status=None, local_site=None),
            ["Add permission checking for JSON API",
             "Made e-mail improvements",
             "Improved login form"])

    def testReviewRequestsFromUser(self):
        """Testing get_review_requests_from_user"""
        self.assertValidSummaries(
            ReviewRequest.objects.from_user("doc", local_site=None), [])

        self.assertValidSummaries(
            ReviewRequest.objects.from_user("doc", status=None, local_site=None),
            ["Improved login form"])

        self.assertValidSummaries(
            ReviewRequest.objects.from_user("doc",
                user=User.objects.get(username="doc"), status=None,
                local_site=None),
            ["Comments Improvements",
             "Improved login form"])

    def testReviewRequestsToUser(self):
        """Testing get_review_requests_to_user"""
        self.assertValidSummaries(
            ReviewRequest.objects.to_user("doc", local_site=None), [
            "Update for cleaned_data changes",
            "Add permission checking for JSON API",
            "Made e-mail improvements"
        ])

        self.assertValidSummaries(
            ReviewRequest.objects.to_user("doc", status=None, local_site=None), [

            "Update for cleaned_data changes",
            "Add permission checking for JSON API",
            "Made e-mail improvements",
            "Improved login form"
        ])

        self.assertValidSummaries(
            ReviewRequest.objects.to_user("doc",
                User.objects.get(username="doc"), status=None, local_site=None), [
            "Comments Improvements",
            "Update for cleaned_data changes",
            "Add permission checking for JSON API",
            "Made e-mail improvements",
            "Improved login form"
        ])

    def assertValidSummaries(self, review_requests, summaries):
        print review_requests
        r_summaries = [r.summary for r in review_requests]

        for summary in r_summaries:
            self.assert_(summary in summaries,
                         u'summary "%s" not found in summary list' % summary)

        for summary in summaries:
            self.assert_(summary in r_summaries,
                         u'summary "%s" not found in review request list' %
                         summary)


class ViewTests(TestCase):
    """Tests for views in reviewboard.reviews.views"""
    fixtures = ['test_users', 'test_reviewrequests', 'test_scmtools',
                'test_site']

    def setUp(self):
        self.siteconfig = SiteConfiguration.objects.get_current()
        self.siteconfig.set("auth_require_sitewide_login", False)
        self.siteconfig.save()

    def getContextVar(self, response, varname):
        for context in response.context:
            if varname in context:
                return context[varname]

        return None

    def testReviewDetail0(self):
        """Testing review_detail redirect"""
        response = self.client.get('/r/1')
        self.assertEqual(response.status_code, 301)

    def testReviewDetail1(self):
        """Testing review_detail view (1)"""
        review_request = ReviewRequest.objects.public()[0]

        response = self.client.get('/r/%d/' % review_request.id)
        self.assertEqual(response.status_code, 200)

        request = self.getContextVar(response, 'review_request')
        self.assertEqual(request.pk, review_request.pk)

    def testReviewDetail2(self):
        """Testing review_detail view (3)"""
        # Make sure this request is made while logged in, to catch the
        # login-only pieces of the review_detail view.
        self.client.login(username='admin', password='admin')

        response = self.client.get('/r/3/')
        self.assertEqual(response.status_code, 200)

        request = self.getContextVar(response, 'review_request')
        self.assertEqual(request.submitter.username, 'admin')
        self.assertEqual(request.summary, 'Add permission checking for JSON API')
        self.assertEqual(request.description,
                         'Added some user permissions checking for JSON API functions.')
        self.assertEqual(request.testing_done, 'Tested some functions.')

        self.assertEqual(request.target_people.count(), 2)
        self.assertEqual(request.target_people.all()[0].username, 'doc')
        self.assertEqual(request.target_people.all()[1].username, 'dopey')

        self.assertEqual(request.target_groups.count(), 1)
        self.assertEqual(request.target_groups.all()[0].name, 'privgroup')

        self.assertEqual(request.bugs_closed, '1234, 5678, 8765, 4321')
        self.assertEqual(request.status, 'P')

        # TODO - diff
        # TODO - reviews

        self.client.logout()

    def testReviewDetailSitewideLogin(self):
        """Testing review_detail view with site-wide login enabled"""
        self.siteconfig.set("auth_require_sitewide_login", True)
        self.siteconfig.save()
        response = self.client.get('/r/1/')
        self.assertEqual(response.status_code, 302)

    def testNewReviewRequest0(self):
        """Testing new_review_request view (basic responses)"""
        response = self.client.get('/r/new')
        self.assertEqual(response.status_code, 301)

        response = self.client.get('/r/new/')
        self.assertEqual(response.status_code, 302)

        self.client.login(username='grumpy', password='grumpy')

        response = self.client.get('/r/new/')
        self.assertEqual(response.status_code, 200)

        self.client.logout()

    def testNewReviewRequest1(self):
        """Testing new_review_request view (uploading diffs)"""
        self.client.login(username='grumpy', password='grumpy')

        response = self.client.get('/r/new/')
        self.assertEqual(response.status_code, 200)

        testdata_dir = os.path.join(
            os.path.dirname(os.path.dirname(__file__)),
            'scmtools', 'testdata')
        svn_repo_path = os.path.join(testdata_dir, 'svn_repo')

        repository = Repository(name='Subversion SVN',
                                path='file://' + svn_repo_path,
                                tool=Tool.objects.get(name='Subversion'))
        repository.save()

        diff_filename = os.path.join(testdata_dir, 'svn_makefile.diff')

        f = open(diff_filename, 'r')

        response = self.client.post('/r/new/', {
            'repository': repository.id,
            'diff_path': f,
            'basedir': '/trunk',
        })

        f.close()

        self.assertEqual(response.status_code, 302)

        r = ReviewRequest.objects.order_by('-time_added')[0]
        self.assertEqual(response['Location'],
                         'http://testserver%s' % r.get_absolute_url())

    def testReviewList(self):
        """Testing all_review_requests view"""
        self.client.login(username='grumpy', password='grumpy')

        response = self.client.get('/r/')
        self.assertEqual(response.status_code, 200)

        datagrid = self.getContextVar(response, 'datagrid')
        self.assert_(datagrid)
        self.assertEqual(len(datagrid.rows), 6)
        self.assertEqual(datagrid.rows[0]['object'].summary,
                         'Interdiff Revision Test')
        self.assertEqual(datagrid.rows[1]['object'].summary,
                         'Made e-mail improvements')
        self.assertEqual(datagrid.rows[2]['object'].summary,
                         'Improved login form')
        self.assertEqual(datagrid.rows[3]['object'].summary,
                         'Error dialog')
        self.assertEqual(datagrid.rows[4]['object'].summary,
                         'Update for cleaned_data changes')
        self.assertEqual(datagrid.rows[5]['object'].summary,
                         'Add permission checking for JSON API')

        self.client.logout()

    def testReviewListSitewideLogin(self):
        """Testing all_review_requests view with site-wide login enabled"""
        self.siteconfig.set("auth_require_sitewide_login", True)
        self.siteconfig.save()
        response = self.client.get('/r/')
        self.assertEqual(response.status_code, 302)

    def testSubmitterList(self):
        """Testing submitter_list view"""
        response = self.client.get('/users/')
        self.assertEqual(response.status_code, 200)

        datagrid = self.getContextVar(response, 'datagrid')
        self.assert_(datagrid)
        self.assertEqual(len(datagrid.rows), 4)
        self.assertEqual(datagrid.rows[0]['object'].username, 'admin')
        self.assertEqual(datagrid.rows[1]['object'].username, 'doc')
        self.assertEqual(datagrid.rows[2]['object'].username, 'dopey')
        self.assertEqual(datagrid.rows[3]['object'].username, 'grumpy')

    def testSubmitterListSitewideLogin(self):
        """Testing submitter_list view with site-wide login enabled"""
        self.siteconfig.set("auth_require_sitewide_login", True)
        self.siteconfig.save()
        response = self.client.get('/users/')
        self.assertEqual(response.status_code, 302)

    def testSubmitterListChars(self):
        """Testing the submitter list with various characters in the username"""
        # Test if this throws an exception. Bug #1250
        reverse('user', args=['user@example.com'])

    def testGroupList(self):
        """Testing group_list view"""
        response = self.client.get('/groups/')
        self.assertEqual(response.status_code, 200)

        datagrid = self.getContextVar(response, 'datagrid')
        self.assert_(datagrid)
        self.assertEqual(len(datagrid.rows), 4)
        self.assertEqual(datagrid.rows[0]['object'].name, 'devgroup')
        self.assertEqual(datagrid.rows[1]['object'].name, 'emptygroup')
        self.assertEqual(datagrid.rows[2]['object'].name, 'newgroup')
        self.assertEqual(datagrid.rows[3]['object'].name, 'privgroup')

    def testGroupListSitewideLogin(self):
        """Testing group_list view with site-wide login enabled"""
        self.siteconfig.set("auth_require_sitewide_login", True)
        self.siteconfig.save()
        response = self.client.get('/groups/')
        self.assertEqual(response.status_code, 302)

    def testDashboard1(self):
        """Testing dashboard view (incoming)"""
        self.client.login(username='doc', password='doc')

        response = self.client.get('/dashboard/', {'view': 'incoming'})
        self.assertEqual(response.status_code, 200)

        datagrid = self.getContextVar(response, 'datagrid')
        self.assert_(datagrid)
        self.assertEqual(len(datagrid.rows), 4)
        self.assertEqual(datagrid.rows[0]['object'].summary,
                         'Made e-mail improvements')
        self.assertEqual(datagrid.rows[1]['object'].summary,
                         'Update for cleaned_data changes')
        self.assertEqual(datagrid.rows[2]['object'].summary,
                         'Comments Improvements')
        self.assertEqual(datagrid.rows[3]['object'].summary,
                         'Add permission checking for JSON API')

        self.client.logout()

    def testDashboard2(self):
        """Testing dashboard view (outgoing)"""
        self.client.login(username='admin', password='admin')

        response = self.client.get('/dashboard/', {'view': 'outgoing'})
        self.assertEqual(response.status_code, 200)

        datagrid = self.getContextVar(response, 'datagrid')
        self.assert_(datagrid)
        self.assertEqual(len(datagrid.rows), 2)
        self.assertEqual(datagrid.rows[0]['object'].summary,
                         'Interdiff Revision Test')
        self.assertEqual(datagrid.rows[1]['object'].summary,
                         'Add permission checking for JSON API')

        self.client.logout()

    def testDashboard3(self):
        """Testing dashboard view (to-me)"""
        self.client.login(username='doc', password='doc')

        response = self.client.get('/dashboard/', {'view': 'to-me'})
        self.assertEqual(response.status_code, 200)

        datagrid = self.getContextVar(response, 'datagrid')
        self.assert_(datagrid)
        self.assertEqual(len(datagrid.rows), 2)
        self.assertEqual(datagrid.rows[0]['object'].summary,
                         'Made e-mail improvements')
        self.assertEqual(datagrid.rows[1]['object'].summary,
                         'Add permission checking for JSON API')

        self.client.logout()

    def testDashboard4(self):
        """Testing dashboard view (to-group devgroup)"""
        self.client.login(username='doc', password='doc')

        response = self.client.get('/dashboard/',
                                   {'view': 'to-group',
                                    'group': 'devgroup'})
        self.assertEqual(response.status_code, 200)

        datagrid = self.getContextVar(response, 'datagrid')
        self.assert_(datagrid)
        self.assertEqual(len(datagrid.rows), 2)
        self.assertEqual(datagrid.rows[0]['object'].summary,
                         'Update for cleaned_data changes')
        self.assertEqual(datagrid.rows[1]['object'].summary,
                         'Comments Improvements')

        self.client.logout()

    def testDashboardSidebar(self):
        """Testing dashboard view (to-group devgroup)"""
        self.client.login(username='doc', password='doc')
        user = User.objects.get(username='doc')
        profile = user.get_profile()
        local_site = None

        response = self.client.get('/dashboard/')
        self.assertEqual(response.status_code, 200)

        datagrid = self.getContextVar(response, 'datagrid')
        self.assertEqual(
            datagrid.counts['outgoing'],
            ReviewRequest.objects.from_user(
                user, user, local_site=local_site).count())
        self.assertEqual(
            datagrid.counts['incoming'],
            ReviewRequest.objects.to_user(user, local_site=local_site).count())
        self.assertEqual(
            datagrid.counts['to-me'],
            ReviewRequest.objects.to_user_directly(
                user, local_site=local_site).count())
        self.assertEqual(
            datagrid.counts['starred'],
            profile.starred_review_requests.public(
                user, local_site=local_site).count())
        self.assertEqual(datagrid.counts['mine'],
            ReviewRequest.objects.from_user(
                user, user, None, local_site=local_site).count())
        self.assertEqual(datagrid.counts['groups']['devgroup'],
            ReviewRequest.objects.to_group(
                'devgroup', local_site=local_site).count())
        self.assertEqual(datagrid.counts['groups']['privgroup'],
            ReviewRequest.objects.to_group(
                'privgroup', local_site=local_site).count())

        self.client.logout()

    # Bug 892
    def testInterdiff(self):
        """Testing the diff viewer with interdiffs"""
        response = self.client.get('/r/8/diff/1-2/')

        # Useful for debugging any actual errors here.
        if response.status_code != 200:
            print "Error: %s" % self.getContextVar(response, 'error')
            print self.getContextVar(response, 'trace')

        self.assertEqual(response.status_code, 200)

        self.assertEqual(self.getContextVar(response, 'num_diffs'), 3)

        files = self.getContextVar(response, 'files')
        self.assert_(files)
        self.assertEqual(len(files), 2)

        self.assertEqual(files[0]['depot_filename'],
                         '/trunk/reviewboard/TESTING')
        self.assert_('fragment' in files[0])
        self.assert_('interfilediff' in files[0])

        self.assertEqual(files[1]['depot_filename'],
                         '/trunk/reviewboard/settings_local.py.tmpl')
        self.assert_('fragment' not in files[1])
        self.assert_('interfilediff' in files[1])

    # Bug 847
    def testInterdiffNewFile(self):
        """Testing the diff viewer with interdiffs containing new files"""
        response = self.client.get('/r/8/diff/2-3/')

        # Useful for debugging any actual errors here.
        if response.status_code != 200:
            print "Error: %s" % self.getContextVar(response, 'error')
            print self.getContextVar(response, 'trace')

        self.assertEqual(response.status_code, 200)

        self.assertEqual(self.getContextVar(response, 'num_diffs'), 3)

        files = self.getContextVar(response, 'files')
        self.assert_(files)
        self.assertEqual(len(files), 1)

        self.assertEqual(files[0]['depot_filename'],
                         '/trunk/reviewboard/NEW_FILE')
        self.assert_('fragment' in files[0])
        self.assert_('interfilediff' in files[0])

    def testDashboard5(self):
        """Testing dashboard view (mine)"""
        self.client.login(username='doc', password='doc')

        response = self.client.get('/dashboard/', {'view': 'mine'})
        self.assertEqual(response.status_code, 200)

        datagrid = self.getContextVar(response, 'datagrid')
        self.assert_(datagrid)
        self.assertEqual(len(datagrid.rows), 2)
        self.assertEqual(datagrid.rows[0]['object'].summary,
                         'Improved login form')
        self.assertEqual(datagrid.rows[1]['object'].summary,
                         'Comments Improvements')

        self.client.logout()


class DraftTests(TestCase):
    fixtures = ['test_users', 'test_reviewrequests', 'test_scmtools']

    def testDraftChanges(self):
        """Testing recording of draft changes."""
        draft = self.getDraft()
        review_request = draft.review_request

        old_summary = review_request.summary
        old_description = review_request.description
        old_testing_done = review_request.testing_done
        old_branch = review_request.branch
        old_bugs = review_request.get_bug_list()

        draft.summary = "New summary"
        draft.description = "New description"
        draft.testing_done = "New testing done"
        draft.branch = "New branch"
        draft.bugs_closed = "12, 34, 56"

        new_bugs = draft.get_bug_list()

        changes = draft.publish()
        fields = changes.fields_changed

        self.assert_("summary" in fields)
        self.assert_("description" in fields)
        self.assert_("testing_done" in fields)
        self.assert_("branch" in fields)
        self.assert_("bugs_closed" in fields)

        old_bugs_norm = set([(bug,) for bug in old_bugs])
        new_bugs_norm = set([(bug,) for bug in new_bugs])

        self.assertEqual(fields["summary"]["old"][0], old_summary)
        self.assertEqual(fields["summary"]["new"][0], draft.summary)
        self.assertEqual(fields["description"]["old"][0], old_description)
        self.assertEqual(fields["description"]["new"][0], draft.description)
        self.assertEqual(fields["testing_done"]["old"][0], old_testing_done)
        self.assertEqual(fields["testing_done"]["new"][0], draft.testing_done)
        self.assertEqual(fields["branch"]["old"][0], old_branch)
        self.assertEqual(fields["branch"]["new"][0], draft.branch)
        self.assertEqual(set(fields["bugs_closed"]["old"]), old_bugs_norm)
        self.assertEqual(set(fields["bugs_closed"]["new"]), new_bugs_norm)
        self.assertEqual(set(fields["bugs_closed"]["removed"]), old_bugs_norm)
        self.assertEqual(set(fields["bugs_closed"]["added"]), new_bugs_norm)

    def getDraft(self):
        """Convenience function for getting a new draft to work with."""
        return ReviewRequestDraft.create(ReviewRequest.objects.get(
            summary="Add permission checking for JSON API"))


class FieldTests(TestCase):
    # Bug #1352
    def testLongBugNumbers(self):
        """Testing review requests with very long bug numbers"""
        review_request = ReviewRequest()
        review_request.bugs_closed = \
            '12006153200030304432010,4432009'
        self.assertEqual(review_request.get_bug_list(),
                         ['4432009', '12006153200030304432010'])

    # Our _("(no summary)") string was failing in the admin UI, as
    # django.template.defaultfilters.stringfilter would fail on a
    # ugettext_lazy proxy object. We can use any stringfilter for this.
    #
    # Bug #1346
    def testNoSummary(self):
        """Testing review requests with no summary"""
        from django.template.defaultfilters import lower
        review_request = ReviewRequest()
        lower(unicode(review_request))


class ConcurrencyTests(TestCase):
    fixtures = ['test_users', 'test_reviewrequests', 'test_scmtools']

    def testDuplicateReviews(self):
        """Testing consolidation of duplicate reviews"""

        body_top = "This is the body_top."
        body_bottom = "This is the body_bottom."
        comment_text_1 = "Comment text 1"
        comment_text_2 = "Comment text 2"
        comment_text_3 = "Comment text 3"

        # Some objects we need.
        user = User.objects.get(username="doc")

        review_request = ReviewRequest.objects.get(
            summary="Add permission checking for JSON API")
        filediff = \
            review_request.diffset_history.diffsets.latest().files.all()[0]

        # Create the first review.
        review = Review(review_request=review_request, user=user)
        review.body_top = body_top
        review.save()
        master_review = review

        comment = review.comments.create(filediff=filediff, first_line=1)
        comment.text = comment_text_1
        comment.num_lines = 1
        comment.save()

        # Create the second review.
        review = Review(review_request=review_request, user=user)
        review.save()

        comment = review.comments.create(filediff=filediff, first_line=1)
        comment.text = comment_text_2
        comment.num_lines = 1
        comment.save()

        # Create the third review.
        review = Review(review_request=review_request, user=user)
        review.body_bottom = body_bottom
        review.save()

        comment = review.comments.create(filediff=filediff, first_line=1)
        comment.text = comment_text_3
        comment.num_lines = 1
        comment.save()

        # Now that we've made a mess, see if we get a single review back.
        logging.disable(logging.WARNING)
        review = review_request.get_pending_review(user)
        self.assert_(review)
        self.assertEqual(review.id, master_review.id)
        self.assertEqual(review.body_top, body_top)
        self.assertEqual(review.body_bottom, body_bottom)

        comments = list(review.comments.all())
        self.assertEqual(len(comments), 3)
        self.assertEqual(comments[0].text, comment_text_1)
        self.assertEqual(comments[1].text, comment_text_2)
        self.assertEqual(comments[2].text, comment_text_3)


class DefaultReviewerTests(TestCase):
    fixtures = ['test_scmtools.json']

    def test_for_repository(self):
        """Testing DefaultReviewer.objects.for_repository"""
        tool = Tool.objects.get(name='CVS')

        default_reviewer1 = DefaultReviewer(name="Test", file_regex=".*")
        default_reviewer1.save()

        default_reviewer2 = DefaultReviewer(name="Bar", file_regex=".*")
        default_reviewer2.save()

        repo1 = Repository(name='Test1', path='path1', tool=tool)
        repo1.save()
        default_reviewer1.repository.add(repo1)

        repo2 = Repository(name='Test2', path='path2', tool=tool)
        repo2.save()

        default_reviewers = DefaultReviewer.objects.for_repository(repo1, None)
        self.assert_(len(default_reviewers) == 2)
        self.assert_(default_reviewer1 in default_reviewers)
        self.assert_(default_reviewer2 in default_reviewers)

        default_reviewers = DefaultReviewer.objects.for_repository(repo2, None)
        self.assert_(len(default_reviewers) == 1)
        self.assert_(default_reviewer2 in default_reviewers)

    def test_for_repository_with_localsite(self):
        """Testing DefaultReviewer.objects.for_repository with a LocalSite."""
        test_site = LocalSite.objects.create(name='test')

        default_reviewer1 = DefaultReviewer(name='Test 1', file_regex='.*',
                                            local_site=test_site)
        default_reviewer1.save()

        default_reviewer2 = DefaultReviewer(name='Test 2', file_regex='.*')
        default_reviewer2.save()

        default_reviewers = DefaultReviewer.objects.for_repository(None, test_site)
        self.assert_(len(default_reviewers) == 1)
        self.assert_(default_reviewer1 in default_reviewers)

        default_reviewers = DefaultReviewer.objects.for_repository(None, None)
        self.assert_(len(default_reviewers) == 1)
        self.assert_(default_reviewer2 in default_reviewers)

    def test_form_with_localsite(self):
        """Testing DefaultReviewerForm with a LocalSite."""
        test_site = LocalSite.objects.create(name='test')

        tool = Tool.objects.get(name='CVS')
        repo = Repository.objects.create(name='Test', path='path', tool=tool,
                                         local_site=test_site)
        user = User.objects.create(username='testuser', password='')
        test_site.users.add(user)

        group = Group.objects.create(name='test', display_name='Test',
                                     local_site=test_site)

        form = DefaultReviewerForm({
            'name': 'Test',
            'file_regex': '.*',
            'local_site': test_site.pk,
            'repository': [repo.pk],
            'people': [user.pk],
            'groups': [group.pk],
        })
        self.assertTrue(form.is_valid())
        default_reviewer = form.save()

        self.assertEquals(default_reviewer.local_site, test_site)
        self.assertEquals(default_reviewer.repository.get(), repo)
        self.assertEquals(default_reviewer.people.get(), user)
        self.assertEquals(default_reviewer.groups.get(), group)

    def test_form_with_localsite_and_bad_user(self):
        """Testing DefaultReviewerForm with a User not on the same LocalSite."""
        test_site = LocalSite.objects.create(name='test')
        user = User.objects.create(username='testuser', password='')

        form = DefaultReviewerForm({
            'name': 'Test',
            'file_regex': '.*',
            'local_site': test_site.pk,
            'people': [user.pk],
        })
        self.assertFalse(form.is_valid())

    def test_form_with_localsite_and_bad_group(self):
        """Testing DefaultReviewerForm with a Group not on the same LocalSite."""
        test_site = LocalSite.objects.create(name='test')
        group = Group.objects.create(name='test', display_name='Test')

        form = DefaultReviewerForm({
            'name': 'Test',
            'file_regex': '.*',
            'local_site': test_site.pk,
            'groups': [group.pk],
        })
        self.assertFalse(form.is_valid())

        group.local_site = test_site
        group.save()

        form = DefaultReviewerForm({
            'name': 'Test',
            'file_regex': '.*',
            'groups': [group.pk],
        })
        self.assertFalse(form.is_valid())

    def test_form_with_localsite_and_bad_repository(self):
        """Testing DefaultReviewerForm with a Repository not on the same LocalSite."""
        test_site = LocalSite.objects.create(name='test')
        tool = Tool.objects.get(name='CVS')
        repo = Repository.objects.create(name='Test', path='path', tool=tool)

        form = DefaultReviewerForm({
            'name': 'Test',
            'file_regex': '.*',
            'local_site': test_site.pk,
            'repository': [repo.pk],
        })
        self.assertFalse(form.is_valid())

        repo.local_site = test_site
        repo.save()

        form = DefaultReviewerForm({
            'name': 'Test',
            'file_regex': '.*',
            'repository': [repo.pk],
        })
        self.assertFalse(form.is_valid())


class GroupTests(TestCase):
    def test_form_with_localsite(self):
        """Tests GroupForm with a LocalSite."""
        test_site = LocalSite.objects.create(name='test')

        user = User.objects.create(username='testuser', password='')
        test_site.users.add(user)

        form = GroupForm({
            'name': 'test',
            'display_name': 'Test',
            'local_site': test_site.pk,
            'users': [user.pk],
        })
        self.assertTrue(form.is_valid())
        group = form.save()

        self.assertEquals(group.local_site, test_site)
        self.assertEquals(group.users.get(), user)

    def test_form_with_localsite_and_bad_user(self):
        """Tests GroupForm with a User not on the same LocalSite."""
        test_site = LocalSite.objects.create(name='test')

        user = User.objects.create(username='testuser', password='')

        form = GroupForm({
            'name': 'test',
            'display_name': 'Test',
            'local_site': test_site.pk,
            'users': [user.pk],
        })
        self.assertFalse(form.is_valid())


class IfNeatNumberTagTests(TestCase):
    def testMilestones(self):
        """Testing the ifneatnumber tag with milestone numbers"""
        self.assertNeatNumberResult(100, "")
        self.assertNeatNumberResult(1000, "milestone")
        self.assertNeatNumberResult(10000, "milestone")
        self.assertNeatNumberResult(20000, "milestone")
        self.assertNeatNumberResult(20001, "")

    def testPalindrome(self):
        """Testing the ifneatnumber tag with palindrome numbers"""
        self.assertNeatNumberResult(101, "")
        self.assertNeatNumberResult(1001, "palindrome")
        self.assertNeatNumberResult(12321, "palindrome")
        self.assertNeatNumberResult(20902, "palindrome")
        self.assertNeatNumberResult(912219, "palindrome")
        self.assertNeatNumberResult(912218, "")

    def assertNeatNumberResult(self, rid, expected):
        t = Template(
            "{% load reviewtags %}"
            "{% ifneatnumber " + str(rid) + " %}"
            "{%  if milestone %}milestone{% else %}"
            "{%  if palindrome %}palindrome{% endif %}{% endif %}"
            "{% endifneatnumber %}")

        self.assertEqual(t.render(Context({})), expected)


class CounterTests(TestCase):
    fixtures = ['test_scmtools.json']

    def setUp(self):
        tool = Tool.objects.get(name='Subversion')
        repository = Repository.objects.create(name='Test1', path='path1',
                                               tool=tool)

        self.user = User.objects.create(username='testuser', password='')
        self.profile, is_new = Profile.objects.get_or_create(user=self.user)
        self.profile.save()

        self.test_site = LocalSite.objects.create(name='test')
        self.site_profile2 = \
            LocalSiteProfile.objects.create(user=self.user,
                                            profile=self.profile,
                                            local_site=self.test_site)

        self.review_request = ReviewRequest.objects.create(self.user,
                                                           repository)
        self.profile.star_review_request(self.review_request)

        self.site_profile = self.profile.site_profiles.get(local_site=None)
        self.assertEqual(self.site_profile.total_outgoing_request_count, 1)
        self.assertEqual(self.site_profile.pending_outgoing_request_count, 1)
        self.assertEqual(self.site_profile.starred_public_request_count, 0)

        self.group = Group.objects.create(name='test-group')
        self.group.users.add(self.user)

        self._reload_objects()
        self.assertEqual(self.site_profile2.total_outgoing_request_count, 0)
        self.assertEqual(self.site_profile2.pending_outgoing_request_count, 0)
        self.assertEqual(self.site_profile2.starred_public_request_count, 0)

    def test_new_site_profile(self):
        """Testing counters on a new LocalSiteProfile"""
        self.site_profile.delete()
        self.site_profile = \
            LocalSiteProfile.objects.create(user=self.user,
                                            profile=self.profile)
        self.assertEqual(self.site_profile.total_outgoing_request_count, None)
        self.assertEqual(self.site_profile.pending_outgoing_request_count, None)
        self.assertEqual(self.site_profile.starred_public_request_count, None)

        self.review_request.publish(self.user)

        self._reload_objects()
        self.assertEqual(self.site_profile.total_outgoing_request_count, 1)
        self.assertEqual(self.site_profile.pending_outgoing_request_count, 1)
        self.assertEqual(self.site_profile.starred_public_request_count, 1)

    def test_outgoing_requests(self):
        """Testing counters with creating outgoing review requests"""
        # The review request was already created
        self._reload_objects()
        self.assertEqual(self.site_profile.total_outgoing_request_count, 1)
        self.assertEqual(self.site_profile.pending_outgoing_request_count, 1)
        self.assertEqual(self.site_profile2.total_outgoing_request_count, 0)
        self.assertEqual(self.site_profile2.pending_outgoing_request_count, 0)

        ReviewRequestDraft.create(self.review_request)
        self.review_request.publish(self.user)

        self._reload_objects()
        self.assertEqual(self.site_profile.total_outgoing_request_count, 1)
        self.assertEqual(self.site_profile.pending_outgoing_request_count, 1)
        self.assertEqual(self.site_profile2.total_outgoing_request_count, 0)
        self.assertEqual(self.site_profile2.pending_outgoing_request_count, 0)

    def test_closing_requests(self, close_type=ReviewRequest.DISCARDED):
        """Testing counters with closing outgoing review requests"""
        # The review request was already created
        self._reload_objects()
        self.assertEqual(self.site_profile.total_outgoing_request_count, 1)
        self.assertEqual(self.site_profile.pending_outgoing_request_count, 1)
        self.assertEqual(self.site_profile.starred_public_request_count, 0)
        self.assertEqual(self.site_profile2.total_outgoing_request_count, 0)
        self.assertEqual(self.site_profile2.pending_outgoing_request_count, 0)
        self.assertEqual(self.site_profile2.starred_public_request_count, 0)

        draft = ReviewRequestDraft.create(self.review_request)
        draft.target_groups.add(self.group)
        draft.target_people.add(self.user)
        self.review_request.publish(self.user)

        self._reload_objects()
        self.assertEqual(self.site_profile.direct_incoming_request_count, 1)
        self.assertEqual(self.site_profile.total_incoming_request_count, 1)
        self.assertEqual(self.site_profile.starred_public_request_count, 1)
        self.assertEqual(self.site_profile2.direct_incoming_request_count, 0)
        self.assertEqual(self.site_profile2.total_incoming_request_count, 0)
        self.assertEqual(self.site_profile2.starred_public_request_count, 0)
        self.assertEqual(self.group.incoming_request_count, 1)

        self.assertTrue(self.review_request.public)
        self.assertEqual(self.review_request.status,
                         ReviewRequest.PENDING_REVIEW)
        self.review_request.close(close_type)

        self._reload_objects()
        self.assertEqual(self.site_profile.total_outgoing_request_count, 1)
        self.assertEqual(self.site_profile.pending_outgoing_request_count, 0)
        self.assertEqual(self.site_profile.direct_incoming_request_count, 0)
        self.assertEqual(self.site_profile.total_incoming_request_count, 0)
        self.assertEqual(self.site_profile.starred_public_request_count, 0)
        self.assertEqual(self.site_profile2.total_outgoing_request_count, 0)
        self.assertEqual(self.site_profile2.pending_outgoing_request_count, 0)
        self.assertEqual(self.site_profile2.direct_incoming_request_count, 0)
        self.assertEqual(self.site_profile2.total_incoming_request_count, 0)
        self.assertEqual(self.site_profile2.starred_public_request_count, 0)
        self.assertEqual(self.group.incoming_request_count, 0)

    def test_closing_draft_requests(self, close_type=ReviewRequest.DISCARDED):
        """Testing counters with closing draft review requests"""
        # The review request was already created
        self._reload_objects()
        self.assertEqual(self.site_profile.total_outgoing_request_count, 1)
        self.assertEqual(self.site_profile.pending_outgoing_request_count, 1)
        self.assertEqual(self.site_profile.starred_public_request_count, 0)
        self.assertEqual(self.site_profile2.total_outgoing_request_count, 0)
        self.assertEqual(self.site_profile2.pending_outgoing_request_count, 0)
        self.assertEqual(self.site_profile2.starred_public_request_count, 0)

        self.assertFalse(self.review_request.public)
        self.assertEqual(self.review_request.status,
                         ReviewRequest.PENDING_REVIEW)
        self.review_request.close(close_type)

        self._reload_objects()
        self.assertEqual(self.site_profile.total_outgoing_request_count, 1)
        self.assertEqual(self.site_profile.pending_outgoing_request_count, 0)
        self.assertEqual(self.site_profile.direct_incoming_request_count, 0)
        self.assertEqual(self.site_profile.total_incoming_request_count, 0)
        self.assertEqual(self.site_profile.starred_public_request_count, 0)
        self.assertEqual(self.site_profile2.total_outgoing_request_count, 0)
        self.assertEqual(self.site_profile2.pending_outgoing_request_count, 0)
        self.assertEqual(self.site_profile2.direct_incoming_request_count, 0)
        self.assertEqual(self.site_profile2.total_incoming_request_count, 0)
        self.assertEqual(self.site_profile2.starred_public_request_count, 0)
        self.assertEqual(self.group.incoming_request_count, 0)

    def test_closing_draft_requests_with_site(self):
        """Testing counters with closing draft review requests"""
        self.review_request.delete()
        self._reload_objects()
        self.assertEqual(self.site_profile2.total_outgoing_request_count, 0)
        self.assertEqual(self.site_profile2.pending_outgoing_request_count, 0)
        self.assertEqual(self.site_profile2.starred_public_request_count, 0)

        tool = Tool.objects.get(name='Subversion')
        repository = Repository.objects.create(name='Test1', path='path1',
                                               tool=tool,
                                               local_site=self.test_site)
        self.review_request = ReviewRequest.objects.create(
            self.user,
            repository,
            local_site=self.test_site)

        self._reload_objects()
        self.assertEqual(self.site_profile2.total_outgoing_request_count, 1)
        self.assertEqual(self.site_profile2.pending_outgoing_request_count, 1)
        self.assertEqual(self.site_profile2.starred_public_request_count, 0)

        self.assertFalse(self.review_request.public)
        self.assertEqual(self.review_request.status,
                         ReviewRequest.PENDING_REVIEW)
        self.review_request.close(ReviewRequest.DISCARDED)

        self._reload_objects()
        self.assertEqual(self.site_profile2.total_outgoing_request_count, 1)
        self.assertEqual(self.site_profile2.pending_outgoing_request_count, 0)
        self.assertEqual(self.site_profile2.direct_incoming_request_count, 0)

    def test_deleting_requests(self):
        """Testing counters with deleting outgoing review requests"""
        # The review request was already created
        self._reload_objects()
        self.assertEqual(self.site_profile.total_outgoing_request_count, 1)
        self.assertEqual(self.site_profile.pending_outgoing_request_count, 1)
        self.assertEqual(self.site_profile.starred_public_request_count, 0)
        self.assertEqual(self.site_profile2.total_outgoing_request_count, 0)
        self.assertEqual(self.site_profile2.pending_outgoing_request_count, 0)
        self.assertEqual(self.site_profile2.starred_public_request_count, 0)

        draft = ReviewRequestDraft.create(self.review_request)
        draft.target_groups.add(self.group)
        draft.target_people.add(self.user)
        self.review_request.publish(self.user)

        self._reload_objects()
        self.assertEqual(self.site_profile.direct_incoming_request_count, 1)
        self.assertEqual(self.site_profile.total_incoming_request_count, 1)
        self.assertEqual(self.site_profile.starred_public_request_count, 1)
        self.assertEqual(self.site_profile2.direct_incoming_request_count, 0)
        self.assertEqual(self.site_profile2.total_incoming_request_count, 0)
        self.assertEqual(self.site_profile2.starred_public_request_count, 0)
        self.assertEqual(self.group.incoming_request_count, 1)

        self.review_request.delete()

        self._reload_objects()
        self.assertEqual(self.site_profile.total_outgoing_request_count, 0)
        self.assertEqual(self.site_profile.pending_outgoing_request_count, 0)
        self.assertEqual(self.site_profile.direct_incoming_request_count, 0)
        self.assertEqual(self.site_profile.total_incoming_request_count, 0)
        self.assertEqual(self.site_profile.starred_public_request_count, 0)
        self.assertEqual(self.site_profile2.total_outgoing_request_count, 0)
        self.assertEqual(self.site_profile2.pending_outgoing_request_count, 0)
        self.assertEqual(self.site_profile2.direct_incoming_request_count, 0)
        self.assertEqual(self.site_profile2.total_incoming_request_count, 0)
        self.assertEqual(self.site_profile2.starred_public_request_count, 0)
        self.assertEqual(self.group.incoming_request_count, 0)

    def test_deleting_draft_requests(self):
        """Testing counters with deleting draft review requests"""
        # The review request was already created
        self._reload_objects()
        self.assertEqual(self.site_profile.total_outgoing_request_count, 1)
        self.assertEqual(self.site_profile.pending_outgoing_request_count, 1)
        self.assertEqual(self.site_profile.starred_public_request_count, 0)
        self.assertEqual(self.site_profile2.total_outgoing_request_count, 0)
        self.assertEqual(self.site_profile2.pending_outgoing_request_count, 0)
        self.assertEqual(self.site_profile2.starred_public_request_count, 0)

        self.review_request.delete()

        self._reload_objects()
        self.assertEqual(self.site_profile.total_outgoing_request_count, 0)
        self.assertEqual(self.site_profile.pending_outgoing_request_count, 0)
        self.assertEqual(self.site_profile.direct_incoming_request_count, 0)
        self.assertEqual(self.site_profile.total_incoming_request_count, 0)
        self.assertEqual(self.site_profile.starred_public_request_count, 0)
        self.assertEqual(self.site_profile2.total_outgoing_request_count, 0)
        self.assertEqual(self.site_profile2.pending_outgoing_request_count, 0)
        self.assertEqual(self.site_profile2.direct_incoming_request_count, 0)
        self.assertEqual(self.site_profile2.total_incoming_request_count, 0)
        self.assertEqual(self.site_profile2.starred_public_request_count, 0)
        self.assertEqual(self.group.incoming_request_count, 0)

    def test_reopen_discarded_requests(self):
        """Testing counters with reopening discarded outgoing review requests"""
        self.test_closing_requests(ReviewRequest.DISCARDED)

        self.review_request.reopen()
        self.assertFalse(self.review_request.public)
        self.assertTrue(self.review_request.status,
                        ReviewRequest.PENDING_REVIEW)

        self._reload_objects()
        self.assertEqual(self.site_profile.total_outgoing_request_count, 1)
        self.assertEqual(self.site_profile.pending_outgoing_request_count, 1)
        self.assertEqual(self.site_profile.direct_incoming_request_count, 0)
        self.assertEqual(self.site_profile.total_incoming_request_count, 0)
        self.assertEqual(self.site_profile.starred_public_request_count, 0)
        self.assertEqual(self.site_profile2.total_outgoing_request_count, 0)
        self.assertEqual(self.site_profile2.pending_outgoing_request_count, 0)
        self.assertEqual(self.site_profile2.direct_incoming_request_count, 0)
        self.assertEqual(self.site_profile2.total_incoming_request_count, 0)
        self.assertEqual(self.site_profile2.starred_public_request_count, 0)
        self.assertEqual(self.group.incoming_request_count, 0)

        self.review_request.publish(self.user)

        self._reload_objects()
        self.assertEqual(self.site_profile.total_outgoing_request_count, 1)
        self.assertEqual(self.site_profile.pending_outgoing_request_count, 1)
        self.assertEqual(self.site_profile.direct_incoming_request_count, 1)
        self.assertEqual(self.site_profile.total_incoming_request_count, 1)
        self.assertEqual(self.site_profile.starred_public_request_count, 1)
        self.assertEqual(self.site_profile2.total_outgoing_request_count, 0)
        self.assertEqual(self.site_profile2.pending_outgoing_request_count, 0)
        self.assertEqual(self.site_profile2.direct_incoming_request_count, 0)
        self.assertEqual(self.site_profile2.total_incoming_request_count, 0)
        self.assertEqual(self.site_profile2.starred_public_request_count, 0)
        self.assertEqual(self.group.incoming_request_count, 1)

    def test_reopen_submitted_requests(self):
        """Testing counters with reopening submitted outgoing review requests"""
        self.test_closing_requests(ReviewRequest.SUBMITTED)

        self.review_request.reopen()
        self.assertTrue(self.review_request.public)
        self.assertTrue(self.review_request.status,
                        ReviewRequest.PENDING_REVIEW)

        self._reload_objects()
        self.assertEqual(self.site_profile.total_outgoing_request_count, 1)
        self.assertEqual(self.site_profile.pending_outgoing_request_count, 1)
        self.assertEqual(self.site_profile.direct_incoming_request_count, 1)
        self.assertEqual(self.site_profile.total_incoming_request_count, 1)
        self.assertEqual(self.site_profile.starred_public_request_count, 1)
        self.assertEqual(self.site_profile2.total_outgoing_request_count, 0)
        self.assertEqual(self.site_profile2.pending_outgoing_request_count, 0)
        self.assertEqual(self.site_profile2.direct_incoming_request_count, 0)
        self.assertEqual(self.site_profile2.total_incoming_request_count, 0)
        self.assertEqual(self.site_profile2.starred_public_request_count, 0)
        self.assertEqual(self.group.incoming_request_count, 1)

        self.review_request.publish(self.user)

        self._reload_objects()
        self.assertEqual(self.site_profile.total_outgoing_request_count, 1)
        self.assertEqual(self.site_profile.pending_outgoing_request_count, 1)
        self.assertEqual(self.site_profile.direct_incoming_request_count, 1)
        self.assertEqual(self.site_profile.total_incoming_request_count, 1)
        self.assertEqual(self.site_profile.starred_public_request_count, 1)
        self.assertEqual(self.site_profile2.total_outgoing_request_count, 0)
        self.assertEqual(self.site_profile2.pending_outgoing_request_count, 0)
        self.assertEqual(self.site_profile2.direct_incoming_request_count, 0)
        self.assertEqual(self.site_profile2.total_incoming_request_count, 0)
        self.assertEqual(self.site_profile2.starred_public_request_count, 0)
        self.assertEqual(self.group.incoming_request_count, 1)

    def test_reopen_discarded_draft_requests(self):
        """Testing counters with reopening discarded draft review requests"""
        self.assertFalse(self.review_request.public)

        self.test_closing_draft_requests(ReviewRequest.DISCARDED)

        self.review_request.reopen()
        self.assertFalse(self.review_request.public)
        self.assertTrue(self.review_request.status,
                        ReviewRequest.PENDING_REVIEW)

        self._reload_objects()
        self.assertEqual(self.site_profile.total_outgoing_request_count, 1)
        self.assertEqual(self.site_profile.pending_outgoing_request_count, 1)
        self.assertEqual(self.site_profile.direct_incoming_request_count, 0)
        self.assertEqual(self.site_profile.total_incoming_request_count, 0)
        self.assertEqual(self.site_profile.starred_public_request_count, 0)
        self.assertEqual(self.site_profile2.total_outgoing_request_count, 0)
        self.assertEqual(self.site_profile2.pending_outgoing_request_count, 0)
        self.assertEqual(self.site_profile2.direct_incoming_request_count, 0)
        self.assertEqual(self.site_profile2.total_incoming_request_count, 0)
        self.assertEqual(self.site_profile2.starred_public_request_count, 0)
        self.assertEqual(self.group.incoming_request_count, 0)

    def test_reopen_submitted_draft_requests(self):
        """Testing counters with reopening submitted draft review requests"""
        self.test_closing_draft_requests(ReviewRequest.SUBMITTED)

        self.review_request.reopen()
        self.assertFalse(self.review_request.public)
        self.assertTrue(self.review_request.status,
                        ReviewRequest.PENDING_REVIEW)

        self._reload_objects()
        self.assertEqual(self.site_profile.total_outgoing_request_count, 1)
        self.assertEqual(self.site_profile.pending_outgoing_request_count, 1)
        self.assertEqual(self.site_profile.direct_incoming_request_count, 0)
        self.assertEqual(self.site_profile.total_incoming_request_count, 0)
        self.assertEqual(self.site_profile.starred_public_request_count, 0)
        self.assertEqual(self.site_profile2.total_outgoing_request_count, 0)
        self.assertEqual(self.site_profile2.pending_outgoing_request_count, 0)
        self.assertEqual(self.site_profile2.direct_incoming_request_count, 0)
        self.assertEqual(self.site_profile2.total_incoming_request_count, 0)
        self.assertEqual(self.site_profile2.starred_public_request_count, 0)
        self.assertEqual(self.group.incoming_request_count, 0)

    def test_add_group(self):
        """Testing counters when adding a group reviewer"""
        draft = ReviewRequestDraft.create(self.review_request)
        draft.target_groups.add(self.group)

        self.assertEqual(self.site_profile.total_incoming_request_count, 0)
        self.assertEqual(self.site_profile2.total_incoming_request_count, 0)
        self.assertEqual(self.group.incoming_request_count, 0)

        self.review_request.publish(self.user)

        self._reload_objects()
        self.assertEqual(self.site_profile.direct_incoming_request_count, 0)
        self.assertEqual(self.site_profile.total_incoming_request_count, 1)
        self.assertEqual(self.site_profile2.direct_incoming_request_count, 0)
        self.assertEqual(self.site_profile2.total_incoming_request_count, 0)
        self.assertEqual(self.group.incoming_request_count, 1)

    def test_remove_group(self):
        """Testing counters when removing a group reviewer"""
        self.test_add_group()

        draft = ReviewRequestDraft.create(self.review_request)
        draft.target_groups.remove(self.group)

        self.assertEqual(self.site_profile.total_incoming_request_count, 1)
        self.assertEqual(self.site_profile2.total_incoming_request_count, 0)
        self.assertEqual(self.group.incoming_request_count, 1)

        self.review_request.publish(self.user)

        self._reload_objects()
        self.assertEqual(self.site_profile.direct_incoming_request_count, 0)
        self.assertEqual(self.site_profile.total_incoming_request_count, 0)
        self.assertEqual(self.site_profile2.direct_incoming_request_count, 0)
        self.assertEqual(self.site_profile2.total_incoming_request_count, 0)
        self.assertEqual(self.group.incoming_request_count, 0)

    def test_add_person(self):
        """Testing counters when adding a person reviewer"""
        draft = ReviewRequestDraft.create(self.review_request)
        draft.target_people.add(self.user)

        self.assertEqual(self.site_profile.direct_incoming_request_count, 0)
        self.assertEqual(self.site_profile2.direct_incoming_request_count, 0)

        self.review_request.publish(self.user)

        self._reload_objects()
        self.assertEqual(self.site_profile.direct_incoming_request_count, 1)
        self.assertEqual(self.site_profile.total_incoming_request_count, 1)
        self.assertEqual(self.site_profile2.direct_incoming_request_count, 0)
        self.assertEqual(self.site_profile2.total_incoming_request_count, 0)

    def test_remove_person(self):
        """Testing counters when removing a person reviewer"""
        self.test_add_person()

        draft = ReviewRequestDraft.create(self.review_request)
        draft.target_people.remove(self.user)

        self.assertEqual(self.site_profile.direct_incoming_request_count, 1)
        self.assertEqual(self.site_profile.total_incoming_request_count, 1)
        self.assertEqual(self.site_profile2.direct_incoming_request_count, 0)
        self.assertEqual(self.site_profile2.total_incoming_request_count, 0)

        self.review_request.publish(self.user)

        self._reload_objects()
        self.assertEqual(self.site_profile.direct_incoming_request_count, 0)
        self.assertEqual(self.site_profile.total_incoming_request_count, 0)
        self.assertEqual(self.site_profile2.direct_incoming_request_count, 0)
        self.assertEqual(self.site_profile2.total_incoming_request_count, 0)

    def test_populate_counters(self):
        """Testing counters when populated from a fresh upgrade or clear"""
        # The review request was already created
        draft = ReviewRequestDraft.create(self.review_request)
        draft.target_groups.add(self.group)
        draft.target_people.add(self.user)
        self.review_request.publish(self.user)

        self._reload_objects()
        self.assertEqual(self.site_profile.direct_incoming_request_count, 1)
        self.assertEqual(self.site_profile.total_incoming_request_count, 1)
        self.assertEqual(self.site_profile.starred_public_request_count, 1)
        self.assertEqual(self.site_profile2.direct_incoming_request_count, 0)
        self.assertEqual(self.site_profile2.total_incoming_request_count, 0)
        self.assertEqual(self.site_profile2.starred_public_request_count, 0)
        self.assertEqual(self.group.incoming_request_count, 1)

        LocalSiteProfile.objects.update(
            direct_incoming_request_count=None,
            total_incoming_request_count=None,
            pending_outgoing_request_count=None,
            total_outgoing_request_count=None,
            starred_public_request_count=None)
        Group.objects.update(incoming_request_count=None)

        self._reload_objects()
        self.assertEqual(self.site_profile.direct_incoming_request_count, 1)
        self.assertEqual(self.site_profile.total_incoming_request_count, 1)
        self.assertEqual(self.site_profile.starred_public_request_count, 1)
        self.assertEqual(self.site_profile2.direct_incoming_request_count, 0)
        self.assertEqual(self.site_profile2.total_incoming_request_count, 0)
        self.assertEqual(self.site_profile2.starred_public_request_count, 0)
        self.assertEqual(self.group.incoming_request_count, 1)

    def test_populate_counters_after_change(self):
        """Testing counter inc/dec on uninitialized counter fields"""
        # The review request was already created
        draft = ReviewRequestDraft.create(self.review_request)
        draft.target_groups.add(self.group)
        draft.target_people.add(self.user)

        LocalSiteProfile.objects.update(
            direct_incoming_request_count=None,
            total_incoming_request_count=None,
            pending_outgoing_request_count=None,
            total_outgoing_request_count=None,
            starred_public_request_count=None)
        Group.objects.update(incoming_request_count=None)

        profile_fields = [
            'direct_incoming_request_count',
            'total_incoming_request_count',
            'pending_outgoing_request_count',
            'total_outgoing_request_count',
            'starred_public_request_count',
        ]

        # Lock the fields so we don't re-initialize them on publish.
        locks = {
            self.site_profile: 1,
            self.site_profile2: 1,
        }

        for field in profile_fields:
            getattr(LocalSiteProfile, field)._locks = locks

        Group.incoming_request_count._locks = locks

        # Publish the review request. This will normally try to
        # increment/decrement the counts, which it should ignore now.
        self.review_request.publish(self.user)

        # Unlock the profiles so we can query/re-initialize them again.
        for field in profile_fields:
            getattr(LocalSiteProfile, field)._locks = {}

        Group.incoming_request_count._locks = {}

        self._reload_objects()
        self.assertEqual(self.site_profile.direct_incoming_request_count, 1)
        self.assertEqual(self.site_profile.total_incoming_request_count, 1)
        self.assertEqual(self.site_profile.starred_public_request_count, 1)
        self.assertEqual(self.site_profile2.direct_incoming_request_count, 0)
        self.assertEqual(self.site_profile2.total_incoming_request_count, 0)
        self.assertEqual(self.site_profile2.starred_public_request_count, 0)
        self.assertEqual(self.group.incoming_request_count, 1)

    def _reload_objects(self):
        self.test_site = LocalSite.objects.get(pk=self.test_site.pk)
        self.site_profile = \
            LocalSiteProfile.objects.get(pk=self.site_profile.pk)
        self.site_profile2 = \
            LocalSiteProfile.objects.get(pk=self.site_profile2.pk)
        self.group = Group.objects.get(pk=self.group.pk)


class PolicyTests(TestCase):
    fixtures = ['test_users', 'test_reviewrequests', 'test_scmtools',
                'test_site']

    def setUp(self):
        self.user = User.objects.create(username='testuser', password='')
        self.anonymous = AnonymousUser()

    def test_group_public(self):
        """Testing access to a public review group"""
        group = Group.objects.create(name='test-group')

        self.assertFalse(group.invite_only)
        self.assertTrue(group.is_accessible_by(self.user))
        self.assertTrue(group.is_accessible_by(self.anonymous))

        self.assertTrue(group in Group.objects.accessible(self.user))
        self.assertTrue(group in Group.objects.accessible(self.anonymous))

    def test_group_invite_only_access_denied(self):
        """Testing no access to unjoined invite-only group"""
        group = Group.objects.create(name='test-group', invite_only=True)

        self.assertTrue(group.invite_only)
        self.assertFalse(group.is_accessible_by(self.user))
        self.assertFalse(group.is_accessible_by(self.anonymous))

        self.assertFalse(group in Group.objects.accessible(self.user))
        self.assertFalse(group in Group.objects.accessible(self.anonymous))

    def test_group_invite_only_access_allowed(self):
        """Testing access to joined invite-only group"""
        group = Group.objects.create(name='test-group', invite_only=True)
        group.users.add(self.user)

        self.assertTrue(group.invite_only)
        self.assertTrue(group.is_accessible_by(self.user))
        self.assertFalse(group.is_accessible_by(self.anonymous))

        self.assertTrue(group in Group.objects.accessible(self.user))
        self.assertFalse(group in Group.objects.accessible(self.anonymous))

    def test_group_public_hidden(self):
        """Testing visibility of a hidden public group"""
        group = Group.objects.create(name='test-group', visible=False)

        self.assertFalse(group.visible)
        self.assertTrue(group.is_accessible_by(self.user))
        self.assertTrue(
            group in Group.objects.accessible(self.user, visible_only=False))
        self.assertFalse(
            group in Group.objects.accessible(self.user, visible_only=True))

    def test_group_invite_only_hidden_access_denied(self):
        """Testing visibility of a hidden unjoined invite-only group"""
        group = Group.objects.create(name='test-group', visible=False,
                                     invite_only=True)

        self.assertFalse(group.visible)
        self.assertTrue(group.invite_only)
        self.assertFalse(group.is_accessible_by(self.user))
        self.assertFalse(
            group in Group.objects.accessible(self.user, visible_only=False))
        self.assertFalse(
            group in Group.objects.accessible(self.user, visible_only=True))

    def test_group_invite_only_hidden_access_allowed(self):
        """Testing visibility of a hidden joined invite-only group"""
        group = Group.objects.create(name='test-group', visible=False,
                                     invite_only=True)
        group.users.add(self.user)

        self.assertFalse(group.visible)
        self.assertTrue(group.invite_only)
        self.assertTrue(group.is_accessible_by(self.user))
        self.assertTrue(
            group in Group.objects.accessible(self.user, visible_only=False))
        self.assertTrue(
            group in Group.objects.accessible(self.user, visible_only=True))

    def test_repository_public(self):
        """Testing access to a public repository"""
        tool = Tool.objects.get(name='CVS')
        repo = Repository.objects.create(name='Test1', path='path1', tool=tool)

        self.assertTrue(repo.public)
        self.assertTrue(repo.is_accessible_by(self.user))
        self.assertTrue(repo.is_accessible_by(self.anonymous))

    def test_repository_private_access_denied(self):
        """Testing no access to a private repository"""
        tool = Tool.objects.get(name='CVS')
        repo = Repository.objects.create(name='Test1', path='path1', tool=tool,
                                         public=False)

        self.assertFalse(repo.public)
        self.assertFalse(repo.is_accessible_by(self.user))
        self.assertFalse(repo.is_accessible_by(self.anonymous))

    def test_repository_private_access_allowed_by_user(self):
        """Testing access to a private repository with user added"""
        tool = Tool.objects.get(name='CVS')
        repo = Repository.objects.create(name='Test1', path='path1', tool=tool,
                                         public=False)
        repo.users.add(self.user)

        self.assertFalse(repo.public)
        self.assertTrue(repo.is_accessible_by(self.user))
        self.assertFalse(repo.is_accessible_by(self.anonymous))

    def test_repository_private_access_allowed_by_review_group(self):
        """Testing access to a private repository with joined review group added"""
        group = Group.objects.create(name='test-group', invite_only=True)
        group.users.add(self.user)

        tool = Tool.objects.get(name='CVS')
        repo = Repository.objects.create(name='Test1', path='path1', tool=tool,
                                         public=False)
        repo.review_groups.add(group)

        self.assertFalse(repo.public)
        self.assertTrue(repo.is_accessible_by(self.user))
        self.assertFalse(repo.is_accessible_by(self.anonymous))

    def test_review_request_public(self):
        """Testing access to a public review request"""
        review_request = self._get_review_request()

        self.assertTrue(review_request.is_accessible_by(self.user))
        self.assertTrue(review_request.is_accessible_by(self.anonymous))

    def test_review_request_with_invite_only_group(self):
        """Testing no access to a review request with only an unjoined invite-only group"""
        group = Group(name='test-group', invite_only=True)
        group.save()

        review_request = self._get_review_request()
        review_request.target_groups.add(group)

        self.assertFalse(review_request.is_accessible_by(self.user))
        self.assertFalse(review_request.is_accessible_by(self.anonymous))

    def test_review_request_with_invite_only_group_and_target_user(self):
        """Testing access to a review request with specific target user and invite-only group"""
        group = Group(name='test-group', invite_only=True)
        group.save()

        review_request = self._get_review_request()
        review_request.target_groups.add(group)
        review_request.target_people.add(self.user)

        self.assertTrue(review_request.is_accessible_by(self.user))
        self.assertFalse(review_request.is_accessible_by(self.anonymous))

    def test_review_request_with_private_repository(self):
        """Testing no access to a review request with a private repository"""
        Group.objects.create(name='test-group', invite_only=True)

        review_request = self._get_review_request()
        review_request.save()

        review_request.repository.public = False
        review_request.repository.save()

        self.assertFalse(review_request.is_accessible_by(self.user))
        self.assertFalse(review_request.is_accessible_by(self.anonymous))

    def test_review_request_with_private_repository_allowed_by_user(self):
        """Testing access to a review request with a private repository with user added"""
        Group.objects.create(name='test-group', invite_only=True)

        review_request = self._get_review_request()
        review_request.save()

        review_request.repository.public = False
        review_request.repository.users.add(self.user)
        review_request.repository.save()

        self.assertTrue(review_request.is_accessible_by(self.user))
        self.assertFalse(review_request.is_accessible_by(self.anonymous))

    def test_review_request_with_private_repository_allowed_by_review_group(self):
        """Testing access to a review request with a private repository with review group added"""
        group = Group.objects.create(name='test-group', invite_only=True)
        group.users.add(self.user)

        review_request = self._get_review_request()
        review_request.save()

        review_request.repository.public = False
        review_request.repository.review_groups.add(group)
        review_request.repository.save()

        self.assertTrue(review_request.is_accessible_by(self.user))
        self.assertFalse(review_request.is_accessible_by(self.anonymous))

    def _get_review_request(self, local_site=None):
        # Get a review request and clear out the reviewers.
        review_request = ReviewRequest.objects.public(local_site=local_site)[0]
        review_request.target_people.clear()
        review_request.target_groups.clear()
        return review_request


class UserInfoboxTests(TestCase):
    def testUnicode(self):
        """Testing user_infobox with a user with non-ascii characters"""
        user = User.objects.create_user('test', 'test@example.com')
        user.first_name = u'Test\u21b9'
        user.last_name = u'User\u2729'
        user.save()

        self.client.get(local_site_reverse('user-infobox', args=['test']))
