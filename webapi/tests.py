import os

from django.contrib.auth.models import User, Permission
from django.test import TestCase
from django.utils import simplejson

import reviewboard.webapi.json as webapi
from reviewboard.diffviewer.models import DiffSet
from reviewboard.reviews.models import Group, ReviewRequest, \
                                       ReviewRequestDraft, Review, \
                                       Comment, Screenshot, ScreenshotComment
from reviewboard.scmtools.models import Repository, Tool


class WebAPITests(TestCase):
    """Testing the webapi support."""
    fixtures = ['test_users', 'test_reviewrequests', 'test_scmtools']

    def setUp(self):
        svn_repo_path = os.path.join(os.path.dirname(__file__),
                                     '../scmtools/testdata/svn_repo')
        self.repository = Repository(name='Subversion SVN',
                                     path='file://' + svn_repo_path,
                                     tool=Tool.objects.get(name='Subversion'))
        self.repository.save()

        self.client.login(username="grumpy", password="grumpy")
        self.user = User.objects.get(username="grumpy")

    def tearDown(self):
        self.client.logout()

    def apiGet(self, path, query={}):
        print "Getting /api/json/%s/" % path
        print "Query data: %s" % query
        response = self.client.get("/api/json/%s/" % path, query)
        self.assertEqual(response.status_code, 200)
        print "Raw response: %s" % response.content
        rsp = simplejson.loads(response.content)
        print "Response: %s" % rsp
        return rsp

    def apiPost(self, path, query={}):
        print "Posting to /api/json/%s/" % path
        print "Post data: %s" % query
        response = self.client.post("/api/json/%s/" % path, query)
        self.assertEqual(response.status_code, 200)
        print "Raw response: %s" % response.content
        rsp = simplejson.loads(response.content)
        print "Response: %s" % rsp
        return rsp

    def testRepositoryList(self):
        """Testing the repositories API"""
        rsp = self.apiGet("repositories")
        self.assertEqual(rsp['stat'], 'ok')
        self.assertEqual(len(rsp['repositories']), Repository.objects.count())

    def testUserList(self):
        """Testing the users API"""
        rsp = self.apiGet("users")
        self.assertEqual(rsp['stat'], 'ok')
        self.assertEqual(len(rsp['users']), User.objects.count())

    def testUserListQuery(self):
        """Testing the users API with custom query"""
        rsp = self.apiGet("users", {'query': 'gru'})
        self.assertEqual(rsp['stat'], 'ok')
        self.assertEqual(len(rsp['users']), 1) # grumpy

    def testGroupList(self):
        """Testing the groups API"""
        rsp = self.apiGet("groups")
        self.assertEqual(rsp['stat'], 'ok')
        self.assertEqual(len(rsp['groups']), Group.objects.count())

    def testGroupListQuery(self):
        """Testing the groups API with custom query"""
        rsp = self.apiGet("groups", {'query': 'dev'})
        self.assertEqual(rsp['stat'], 'ok')
        self.assertEqual(len(rsp['groups']), 1) #devgroup

    def testGroupStar(self):
        """Testing the groups/star API"""
        rsp = self.apiGet("groups/devgroup/star")
        self.assertEqual(rsp['stat'], 'ok')
        self.assert_(Group.objects.get(name="devgroup") in
                     self.user.get_profile().starred_groups.all())

    def testGroupStarDoesNotExist(self):
        """Testing the groups/star API with Does Not Exist error"""
        rsp = self.apiGet("groups/invalidgroup/star")
        self.assertEqual(rsp['stat'], 'fail')
        self.assertEqual(rsp['err']['code'], webapi.DOES_NOT_EXIST.code)

    def testGroupUnstar(self):
        """Testing the groups/unstar API"""
        # First, star it.
        self.testGroupStar()

        rsp = self.apiGet("groups/devgroup/unstar")
        self.assertEqual(rsp['stat'], 'ok')
        self.assert_(Group.objects.get(name="devgroup") not in
                     self.user.get_profile().starred_groups.all())

    def testGroupUnstarDoesNotExist(self):
        """Testing the groups/unstar API with Does Not Exist error"""
        rsp = self.apiGet("groups/invalidgroup/unstar")
        self.assertEqual(rsp['stat'], 'fail')
        self.assertEqual(rsp['err']['code'], webapi.DOES_NOT_EXIST.code)

    def testReviewRequestList(self):
        """Testing the reviewrequests/all API"""
        rsp = self.apiGet("reviewrequests/all")
        self.assertEqual(rsp['stat'], 'ok')
        self.assertEqual(len(rsp['review_requests']),
                         ReviewRequest.objects.public().count())

    def testReviewRequestListWithStatus(self):
        """Testing the reviewrequests/all API with custom status"""
        rsp = self.apiGet("reviewrequests/all", {'status': 'submitted'})
        self.assertEqual(rsp['stat'], 'ok')
        self.assertEqual(len(rsp['review_requests']),
                         ReviewRequest.objects.public(status='S').count())

        rsp = self.apiGet("reviewrequests/all", {'status': 'discarded'})
        self.assertEqual(rsp['stat'], 'ok')
        self.assertEqual(len(rsp['review_requests']),
                         ReviewRequest.objects.public(status='D').count())

        rsp = self.apiGet("reviewrequests/all", {'status': 'all'})
        self.assertEqual(rsp['stat'], 'ok')
        self.assertEqual(len(rsp['review_requests']),
                         ReviewRequest.objects.public(status=None).count())

    def testReviewRequestListCount(self):
        """Testing the reviewrequests/all/count API"""
        rsp = self.apiGet("reviewrequests/all/count")
        self.assertEqual(rsp['stat'], 'ok')
        self.assertEqual(rsp['count'], ReviewRequest.objects.public().count())

    def testReviewRequestsToGroup(self):
        """Testing the reviewrequests/to/group API"""
        rsp = self.apiGet("reviewrequests/to/group/devgroup")
        self.assertEqual(rsp['stat'], 'ok')
        self.assertEqual(len(rsp['review_requests']),
                         ReviewRequest.objects.to_group("devgroup").count())

    def testReviewRequestsToGroupWithStatus(self):
        """Testing the reviewrequests/to/group API with custom status"""
        rsp = self.apiGet("reviewrequests/to/group/devgroup",
                          {'status': 'submitted'})
        self.assertEqual(rsp['stat'], 'ok')
        self.assertEqual(len(rsp['review_requests']),
            ReviewRequest.objects.to_group("devgroup", status='S').count())

        rsp = self.apiGet("reviewrequests/to/group/devgroup",
                          {'status': 'discarded'})
        self.assertEqual(rsp['stat'], 'ok')
        self.assertEqual(len(rsp['review_requests']),
            ReviewRequest.objects.to_group("devgroup", status='D').count())

    def testReviewRequestsToGroupCount(self):
        """Testing the reviewrequests/to/group/count API"""
        rsp = self.apiGet("reviewrequests/to/group/devgroup/count")
        self.assertEqual(rsp['stat'], 'ok')
        self.assertEqual(rsp['count'],
                         ReviewRequest.objects.to_group("devgroup").count())

    def testReviewRequestsToUser(self):
        """Testing the reviewrequests/to/user API"""
        rsp = self.apiGet("reviewrequests/to/user/grumpy")
        self.assertEqual(rsp['stat'], 'ok')
        self.assertEqual(len(rsp['review_requests']),
                         ReviewRequest.objects.to_user("grumpy").count())

    def testReviewRequestsToUserWithStatus(self):
        """Testing the reviewrequests/to/user API with custom status"""
        rsp = self.apiGet("reviewrequests/to/user/grumpy",
                          {'status': 'submitted'})
        self.assertEqual(rsp['stat'], 'ok')
        self.assertEqual(len(rsp['review_requests']),
            ReviewRequest.objects.to_user("grumpy", status='S').count())

        rsp = self.apiGet("reviewrequests/to/user/grumpy",
                          {'status': 'discarded'})
        self.assertEqual(rsp['stat'], 'ok')
        self.assertEqual(len(rsp['review_requests']),
            ReviewRequest.objects.to_user("grumpy", status='D').count())

    def testReviewRequestsToUserCount(self):
        """Testing the reviewrequests/to/user/count API"""
        rsp = self.apiGet("reviewrequests/to/user/grumpy/count")
        self.assertEqual(rsp['stat'], 'ok')
        self.assertEqual(rsp['count'],
                         ReviewRequest.objects.to_user("grumpy").count())

    def testReviewRequestsToUserDirectly(self):
        """Testing the reviewrequests/to/user/directly API"""
        rsp = self.apiGet("reviewrequests/to/user/doc/directly")
        self.assertEqual(rsp['stat'], 'ok')
        self.assertEqual(len(rsp['review_requests']),
                         ReviewRequest.objects.to_user_directly("doc").count())

    def testReviewRequestsToUserDirectlyWithStatus(self):
        """Testing the reviewrequests/to/user/directly API with custom status"""
        rsp = self.apiGet("reviewrequests/to/user/doc/directly",
                          {'status': 'submitted'})
        self.assertEqual(rsp['stat'], 'ok')
        self.assertEqual(len(rsp['review_requests']),
            ReviewRequest.objects.to_user_directly("doc", status='S').count())

        rsp = self.apiGet("reviewrequests/to/user/doc/directly",
                          {'status': 'discarded'})
        self.assertEqual(rsp['stat'], 'ok')
        self.assertEqual(len(rsp['review_requests']),
            ReviewRequest.objects.to_user_directly("doc", status='D').count())

    def testReviewRequestsToUserDirectlyCount(self):
        """Testing the reviewrequests/to/user/directly/count API"""
        rsp = self.apiGet("reviewrequests/to/user/doc/directly/count")
        self.assertEqual(rsp['stat'], 'ok')
        self.assertEqual(rsp['count'],
                         ReviewRequest.objects.to_user_directly("doc").count())

    def testReviewRequestsFromUser(self):
        """Testing the reviewrequests/from/user API"""
        rsp = self.apiGet("reviewrequests/from/user/grumpy")
        self.assertEqual(rsp['stat'], 'ok')
        self.assertEqual(len(rsp['review_requests']),
                         ReviewRequest.objects.from_user("grumpy").count())

    def testReviewRequestsFromUserWithStatus(self):
        """Testing the reviewrequests/from/user API with custom status"""
        rsp = self.apiGet("reviewrequests/from/user/grumpy",
                          {'status': 'submitted'})
        self.assertEqual(rsp['stat'], 'ok')
        self.assertEqual(len(rsp['review_requests']),
            ReviewRequest.objects.from_user("grumpy", status='S').count())

        rsp = self.apiGet("reviewrequests/from/user/grumpy",
                          {'status': 'discarded'})
        self.assertEqual(rsp['stat'], 'ok')
        self.assertEqual(len(rsp['review_requests']),
            ReviewRequest.objects.from_user("grumpy", status='D').count())

    def testReviewRequestsFromUserCount(self):
        """Testing the reviewrequests/from/user/count API"""
        rsp = self.apiGet("reviewrequests/from/user/grumpy/count")
        self.assertEqual(rsp['stat'], 'ok')
        self.assertEqual(rsp['count'],
                         ReviewRequest.objects.from_user("grumpy").count())

    def testNewReviewRequest(self):
        """Testing the reviewrequests/new API"""
        rsp = self.apiPost("reviewrequests/new", {
            'repository_path': self.repository.path,
        })
        self.assertEqual(rsp['stat'], 'ok')
        self.assertEqual(rsp['review_request']['repository']['id'],
                         self.repository.id)

        # See if we can fetch this. Also return it for use in other
        # unit tests.
        return ReviewRequest.objects.get(pk=rsp['review_request']['id'])

    def testNewReviewRequestWithInvalidRepository(self):
        """Testing the reviewrequests/new API with Invalid Repository error"""
        rsp = self.apiPost("reviewrequests/new", {
            'repository_path': 'gobbledygook',
        })
        self.assertEqual(rsp['stat'], 'fail')
        self.assertEqual(rsp['err']['code'], webapi.INVALID_REPOSITORY.code)

    def testNewReviewRequestAsUser(self):
        """Testing the reviewrequests/new API with submit_as"""
        self.user.is_superuser = True
        self.user.save()

        rsp = self.apiPost("reviewrequests/new", {
            'repository_path': self.repository.path,
            'submit_as': 'doc',
        })
        self.assertEqual(rsp['stat'], 'ok')
        self.assertEqual(rsp['review_request']['repository']['id'],
                         self.repository.id)
        self.assertEqual(rsp['review_request']['submitter']['username'], 'doc')

        ReviewRequest.objects.get(pk=rsp['review_request']['id'])

    def testNewReviewRequestAsUserPermissionDenied(self):
        """Testing the reviewrequests/new API with submit_as and Permission Denied error"""
        rsp = self.apiPost("reviewrequests/new", {
            'repository_path': self.repository.path,
            'submit_as': 'doc',
        })
        self.assertEqual(rsp['stat'], 'fail')
        self.assertEqual(rsp['err']['code'], webapi.PERMISSION_DENIED.code)

    def testReviewRequest(self):
        """Testing the reviewrequests/<id> API"""
        review_request = ReviewRequest.objects.public()[0]
        rsp = self.apiGet("reviewrequests/%s" % review_request.id)
        self.assertEqual(rsp['stat'], 'ok')
        self.assertEqual(rsp['review_request']['id'], review_request.id)
        self.assertEqual(rsp['review_request']['summary'],
                         review_request.summary)

    def testReviewRequestPermissionDenied(self):
        """Testing the reviewrequests/<id> API with Permission Denied error"""
        review_request = ReviewRequest.objects.filter(public=False).\
            exclude(submitter=self.user)[0]
        rsp = self.apiGet("reviewrequests/%s" % review_request.id)
        self.assertEqual(rsp['stat'], 'fail')
        self.assertEqual(rsp['err']['code'], webapi.PERMISSION_DENIED.code)

    def testReviewRequestByChangenum(self):
        """Testing the reviewrequests/repository/changenum API"""
        review_request = \
            ReviewRequest.objects.filter(changenum__isnull=False)[0]
        rsp = self.apiGet("reviewrequests/repository/%s/changenum/%s" %
                          (review_request.repository.id,
                           review_request.changenum))
        self.assertEqual(rsp['stat'], 'ok')
        self.assertEqual(rsp['review_request']['id'], review_request.id)
        self.assertEqual(rsp['review_request']['summary'],
                         review_request.summary)
        self.assertEqual(rsp['review_request']['changenum'],
                         review_request.changenum)

    def testReviewRequestStar(self):
        """Testing the reviewrequests/star API"""
        review_request = ReviewRequest.objects.public()[0]
        rsp = self.apiGet("reviewrequests/%s/star" % review_request.id)
        self.assertEqual(rsp['stat'], 'ok')
        self.assert_(review_request in
                     self.user.get_profile().starred_review_requests.all())

    def testReviewRequestStarDoesNotExist(self):
        """Testing the reviewrequests/star API with Does Not Exist error"""
        rsp = self.apiGet("reviewrequests/999/star")
        self.assertEqual(rsp['stat'], 'fail')
        self.assertEqual(rsp['err']['code'], webapi.DOES_NOT_EXIST.code)

    def testReviewRequestUnstar(self):
        """Testing the reviewrequests/unstar API"""
        # First, star it.
        self.testReviewRequestStar()

        review_request = ReviewRequest.objects.public()[0]
        rsp = self.apiGet("reviewrequests/%s/unstar" % review_request.id)
        self.assertEqual(rsp['stat'], 'ok')
        self.assert_(review_request not in
                     self.user.get_profile().starred_review_requests.all())

    def testReviewRequestUnstarWithDoesNotExist(self):
        """Testing the reviewrequests/unstar API with Does Not Exist error"""
        rsp = self.apiGet("reviewrequests/999/unstar")
        self.assertEqual(rsp['stat'], 'fail')
        self.assertEqual(rsp['err']['code'], webapi.DOES_NOT_EXIST.code)

    def testReviewRequestDelete(self):
        """Testing the reviewrequests/delete API"""
        self.user.user_permissions.add(
            Permission.objects.get(codename='delete_reviewrequest'))
        self.user.save()
        self.assert_(self.user.has_perm('reviews.delete_reviewrequest'))

        review_request_id = \
            ReviewRequest.objects.from_user(self.user.username)[0].id
        rsp = self.apiGet("reviewrequests/%s/delete" % review_request_id)
        self.assertEqual(rsp['stat'], 'ok')
        self.assertRaises(ReviewRequest.DoesNotExist,
                          ReviewRequest.objects.get, pk=review_request_id)

    def testReviewRequestDeletePermissionDenied(self):
        """Testing the reviewrequests/delete API with Permission Denied error"""
        review_request_id = \
            ReviewRequest.objects.exclude(submitter=self.user)[0].id
        rsp = self.apiGet("reviewrequests/%s/delete" % review_request_id)
        self.assertEqual(rsp['stat'], 'fail')
        self.assertEqual(rsp['err']['code'], webapi.PERMISSION_DENIED.code)

    def testReviewRequestDeleteDoesNotExist(self):
        """Testing the reviewrequests/delete API with Does Not Exist error"""
        self.user.user_permissions.add(
            Permission.objects.get(codename='delete_reviewrequest'))
        self.user.save()
        self.assert_(self.user.has_perm('reviews.delete_reviewrequest'))

        rsp = self.apiGet("reviewrequests/999/delete")
        self.assertEqual(rsp['stat'], 'fail')
        self.assertEqual(rsp['err']['code'], webapi.DOES_NOT_EXIST.code)

    def testReviewRequestDraftSet(self):
        """Testing the reviewrequests/draft/set API"""
        summary = "My Summary"
        description = "My Description"
        testing_done = "My Testing Done"
        branch = "My Branch"
        bugs = ""

        review_request_id = \
            ReviewRequest.objects.from_user(self.user.username)[0].id
        rsp = self.apiPost("reviewrequests/%s/draft/set" % review_request_id, {
            'summary': summary,
            'description': description,
            'testing_done': testing_done,
            'branch': branch,
            'bugs_closed': bugs,
        })

        self.assertEqual(rsp['stat'], 'ok')
        self.assertEqual(rsp['draft']['summary'], summary)
        self.assertEqual(rsp['draft']['description'], description)
        self.assertEqual(rsp['draft']['testing_done'], testing_done)
        self.assertEqual(rsp['draft']['branch'], branch)
        self.assertEqual(rsp['draft']['bugs_closed'], [])

        draft = ReviewRequestDraft.objects.get(pk=rsp['draft']['id'])
        self.assertEqual(draft.summary, summary)
        self.assertEqual(draft.description, description)
        self.assertEqual(draft.testing_done, testing_done)
        self.assertEqual(draft.branch, branch)
        self.assertEqual(draft.get_bug_list(), [])

    def testReviewRequestDraftSetField(self):
        """Testing the reviewrequests/draft/set/<field> API"""
        bugs_closed = '123,456'
        review_request_id = \
            ReviewRequest.objects.from_user(self.user.username)[0].id
        rsp = self.apiPost("reviewrequests/%s/draft/set/bugs_closed" %
                           review_request_id, {
            'value': bugs_closed,
        })

        self.assertEqual(rsp['stat'], 'ok')
        self.assertEqual(rsp['bugs_closed'], bugs_closed.split(","))

    def testReviewRequestDraftSetFieldInvalidName(self):
        """Testing the reviewrequests/draft/set/<field> API with invalid name"""
        review_request_id = \
            ReviewRequest.objects.from_user(self.user.username)[0].id
        rsp = self.apiPost("reviewrequests/%s/draft/set/foobar" %
                           review_request_id, {
            'value': 'foo',
        })

        self.assertEqual(rsp['stat'], 'fail')
        self.assertEqual(rsp['err']['code'], webapi.INVALID_ATTRIBUTE.code)
        self.assertEqual(rsp['attribute'], 'foobar')

    def testReviewRequestDraftSave(self):
        """Testing the reviewrequests/draft/save API"""
        # Set some data first.
        self.testReviewRequestDraftSet()

        review_request_id = \
            ReviewRequest.objects.from_user(self.user.username)[0].id
        rsp = self.apiPost("reviewrequests/%s/draft/save" % review_request_id)

        self.assertEqual(rsp['stat'], 'ok')

        review_request = ReviewRequest.objects.get(pk=review_request_id)
        self.assertEqual(review_request.summary, "My Summary")
        self.assertEqual(review_request.description, "My Description")
        self.assertEqual(review_request.testing_done, "My Testing Done")
        self.assertEqual(review_request.branch, "My Branch")

    def testReviewRequestDraftSaveDoesNotExist(self):
        """Testing the reviewrequests/draft/save API with Does Not Exist error"""
        review_request_id = \
            ReviewRequest.objects.from_user(self.user.username)[0].id
        rsp = self.apiPost("reviewrequests/%s/draft/save" % review_request_id)

        self.assertEqual(rsp['stat'], 'fail')
        self.assertEqual(rsp['err']['code'], webapi.DOES_NOT_EXIST.code)

    def testReviewRequestDraftDiscard(self):
        """Testing the reviewrequests/draft/discard API"""
        review_request = ReviewRequest.objects.from_user(self.user.username)[0]
        summary = review_request.summary
        description = review_request.description

        # Set some data.
        self.testReviewRequestDraftSet()

        rsp = self.apiPost("reviewrequests/%s/draft/discard" %
                           review_request.id)
        self.assertEqual(rsp['stat'], 'ok')

        review_request = ReviewRequest.objects.get(pk=review_request.id)
        self.assertEqual(review_request.summary, summary)
        self.assertEqual(review_request.description, description)

    def testReviewDraftSave(self):
        """Testing the reviewrequests/reviews/draft/save API"""
        body_top = ""
        body_bottom = "My Body Bottom"
        ship_it = True

        # Clear out any reviews on the first review request we find.
        review_request = ReviewRequest.objects.public()[0]
        review_request.reviews = []
        review_request.save()

        rsp = self.apiPost("reviewrequests/%s/reviews/draft/save" %
                           review_request.id, {
            'shipit': ship_it,
            'body_top': body_top,
            'body_bottom': body_bottom,
        })

        reviews = review_request.reviews.filter(user=self.user)
        self.assertEqual(len(reviews), 1)
        review = reviews[0]

        self.assertEqual(review.ship_it, ship_it)
        self.assertEqual(review.body_top, body_top)
        self.assertEqual(review.body_bottom, body_bottom)
        self.assertEqual(review.public, False)

    def testReviewDraftPublish(self):
        """Testing the reviewrequests/reviews/draft/publish API"""
        body_top = "My Body Top"
        body_bottom = ""
        ship_it = True

        # Clear out any reviews on the first review request we find.
        review_request = ReviewRequest.objects.public()[0]
        review_request.reviews = []
        review_request.save()

        rsp = self.apiPost("reviewrequests/%s/reviews/draft/publish" %
                           review_request.id, {
            'shipit': ship_it,
            'body_top': body_top,
            'body_bottom': body_bottom,
        })

        self.assertEqual(rsp['stat'], 'ok')

        reviews = review_request.reviews.filter(user=self.user)
        self.assertEqual(len(reviews), 1)
        review = reviews[0]

        self.assertEqual(review.ship_it, ship_it)
        self.assertEqual(review.body_top, body_top)
        self.assertEqual(review.body_bottom, body_bottom)
        self.assertEqual(review.public, True)

    def testReviewDraftDelete(self):
        """Testing the reviewrequests/reviews/draft/delete API"""
        # Set up the draft to delete.
        self.testReviewDraftSave()

        review_request = ReviewRequest.objects.public()[0]
        rsp = self.apiPost("reviewrequests/%s/reviews/draft/delete" %
                           review_request.id)
        self.assertEqual(rsp['stat'], 'ok')
        self.assertEqual(review_request.reviews.count(), 0)

    def testReviewDraftDeleteDoesNotExist(self):
        """Testing the reviewrequests/reviews/draft/delete API with Does Not Exist error"""
        # Set up the draft to delete
        self.testReviewDraftPublish()

        review_request = ReviewRequest.objects.public()[0]
        rsp = self.apiPost("reviewrequests/%s/reviews/draft/delete" %
                           review_request.id)
        self.assertEqual(rsp['stat'], 'fail')
        self.assertEqual(rsp['err']['code'], webapi.DOES_NOT_EXIST.code)

    def testReviewDraftComments(self):
        """Testing the reviewrequests/reviews/draft/comments API"""
        diff_comment_text = "Test diff comment"
        screenshot_comment_text = "Test screenshot comment"
        x, y, w, h = 2, 2, 10, 10

        screenshot = self.testNewScreenshot()
        review_request = screenshot.review_request.get()
        diffset = self.testNewDiff(review_request)
        rsp = self.apiPost("reviewrequests/%s/draft/save" % review_request.id)
        self.assertEqual(rsp['stat'], 'ok')

        self.postNewDiffComment(review_request, diff_comment_text)
        self.postNewScreenshotComment(review_request, screenshot,
                                      screenshot_comment_text, x, y, w, h)

        rsp = self.apiGet("reviewrequests/%s/reviews/draft/comments" %
                          review_request.id)
        self.assertEqual(rsp['stat'], 'ok')
        self.assertEqual(len(rsp['comments']), 1)
        self.assertEqual(len(rsp['screenshot_comments']), 1)
        self.assertEqual(rsp['comments'][0]['text'], diff_comment_text)
        self.assertEqual(rsp['screenshot_comments'][0]['text'],
                         screenshot_comment_text)

    def testReviewsList(self):
        """Testing the reviewrequests/reviews API"""
        review_request = Review.objects.all()[0].review_request
        rsp = self.apiGet("reviewrequests/%s/reviews" % review_request.id)
        self.assertEqual(rsp['stat'], 'ok')
        self.assertEqual(len(rsp['reviews']), review_request.reviews.count())

    def testReviewsListCount(self):
        """Testing the reviewrequests/reviews/count API"""
        review_request = Review.objects.all()[0].review_request
        rsp = self.apiGet("reviewrequests/%s/reviews/count" %
                          review_request.id)
        self.assertEqual(rsp['stat'], 'ok')
        self.assertEqual(rsp['reviews'], review_request.reviews.count())

    def testReviewCommentsList(self):
        """Testing the reviewrequests/reviews/comments API"""
        review = Review.objects.filter(comments__pk__gt=0)[0]

        rsp = self.apiGet("reviewrequests/%s/reviews/%s/comments" %
                          (review.review_request.id, review.id))
        self.assertEqual(rsp['stat'], 'ok')
        self.assertEqual(len(rsp['comments']), review.comments.count())

    def testReviewCommentsCount(self):
        """Testing the reviewrequests/reviews/comments/count API"""
        review = Review.objects.filter(comments__pk__gt=0)[0]

        rsp = self.apiGet("reviewrequests/%s/reviews/%s/comments/count" %
                          (review.review_request.id, review.id))
        self.assertEqual(rsp['stat'], 'ok')
        self.assertEqual(rsp['count'], review.comments.count())

    def testReplyDraftComment(self):
        """Testing the reviewrequests/reviews/replies/draft API with comment"""
        comment_text = "My Comment Text"

        comment = Comment.objects.all()[0]
        review = comment.review.get()

        rsp = self.apiPost("reviewrequests/%s/reviews/%s/replies/draft" %
                           (review.review_request.id, review.id), {
            'type': 'comment',
            'id': comment.id,
            'value': comment_text
        })

        self.assertEqual(rsp['stat'], 'ok')

        reply_comment = Comment.objects.get(pk=rsp['comment']['id'])
        self.assertEqual(reply_comment.text, comment_text)

    def testReplyDraftScreenshotComment(self):
        """Testing the reviewrequests/reviews/replies/draft API with screenshot_comment"""
        comment_text = "My Comment Text"

        comment = self.testScreenshotCommentsSet()
        review = comment.review.get()

        rsp = self.apiPost("reviewrequests/%s/reviews/%s/replies/draft" %
                           (review.review_request.id, review.id), {
            'type': 'screenshot_comment',
            'id': comment.id,
            'value': comment_text,
        })

        self.assertEqual(rsp['stat'], 'ok')

        reply_comment = ScreenshotComment.objects.get(
            pk=rsp['screenshot_comment']['id'])
        self.assertEqual(reply_comment.text, comment_text)

    def testReplyDraftBodyTop(self):
        """Testing the reviewrequests/reviews/replies/draft API with body_top"""
        body_top = 'My Body Top'

        review = \
            Review.objects.filter(base_reply_to__isnull=True, public=True)[0]

        rsp = self.apiPost("reviewrequests/%s/reviews/%s/replies/draft" %
                           (review.review_request.id, review.id), {
            'type': 'body_top',
            'value': body_top,
        })

        self.assertEqual(rsp['stat'], 'ok')

        reply = Review.objects.get(pk=rsp['reply']['id'])
        self.assertEqual(reply.body_top, body_top)

    def testReplyDraftBodyBottom(self):
        """Testing the reviewrequests/reviews/replies/draft API with body_bottom"""
        body_bottom = 'My Body Bottom'

        review = \
            Review.objects.filter(base_reply_to__isnull=True, public=True)[0]

        rsp = self.apiPost("reviewrequests/%s/reviews/%s/replies/draft" %
                           (review.review_request.id, review.id), {
            'type': 'body_bottom',
            'value': body_bottom,
        })

        self.assertEqual(rsp['stat'], 'ok')

        reply = Review.objects.get(pk=rsp['reply']['id'])
        self.assertEqual(reply.body_bottom, body_bottom)

    def testReplyDraftSave(self):
        """Testing the reviewrequests/reviews/replies/draft/save API"""
        review = \
            Review.objects.filter(base_reply_to__isnull=True, public=True)[0]

        rsp = self.apiPost("reviewrequests/%s/reviews/%s/replies/draft" %
                           (review.review_request.id, review.id), {
            'type': 'body_top',
            'value': 'Test',
        })

        self.assertEqual(rsp['stat'], 'ok')
        reply_id = rsp['reply']['id']

        rsp = self.apiPost("reviewrequests/%s/reviews/%s/replies/draft/save" %
                           (review.review_request.id, review.id))
        self.assertEqual(rsp['stat'], 'ok')

        reply = Review.objects.get(pk=reply_id)
        self.assertEqual(reply.public, True)

    def testReplyDraftDiscard(self):
        """Testing the reviewrequests/reviews/replies/draft/discard API"""
        review = \
            Review.objects.filter(base_reply_to__isnull=True, public=True)[0]

        rsp = self.apiPost("reviewrequests/%s/reviews/%s/replies/draft" %
                           (review.review_request.id, review.id), {
            'type': 'body_top',
            'value': 'Test',
        })

        self.assertEqual(rsp['stat'], 'ok')
        reply_id = rsp['reply']['id']

        rsp = self.apiPost(
            "reviewrequests/%s/reviews/%s/replies/draft/discard" %
            (review.review_request.id, review.id))
        self.assertEqual(rsp['stat'], 'ok')

        self.assertEqual(Review.objects.filter(pk=reply_id).count(), 0)

    def testRepliesList(self):
        """Testing the reviewrequests/reviews/replies API"""
        review = \
            Review.objects.filter(base_reply_to__isnull=True, public=True)[0]
        self.testReplyDraftSave()

        rsp = self.apiGet("reviewrequests/%s/reviews/%s/replies" %
                          (review.review_request.id, review.id))
        self.assertEqual(rsp['stat'], 'ok')
        self.assertEqual(len(rsp['replies']), len(review.public_replies()))

        for reply in review.public_replies():
            self.assertEqual(rsp['replies'][0]['id'], reply.id)
            self.assertEqual(rsp['replies'][0]['body_top'], reply.body_top)
            self.assertEqual(rsp['replies'][0]['body_bottom'],
                             reply.body_bottom)

    def testRepliesListCount(self):
        """Testing the reviewrequests/reviews/replies/count API"""
        review = \
            Review.objects.filter(base_reply_to__isnull=True, public=True)[0]
        self.testReplyDraftSave()

        rsp = self.apiGet("reviewrequests/%s/reviews/%s/replies/count" %
                          (review.review_request.id, review.id))
        self.assertEqual(rsp['stat'], 'ok')
        self.assertEqual(rsp['count'], len(review.public_replies()))

    def testNewDiff(self, review_request=None):
        """Testing the reviewrequests/diff/new API"""

        if review_request is None:
            review_request = self.testNewReviewRequest()

        f = open("scmtools/testdata/svn_makefile.diff", "r")
        rsp = self.apiPost("reviewrequests/%s/diff/new" % review_request.id, {
            'path': f,
            'basedir': "/trunk",
        })
        f.close()

        self.assertEqual(rsp['stat'], 'ok')

        # Return this so it can be used in other tests.
        return DiffSet.objects.get(pk=rsp['diffset_id'])

    def testNewDiffInvalidFormData(self):
        """Testing the reviewrequests/diff/new API with Invalid Form Data"""
        review_request = self.testNewReviewRequest()

        rsp = self.apiPost("reviewrequests/%s/diff/new" % review_request.id)
        self.assertEqual(rsp['stat'], 'fail')
        self.assertEqual(rsp['err']['code'], webapi.INVALID_FORM_DATA.code)
        self.assert_('path' in rsp['fields'])
        self.assert_('basedir' in rsp['fields'])

    def testNewScreenshot(self):
        """Testing the reviewrequests/screenshot/new API"""
        review_request = self.testNewReviewRequest()

        f = open("htdocs/media/rb/images/trophy.png", "r")
        self.assert_(f)
        rsp = self.apiPost("reviewrequests/%s/screenshot/new" %
                           review_request.id, {
            'path': f,
        })
        f.close()

        self.assertEqual(rsp['stat'], 'ok')

        # Return the screenshot so we can use it in other tests.
        return Screenshot.objects.get(pk=rsp['screenshot_id'])

    def testNewScreenshotPermissionDenied(self):
        """Testing the reviewrequests/screenshot/new API with Permission Denied error"""
        review_request = ReviewRequest.objects.filter(public=True).\
            exclude(submitter=self.user)[0]

        f = open("htdocs/media/rb/images/trophy.png", "r")
        self.assert_(f)
        rsp = self.apiPost("reviewrequests/%s/screenshot/new" %
                           review_request.id, {
            'caption': 'Trophy',
            'path': f,
        })
        f.close()

        self.assertEqual(rsp['stat'], 'fail')
        self.assertEqual(rsp['err']['code'], webapi.PERMISSION_DENIED.code)

    def postNewDiffComment(self, review_request, comment_text):
        """Utility function for posting a new diff comment."""
        diffset = review_request.diffset_history.diffsets.latest()
        filediff = diffset.files.all()[0]

        rsp = self.apiPost(
            "reviewrequests/%s/diff/%s/file/%s/line/%s/comments" %
            (review_request.id, diffset.revision, filediff.id, 10),
            {
                'action': 'set',
                'text': comment_text,
                'num_lines': 5,
            }
        )

        self.assertEqual(rsp['stat'], 'ok')

        return rsp

    def testDiffCommentsSet(self):
        """Testing the reviewrequests/diff/file/line/comments set API"""
        comment_text = "This is a test comment."

        review_request = ReviewRequest.objects.public()[0]
        review_request.reviews = []

        rsp = self.postNewDiffComment(review_request, comment_text)

        self.assertEqual(len(rsp['comments']), 1)
        self.assertEqual(rsp['comments'][0]['text'], comment_text)

    def testDiffCommentsDelete(self):
        """Testing the reviewrequests/diff/file/line/comments delete API"""
        comment_text = "This is a test comment."

        self.testDiffCommentsSet()

        review_request = ReviewRequest.objects.public()[0]
        diffset = review_request.diffset_history.diffsets.latest()
        filediff = diffset.files.all()[0]

        rsp = self.apiPost(
            "reviewrequests/%s/diff/%s/file/%s/line/%s/comments" %
            (review_request.id, diffset.revision, filediff.id, 10),
            {
                'action': 'delete',
                'num_lines': 5,
            }
        )

        self.assertEqual(rsp['stat'], 'ok')
        self.assertEqual(len(rsp['comments']), 0)

    def testDiffCommentsList(self):
        """Testing the reviewrequests/diff/file/line/comments list API"""
        self.testDiffCommentsSet()

        review_request = ReviewRequest.objects.public()[0]
        diffset = review_request.diffset_history.diffsets.latest()
        filediff = diffset.files.all()[0]

        rsp = self.apiGet(
            "reviewrequests/%s/diff/%s/file/%s/line/%s/comments" %
            (review_request.id, diffset.revision, filediff.id, 10))

        self.assertEqual(rsp['stat'], 'ok')

        comments = Comment.objects.filter(filediff=filediff)
        self.assertEqual(len(rsp['comments']), comments.count())

        for i in range(0, len(rsp['comments'])):
            self.assertEqual(rsp['comments'][i]['text'], comments[i].text)


    def testInterDiffCommentsSet(self):
        """Testing the reviewrequests/diff/file/line/comments interdiff set API"""
        comment_text = "This is a test comment."

        # Create a review request for this test.
        review_request = self.testNewReviewRequest()

        # Upload the first diff and publish the draft.
        diffset_id = self.testNewDiff(review_request).id
        rsp = self.apiPost("reviewrequests/%s/draft/save" % review_request.id)
        self.assertEqual(rsp['stat'], 'ok')

        # Upload the second diff and publish the draft.
        interdiffset_id = self.testNewDiff(review_request).id
        rsp = self.apiPost("reviewrequests/%s/draft/save" % review_request.id)
        self.assertEqual(rsp['stat'], 'ok')

        # Reload the diffsets, now that they've been modified.
        diffset = DiffSet.objects.get(pk=diffset_id)
        interdiffset = DiffSet.objects.get(pk=interdiffset_id)

        # Get the interdiffs
        filediff = diffset.files.all()[0]
        interfilediff = interdiffset.files.all()[0]

        rsp = self.apiPost(
            "reviewrequests/%s/diff/%s-%s/file/%s-%s/line/%s/comments" %
            (review_request.id, diffset.revision, interdiffset.revision,
             filediff.id, interfilediff.id, 10),
            {
                'action': 'set',
                'text': comment_text,
                'num_lines': 5,
            }
        )

        self.assertEqual(rsp['stat'], 'ok')
        self.assertEqual(len(rsp['comments']), 1)
        self.assertEqual(rsp['comments'][0]['text'], comment_text)

        # Return some information for use in other tests.
        return (review_request, diffset, interdiffset, filediff, interfilediff)

    def testInterDiffCommentsDelete(self):
        """Testing the reviewrequests/diff/file/line/comments interdiff delete API"""
        comment_text = "This is a test comment."

        review_request, diffset, interdiffset, filediff, interfilediff = \
            self.testInterDiffCommentsSet()

        rsp = self.apiPost(
            "reviewrequests/%s/diff/%s-%s/file/%s-%s/line/%s/comments" %
            (review_request.id, diffset.revision, interdiffset.revision,
             filediff.id, interfilediff.id, 10),
            {
                'action': 'delete',
                'num_lines': 5,
            }
        )

        self.assertEqual(rsp['stat'], 'ok')
        self.assertEqual(len(rsp['comments']), 0)

    def testInterDiffCommentsList(self):
        """Testing the reviewrequests/diff/file/line/comments interdiff list API"""
        review_request, diffset, interdiffset, filediff, interfilediff = \
            self.testInterDiffCommentsSet()

        rsp = self.apiGet(
            "reviewrequests/%s/diff/%s-%s/file/%s-%s/line/%s/comments" %
            (review_request.id, diffset.revision, interdiffset.revision,
             filediff.id, interfilediff.id, 10))

        self.assertEqual(rsp['stat'], 'ok')

        comments = Comment.objects.filter(filediff=filediff,
                                          interfilediff=interfilediff)
        self.assertEqual(len(rsp['comments']), comments.count())

        for i in range(0, len(rsp['comments'])):
            self.assertEqual(rsp['comments'][i]['text'], comments[i].text)

    def postNewScreenshotComment(self, review_request, screenshot,
                                 comment_text, x, y, w, h):
        """Utility function for posting a new screenshot comment."""
        rsp = self.apiPost(
            "reviewrequests/%s/s/%s/comments/%sx%s+%s+%s" %
            (review_request.id, screenshot.id, w, h, x, y),
            {
                'action': 'set',
                'text': comment_text,
            }
        )

        self.assertEqual(rsp['stat'], 'ok')
        return rsp

    def testScreenshotCommentsSet(self):
        """Testing the reviewrequests/s/comments set API"""
        comment_text = "This is a test comment."
        x, y, w, h = (2, 2, 10, 10)

        screenshot = self.testNewScreenshot()
        review_request = screenshot.review_request.get()

        rsp = self.postNewScreenshotComment(review_request, screenshot,
                                            comment_text, x, y, w, h)

        self.assertEqual(len(rsp['comments']), 1)
        self.assertEqual(rsp['comments'][0]['text'], comment_text)
        self.assertEqual(rsp['comments'][0]['x'], x)
        self.assertEqual(rsp['comments'][0]['y'], y)
        self.assertEqual(rsp['comments'][0]['w'], w)
        self.assertEqual(rsp['comments'][0]['h'], h)

        # Return this so it can be used in other tests.
        return ScreenshotComment.objects.get(pk=rsp['comments'][0]['id'])

    def testScreenshotCommentsDelete(self):
        """Testing the reviewrequests/s/comments delete API"""
        comment = self.testScreenshotCommentsSet()
        screenshot = comment.screenshot
        review_request = screenshot.review_request.get()

        rsp = self.apiPost(
            "reviewrequests/%s/s/%s/comments/%sx%s+%s+%s" %
            (review_request.id, screenshot.id, comment.w, comment.h,
             comment.x, comment.y),
            {
                'action': 'delete',
            }
        )

        self.assertEqual(rsp['stat'], 'ok')
        self.assertEqual(len(rsp['comments']), 0)

    def testScreenshotCommentsDeleteNonExistant(self):
        """Testing the reviewrequests/s/comments delete API with non-existant comment"""
        comment = self.testScreenshotCommentsSet()
        screenshot = comment.screenshot
        review_request = screenshot.review_request.get()

        rsp = self.apiPost(
            "reviewrequests/%s/s/%s/comments/%sx%s+%s+%s" %
            (review_request.id, screenshot.id, 1, 2, 3, 4),
            {
                'action': 'delete',
            }
        )

        self.assertEqual(rsp['stat'], 'ok')
        self.assertEqual(len(rsp['comments']), 0)

    def testScreenshotCommentsList(self):
        """Testing the reviewrequests/s/comments list API"""
        comment = self.testScreenshotCommentsSet()
        screenshot = comment.screenshot
        review_request = screenshot.review_request.get()

        rsp = self.apiGet(
            "reviewrequests/%s/s/%s/comments/%sx%s+%s+%s" %
            (review_request.id, screenshot.id, comment.w, comment.h,
             comment.x, comment.y))

        self.assertEqual(rsp['stat'], 'ok')

        comments = ScreenshotComment.objects.filter(screenshot=screenshot)
        self.assertEqual(len(rsp['comments']), comments.count())

        for i in range(0, len(rsp['comments'])):
            self.assertEqual(rsp['comments'][i]['text'], comments[i].text)
            self.assertEqual(rsp['comments'][i]['x'], comments[i].x)
            self.assertEqual(rsp['comments'][i]['y'], comments[i].y)
            self.assertEqual(rsp['comments'][i]['w'], comments[i].w)
            self.assertEqual(rsp['comments'][i]['h'], comments[i].h)
