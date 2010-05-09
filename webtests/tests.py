from datetime import datetime
import os
import time

from django.conf import settings
from django.contrib.auth import authenticate, login
from django.contrib.auth.models import Permission, User
from django.core.urlresolvers import reverse
from django.db import transaction
from django.http import HttpRequest
from djblets.testing import testcases

from reviewboard.reviews.models import Group, Review, ReviewRequest, \
                                       ReviewRequestDraft, Screenshot
from reviewboard.scmtools.models import Repository, Tool


def create_screenshot(r, caption=""):
    """Utility function to create a Screenshot."""
    screenshot = Screenshot.objects.create(caption=caption)
    screenshot.image.name = os.path.join('rb', 'images', 'logo.png')
    screenshot.save()

    r.screenshots.add(screenshot)
    r.save()

    return screenshot


class SeleniumUnitTest(testcases.SeleniumUnitTest):
    fixtures = ['test_users', 'test_reviewrequests', 'test_scmtools']

    def setUp(self):
        super(SeleniumUnitTest, self).setUp()

        self.user = User.objects.get(username='grumpy')
        self.login()

    def login(self):
        self.selenium.open('/account/login/')
        self.selenium.type('id_username', 'grumpy')
        self.selenium.type('id_password', 'grumpy')
        self.selenium.click('//input[@value="Log in"]')
        self.selenium.wait_for_page_to_load("6000")
        self.assertTrue(self.selenium.is_text_present("Welcome, Grumpy Dwarf"))

    def wait_for_ajax_finish(self, timeout=6000):
        """Waits for the loading/saving indicator to go away."""
        self.selenium.wait_for_condition(
            '!selenium.isElementPresent("activity-indicator") || '
            '!selenium.isVisible("activity-indicator")',
            timeout)

    def wait_for_element_present(self, locator, timeout=6000):
        self.selenium.wait_for_condition(
            'selenium.isElementPresent("%s")' % locator,
            timeout)

    def wait_for_element_not_present(self, locator, timeout=6000):
        self.selenium.wait_for_condition(
            '!selenium.isElementPresent("%s")' % locator,
            timeout)

    def wait_for_visible(self, locator, timeout=6000):
        self.selenium.wait_for_condition(
            'selenium.isVisible("%s")' % locator,
            timeout)

    def wait_for_not_visible(self, locator, timeout=6000):
        self.selenium.wait_for_condition(
            '!selenium.isVisible("%s")' % locator,
            timeout)


class DiffTests(SeleniumUnitTest):
    """Testing diff functionality."""
    def test_load_diff(self):
        """Testing diff loading"""
        r = ReviewRequest.objects.get(pk=4)
        diffset = r.diffset_history.diffsets.all()[0]
        self.assertTrue(diffset.files.count() > 1)

        self.selenium.open(reverse('view_diff', kwargs={
            'review_request_id': r.id
        }))

        for filediff in diffset.files.all():
            file_id = 'file%s' % filediff.id
            self.wait_for_visible(file_id)
            self.assertEquals(
                self.selenium.get_text('css=#%s thead th' % file_id).strip(),
                filediff.source_file)

    def test_new_diff(self):
        """Testing diff uploading"""
        testdata_dir = os.path.join(
            os.path.dirname(os.path.dirname(__file__)),
            'reviewboard', 'scmtools', 'testdata')

        diff_filename = os.path.join(testdata_dir, 'svn_makefile.diff')
        self.assertTrue(os.path.exists(diff_filename))

        # Create a fake repo and review request
        svn_repo_path = os.path.join(testdata_dir, 'svn_repo')
        repository = Repository.objects.create(
            name='Subversion SVN',
            path='file://' + svn_repo_path,
            tool=Tool.objects.get(name='Subversion'))

        r = ReviewRequest.objects.create(self.user, repository)
        transaction.commit()

        # Upload the diff we'll reference. This is just easier to fake
        # through the web API.
        f = open(diff_filename, "r")
        self.client.login(username="grumpy", password="grumpy")
        response = self.client.post(
            '/api/json/reviewrequests/%s/diff/new/' % r.id, {
                'path': f,
                'basedir': '/trunk',
            }
        )
        self.assertEqual(response.status_code, 200)
        self.assertTrue('"ok"' in response.content)
        f.close()

        r.publish(self.user)

        # Now we can begin testing the actual upload.
        raw_diff_url = reverse('raw_diff', kwargs={'review_request_id': r.id})

        self.selenium.open(r.get_absolute_url())
        self.selenium.click('upload-diff-link')
        self.selenium.type('id_basedir', '/trunk')
        self.selenium.focus('id_path')
        self.selenium.attach_file('id_path',
                                  self.test_url + raw_diff_url.strip('/'))
        self.selenium.click('css=.modalbox input[value="Upload"]')
        self.selenium.wait_for_page_to_load("10000")

        draft = r.get_draft(self.user)
        self.assertNotEqual(draft, None)
        self.assertNotEqual(draft.diffset, None)

        expected_files = list(r.diffset_history.diffsets.latest().files.all())
        result_files = list(draft.diffset.files.all())

        self.assertEqual(len(expected_files), len(result_files))

        for file1, file2 in zip(expected_files, result_files):
            self.assertEqual(file1.source_file, file2.source_file)
            self.assertEqual(file1.dest_file, file2.dest_file)
            self.assertEqual(file1.source_revision, file2.source_revision)
            self.assertEqual(file1.dest_detail, file2.dest_detail)


