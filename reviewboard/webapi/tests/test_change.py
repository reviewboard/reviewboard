from datetime import timedelta

from django.contrib.auth.models import User
from django.core.files import File
from django.utils import timezone
from djblets.testing.decorators import add_fixtures

from reviewboard.changedescs.models import ChangeDescription
from reviewboard.diffviewer.models import DiffSet
from reviewboard.reviews.models import (Group, ReviewRequest,
                                        ReviewRequestDraft, Screenshot)
from reviewboard.webapi.tests.base import BaseWebAPITestCase
from reviewboard.webapi.tests.mimetypes import (change_item_mimetype,
                                                change_list_mimetype)
from reviewboard.webapi.tests.urls import get_change_item_url


class ChangeResourceTests(BaseWebAPITestCase):
    """Testing the ChangeResourceAPIs."""
    fixtures = ['test_users', 'test_scmtools', 'test_reviewrequests']

    def test_get_changes(self):
        """Testing the GET review-requests/<id>/changes/ API"""
        rsp = self._postNewReviewRequest()
        self.assertTrue('changes' in rsp['review_request']['links'])

        r = ReviewRequest.objects.get(pk=rsp['review_request']['id'])

        now = timezone.now()
        change1 = ChangeDescription(public=True,
                                    timestamp=now)
        change1.record_field_change('summary', 'foo', 'bar')
        change1.save()
        r.changedescs.add(change1)

        change2 = ChangeDescription(public=True,
                                    timestamp=now + timedelta(seconds=1))
        change2.record_field_change('description', 'foo', 'bar')
        change2.save()
        r.changedescs.add(change2)

        rsp = self.apiGet(rsp['review_request']['links']['changes']['href'],
                          expected_mimetype=change_list_mimetype)
        self.assertEqual(rsp['stat'], 'ok')
        self.assertEqual(len(rsp['changes']), 2)

        self.assertEqual(rsp['changes'][0]['id'], change2.pk)
        self.assertEqual(rsp['changes'][1]['id'], change1.pk)

    def test_get_change(self):
        """Testing the GET review-requests/<id>/changes/<id>/ API"""
        def write_fields(obj, index):
            for field, data in test_data.iteritems():
                value = data[index]

                if isinstance(value, list) and field not in model_fields:
                    value = ','.join(value)

                if field == 'diff':
                    field = 'diffset'

                setattr(obj, field, value)

        changedesc_text = 'Change description text'
        user1, user2 = User.objects.all()[:2]
        group1, group2 = Group.objects.all()[:2]
        diff1, diff2 = DiffSet.objects.all()[:2]
        old_screenshot_caption = 'old screenshot'
        new_screenshot_caption = 'new screenshot'
        screenshot1 = Screenshot.objects.create()
        screenshot2 = Screenshot.objects.create()
        screenshot3 = Screenshot.objects.create(caption=old_screenshot_caption)

        for screenshot in [screenshot1, screenshot2, screenshot3]:
            f = open(self._getTrophyFilename(), 'r')
            screenshot.image.save('foo.png', File(f), save=True)
            f.close()

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
        model_fields = ('target_people', 'target_groups', 'screenshots', 'diff')

        rsp = self._postNewReviewRequest()
        self.assertTrue('changes' in rsp['review_request']['links'])

        # Set the initial data on the review request.
        r = ReviewRequest.objects.get(pk=rsp['review_request']['id'])
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

        for field, data in test_data.iteritems():
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
                self.assertTrue('removed' not in field_data)
                self.assertTrue('added' not in field_data)

        self.assertTrue('screenshot_captions' in change.fields_changed)
        field_data = change.fields_changed['screenshot_captions']
        screenshot_id = str(screenshot3.pk)
        self.assertTrue(screenshot_id in field_data)
        self.assertTrue('old' in field_data[screenshot_id])
        self.assertTrue('new' in field_data[screenshot_id])
        self.assertEqual(field_data[screenshot_id]['old'][0],
                         old_screenshot_caption)
        self.assertEqual(field_data[screenshot_id]['new'][0],
                         new_screenshot_caption)

        # Now confirm with the API
        rsp = self.apiGet(rsp['review_request']['links']['changes']['href'],
                          expected_mimetype=change_list_mimetype)
        self.assertEqual(rsp['stat'], 'ok')
        self.assertEqual(len(rsp['changes']), 1)

        self.assertEqual(rsp['changes'][0]['id'], change.pk)
        rsp = self.apiGet(rsp['changes'][0]['links']['self']['href'],
                          expected_mimetype=change_item_mimetype)
        self.assertEqual(rsp['stat'], 'ok')
        self.assertEqual(rsp['change']['text'], changedesc_text)

        fields_changed = rsp['change']['fields_changed']

        for field, data in test_data.iteritems():
            old, new, removed, added = data

            self.assertTrue(field in fields_changed)
            field_data = fields_changed[field]

            if field == 'diff':
                self.assertTrue('added' in field_data)
                self.assertEqual(field_data['added']['id'], added.pk)
            elif field in model_fields:
                self.assertTrue('old' in field_data)
                self.assertTrue('new' in field_data)
                self.assertTrue('added' in field_data)
                self.assertTrue('removed' in field_data)
                self.assertEqual([item['id'] for item in field_data['old']],
                                 [obj.pk for obj in old])
                self.assertEqual([item['id'] for item in field_data['new']],
                                 [obj.pk for obj in new])
                self.assertEqual([item['id'] for item in field_data['removed']],
                                 [obj.pk for obj in removed])
                self.assertEqual([item['id'] for item in field_data['added']],
                                 [obj.pk for obj in added])
            else:
                self.assertTrue('old' in field_data)
                self.assertTrue('new' in field_data)
                self.assertEqual(field_data['old'], old)
                self.assertEqual(field_data['new'], new)

                if isinstance(old, list):
                    self.assertTrue('added' in field_data)
                    self.assertTrue('removed' in field_data)

                    self.assertEqual(field_data['added'], added)
                    self.assertEqual(field_data['removed'], removed)

        self.assertTrue('screenshot_captions' in fields_changed)
        field_data = fields_changed['screenshot_captions']
        self.assertEqual(len(field_data), 1)
        screenshot_data = field_data[0]
        self.assertTrue('old' in screenshot_data)
        self.assertTrue('new' in screenshot_data)
        self.assertTrue('screenshot' in screenshot_data)
        self.assertEqual(screenshot_data['old'], old_screenshot_caption)
        self.assertEqual(screenshot_data['new'], new_screenshot_caption)
        self.assertEqual(screenshot_data['screenshot']['id'], screenshot3.pk)

    @add_fixtures(['test_site'])
    def test_get_change_not_modified(self):
        """Testing the GET review-requests/<id>/changes/<id>/ API with Not Modified response"""
        review_request = ReviewRequest.objects.public()[0]

        changedesc = ChangeDescription(public=True)
        changedesc.save()
        review_request.changedescs.add(changedesc)

        self._testHttpCaching(get_change_item_url(changedesc),
                              check_last_modified=True)
