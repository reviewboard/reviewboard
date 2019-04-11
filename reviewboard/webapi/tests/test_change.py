from __future__ import unicode_literals

from datetime import timedelta

from django.contrib.auth.models import User
from django.core.files import File
from django.utils import six, timezone
from djblets.testing.decorators import add_fixtures
from djblets.webapi.errors import PERMISSION_DENIED

from reviewboard.changedescs.models import ChangeDescription
from reviewboard.reviews.models import (Group,
                                        ReviewRequest,
                                        ReviewRequestDraft,
                                        Screenshot)
from reviewboard.webapi.tests.base import BaseWebAPITestCase
from reviewboard.webapi.tests.mimetypes import (change_item_mimetype,
                                                change_list_mimetype)
from reviewboard.webapi.tests.mixins import (ReviewRequestChildItemMixin,
                                             ReviewRequestChildListMixin)
from reviewboard.webapi.tests.urls import (get_change_item_url,
                                           get_change_list_url)


class ResourceListTests(ReviewRequestChildListMixin, BaseWebAPITestCase):
    """Testing the ChangeResource list APIs."""
    fixtures = ['test_users']
    sample_api_url = 'review-requests/<id>/changes/'

    def setup_review_request_child_test(self, review_request):
        return get_change_list_url(review_request), change_list_mimetype

    #
    # HTTP GET tests
    #

    @add_fixtures(['test_scmtools'])
    def test_get(self):
        """Testing the GET review-requests/<id>/changes/ API"""
        review_request = self.create_review_request(publish=True)

        now = timezone.now()
        change1 = ChangeDescription(public=True,
                                    timestamp=now)
        change1.record_field_change('summary', 'foo', 'bar')
        change1.save()
        review_request.changedescs.add(change1)

        change2 = ChangeDescription(public=True,
                                    timestamp=now + timedelta(seconds=1))
        change2.record_field_change('description', 'foo', 'bar')
        change2.save()
        review_request.changedescs.add(change2)

        rsp = self.api_get(get_change_list_url(review_request),
                           expected_mimetype=change_list_mimetype)
        self.assertEqual(rsp['stat'], 'ok')
        self.assertEqual(len(rsp['changes']), 2)

        self.assertEqual(rsp['changes'][0]['id'], change2.pk)
        self.assertEqual(rsp['changes'][1]['id'], change1.pk)

    @add_fixtures(['test_scmtools'])
    def test_get_with_status_change(self):
        """Testing the GET review-requests/<id>/changes/ API
        with review request status changes.
        """
        review_request = self.create_review_request(publish=True)
        review_request.close(ReviewRequest.SUBMITTED, description='Closed!')

        rsp = self.api_get(get_change_list_url(review_request),
                           expected_mimetype=change_list_mimetype)
        self.assertEqual(rsp['stat'], 'ok')
        self.assertEqual(len(rsp['changes']), 1)

        self.assertTrue('status' in rsp['changes'][0]['fields_changed'])

    @add_fixtures(['test_site'])
    def test_get_with_site(self):
        """Testing the GET review-requests/<id>/changes/ API
        with access to a local site
        """
        review_request = self.create_review_request(publish=True,
                                                    with_local_site=True)

        self._login_user(local_site=True)

        now = timezone.now()
        change1 = ChangeDescription(public=True,
                                    timestamp=now)
        change1.record_field_change('summary', 'foo', 'bar')
        change1.save()
        review_request.changedescs.add(change1)

        change2 = ChangeDescription(public=True,
                                    timestamp=now + timedelta(seconds=1))
        change2.record_field_change('description', 'foo', 'bar')
        change2.save()
        review_request.changedescs.add(change2)

        rsp = self.api_get(
            get_change_list_url(review_request, self.local_site_name),
            expected_mimetype=change_list_mimetype)
        self.assertEqual(rsp['stat'], 'ok')
        self.assertEqual(len(rsp['changes']), 2)

        self.assertEqual(rsp['changes'][0]['id'], change2.pk)
        self.assertEqual(rsp['changes'][1]['id'], change1.pk)

    @add_fixtures(['test_site'])
    def test_get_with_site_no_access(self):
        """Testing the GET review-requests/<id>/changes/ API
        without access to a local site
        """
        review_request = self.create_review_request(publish=True,
                                                    with_local_site=True)

        rsp = self.api_get(
            get_change_list_url(review_request, self.local_site_name),
            expected_status=403)
        self.assertEqual(rsp['stat'], 'fail')
        self.assertEqual(rsp['err']['code'], PERMISSION_DENIED.code)

    #
    # HTTP POST tests
    #

    def test_post_method_not_allowed(self):
        """Testing the POST review-requests/<id>/changes/ API
        gives Method Not Allowed
        """
        review_request = self.create_review_request()

        self.api_post(get_change_list_url(review_request), expected_status=405)