class DiffCommentTests(SeleniumUnitTest):
    """Testing diff comment functionality."""
    def test_new_comment(self):
        """Testing diff comment creation"""
        comment_text = 'This is my test comment'
        first_line = 10
        last_line = 12

        r = ReviewRequest.objects.filter(public=True, status='P',
                                         submitter=self.user)[0]
        diffset = r.diffset_history.diffsets.all()[0]
        file = diffset.files.all()[0]

        self.selenium.open(reverse('view_diff', kwargs={
            'review_request_id': r.id
        }))
        self.selenium.wait_for_page_to_load("6000")
        self.wait_for_element_present('file%s' % file.id)

        self.open_comment_box(file.id, first_line, last_line)
        self.selenium.type_keys('comment_text', comment_text)
        self.selenium.click('comment_save')
        self.selenium.click('review-banner-publish')
        self.selenium.wait_for_page_to_load("6000")

        self.assertEqual(r.reviews.count(), 1)
        review = r.reviews.latest()
        self.assertTrue(review.public)
        self.assertEqual(review.comments.count(), 1)
        comment = review.comments.all()[0]
        self.assertEqual(comment.text, comment_text)
        self.assertEqual(comment.first_line, first_line)
        self.assertEqual(comment.last_line, last_line)

    def test_multiline_comment(self):
        """Testing diff comment creation with a multi-line comment."""
        comment_text = 'This is my\ntest\ncomment'
        first_line = 10
        last_line = 12

        r = ReviewRequest.objects.filter(public=True, status='P',
                                         submitter=self.user)[0]
        diffset = r.diffset_history.diffsets.all()[0]
        file = diffset.files.all()[0]

        self.selenium.open(reverse('view_diff', kwargs={
            'review_request_id': r.id
        }))
        self.selenium.wait_for_page_to_load("6000")
        self.wait_for_element_present('file%s' % file.id)

        self.open_comment_box(file.id, first_line, last_line)

        first = True

        for text in comment_text.split('\n'):
            if not first:
                self.selenium.key_press('comment_text', '\\13')

            self.selenium.type_keys('comment_text', text)
            first = False

        self.selenium.focus('comment_save')

        self.selenium.click('comment_save')
        self.wait_for_ajax_finish()

        self.assertEqual(r.reviews.count(), 1)
        review = r.reviews.latest()
        self.assertFalse(review.public)
        self.assertEqual(review.comments.count(), 1)
        comment = review.comments.all()[0]
        self.assertEqual(comment.text, comment_text)

        # Make sure that the Edit Review form properly handles this.
        # Bug 1636.
        self.selenium.click('review-link')
        self.wait_for_element_present('review-form')
        self.assertTrue(self.selenium.is_element_present('css=.diff-comments'))
        self.assertTrue(self.selenium.is_element_present(
            'css=.diff-comments #diff-comment-%s' % comment.id))
        self.wait_for_element_present('css=.diff-comments textarea')
        self.assertEqual(self.selenium.get_value('css=.diff-comments textarea'),
                         comment_text)

    def test_delete_comment(self):
        """Testing deleting draft diff comments"""
        comment_text = 'This is my test comment'
        first_line = 10
        last_line = 12

        r = ReviewRequest.objects.filter(public=True, status='P',
                                         submitter=self.user)[0]
        diffset = r.diffset_history.diffsets.all()[0]
        file = diffset.files.all()[0]

        self.selenium.open(reverse('view_diff', kwargs={
            'review_request_id': r.id
        }))
        self.selenium.wait_for_page_to_load("6000")

        self.open_comment_box(file.id, first_line, last_line)
        self.selenium.type_keys('comment_text', comment_text)
        self.selenium.click('comment_save')
        self.wait_for_visible('review-banner')
        time.sleep(0.25) # It will be animating, so wait.

        # Now delete it
        self.open_comment_box(file.id, first_line, first_line)
        self.wait_for_visible('comment-detail')
        self.selenium.click('comment_delete')
        self.wait_for_ajax_finish()
        time.sleep(0.25) # It will be animating, so wait.

        self.assertEqual(r.reviews.count(), 0)

    def open_comment_box(self, file_id, first_line, last_line):
        first_line_locator = self.build_line_locator(file_id, first_line)
        last_line_locator = self.build_line_locator(file_id, last_line)

        self.selenium.mouse_over(first_line_locator)
        self.selenium.mouse_down(first_line_locator)
        self.selenium.mouse_over(last_line_locator)
        self.selenium.mouse_up(last_line_locator)
        self.wait_for_visible('comment-detail')

    def build_line_locator(self, file_id, line_num):
        return 'css=#file%s tr[line=%s] th' % (file_id, line_num)


