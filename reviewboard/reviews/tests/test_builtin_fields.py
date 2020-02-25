"""Unit tests for reviewboard.reviews.builtin_fields."""

from __future__ import unicode_literals

from django.contrib.auth.models import AnonymousUser, User
from django.core.urlresolvers import resolve
from django.test.client import RequestFactory
from django.utils.safestring import SafeText

from reviewboard.reviews.builtin_fields import (CommitListField,
                                                FileAttachmentsField)
from reviewboard.reviews.detail import ReviewRequestPageData
from reviewboard.reviews.models import ReviewRequestDraft
from reviewboard.testing.testcase import TestCase


class FieldsTestCase(TestCase):
    """Base test case for built-in fields."""

    field_cls = None

    def make_field(self, review_request):
        """Return an instance of the field to test with.

        The field will be populated with all review request page state.

        Args:
            review_request (reviewboard.reviews.models.review_request.
                            ReviewRequest):
                The review request being tested.

        Returns:
            reviewboard.reviews.fields.BaseReviewRequestField:
            The resulting field instance.
        """
        request = self.build_review_request_get(review_request)

        data = ReviewRequestPageData(review_request, request)
        data.query_data_pre_etag()
        data.query_data_post_etag()

        return self.field_cls(review_request, request=request, data=data)

    def build_review_request_get(self, review_request):
        """Return an HTTP GET request for the review request.

        This will return a new HTTP request to a review request's page,
        containing a resolver match, without actually fetching the page.

        Args:
            review_request (reviewboard.reviews.models.review_request.
                            ReviewRequest):
                The review request being tested.

        Returns:
            django.http.HttpRequest:
            The request for the review request detail page.
        """
        url = review_request.get_absolute_url()
        request = RequestFactory().get(url)
        request.user = AnonymousUser()
        request.resolver_match = resolve(url)

        return request