class ResourceItemTests(ReviewRequestChildItemMixin, BaseWebAPITestCase):
    """Testing the ChangeResource item APIs."""
    fixtures = ['test_users']
    sample_api_url = 'review-requests/<id>/changes/<id>/'

    def setup_review_request_child_test(self, review_request):
        change = ChangeDescription.objects.create(public=True)
        review_request.changedescs.add(change)

        return get_change_item_url(change), change_item_mimetype

    #
    # HTTP DELETE tests
    #

    def test_delete_method_not_allowed(self):
        """Testing the DELETE review-requests/<id>/changes/ API
        gives Method Not Allowed
        """
        review_request = self.create_review_request()

        change = ChangeDescription.objects.create(public=True)
        review_request.changedescs.add(change)

        self.api_delete(get_change_item_url(change), expected_status=405)

    #
    # HTTP GET tests
    #

    @add_fixtures(['test_scmtools'])
    def test_get(self):
        """Testing the GET review-requests/<id>/changes/<id>/ API"""
        def write_fields(obj, index):
            for field, data in six.iteritems(test_data):
                value = data[index]

                if isinstance(value, list) and field not in model_fields:
                    value = ','.join(value)

                if field == 'diff':
                    field = 'diffset'

                setattr(obj, field, value)

        changedesc_text = 'Change description text'
        user1, user2 = User.objects.all()[:2]
        group1 = Group.objects.create(name='group1')
        group2 = Group.objects.create(name='group2')
        repository = self.create_repository()
        diff1 = self.create_diffset(revision=1, repository=repository)
        diff2 = self.create_diffset(revision=2, repository=repository)
        old_screenshot_caption = 'old screenshot'
        new_screenshot_caption = 'new screenshot'
        screenshot1 = Screenshot.objects.create()
        screenshot2 = Screenshot.objects.create()
        screenshot3 = Screenshot.objects.create(caption=old_screenshot_caption)

        for screenshot in [screenshot1, screenshot2, screenshot3]:
            with open(self.get_sample_image_filename(), 'rb') as f:
                screenshot.image.save('foo.png', File(f), save=True)

        test_data = {
            'summary': ('old summary', 'new summary', None, None),
            'description': ('old description', 'new description', None, None),
            'testing_done': ('old testing done', 'new testing done',
                             None, None),
            'branch': ('old branch', 'new branch', None, None),
            'bugs_closed': (['1', '2', '3'], ['2', '3', '4'], ['1'], ['4']),
            'target_people': ([user1], [user2], [user1], [user2]),
            'target_groups': ([group1], [group2], [group1], [group2]),
            'screenshots': ([screenshot1, screenshot3],
                            [screenshot2, screenshot3],
                            [screenshot1],
                            [screenshot2]),
            'diff': (diff1, diff2, None, diff2),
        }
        model_fields = ('target_people', 'target_groups', 'screenshots',
                        'diff')

        # Set the initial data on the review request.
        r = self.create_review_request(submitter=self.user)
        write_fields(r, 0)
        r.publish(self.user)

        # Create some draft data that will end up in the change description.
        draft = ReviewRequestDraft.create(r)
        write_fields(draft, 1)

        # Special-case screenshots
        draft.inactive_screenshots = test_data['screenshots'][2]
        screenshot3.draft_caption = new_screenshot_caption
        screenshot3.save()

        draft.changedesc.text = changedesc_text
        draft.changedesc.save()
        draft.save()
        r.publish(self.user)

        # Sanity check the ChangeDescription
        self.assertEqual(r.changedescs.count(), 1)
        change = r.changedescs.get()
        self.assertEqual(change.text, changedesc_text)

        for field, data in six.iteritems(test_data):
            old, new, removed, added = data
            field_data = change.fields_changed[field]

            if field == 'diff':
                # Diff fields are special. They only have "added".
                self.assertEqual(len(field_data['added']), 1)
                self.assertEqual(field_data['added'][0][2], added.pk)
            elif field in model_fields:
                self.assertEqual([item[2] for item in field_data['old']],
                                 [obj.pk for obj in old])
                self.assertEqual([item[2] for item in field_data['new']],
                                 [obj.pk for obj in new])
                self.assertEqual([item[2] for item in field_data['removed']],
                                 [obj.pk for obj in removed])
                self.assertEqual([item[2] for item in field_data['added']],
                                 [obj.pk for obj in added])
            elif isinstance(old, list):
                self.assertEqual(field_data['old'],
                                 [[value] for value in old])
                self.assertEqual(field_data['new'],
                                 [[value] for value in new])
                self.assertEqual(field_data['removed'],
                                 [[value] for value in removed])
                self.assertEqual(field_data['added'],
                                 [[value] for value in added])
            else:
                self.assertEqual(field_data['old'], [old])
                self.assertEqual(field_data['new'], [new])
                self.assertNotIn('removed', field_data)
                self.assertNotIn('added', field_data)

        self.assertIn('screenshot_captions', change.fields_changed)
        field_data = change.fields_changed['screenshot_captions']
        screenshot_id = six.text_type(screenshot3.pk)
        self.assertIn(screenshot_id, field_data)
        self.assertIn('old', field_data[screenshot_id])
        self.assertIn('new', field_data[screenshot_id])
        self.assertEqual(field_data[screenshot_id]['old'][0],
                         old_screenshot_caption)
        self.assertEqual(field_data[screenshot_id]['new'][0],
                         new_screenshot_caption)

        # Now confirm with the API
        rsp = self.api_get(get_change_list_url(r),
                           expected_mimetype=change_list_mimetype)
        self.assertEqual(rsp['stat'], 'ok')
        self.assertEqual(len(rsp['changes']), 1)

        self.assertEqual(rsp['changes'][0]['id'], change.pk)
        rsp = self.api_get(rsp['changes'][0]['links']['self']['href'],
                           expected_mimetype=change_item_mimetype)
        self.assertEqual(rsp['stat'], 'ok')
        self.assertEqual(rsp['change']['text'], changedesc_text)

        fields_changed = rsp['change']['fields_changed']

        for field, data in six.iteritems(test_data):
            old, new, removed, added = data

            self.assertIn(field, fields_changed)
            field_data = fields_changed[field]

            if field == 'diff':
                self.assertIn('added', field_data)
                self.assertEqual(field_data['added']['id'], added.pk)
            elif field in model_fields:
                self.assertIn('old', field_data)
                self.assertIn('new', field_data)
                self.assertIn('added', field_data)
                self.assertIn('removed', field_data)
                self.assertEqual(
                    [item['id'] for item in field_data['old']],
                    [obj.pk for obj in old])
                self.assertEqual(
                    [item['id'] for item in field_data['new']],
                    [obj.pk for obj in new])
                self.assertEqual(
                    [item['id'] for item in field_data['removed']],
                    [obj.pk for obj in removed])
                self.assertEqual(
                    [item['id'] for item in field_data['added']],
                    [obj.pk for obj in added])
            else:
                self.assertIn('old', field_data)
                self.assertIn('new', field_data)
                self.assertEqual(field_data['old'], old)
                self.assertEqual(field_data['new'], new)

                if isinstance(old, list):
                    self.assertIn('added', field_data)
                    self.assertIn('removed', field_data)

                    self.assertEqual(field_data['added'], added)
                    self.assertEqual(field_data['removed'], removed)

        self.assertIn('screenshot_captions', fields_changed)
        field_data = fields_changed['screenshot_captions']
        self.assertEqual(len(field_data), 1)
        screenshot_data = field_data[0]
        self.assertIn('old', screenshot_data)
        self.assertIn('new', screenshot_data)
        self.assertIn('screenshot', screenshot_data)
        self.assertEqual(screenshot_data['old'], old_screenshot_caption)
        self.assertEqual(screenshot_data['new'], new_screenshot_caption)
        self.assertEqual(screenshot_data['screenshot']['id'], screenshot3.pk)

    @add_fixtures(['test_site'])
    def test_get_with_site(self):
        """Testing the GET review-requests/<id>/changes/<id>/ API
        with access to a local site
        """
        review_request = self.create_review_request(publish=True,
                                                    with_local_site=True)

        self._login_user(local_site=True)

        now = timezone.now()
        change = ChangeDescription(public=True, timestamp=now)
        change.record_field_change('summary', 'foo', 'bar')
        change.save()
        review_request.changedescs.add(change)

        rsp = self.api_get(
            get_change_item_url(change, self.local_site_name),
            expected_mimetype=change_item_mimetype)
        self.assertEqual(rsp['stat'], 'ok')
        self.assertEqual(rsp['change']['id'], change.pk)

    @add_fixtures(['test_site'])
    def test_get_with_site_no_access(self):
        """Testing the GET review-requests/<id>/changes/<id>/ API
        without access to a local site
        """
        review_request = self.create_review_request(publish=True,
                                                    with_local_site=True)

        now = timezone.now()
        change = ChangeDescription(public=True, timestamp=now)
        change.record_field_change('summary', 'foo', 'bar')
        change.save()
        review_request.changedescs.add(change)

        rsp = self.api_get(
            get_change_item_url(change, self.local_site_name),
            expected_status=403)
        self.assertEqual(rsp['stat'], 'fail')
        self.assertEqual(rsp['err']['code'], PERMISSION_DENIED.code)

    def test_get_not_modified(self):
        """Testing the GET review-requests/<id>/changes/<id>/ API
        with Not Modified response
        """
        review_request = self.create_review_request(publish=True)

        changedesc = ChangeDescription.objects.create(public=True)
        review_request.changedescs.add(changedesc)

        self._testHttpCaching(get_change_item_url(changedesc),
                              check_etags=True)

    #
    # HTTP PUT tests
    #

    def test_put_method_not_allowed(self):
        """Testing the PUT review-requests/<id>/changes/ API
        gives Method Not Allowed
        """
        review_request = self.create_review_request()

        change = ChangeDescription.objects.create(public=True)
        review_request.changedescs.add(change)

        self.api_put(get_change_item_url(change), {}, expected_status=405)