class ReviewRequestTests(SeleniumUnitTest):
    """Testing review request functionality."""
    def test_check_for_updates(self):
        """Testing the check for updates functionality"""
        r = ReviewRequest.objects.filter(public=True, status='P',
                                         submitter=self.user)[0]

        self.selenium.open(r.get_absolute_url())

        # Simulate an update.
        r.last_updated = datetime.now()
        r.save()
        transaction.commit()

        self.selenium.get_eval('this.browserbot.getCurrentWindow().'
                               'gReviewRequest._checkForUpdates()')
        self.wait_for_element_present('updates-bubble')
        self.wait_for_visible('updates-bubble')

    def test_close_submitted(self):
        """Testing closing a review request as submitted"""
        r = ReviewRequest.objects.filter(public=True, status='P',
                                         submitter=self.user)[0]

        self.selenium.open(r.get_absolute_url())

        self.selenium.mouse_over('close-review-request-link')
        self.selenium.click('link-review-request-close-submitted')
        self.selenium.wait_for_page_to_load("6000")

        r = ReviewRequest.objects.get(pk=r.id)
        self.assertEqual(r.status, 'S')

    def test_close_discarded(self):
        """Testing closing a review request as discarded"""
        r = ReviewRequest.objects.filter(public=True, status='P',
                                         submitter=self.user)[0]

        self.selenium.open(r.get_absolute_url())

        self.selenium.mouse_over('close-review-request-link')
        self.selenium.click('discard-review-request-link')
        self.selenium.wait_for_page_to_load("6000")

        r = ReviewRequest.objects.get(pk=r.id)
        self.assertEqual(r.status, 'D')

    def test_delete_permanently(self):
        """Testing deleting a review request permanently"""
        r = ReviewRequest.objects.filter(public=True, status='P',
                                         submitter=self.user)[0]

        self.user.user_permissions.add(
            Permission.objects.get(codename='delete_reviewrequest'))
        self.user.save()
        transaction.commit()

        self.selenium.open(r.get_absolute_url())
        self.selenium.mouse_over('close-review-request-link')
        self.assertTrue(
            self.selenium.is_element_present('delete-review-request-link'))
        self.selenium.click('delete-review-request-link')
        self.assertTrue(self.selenium.is_text_present(
            'Are you sure you want to delete this review request?'))
        self.selenium.click('css=.modalbox input[value="Delete"]')
        self.selenium.wait_for_page_to_load("6000")

        self.assertRaises(ReviewRequest.DoesNotExist,
                          lambda: ReviewRequest.objects.get(pk=r.id))

    def test_discard_draft(self):
        """Testing discarding a draft to an existing review request"""
        branch = 'testbranch'

        r = ReviewRequest.objects.filter(public=True, status='P',
                                         submitter=self.user)[0]

        self.selenium.open(r.get_absolute_url())
        self._edit_field('branch', branch)
        self.wait_for_ajax_finish()

        r = ReviewRequest.objects.get(pk=r.id)
        self.assertEqual(r.draft.get().branch, branch)

        self.selenium.click('btn-draft-discard')
        self.selenium.wait_for_page_to_load("6000")

        r = ReviewRequest.objects.get(pk=r.id)
        self.assertTrue(r.public)
        self.assertEqual(r.status, 'P')
        self.assertRaises(ReviewRequestDraft.DoesNotExist,
                          lambda: r.draft.get())

    def test_discard_new_review_request(self):
        """Testing discarding a new review request"""
        r = ReviewRequest.objects.filter(public=True, status='P',
                                         submitter=self.user)[0]
        r.public = False
        r.save()
        transaction.commit()

        self.selenium.open(r.get_absolute_url())
        self.selenium.click('btn-review-request-discard')
        self.selenium.wait_for_page_to_load("6000")

        r = ReviewRequest.objects.get(pk=r.id)
        self.assertFalse(r.public)
        self.assertEqual(r.status, 'D')

    def test_modify_fields(self):
        """Testing modifying a review request's fields"""
        r = ReviewRequest.objects.filter(public=True, status='P',
                                         submitter=self.user)[0]

        self.selenium.open(r.get_absolute_url())

        summary = 'My new summary'
        branch = 'mybranch'
        bugs_closed = '123, 789'
        target_groups = 'devgroup'
        target_people = 'grumpy'
        description = 'My new description'
        testing_done = 'My new testing done'

        self._edit_field('summary', summary, field_suffix='_wrapper')
        self._edit_field('branch', branch)
        self._edit_field('bugs-closed', bugs_closed)
        self._edit_field('target-groups', target_groups)
        self._edit_field('target-people', target_people)
        self._edit_field('description', description, True)
        self._edit_field('testing-done', testing_done, True)
        self.wait_for_ajax_finish()

        draft = r.draft.get()
        self.assertEqual(draft.summary, summary)
        self.assertEqual(draft.description, description)
        self.assertEqual(draft.testing_done, testing_done)
        self.assertEqual(draft.branch, branch)
        self.assertEqual(draft.bugs_closed, bugs_closed)
        self.assertEqual(
            ', '.join([g.name for g in draft.target_groups.all()]),
            target_groups)
        self.assertEqual(
            ', '.join([u.username for u in draft.target_people.all()]),
            target_people)

    def test_publish_draft(self):
        """Testing publishing a draft to an existing review request"""
        branch = 'testbranch'

        r = ReviewRequest.objects.filter(public=True, status='P',
                                         submitter=self.user)[0]
        self.assertNotEqual(r.branch, branch)

        self.selenium.open(r.get_absolute_url())
        self._edit_field('branch', branch)
        self.wait_for_ajax_finish()

        r = ReviewRequest.objects.get(pk=r.id)
        self.assertEqual(r.draft.get().branch, branch)
        self.assertTrue(r.can_publish())

        self.selenium.open(r.get_absolute_url())
        self._click_publish_draft()

        r = ReviewRequest.objects.get(pk=r.id)
        self.assertEqual(r.branch, branch)
        self.assertRaises(ReviewRequestDraft.DoesNotExist,
                          lambda: r.draft.get())

    def test_publish_new_review_request(self):
        """Testing publishing a new review request"""
        r = ReviewRequest.objects.filter(public=True, status='P',
                                         submitter=self.user)[0]
        r.public = False
        r.save()
        transaction.commit()

        self.assertTrue(r.can_publish())

        self.selenium.open(r.get_absolute_url())
        self._click_publish_draft()

        r = ReviewRequest.objects.get(pk=r.id)
        self.assertTrue(r.public)

    def test_reopen(self):
        """Testing reopening a review request"""
        r = ReviewRequest.objects.filter(public=True, status='P',
                                         submitter=self.user)[0]
        r.close(ReviewRequest.SUBMITTED)
        r.save()
        transaction.commit()

        self.selenium.open(r.get_absolute_url())

        self.assertTrue(self.selenium.is_text_present(
            'This change has been marked as submitted.'))
        self.selenium.click('btn-review-request-reopen')
        self.selenium.wait_for_page_to_load("6000")

        r = ReviewRequest.objects.get(pk=r.id)
        self.assertEqual(r.status, 'P')

    def test_star_on_review_request_page(self):
        """Testing starring a review request on the review request page"""
        r = ReviewRequest.objects.filter(public=True, status='P',
                                         submitter=self.user)[0]

        profile = self.user.get_profile()
        self.assertFalse(r in profile.starred_review_requests.all())

        self._click_star_on_review_request(r)
        self.assertTrue(r in profile.starred_review_requests.all())

    def test_star_on_all_review_requests_page(self):
        """Testing starring a review request on the All Review Requests page"""
        r = ReviewRequest.objects.filter(public=True, status='P',
                                         submitter=self.user)[0]

        profile = self.user.get_profile()
        self.assertFalse(r in profile.starred_review_requests.all())

        self._click_star_on_review_requests_page(r)
        self.assertTrue(r in profile.starred_review_requests.all())

    def test_unstar_on_review_request_page(self):
        """Testing unstarring a review request"""
        r = ReviewRequest.objects.filter(public=True, status='P',
                                         submitter=self.user)[0]
        profile = self.user.get_profile()
        self.assertFalse(r in profile.starred_review_requests.all())

        profile.starred_review_requests.add(r)
        profile.save()
        transaction.commit()

        self._click_star_on_review_request(r)
        self.assertFalse(r in profile.starred_review_requests.all())

    def test_unstar_on_all_review_requests_page(self):
        """Testing unstarring a review request on the All Review Requests page"""
        r = ReviewRequest.objects.filter(public=True, status='P',
                                         submitter=self.user)[0]
        profile = self.user.get_profile()
        self.assertFalse(r in profile.starred_review_requests.all())

        profile.starred_review_requests.add(r)
        profile.save()
        transaction.commit()

        self._click_star_on_review_requests_page(r)
        self.assertFalse(r in profile.starred_review_requests.all())

    def _edit_field(self, field, value, is_textarea=False,
                   field_suffix="-value-cell"):
        """Edits a field on the review request page and saves it"""
        cell_name = '#%s%s' % (field, field_suffix)

        if is_textarea:
            input_el = 'textarea'
        else:
            input_el = 'input[type="text"]'

        self.selenium.click('css=%s .editicon' % cell_name)
        self.selenium.type('css=%s %s' % (cell_name, input_el), value)
        self.selenium.click('css=%s input[class="save"]' % cell_name)

    def _click_star_on_review_requests_page(self, review_request):
        self.selenium.open(reverse('all-review-requests') + '?columns=star')
        self.selenium.click('star-reviewrequests-%s' % review_request.id)
        self.wait_for_ajax_finish()

    def _click_star_on_review_request(self, review_request):
        self.selenium.open(review_request.get_absolute_url())
        self.selenium.click('star-reviewrequests-%s' % review_request.id)
        self.wait_for_ajax_finish()

    def _click_publish_draft(self):
        self.selenium.click('btn-draft-publish')
        self.selenium.wait_for_page_to_load("6000")