class CommitListFieldTests(FieldsTestCase):
    """Unit tests for CommitListField."""

    field_cls = CommitListField
    fixtures = ['test_scmtools', 'test_users']

    def test_should_render_history_review_request(self):
        """Testing CommitListField.should_render with a review request created
        with history
        """
        review_request = self.create_review_request(create_with_history=True)
        request = self.build_review_request_get(review_request)
        field = CommitListField(review_request, request=request)

        self.assertTrue(field.should_render)

    def test_should_render_history_draft(self):
        """Testing CommitListField.should_render with a draft of a review
        request created with history
        """
        review_request = self.create_review_request(create_with_history=True)
        draft = ReviewRequestDraft.create(review_request)
        request = self.build_review_request_get(review_request)
        field = CommitListField(draft, request=request)

        self.assertTrue(field.should_render)

    def test_should_render_no_history_review_request(self):
        """Testing CommitListField.should_render with a review request created
        without history
        """
        review_request = self.create_review_request()
        request = self.build_review_request_get(review_request)
        field = CommitListField(review_request, request=request)

        self.assertFalse(field.should_render)

    def test_should_render_no_history_draft(self):
        """Testing CommitListField.should_render with a draft of a review
        request created without history
        """
        review_request = self.create_review_request()
        draft = ReviewRequestDraft.create(review_request)
        request = self.build_review_request_get(review_request)
        field = CommitListField(draft, request=request)

        self.assertFalse(field.should_render)

    def test_can_record_change_entry_history_review_request(self):
        """Testing CommitListField.can_record_change_entry with a review
        request created with history
        """
        review_request = self.create_review_request(create_with_history=True)
        field = CommitListField(review_request)

        self.assertTrue(field.can_record_change_entry)

    def test_can_record_change_entry_history_draft(self):
        """Testing CommitListField.can_record_change_entry with a draft of a
        review request created with history
        """
        review_request = self.create_review_request(create_with_history=True)
        draft = ReviewRequestDraft.create(review_request)
        field = CommitListField(draft)

        self.assertTrue(field.can_record_change_entry)

    def test_can_record_change_entry_no_history_review_request(self):
        """Testing CommitListField.can_record_change_entry with a review
        request created without history
        """
        review_request = self.create_review_request()
        field = CommitListField(review_request)

        self.assertFalse(field.can_record_change_entry)

    def test_can_record_change_entry_no_history_draft(self):
        """Testing CommitListField.can_record_change_entry with a draft of a
        review request created without history
        """
        review_request = self.create_review_request()
        draft = ReviewRequestDraft.create(review_request)
        field = CommitListField(draft)

        self.assertFalse(field.can_record_change_entry)

    def test_render_value(self):
        """Testing CommitListField.render_value"""
        repository = self.create_repository(tool_name='Git')
        review_request = self.create_review_request(repository=repository,
                                                    create_with_history=True)
        diffset = self.create_diffset(review_request)

        author_name = review_request.submitter.get_full_name()

        self.create_diffcommit(diffset=diffset,
                               commit_id='r1',
                               parent_id='r0',
                               commit_message='Commit message 1',
                               author_name=author_name),
        self.create_diffcommit(diffset=diffset,
                               commit_id='r2',
                               parent_id='r1',
                               commit_message='Commit message 2',
                               author_name=author_name)

        field = self.make_field(review_request)
        result = field.render_value(field.load_value(review_request))

        self.assertInHTML('<colgroup><col></colgroup>', result)
        self.assertInHTML('<tr><th>Summary</th></tr>', result)
        self.assertInHTML(
            '<tbody>'
            ' <tr>'
            '  <td class="commit-message"><pre>Commit message 1</pre></td>'
            ' </tr>'
            ' <tr>'
            '  <td class="commit-message"><pre>Commit message 2</pre></td>'
            ' </tr>'
            '</tbody>',
            result)

    def test_render_value_with_author(self):
        """Testing CommitListField.render_value with an author that differs
        from the review request submitter
        """
        repository = self.create_repository(tool_name='Git')
        review_request = self.create_review_request(repository=repository,
                                                    create_with_history=True)
        diffset = self.create_diffset(review_request)

        submitter_name = review_request.submitter.get_full_name()

        self.create_diffcommit(diffset=diffset,
                               commit_id='r1',
                               parent_id='r0',
                               commit_message='Commit message 1',
                               author_name='Example Author')
        self.create_diffcommit(diffset=diffset,
                               commit_id='r2',
                               parent_id='r1',
                               commit_message='Commit message 2',
                               author_name=submitter_name)

        field = self.make_field(review_request)
        result = field.render_value(field.load_value(review_request))

        self.assertInHTML('<colgroup><col><col></colgroup>', result)
        self.assertInHTML(
            '<tr><th>Summary</th><th>Author</th></tr>',
            result)
        self.assertInHTML(
            '<tbody>'
            ' <tr>'
            '  <td class="commit-message"><pre>Commit message 1</pre></td>'
            '  <td>Example Author</td>'
            ' </tr>'
            ' <tr>'
            '  <td class="commit-message"><pre>Commit message 2</pre></td>'
            '  <td>%s</td>'
            ' </tr>'
            '</tbody>'
            % submitter_name,
            result)

    def test_render_value_with_collapse(self):
        """Testing CommitListField.render_value with a multi-line commit
        message
        """
        repository = self.create_repository(tool_name='Git')
        review_request = self.create_review_request(repository=repository,
                                                    create_with_history=True)
        diffset = self.create_diffset(review_request)

        author_name = review_request.submitter.get_full_name()

        self.create_diffcommit(diffset=diffset,
                               commit_id='r1',
                               parent_id='r0',
                               commit_message='Commit message 1',
                               author_name=author_name)
        self.create_diffcommit(diffset=diffset,
                               commit_id='r2',
                               parent_id='r1',
                               commit_message='Commit message 2\n'
                                              'Longer message\n',
                               author_name=author_name)

        field = self.make_field(review_request)
        result = field.render_value(field.load_value(review_request))

        self.assertInHTML(
            '<colgroup>'
            ' <col class="expand-collapse-control">'
            ' <col>'
            '</colgroup>',
            result)
        self.assertInHTML('<tr><th colspan="2">Summary</th></tr>', result)
        self.assertInHTML(
            '<tbody>'
            ' <tr>'
            '  <td></td>'
            '  <td class="commit-message"><pre>Commit message 1</pre></td>'
            ' </tr>'
            ' <tr>'
            '  <td>'
            '   <a href="#" class="expand-commit-message" '
            '      data-commit-id="2" aria-role="button">'
            '    <span class="fa fa-plus" title="Expand commit message." />'
            '   </a>'
            '  </td>'
            '  <td class="commit-message"><pre>Commit message 2</pre></td>'
            ' </tr>'
            '</tbody>',
            result)

    def test_render_value_with_collapse_and_author(self):
        """Testing CommitListField.render_value with an author that differs
        from the review request submitter and a multi-line commit message
        """
        repository = self.create_repository(tool_name='Git')
        review_request = self.create_review_request(repository=repository,
                                                    create_with_history=True)
        diffset = self.create_diffset(review_request)

        submitter_name = review_request.submitter.get_full_name()

        self.create_diffcommit(diffset=diffset,
                               commit_id='r1',
                               parent_id='r0',
                               commit_message='Commit message 1',
                               author_name='Example Author')
        self.create_diffcommit(diffset=diffset,
                               commit_id='r2',
                               parent_id='r1',
                               commit_message='Commit message 2\n'
                                              'Longer message\n',
                               author_name=submitter_name)

        field = self.make_field(review_request)
        result = field.render_value(field.load_value(review_request))

        self.assertInHTML(
            '<colgroup>'
            ' <col class="expand-collapse-control">'
            ' <col>'
            ' <col>'
            '</colgroup>',
            result)
        self.assertInHTML(
            '<tr>'
            ' <th colspan="2">Summary</th>'
            ' <th>Author</th>'
            '</tr>',
            result)
        self.assertInHTML(
            '<tbody>'
            ' <tr>'
            '  <td></td>'
            '  <td class="commit-message"><pre>Commit message 1</pre></td>'
            '  <td>Example Author</td>'
            ' </tr>'
            ' <tr>'
            '  <td>'
            '   <a href="#" class="expand-commit-message" '
            '      data-commit-id="2" aria-role="button">'
            '    <span class="fa fa-plus" title="Expand commit message." />'
            '   </a>'
            '  </td>'
            '  <td class="commit-message"><pre>Commit message 2</pre></td>'
            '  <td>%s</td>'
            ' </tr>'
            '</tbody>'
            % submitter_name,
            result)

    def test_render_change_entry_html(self):
        """Testing CommitListField.render_change_entry_html"""
        target = User.objects.get(username='doc')
        repository = self.create_repository(tool_name='Git')
        review_request = self.create_review_request(repository=repository,
                                                    target_people=[target],
                                                    public=True,
                                                    create_with_history=True)
        diffset = self.create_diffset(review_request)

        author_name = review_request.submitter.get_full_name()

        self.create_diffcommit(diffset=diffset,
                               commit_id='r1',
                               parent_id='r0',
                               commit_message='Commit message 1',
                               author_name=author_name)
        self.create_diffcommit(diffset=diffset,
                               commit_id='r2',
                               parent_id='r1',
                               commit_message='Commit message 2',
                               author_name=author_name)

        draft_diffset = self.create_diffset(review_request, draft=True)
        self.create_diffcommit(diffset=draft_diffset,
                               commit_id='r1',
                               parent_id='r0',
                               commit_message='New commit message 1',
                               author_name=author_name)

        self.create_diffcommit(diffset=draft_diffset,
                               commit_id='r2',
                               parent_id='r1',
                               commit_message='New commit message 2',
                               author_name=author_name)

        draft_diffset.finalize_commit_series(
            cumulative_diff=self.DEFAULT_GIT_FILEDIFF_DATA_DIFF,
            validation_info=None,
            validate=False,
            save=True)

        review_request.publish(user=review_request.submitter)
        changedesc = review_request.changedescs.latest()

        field = self.make_field(review_request)
        result = field.render_change_entry_html(
            changedesc.fields_changed[field.field_id])

        self.assertInHTML('<colgroup><col><col></colgroup>', result)
        self.assertInHTML(
            '<thead>'
            ' <tr>'
            '  <th class="marker"></th>'
            '  <th>Summary</th>'
            ' </tr>'
            '</thead>',
            result)
        self.assertInHTML(
            '<tbody>'
            ' <tr class="old-value">'
            '  <td class="marker">-</td>'
            '  <td class="value"><pre>Commit message 1</pre></td>'
            ' </tr>'
            ' <tr class="old-value">'
            '  <td class="marker">-</td>'
            '  <td class="value"><pre>Commit message 2</pre></td>'
            ' </tr>'
            ' <tr class="new-value">'
            '  <td class="marker">+</td>'
            '  <td class="value"><pre>New commit message 1</pre></td>'
            ' </tr>'
            ' <tr class="new-value">'
            '  <td class="marker">+</td>'
            '  <td class="value"><pre>New commit message 2</pre></td>'
            ' </tr>'
            '</tbody>',
            result)

    def test_render_change_entry_html_expand(self):
        """Testing CommitListField.render_change_entry_html with a multi-line
        commit message
        """
        target = User.objects.get(username='doc')
        repository = self.create_repository(tool_name='Git')
        review_request = self.create_review_request(repository=repository,
                                                    target_people=[target],
                                                    public=True,
                                                    create_with_history=True)
        diffset = self.create_diffset(review_request)

        author_name = review_request.submitter.get_full_name()

        self.create_diffcommit(diffset=diffset,
                               commit_id='r1',
                               parent_id='r0',
                               commit_message='Commit message 1\n\n'
                                              'A long message.\n',
                               author_name=author_name)
        self.create_diffcommit(diffset=diffset,
                               commit_id='r2',
                               parent_id='r1',
                               commit_message='Commit message 2',
                               author_name=author_name)

        draft_diffset = self.create_diffset(review_request, draft=True)
        self.create_diffcommit(diffset=draft_diffset,
                               commit_id='r1',
                               parent_id='r0',
                               commit_message='New commit message 1',
                               author_name=author_name)

        self.create_diffcommit(diffset=draft_diffset,
                               commit_id='r2',
                               parent_id='r1',
                               commit_message='New commit message 2\n\n'
                                              'So very long of a message.\n',
                               author_name=author_name)

        draft_diffset.finalize_commit_series(
            cumulative_diff=self.DEFAULT_GIT_FILEDIFF_DATA_DIFF,
            validation_info=None,
            validate=False,
            save=True)

        review_request.publish(user=review_request.submitter)
        changedesc = review_request.changedescs.latest()

        field = self.make_field(review_request)
        result = field.render_change_entry_html(
            changedesc.fields_changed[field.field_id])

        self.assertInHTML(
            '<colgroup>'
            ' <col>'
            ' <col class="expand-collapse-control">'
            ' <col>'
            '</colgroup>',
            result)
        self.assertInHTML(
            '<thead>'
            ' <tr>'
            '  <th class="marker"></th>'
            '  <th colspan="2">Summary</th>'
            ' </tr>'
            '</thead>',
            result)
        self.assertInHTML(
            '<tbody>'
            ' <tr class="old-value">'
            '  <td class="marker">-</td>'
            '  <td>'
            '   <a href="#" class="expand-commit-message" '
            '      data-commit-id="1" aria-role="button">'
            '    <span class="fa fa-plus" title="Expand commit message." />'
            '   </a>'
            '  </td>'
            '  <td class="value"><pre>Commit message 1</pre></td>'
            ' </tr>'
            ' <tr class="old-value">'
            '  <td class="marker">-</td>'
            '  <td />'
            '  <td class="value"><pre>Commit message 2</pre></td>'
            ' </tr>'
            ' <tr class="new-value">'
            '  <td class="marker">+</td>'
            '  <td />'
            '  <td class="value"><pre>New commit message 1</pre></td>'
            ' </tr>'
            ' <tr class="new-value">'
            '  <td class="marker">+</td>'
            '  <td>'
            '   <a href="#" class="expand-commit-message" '
            '      data-commit-id="4" aria-role="button">'
            '    <span class="fa fa-plus" title="Expand commit message." />'
            '   </a>'
            '  </td>'
            '  <td class="value"><pre>New commit message 2</pre></td>'
            ' </tr>'
            '</tbody>',
            result)

    def test_render_change_entry_html_expand_with_author(self):
        """Testing CommitListField.render_change_entry_html with an author that
        differs from the review request submitter and a multi-line commit
        message
        """
        target = User.objects.get(username='doc')
        repository = self.create_repository(tool_name='Git')
        review_request = self.create_review_request(repository=repository,
                                                    target_people=[target],
                                                    public=True,
                                                    create_with_history=True)
        diffset = self.create_diffset(review_request)

        submitter_name = review_request.submitter.get_full_name()

        self.create_diffcommit(diffset=diffset,
                               commit_id='r1',
                               parent_id='r0',
                               commit_message='Commit message 1\n\n'
                                              'A long message.\n',
                               author_name='Example Author')
        self.create_diffcommit(diffset=diffset,
                               commit_id='r2',
                               parent_id='r1',
                               commit_message='Commit message 2',
                               author_name=submitter_name)

        draft_diffset = self.create_diffset(review_request, draft=True)
        self.create_diffcommit(diffset=draft_diffset,
                               commit_id='r1',
                               parent_id='r0',
                               commit_message='New commit message 1',
                               author_name=submitter_name)

        self.create_diffcommit(diffset=draft_diffset,
                               commit_id='r2',
                               parent_id='r1',
                               commit_message='New commit message 2\n\n'
                                              'So very long of a message.\n',
                               author_name=submitter_name)

        draft_diffset.finalize_commit_series(
            cumulative_diff=self.DEFAULT_GIT_FILEDIFF_DATA_DIFF,
            validation_info=None,
            validate=False,
            save=True)

        review_request.publish(user=review_request.submitter)
        changedesc = review_request.changedescs.latest()

        field = self.make_field(review_request)
        result = field.render_change_entry_html(
            changedesc.fields_changed[field.field_id])

        self.assertInHTML(
            '<colgroup>'
            ' <col>'
            ' <col class="expand-collapse-control">'
            ' <col>'
            ' <col>'
            '</colgroup>',
            result)
        self.assertInHTML(
            '<thead>'
            ' <tr>'
            '  <th class="marker"></th>'
            '  <th colspan="2">Summary</th>'
            '  <th>Author</th>'
            ' </tr>'
            '</thead>',
            result)
        self.assertInHTML(
            '<tbody>'
            ' <tr class="old-value">'
            '  <td class="marker">-</td>'
            '  <td>'
            '   <a href="#" class="expand-commit-message" '
            '      data-commit-id="1" aria-role="button">'
            '    <span class="fa fa-plus" title="Expand commit message." />'
            '   </a>'
            '  </td>'
            '  <td class="value"><pre>Commit message 1</pre></td>'
            '  <td class="value">Example Author</td>'
            ' </tr>'
            ' <tr class="old-value">'
            '  <td class="marker">-</td>'
            '  <td />'
            '  <td class="value"><pre>Commit message 2</pre></td>'
            '  <td class="value">%(name)s</td>'
            ' </tr>'
            ' <tr class="new-value">'
            '  <td class="marker">+</td>'
            '  <td />'
            '  <td class="value"><pre>New commit message 1</pre></td>'
            '  <td class="value">%(name)s</td>'
            ' </tr>'
            ' <tr class="new-value">'
            '  <td class="marker">+</td>'
            '  <td>'
            '   <a href="#" class="expand-commit-message" '
            '      data-commit-id="4" aria-role="button">'
            '    <span class="fa fa-plus" title="Expand commit message." />'
            '   </a>'
            '  </td>'
            '  <td class="value"><pre>New commit message 2</pre></td>'
            '  <td class="value">%(name)s</td>'
            ' </tr>'
            '</tbody>'
            % {'name': submitter_name},
            result)

    def test_render_change_entry_html_with_author_old(self):
        """Testing CommitListField.render_change_entry_html with an author that
        differs from the review request submitter in the old commits
        """
        target = User.objects.get(username='doc')
        repository = self.create_repository(tool_name='Git')
        review_request = self.create_review_request(repository=repository,
                                                    target_people=[target],
                                                    public=True,
                                                    create_with_history=True)
        diffset = self.create_diffset(review_request)

        submitter_name = review_request.submitter.get_full_name()

        self.create_diffcommit(diffset=diffset,
                               commit_id='r1',
                               parent_id='r0',
                               commit_message='Commit message 1',
                               author_name='Example Author')
        self.create_diffcommit(diffset=diffset,
                               commit_id='r2',
                               parent_id='r1',
                               commit_message='Commit message 2',
                               author_name=submitter_name)

        draft_diffset = self.create_diffset(review_request, draft=True)
        self.create_diffcommit(diffset=draft_diffset,
                               commit_id='r1',
                               parent_id='r0',
                               commit_message='New commit message 1',
                               author_name=submitter_name)

        self.create_diffcommit(diffset=draft_diffset,
                               commit_id='r2',
                               parent_id='r1',
                               commit_message='New commit message 2',
                               author_name=submitter_name)

        draft_diffset.finalize_commit_series(
            cumulative_diff=self.DEFAULT_GIT_FILEDIFF_DATA_DIFF,
            validation_info=None,
            validate=False,
            save=True)

        review_request.publish(user=review_request.submitter)
        changedesc = review_request.changedescs.latest()

        field = self.make_field(review_request)
        result = field.render_change_entry_html(
            changedesc.fields_changed[field.field_id])

        self.assertInHTML('<colgroup><col><col><col></colgroup>', result)
        self.assertInHTML(
            '<thead>'
            ' <tr>'
            '  <th class="marker"></th>'
            '  <th>Summary</th>'
            '  <th>Author</th>'
            ' </tr>'
            '</thead>',
            result)
        self.assertInHTML(
            '<tbody>'
            ' <tr class="old-value">'
            '  <td class="marker">-</td>'
            '  <td class="value"><pre>Commit message 1</pre></td>'
            '  <td class="value">Example Author</td>'
            ' </tr>'
            ' <tr class="old-value">'
            '  <td class="marker">-</td>'
            '  <td class="value"><pre>Commit message 2</pre></td>'
            '  <td class="value">%(name)s</td>'
            ' </tr>'
            ' <tr class="new-value">'
            '  <td class="marker">+</td>'
            '  <td class="value"><pre>New commit message 1</pre></td>'
            '  <td class="value">%(name)s</td>'
            ' </tr>'
            ' <tr class="new-value">'
            '  <td class="marker">+</td>'
            '  <td class="value"><pre>New commit message 2</pre></td>'
            '  <td class="value">%(name)s</td>'
            ' </tr>'
            '</tbody>'
            % {'name': submitter_name},
            result)

    def test_render_change_entry_html_with_author_new(self):
        """Testing CommitListField.render_change_entry_html with an author that
        differs from the review request submitter in the new commits
        """
        target = User.objects.get(username='doc')
        repository = self.create_repository(tool_name='Git')
        review_request = self.create_review_request(repository=repository,
                                                    target_people=[target],
                                                    public=True,
                                                    create_with_history=True)
        diffset = self.create_diffset(review_request)

        submitter_name = review_request.submitter.get_full_name()

        self.create_diffcommit(diffset=diffset,
                               commit_id='r1',
                               parent_id='r0',
                               commit_message='Commit message 1',
                               author_name=submitter_name)
        self.create_diffcommit(diffset=diffset,
                               commit_id='r2',
                               parent_id='r1',
                               commit_message='Commit message 2',
                               author_name=submitter_name)

        draft_diffset = self.create_diffset(review_request, draft=True)
        self.create_diffcommit(diffset=draft_diffset,
                               commit_id='r1',
                               parent_id='r0',
                               commit_message='New commit message 1',
                               author_name=submitter_name)

        self.create_diffcommit(diffset=draft_diffset,
                               commit_id='r2',
                               parent_id='r1',
                               commit_message='New commit message 2',
                               author_name='Example Author')

        draft_diffset.finalize_commit_series(
            cumulative_diff=self.DEFAULT_GIT_FILEDIFF_DATA_DIFF,
            validation_info=None,
            validate=False,
            save=True)

        review_request.publish(user=review_request.submitter)
        changedesc = review_request.changedescs.latest()

        field = self.make_field(review_request)
        result = field.render_change_entry_html(
            changedesc.fields_changed[field.field_id])

        self.assertInHTML('<colgroup><col><col><col></colgroup>', result)
        self.assertInHTML(
            '<thead>'
            ' <tr>'
            '  <th class="marker"></th>'
            '  <th>Summary</th>'
            '  <th>Author</th>'
            ' </tr>'
            '</thead>',
            result)
        self.assertInHTML(
            '<tbody>'
            ' <tr class="old-value">'
            '  <td class="marker">-</td>'
            '  <td class="value"><pre>Commit message 1</pre></td>'
            '  <td class="value">%(name)s</td>'
            ' </tr>'
            ' <tr class="old-value">'
            '  <td class="marker">-</td>'
            '  <td class="value"><pre>Commit message 2</pre></td>'
            '  <td class="value">%(name)s</td>'
            ' </tr>'
            ' <tr class="new-value">'
            '  <td class="marker">+</td>'
            '  <td class="value"><pre>New commit message 1</pre></td>'
            '  <td class="value">%(name)s</td>'
            ' </tr>'
            ' <tr class="new-value">'
            '  <td class="marker">+</td>'
            '  <td class="value"><pre>New commit message 2</pre></td>'
            '  <td class="value">Example Author</td>'
            ' </tr>'
            '</tbody>'
            % {'name': submitter_name},
            result)

    def test_serialize_change_entry(self):
        """Testing CommitListField.serialize_change_entry"""
        target = User.objects.get(username='doc')
        repository = self.create_repository(tool_name='Git')
        review_request = self.create_review_request(repository=repository,
                                                    target_people=[target],
                                                    public=True,
                                                    create_with_history=True)
        diffset = self.create_diffset(review_request)

        submitter_name = review_request.submitter.get_full_name()

        self.create_diffcommit(diffset=diffset,
                               commit_id='r1',
                               parent_id='r0',
                               commit_message='Commit message 1',
                               author_name=submitter_name)
        self.create_diffcommit(diffset=diffset,
                               commit_id='r2',
                               parent_id='r1',
                               commit_message='Commit message 2',
                               author_name=submitter_name)

        draft_diffset = self.create_diffset(review_request, draft=True)
        self.create_diffcommit(diffset=draft_diffset,
                               commit_id='r1',
                               parent_id='r0',
                               commit_message='New commit message 1',
                               author_name=submitter_name)

        self.create_diffcommit(diffset=draft_diffset,
                               commit_id='r2',
                               parent_id='r1',
                               commit_message='New commit message 2',
                               author_name='Example Author')

        draft_diffset.finalize_commit_series(
            cumulative_diff=self.DEFAULT_GIT_FILEDIFF_DATA_DIFF,
            validation_info=None,
            validate=False,
            save=True)

        review_request.publish(user=review_request.submitter)
        changedesc = review_request.changedescs.latest()
        field = self.make_field(review_request)

        self.assertEqual(
            {
                'old': [
                    {
                        'author': submitter_name,
                        'summary': 'Commit message 1',
                    },
                    {
                        'author': submitter_name,
                        'summary': 'Commit message 2',
                    },
                ],
                'new': [
                    {
                        'author': submitter_name,
                        'summary': 'New commit message 1',
                    },
                    {
                        'author': 'Example Author',
                        'summary': 'New commit message 2',
                    },
                ],
            },
            field.serialize_change_entry(changedesc))


