from __future__ import unicode_literals

import os
import re
import warnings
from contextlib import contextmanager

from django.conf import settings
from django.contrib.auth.models import User
from django.core.cache import cache
from django.core.files import File
from django.utils import six
from djblets.testing.testcases import (FixturesCompilerMixin,
                                       TestCase as DjbletsTestCase)

from reviewboard import scmtools, initialize
from reviewboard.accounts.models import ReviewRequestVisit
from reviewboard.attachments.models import FileAttachment
from reviewboard.diffviewer.differ import DiffCompatVersion
from reviewboard.diffviewer.models import DiffSet, DiffSetHistory, FileDiff
from reviewboard.notifications.models import WebHookTarget
from reviewboard.reviews.models import (Comment, FileAttachmentComment,
                                        Group, Review, ReviewRequest,
                                        ReviewRequestDraft, Screenshot,
                                        ScreenshotComment)
from reviewboard.scmtools.models import Repository, Tool
from reviewboard.site.models import LocalSite
from reviewboard.webapi.models import WebAPIToken


class TestCase(FixturesCompilerMixin, DjbletsTestCase):
    """The base class for Review Board test cases.

    This class provides a number of convenient functions for creating
    common objects for testing, such as review requests and comments. They're
    populated with default data that can be overridden by the callers.

    This also overcomes an annoyance with default Django unit tests where
    the cache is not cleared across tests, leading to inconsistent results
    and useless testing.
    """
    local_site_name = 'local-site-1'
    local_site_id = 1

    ws_re = re.compile(r'\s+')

    DEFAULT_FILEDIFF_DATA = (
        b'--- README\trevision 123\n'
        b'+++ README\trevision 123\n'
        b'@@ -1 +1 @@\n'
        b'-Hello, world!\n'
        b'+Hello, everybody!\n'
    )

    def setUp(self):
        super(TestCase, self).setUp()

        initialize()

        self._local_sites = {}

        # Clear the cache so that previous tests don't impact this one.
        cache.clear()

    def shortDescription(self):
        """Returns the description of the current test.

        This changes the default behavior to replace all newlines with spaces,
        allowing a test description to span lines. It should still be kept
        short, though.
        """
        doc = self._testMethodDoc

        if doc is not None:
            doc = doc.split('\n\n', 1)[0]
            doc = self.ws_re.sub(' ', doc).strip()

        return doc

    def get_local_site_or_none(self, name):
        """Returns a LocalSite matching the name, if provided, or None."""
        if name:
            return self.get_local_site(name=name)
        else:
            return None

    def get_local_site(self, name):
        if name not in self._local_sites:
            self._local_sites[name] = LocalSite.objects.get(name=name)

        return self._local_sites[name]

    def create_webapi_token(self, user, note='Sample note',
                            policy={'access': 'rw'},
                            with_local_site=False,
                            **kwargs):
        """Creates a WebAPIToken for testing."""
        if with_local_site:
            local_site = self.get_local_site(name=self.local_site_name)
        else:
            local_site = None

        return WebAPIToken.objects.generate_token(user=user,
                                                  note=note,
                                                  policy=policy,
                                                  local_site=local_site)

    @contextmanager
    def assert_warns(self, cls=DeprecationWarning, message=None):
        """A context manager for asserting code generates a warning.

        This method only supports code which generates a single warning.
        Tests which make use of code generating multiple warnings will
        need to manually catch their warnings.
        """
        with warnings.catch_warnings(record=True) as w:
            # Some warnings such as DeprecationWarning are filtered by
            # default, stop filtering them.
            warnings.simplefilter("always")
            self.assertEqual(len(w), 0)

            yield

            self.assertEqual(len(w), 1)
            self.assertTrue(issubclass(w[-1].category, cls))

            if message is not None:
                self.assertEqual(message, six.text_type(w[-1].message))


    def create_diff_file_attachment(self, filediff, from_modified=True,
                                    review_request=None,
                                    orig_filename='filename.png',
                                    caption='My Caption',
                                    mimetype='image/png',
                                    **kwargs):
        """Creates a diff-based FileAttachment for testing.

        The FileAttachment is tied to the given FileDiff. It's populated
        with default data that can be overridden by the caller.
        """
        file_attachment = FileAttachment.objects.create_from_filediff(
            filediff=filediff,
            from_modified=from_modified,
            caption=caption,
            orig_filename=orig_filename,
            mimetype=mimetype,
            **kwargs)

        filename = os.path.join(settings.STATIC_ROOT, 'rb', 'images',
                                'trophy.png')

        with open(filename, 'r') as f:
            file_attachment.file.save(filename, File(f), save=True)

        if review_request:
            review_request.file_attachments.add(file_attachment)

        return file_attachment

    def create_diffset(self, review_request=None, revision=1, repository=None,
                       draft=False, name='diffset'):
        """Creates a DiffSet for testing.

        The DiffSet defaults to revision 1. This can be overriden by the
        caller.

        DiffSets generally are tied to a ReviewRequest, but it's optional.
        """
        if review_request:
            repository = review_request.repository

        diffset = DiffSet.objects.create(
            name=name,
            revision=revision,
            repository=repository,
            diffcompat=DiffCompatVersion.DEFAULT)

        if review_request:
            if draft:
                review_request_draft = \
                    ReviewRequestDraft.create(review_request)
                review_request_draft.diffset = diffset
                review_request_draft.save()
            else:
                review_request.diffset_history.diffsets.add(diffset)

        return diffset

    def create_diff_comment(self, review, filediff, interfilediff=None,
                            text='My comment', issue_opened=False,
                            issue_status=None,
                            first_line=1, num_lines=5, extra_fields=None,
                            reply_to=None, **kwargs):
        """Creates a Comment for testing.

        The comment is tied to the given Review and FileDiff (and, optionally,
        an interfilediff). It's populated with default data that can be
        overridden by the caller.
        """
        if issue_opened and not issue_status:
            issue_status = Comment.OPEN

        comment = Comment(
            filediff=filediff,
            interfilediff=interfilediff,
            first_line=first_line,
            num_lines=num_lines,
            text=text,
            issue_opened=issue_opened,
            issue_status=issue_status,
            reply_to=reply_to,
            **kwargs)

        if extra_fields:
            comment.extra_data = extra_fields

        comment.save()
        review.comments.add(comment)

        return comment

    def create_file_attachment(self, review_request,
                               orig_filename='filename.png',
                               caption='My Caption',
                               draft=False,
                               active=True,
                               **kwargs):
        """Creates a FileAttachment for testing.

        The FileAttachment is tied to the given ReviewRequest. It's populated
        with default data that can be overridden by the caller.
        """
        file_attachment = FileAttachment(
            caption=caption,
            orig_filename=orig_filename,
            mimetype='image/png',
            **kwargs)

        filename = os.path.join(settings.STATIC_ROOT, 'rb', 'images',
                                'trophy.png')

        with open(filename, 'r') as f:
            file_attachment.file.save(filename, File(f), save=True)

        if draft:
            review_request_draft = ReviewRequestDraft.create(review_request)

            if active:
                attachments = review_request_draft.file_attachments
            else:
                attachments = review_request_draft.inactive_file_attachments
        else:
            if active:
                attachments = review_request.file_attachments
            else:
                attachments = review_request.inactive_file_attachments

        attachments.add(file_attachment)

        return file_attachment

    def create_file_attachment_comment(self, review, file_attachment,
                                       text='My comment', issue_opened=False,
                                       extra_fields=None, reply_to=None):
        """Creates a FileAttachmentComment for testing.

        The comment is tied to the given Review and FileAttachment. It's
        populated with default data that can be overridden by the caller.
        """
        if issue_opened:
            issue_status = Comment.OPEN
        else:
            issue_status = None

        comment = FileAttachmentComment(
            file_attachment=file_attachment,
            text=text,
            issue_opened=issue_opened,
            issue_status=issue_status,
            reply_to=reply_to)

        if extra_fields:
            comment.extra_data = extra_fields

        comment.save()
        review.file_attachment_comments.add(comment)

        return comment

    def create_filediff(self, diffset, source_file='/test-file',
                        dest_file='/test-file', source_revision='123',
                        dest_detail='124', status=FileDiff.MODIFIED,
                        diff=DEFAULT_FILEDIFF_DATA):
        """Creates a FileDiff for testing.

        The FileDiff is tied to the given DiffSet. It's populated with
        default data that can be overridden by the caller.
        """
        return FileDiff.objects.create(
            diffset=diffset,
            source_file=source_file,
            dest_file=dest_file,
            source_revision=source_revision,
            dest_detail=dest_detail,
            status=status,
            diff=diff)

    def create_repository(self, with_local_site=False, name='Test Repo',
                          tool_name='Git', path=None, local_site=None,
                          **kwargs):
        """Creates a Repository for testing.

        The Repository may optionally be attached to a LocalSite. It's also
        populated with default data that can be overridden by the caller.

        This accepts a tool_name of "Git", "Mercurial" or "Subversion".
        The correct bundled repository path will be used for the given
        tool_name.
        """
        if not local_site:
            if with_local_site:
                local_site = self.get_local_site(name=self.local_site_name)
            else:
                local_site = None

        testdata_dir = os.path.join(os.path.dirname(scmtools.__file__),
                                    'testdata')

        if not path:
            if tool_name in ('Git', 'Test',
                             'TestToolSupportsPendingChangeSets'):
                path = os.path.join(testdata_dir, 'git_repo')
            elif tool_name == 'Subversion':
                path = 'file://' + os.path.join(testdata_dir, 'svn_repo')
            elif tool_name == 'Mercurial':
                path = os.path.join(testdata_dir, 'hg_repo.bundle')
            elif tool_name == 'CVS':
                path = os.path.join(testdata_dir, 'cvs_repo')
            else:
                raise NotImplementedError

        return Repository.objects.create(
            name=name,
            local_site=local_site,
            tool=Tool.objects.get(name=tool_name),
            path=path,
            **kwargs)

    def create_review_request(self, with_local_site=False, local_site=None,
                              summary='Test Summary',
                              description='Test Description',
                              testing_done='Testing',
                              submitter='doc', local_id=1001,
                              bugs_closed='', status='P', public=False,
                              publish=False, commit_id=None, changenum=None,
                              repository=None, id=None,
                              create_repository=False):
        """Create a ReviewRequest for testing.

        The ReviewRequest may optionally be attached to a LocalSite. It's also
        populated with default data that can be overridden by the caller.

        If create_repository is True, a Repository will be created
        automatically. If set, a custom repository cannot be provided.

        The provided submitter may either be a username or a User object.

        If publish is True, ReviewRequest.publish() will be called.
        """
        if not local_site:
            if with_local_site:
                local_site = self.get_local_site(name=self.local_site_name)
            else:
                local_site = None

        if not local_site:
            local_id = None

        if create_repository:
            assert not repository

            repository = \
                self.create_repository(with_local_site=with_local_site)

        if not isinstance(submitter, User):
            submitter = User.objects.get(username=submitter)

        review_request = ReviewRequest(
            summary=summary,
            description=description,
            testing_done=testing_done,
            local_site=local_site,
            local_id=local_id,
            submitter=submitter,
            diffset_history=DiffSetHistory.objects.create(),
            repository=repository,
            public=public,
            commit_id=commit_id,
            changenum=changenum,
            bugs_closed=bugs_closed,
            status=status)

        # Set this separately to avoid issues with CounterField updates.
        review_request.id = id

        review_request.save()

        if publish:
            review_request.publish(review_request.submitter)

        return review_request

    def create_visit(self, review_request, visibility, user='doc',
                     username=None, timestamp=None):
        """Create a ReviewRequestVisit for testing.

        The ReviewRequestVisit is tied to the given ReviewRequest and User.
        It's populated with default data that can be overridden by the caller.

        The provided user may either be a username or a User object.
        """
        if not isinstance(user, basestring):
            user = User.objects.get(username=user)

        return ReviewRequestVisit.objects.create(
            review_request=review_request,
            visibility=visibility,
            user=user)

    def create_review(self, review_request, user='dopey', username=None,
                      body_top='Test Body Top', body_bottom='Test Body Bottom',
                      ship_it=False, publish=False):
        """Creates a Review for testing.

        The Review is tied to the given ReviewRequest. It's populated with
        default data that can be overridden by the caller.

        The provided user may either be a username or a User object.

        If publish is True, Review.publish() will be called.
        """
        if not isinstance(user, User):
            user = User.objects.get(username=user)

        review = Review.objects.create(
            review_request=review_request,
            user=user,
            body_top=body_top,
            body_bottom=body_bottom,
            ship_it=ship_it)

        if publish:
            review.publish()

        return review

    def create_review_group(self, name='test-group', with_local_site=False,
                            local_site=None, visible=True, invite_only=False,
                            is_default_group=False):
        """Creates a review group for testing.

        The group may optionally be attached to a LocalSite. It's also
        populated with default data that can be overridden by the caller.
        """
        if not local_site and with_local_site:
            local_site = self.get_local_site(name=self.local_site_name)

        return Group.objects.create(
            name=name,
            local_site=local_site,
            visible=visible,
            invite_only=invite_only,
            is_default_group=is_default_group)

    def create_reply(self, review, user='grumpy', username=None,
                     body_top='Test Body Top', timestamp=None,
                     publish=False):
        """Creates a review reply for testing.

        The reply is tied to the given Review. It's populated with default
        data that can be overridden by the caller.
        """
        if not isinstance(user, User):
            user = User.objects.get(username=user)

        reply = Review.objects.create(
            review_request=review.review_request,
            user=user,
            body_top=body_top,
            base_reply_to=review,
            timestamp=timestamp)

        if publish:
            reply.publish()

        return reply

    def create_screenshot(self, review_request, caption='My caption',
                          draft=False, active=True):
        """Creates a Screenshot for testing.

        The Screenshot is tied to the given ReviewRequest. It's populated
        with default data that can be overridden by the caller.
        """
        screenshot = Screenshot(caption=caption)
        filename = os.path.join(settings.STATIC_ROOT, 'rb', 'images',
                                'trophy.png')

        with open(filename, 'r') as f:
            screenshot.image.save(filename, File(f), save=True)

        if draft:
            review_request_draft = ReviewRequestDraft.create(review_request)

            if active:
                screenshots = review_request_draft.screenshots
            else:
                screenshots = review_request_draft.inactive_screenshots
        else:
            if active:
                screenshots = review_request.screenshots
            else:
                screenshots = review_request.inactive_screenshots

        screenshots.add(screenshot)

        return screenshot

    def create_screenshot_comment(self, review, screenshot, text='My comment',
                                  x=1, y=1, w=5, h=5, issue_opened=False,
                                  extra_fields=None, reply_to=None, **kwargs):
        """Creates a ScreenshotComment for testing.

        The comment is tied to the given Review and Screenshot. It's
        It's populated with default data that can be overridden by the caller.
        """
        if issue_opened:
            issue_status = Comment.OPEN
        else:
            issue_status = None

        comment = ScreenshotComment(
            screenshot=screenshot,
            text=text,
            x=x,
            y=y,
            w=w,
            h=h,
            issue_opened=issue_opened,
            issue_status=issue_status,
            reply_to=reply_to,
            **kwargs)

        if extra_fields:
            comment.extra_data = extra_fields

        comment.save()
        review.screenshot_comments.add(comment)

        return comment

    def create_webhook(self, enabled=False, events=WebHookTarget.ALL_EVENTS,
                       url='http://example.com',
                       encoding=WebHookTarget.ENCODING_JSON,
                       use_custom_content=False, custom_content='',
                       secret='', apply_to=WebHookTarget.APPLY_TO_ALL,
                       repositories=None, with_local_site=False,
                       local_site=None, extra_fields=None):
        """Create a webhook for testing.

        It is populated with default data that can be overridden by the caller.

        Args:
            enabled (bool):
                Whether or not the webhook is enabled when it is created.

            events (unicode):
                A comma-separated list of events that the webhook will trigger
                on.

            url (unicode):
                The URL that requests will be made against.

            encoding (unicode):
                The encoding of the payload to send.

            use_custom_content (bool):
                Determines if custom content will be sent for the payload (if
                ``True``) or if it will be auto-generated (if ``False``).

            custom_content (unicode):
                The custom content to send when ``use_custom_content`` is
                ``True``.

            secret (unicode):
                An HMAC secret to sign the payload with.

            apply_to (unicode):
                The types of repositories the webhook will apply to.

            repositories (list):
                A list of repositories that the webhook will be limited to if
                ``apply_to`` is ``WebHookTarget.APPLY_TO_SELECTED_REPOS``.

            with_local_site (bool):
                Determines if this should be created with a local site.

            local_site (reviewboard.site.models.LocalSite):
                An optional local site. If ``with_local_site`` is ``True`` and
                this argument is ``None``, the local site will be looked up.

            extra_fields (dict):
                Extra data to be imported into the webhook.

        Returns:
            WebHookTarget: A webhook constructed with the given arguments.
        """
        if not local_site:
            if with_local_site:
                local_site = self.get_local_site(name=self.local_site_name)
            else:
                local_site = None

        webhook = WebHookTarget.objects.create(
            enabled=enabled,
            events=events,
            url=url,
            encoding=encoding,
            use_custom_content=use_custom_content,
            custom_content=custom_content,
            secret=secret,
            apply_to=apply_to,
            local_site=local_site)

        if repositories:
            webhook.repositories = repositories

        if extra_fields:
            webhook.extra_data = extra_fields
            webhook.save(update_fields=['extra_data'])

        return webhook