class ReviewTests(SeleniumUnitTest):
    """Testing review functionality."""
    def test_save_review(self):
        """Testing modifying and saving a new review"""
        body_top_text = 'This is the body top text'

        # NOTE: The UI doesn't show body_bottom unless there are existing
        #       comments.

        r = self._get_review_request()

        self.selenium.open(r.get_absolute_url())
        self.selenium.wait_for_page_to_load("6000")

        self.assertFalse(self.selenium.is_visible('review-banner'))

        self._open_review_dlg()
        self.selenium.check('id_shipit')
        self._type_review_text('body-top', body_top_text)
        self._click_save()

        self.assertEqual(r.reviews.count(), 1)
        review = r.reviews.latest()
        self.assertEqual(review.body_top, body_top_text)
        self.assertTrue(review.ship_it)
        self.assertFalse(review.public)

    def test_publish_review_from_form(self):
        """Testing modifying and publishing a new review from the form"""
        body_top_text = 'This is the body top text'

        # NOTE: The UI doesn't show body_bottom unless there are existing
        #       comments.

        r = self._get_review_request()

        self.selenium.open(r.get_absolute_url())
        self.selenium.wait_for_page_to_load("6000")

        self.assertFalse(self.selenium.is_visible('review-banner'))

        self._open_review_dlg()
        self.selenium.check('id_shipit')
        self._type_review_text('body-top', body_top_text)
        self._click_dlg_button('Publish Review', reloads_page=True)

        self.assertEqual(r.reviews.count(), 1)
        review = r.reviews.latest()
        self.assertEqual(review.body_top, body_top_text)
        self.assertTrue(review.ship_it)
        self.assertTrue(review.public)

    def test_publish_review_from_banner(self):
        """Testing modifying and publishing a new review from the banner"""
        body_top_text = 'This is the body top text'

        # NOTE: The UI doesn't show body_bottom unless there are existing
        #       comments.

        r = self._get_review_request()

        self.selenium.open(r.get_absolute_url())
        self.selenium.wait_for_page_to_load("6000")

        self.assertFalse(self.selenium.is_visible('review-banner'))

        self._open_review_dlg()
        self.selenium.check('id_shipit')
        self._type_review_text('body-top', body_top_text)
        self._click_save()

        # Review banner
        self.assertTrue(self.selenium.is_visible('review-banner'))
        self.selenium.click('review-banner-publish')
        self.wait_for_element_not_present('review-banner')

        self.assertEqual(r.reviews.count(), 1)
        review = r.reviews.latest()
        self.assertEqual(review.body_top, body_top_text)
        self.assertTrue(review.ship_it)
        self.assertTrue(review.public)

    def test_discard_review_from_form(self):
        """Testing modifying and then deleting a new review from the form"""
        body_top_text = 'This is the body top text'

        # NOTE: The UI doesn't show body_bottom unless there are existing
        #       comments.

        r = self._get_review_request()

        self.selenium.open(r.get_absolute_url())
        self.selenium.wait_for_page_to_load("6000")

        self.assertFalse(self.selenium.is_visible('review-banner'))

        self._open_review_dlg()
        self.selenium.check('id_shipit')
        self._type_review_text('body-top', body_top_text)
        self._click_save()

        self._open_review_dlg()
        self._click_discard()

        self.assertEqual(r.reviews.count(), 0)

    def test_discard_review_from_banner(self):
        """Testing modifying and then deleting a new review from the banner"""
        body_top_text = 'This is the body top text'

        # NOTE: The UI doesn't show body_bottom unless there are existing
        #       comments.
        r = self._get_review_request()

        self.selenium.open(r.get_absolute_url())
        self.selenium.wait_for_page_to_load("6000")

        self.assertFalse(self.selenium.is_visible('review-banner'))

        self._open_review_dlg()
        self.selenium.check('id_shipit')
        self._type_review_text('body-top', body_top_text)
        self._click_save()

        # Review banner
        self.selenium.click('review-banner-discard')

        # Confirmation box
        self._click_dlg_button('Discard', reloads_page=True)

        self.assertEqual(r.reviews.count(), 0)

    def _get_review_request(self):
        r = ReviewRequest.objects.filter(public=True, status='P',
                                         submitter=self.user)[0]
        r.reviews = []
        r.save()

        return r

    def _open_review_dlg(self):
        self.selenium.click('review-link')
        self.wait_for_element_present('review-form')

    def _type_review_text(self, section, text):
        self.selenium.type(
            'css=#review-form-comments .%s-editor textarea' % section,
            text)

    def _click_dlg_button(self, button_label, reloads_page=False):
        self.selenium.click('css=.modalbox-buttons input[value="%s"]' %
                            button_label)

        if reloads_page:
            self.selenium.wait_for_page_to_load("6000")
        else:
            self.wait_for_ajax_finish()

    def _click_save(self):
        self._click_dlg_button('Save')
        self.assertTrue(self.selenium.is_visible('review-banner'))

    def _click_discard(self):
        self._click_dlg_button('Discard Review', reloads_page=True)