class FileAttachmentsFieldTests(FieldsTestCase):
    """Unit tests for FileAttachmentsField."""

    field_cls = FileAttachmentsField
    fixtures = ['test_users']

    def test_render_change_entry_html(self):
        """Testing FileAttachmentsField.render_change_entry_html"""
        target = User.objects.get(username='doc')
        review_request = self.create_review_request(public=True,
                                                    create_with_history=True,
                                                    target_people=[target])
        attachment1 = self.create_file_attachment(
            review_request,
            caption='Attachment 1',
            orig_filename='file1.png')

        attachment2 = self.create_file_attachment(
            review_request,
            draft=True,
            draft_caption='Attachment 2',
            orig_filename='file2.png')
        attachment3 = self.create_file_attachment(
            review_request,
            draft=True,
            draft_caption='Attachment 3',
            orig_filename='file3.png')

        draft = review_request.get_draft()
        draft.inactive_file_attachments.add(attachment1)
        draft.file_attachments.remove(attachment1)

        review_request.publish(user=review_request.submitter)
        changedesc = review_request.changedescs.latest()

        field = self.make_field(review_request)

        # Check the added file attachments. Only file attachments 2 and 3
        # should be present.
        result = field.render_change_entry_html(
            changedesc.fields_changed[field.field_id]['added'])

        self.assertIsInstance(result, SafeText)

        self.assertNotIn('"id": %s,' % attachment1.pk, result)
        self.assertIn('"id": %s,' % attachment2.pk, result)
        self.assertIn('"id": %s,' % attachment3.pk, result)

        # Check the removed file attachments. Only file attachment 1
        # should be present.
        result = field.render_change_entry_html(
            changedesc.fields_changed[field.field_id]['removed'])

        self.assertIsInstance(result, SafeText)

        self.assertIn('"id": %s,' % attachment1.pk, result)
        self.assertNotIn('"id": %s,' % attachment2.pk, result)
        self.assertNotIn('"id": %s,' % attachment3.pk, result)