class ReviewGroupTests(SeleniumUnitTest):
    """Testing review group functionality."""
    def test_star(self):
        """Testing starring a review group"""
        group = Group.objects.all()[0]

        profile = self.user.get_profile()
        self.assertFalse(group in profile.starred_groups.all())

        self._click_star_group_on_groups_page(group)
        self.assertTrue(group in profile.starred_groups.all())

    def test_unstar(self):
        """Testing unstarring a review group"""
        group = Group.objects.all()[0]

        profile = self.user.get_profile()
        self.assertFalse(group in profile.starred_groups.all())

        profile.starred_groups.add(group)
        profile.save()
        transaction.commit()

        self._click_star_group_on_groups_page(group)
        self.assertFalse(group in profile.starred_groups.all())

    def _click_star_group_on_groups_page(self, group):
        self.selenium.open(reverse('all-groups') + '?columns=star')
        self.selenium.click('star-groups-%s' % group.name)
        self.wait_for_ajax_finish()


class ReviewReplyTests(SeleniumUnitTest):
    """Testing review reply functionality."""
    def test_reply_body(self):
        """Testing making a reply to the body of a review"""
        body_top = 'Reply to body top'
        body_bottom = 'Reply to body bottom'

        review = self._get_review()
        self.selenium.open(review.review_request.get_absolute_url())

        self._add_comment(body_top, review, 'body_top')
        self._add_comment(body_bottom, review, 'body_bottom')

        self.assertEqual(review.replies.count(), 1)
        reply = review.replies.get()
        self.assertFalse(reply.public)
        self.assertEqual(reply.base_reply_to, review)
        self.assertEqual(reply.body_top, body_top)
        self.assertEqual(reply.body_bottom, body_bottom)

    def test_reply_diff_comment(self):
        """Testing making a reply to a diff comment"""

        def make_comment_text(comment):
            return 'This is a reply to comment %s' % comment.id

        review = self._get_review(comments__pk__gt=0)
        comments = list(review.comments.all())
        self.assertTrue(len(comments) > 0)

        self.selenium.open(review.review_request.get_absolute_url())

        for comment in comments:
            self._add_comment(make_comment_text(comment), review,
                              'comment', comment)

        self.assertEqual(review.replies.count(), 1)
        reply = review.replies.get()
        self.assertFalse(reply.public)
        self.assertEqual(reply.base_reply_to, review)

        reply_comments = list(reply.comments.all())
        self.assertEqual(len(reply_comments), len(comments))

        for reply_comment in reply_comments:
            review_comment = reply_comment.reply_to
            self.assertNotEqual(review_comment, None)

            self.assertEqual(reply_comment.text,
                             make_comment_text(review_comment))

    def test_reply_publish(self):
        """Testing publishing a reply to a review"""
        body_top = 'Reply to body top'
        body_bottom = 'Reply to body bottom'

        review = self._get_review()
        self.selenium.open(review.review_request.get_absolute_url())

        self._add_comment(body_top, review, 'body_top')
        self._add_comment(body_bottom, review, 'body_bottom')
        self._click_draft_banner_button(review, 'Publish')

        self.assertEqual(review.replies.count(), 1)
        reply = review.replies.get()
        self.assertTrue(reply.public)
        self.assertEqual(reply.base_reply_to, review)
        self.assertEqual(reply.body_top, body_top)
        self.assertEqual(reply.body_bottom, body_bottom)

    def test_reply_publish(self):
        """Testing discarding a reply to a review"""
        body_top = 'Reply to body top'
        body_bottom = 'Reply to body bottom'

        review = self._get_review()
        self.selenium.open(review.review_request.get_absolute_url())

        self._add_comment(body_top, review, 'body_top')
        self._add_comment(body_bottom, review, 'body_bottom')
        self._click_draft_banner_button(review, 'Discard')

        self.assertEqual(review.replies.count(), 0)

    def _get_review(self, **kwargs):
        review = Review.objects.filter(public=True, **kwargs)[0]
        review.body_top = 'Review body top'
        review.body_bottom = 'Review body bottom'
        review.replies = []
        review.save()
        transaction.commit()

        return review

    def _add_comment(self, text, review, context_type, comment=None):
        key = '%s_%s' % (review.id, context_type)

        if context_type == 'comment':
            self.assertNotEqual(comment, None)
            key += '_%s' % comment.id

        self.selenium.click('add_%s' % key)
        yourcomment_id = '#yourcomment_%s-draft-item' % key
        self.selenium.type_keys('css=%s textarea' % yourcomment_id,
                                text)
        self.selenium.click('css=%s input[value="OK"]' % yourcomment_id)
        self.wait_for_ajax_finish()
        self.assertTrue(self.selenium.is_visible('css=#review%s .banner' %
                                                 review.id))

    def _click_draft_banner_button(self, review, button_label):
        self.selenium.click('css=#review%s .banner input[value="%s"]' %
                            (review.id, button_label))
        self.selenium.wait_for_page_to_load("6000")


class ScreenshotTests(SeleniumUnitTest):
    """Testing screenshot functionality."""
    def test_upload_screenshot(self):
        """Testing uploading a screenshot"""
        caption = 'Test caption'

        r = ReviewRequest.objects.filter(public=True, status='P',
                                         submitter=self.user)[0]
        r.screenshots = []
        r.save()

        self.selenium.open(r.get_absolute_url())
        self.selenium.click('upload-screenshot-link')
        self.selenium.type('id_caption', caption)
        self.selenium.focus('id_path')
        self.selenium.attach_file('id_path',
                                  self.test_url + 'media/rb/images/logo.png')
        self.selenium.click('css=.modalbox input[value="Upload"]')
        self.wait_for_ajax_finish()

        draft = r.get_draft(self.user)
        self.assertNotEqual(draft, None)
        self.assertEqual(draft.screenshots.count(), 1)

        screenshot = draft.screenshots.get()

        url = self.test_url + screenshot.image.url.strip('/')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)

        self.assertEqual(screenshot.draft_caption, caption)
        self.assertTrue(self.selenium.is_visible(
            'css=img[alt="%s"][src="%s"]' % (caption,
                                             screenshot.get_thumbnail_url())))

    def test_modify_screenshot_caption(self):
        """Testing modifying a screenshot's caption on a review request"""
        caption = 'Test screenshot caption'
        draft_caption = 'New screenshot caption'

        r = ReviewRequest.objects.filter(public=True, status='P',
                                         submitter=self.user)[0]
        create_screenshot(r, caption)
        r.publish(self.user)

        self.selenium.open(r.get_absolute_url())
        self.selenium.click('css=.screenshot-caption .editicon')
        self.selenium.type('css=.screenshot-caption input[type="text"]',
                           draft_caption)
        self.selenium.key_press('css=.screenshot-caption input[type="text"]',
                                '\\13')
        self.wait_for_ajax_finish()

        draft = r.get_draft(self.user)
        self.assertNotEqual(draft, None)
        self.assertEqual(draft.screenshots.count(), 1)

        screenshot = draft.screenshots.get()
        self.assertEqual(screenshot.caption, caption)
        self.assertEqual(screenshot.draft_caption, draft_caption)

    def test_delete_screenshot(self):
        """Testing deleting a screenshot from a review request"""
        r = ReviewRequest.objects.filter(public=True, status='P',
                                         submitter=self.user)[0]
        create_screenshot(r)
        r.publish(self.user)

        self.selenium.open(r.get_absolute_url())
        self.selenium.click('css=.screenshot-caption '
                            'img[alt="Delete Screenshot"]')
        self.selenium.wait_for_page_to_load("6000")

        draft = r.get_draft(self.user)
        self.assertNotEqual(draft, None)
        self.assertEqual(draft.screenshots.count(), 0)
        self.assertEqual(r.screenshots.count(), 1)


class ScreenshotCommentTests(SeleniumUnitTest):
    """Testing screenshot comment functionality."""
    # NOTE: Much of this is common between ScreenshotTests and
    #       ScreenshotCommentTests. May want to commonize this in some way.
    def test_new_comment(self):
        """Testing screenshot comment creation"""
        comment_text = 'This is my test comment'
        comment_x = 3
        comment_y = 4
        comment_w = 12
        comment_h = 6

        r = self._get_review_request()
        screenshot = create_screenshot(r)

        self.selenium.open(screenshot.get_absolute_url())
        self._create_comment_at(comment_x, comment_y, comment_w, comment_h,
                                comment_text)

        self.assertEqual(r.reviews.count(), 1)
        review = r.reviews.latest()
        self.assertFalse(review.public)
        self.assertEqual(review.screenshot_comments.count(), 1)
        comment = review.screenshot_comments.all()[0]
        self.assertEqual(comment.text, comment_text)
        self.assertEqual(comment.x, comment_x)
        self.assertEqual(comment.y, comment_y)
        self.assertEqual(comment.w, comment_w)
        self.assertEqual(comment.h, comment_h)

    def test_delete_comment(self):
        """Testing deleting draft screenshot comment"""
        comment_text = 'This is my test comment'
        comment_x = 3
        comment_y = 4
        comment_w = 12
        comment_h = 6

        r = self._get_review_request()
        screenshot = create_screenshot(r)

        self.selenium.open(screenshot.get_absolute_url())
        self._create_comment_at(comment_x, comment_y, comment_w, comment_h,
                                comment_text)

        # Now delete it
        self.selenium.click('css=.flag-draft')
        self.wait_for_visible('comment-detail')
        self.selenium.click('comment_delete')
        self.wait_for_ajax_finish()

        self.assertEqual(r.reviews.count(), 0)

    def _get_review_request(self):
        r = ReviewRequest.objects.filter(public=True, status='P',
                                         submitter=self.user)[0]
        r.screenshots = []
        r.reviews = []
        r.save()

        return r

    def _create_comment_at(self, x, y, w, h, text):
        # NOTE: There appears to be an off-by-two in Selenium's interaction
        #       with our screenshot page. Coordinates given must be two higher
        #       than coordinates we want. Verified with the same browsers that
        #       this doesn't happen when manually attempting this.
        x += 2
        y += 2

        screenshot_img_el = 'css=#screenshot-display img'
        self.selenium.mouse_down_at(screenshot_img_el, '%s,%s' % (x, y))

        mouse_up_pos = '%s,%s' % (x + w, y + h)
        self.selenium.mouse_move_at(screenshot_img_el, mouse_up_pos)
        self.selenium.mouse_up_at(screenshot_img_el, mouse_up_pos)

        self.selenium.type_keys('comment_text', text)
        self.selenium.click('comment_save')
        self.wait_for_ajax_finish()
