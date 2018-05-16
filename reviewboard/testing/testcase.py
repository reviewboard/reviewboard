from __future__ import unicode_literals

import os
import re
import warnings
from contextlib import contextmanager
from datetime import timedelta

from django.conf import settings
from django.contrib.auth.models import User
from django.core.cache import cache
from django.core.files import File
from django.utils import six, timezone
from djblets.testing.testcases import (FixturesCompilerMixin,
                                       TestCase as DjbletsTestCase)
from oauthlib.common import generate_token
from oauth2_provider.models import AccessToken

from reviewboard import scmtools, initialize
from reviewboard.accounts.models import ReviewRequestVisit
from reviewboard.admin.siteconfig import load_site_config
from reviewboard.attachments.models import FileAttachment
from reviewboard.diffviewer.differ import DiffCompatVersion
from reviewboard.diffviewer.models import DiffSet, DiffSetHistory, FileDiff
from reviewboard.notifications.models import WebHookTarget
from reviewboard.oauth.models import Application
from reviewboard.reviews.models import (Comment,
                                        FileAttachmentComment,
                                        GeneralComment,
                                        Group,
                                        Review,
                                        ReviewRequest,
                                        ReviewRequestDraft,
                                        Screenshot,
                                        ScreenshotComment,
                                        StatusUpdate)
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

    DEFAULT_GIT_FILEDIFF_DATA = (
        b'diff --git a/README b/README\n'
        b'index 94bdd3e..197009f 100644\n'
        b'--- README\n'
        b'+++ README\n'
        b'@@ -2 +2 @@\n'
        b'-blah blah\n'
        b'+blah!\n'
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
                                'logo.png')

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
                            issue_status=None, first_line=1, num_lines=5,
                            extra_fields=None, reply_to=None, **kwargs):
        """Create a Comment for testing.

        The comment is tied to the given Review and FileDiff (and, optionally,
        an interfilediff). It's populated with default data that can be
        overridden by the caller.

        Args:
            review (reviewboard.reviews.models.review.Review):
                The review associated with the comment.

            filediff (reviewboard.diffviewer.models.FileDiff):
                The FileDiff associated with the comment.

            interfilediff (reviewboard.diffviewer.models.FileDiff, optional):
                The FileDiff used for the end of an interdiff range associated
                with the comment.

            text (unicode):
                The text for the comment.

            issue_opened (bool, optional):
                Whether an issue is to be opened for the comment.

            issue_status (unicode, optional):
                The issue status to set, if an issue is opened. Defaults to
                being an open issue.

            first_line (int, optional):
                The first line (0-based) of the comment range.

            num_lines (int, optional):
                The number of lines in the comment.

            extra_fields (dict, optional):
                Extra data to set on the comment.

            reply_to (reviewboard.reviews.models.diff_comment.Comment,
                      optional):
                The comment this comment replies to.

            **kwargs (dict):
                Additional model attributes to set on the comment.

        Returns:
            reviewboard.reviews.models.diff_comment.Comment:
            The resulting comment.
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
        """Create a FileAttachment for testing.

        The attachment is tied to the given
        :py:class:`~reviewboard.reviews.models.review_request.ReviewRequest`.
        It's populated with default data that can be overridden by the caller.

        Args:
            review_request (reviewboard.reviews.models.review_request.
                            ReviewRequest):
                The review request that ultimately owns the file attachment.

            orig_filename (unicode, optional):
                The filename to use for the file attachment.

            caption (unicode, optional):
                The caption to use for the file attachment.

            draft (bool or
                   reviewboard.reviews.models.review_request_draft.
                   ReviewRequestDraft):
                A draft to associate the attachment with. This can also be
                a boolean, for legacy reasons, which will attempt to look up
                or create a draft for the review request.

            active (bool):
                Whether this attachment is considered active (not deleted).

            **kwargs (dict):
                Additional fields to set on the attachment.

        Returns:
            reviewboard.attachments.models.FileAttachment:
            The resulting file attachment.
        """
        file_attachment = self._create_base_file_attachment(
            caption=caption,
            orig_filename=orig_filename,
            **kwargs)

        if draft:
            if isinstance(draft, ReviewRequestDraft):
                review_request_draft = draft
            else:
                review_request_draft = \
                    ReviewRequestDraft.create(review_request)

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

    def create_user_file_attachment(self, user,
                                    caption='My Caption',
                                    with_local_site=False,
                                    local_site_name=None,
                                    local_site=None,
                                    has_file=False,
                                    orig_filename='filename.png',
                                    **kwargs):
        """Create a user FileAttachment for testing.

        The :py:class:`reviewboard.attachments.models.FileAttachment` is tied
        to the given :py:class:`django.contrib.auth.models.User`. It's
        populated with default data that can be overridden by the caller.
        Notably, by default the FileAttachment will be created without a file
        or a local_site.

        Args:
            user (django.contrib.auth.models.User):
                The user who owns the file attachment.

            caption (unicode, optional):
                The caption for the file attachment.

            with_local_site (bool, optional):
                ``True`` if the file attachment should be associated with a
                local site. If this is set, one of ``local_site_name`` or
                ``local_site`` should be provided as well.

            local_site_name (unicode, optional):
                The name of the local site to associate this attachment with.

            local_site (reviewboard.site.models.LocalSite, optional):
                The local site to associate this attachment with.

            has_file (bool, optional):
                ``True`` if an actual file object should be included in the
                model.

            orig_filename (unicode, optional):
                The original name of the file to set in the model.

            kwargs (dict):
                Additional keyword arguments to pass into the FileAttachment
                constructor.

        Returns:
            reviewboard.attachments.models.FileAttachment:
            The new file attachment instance.
        """
        return self._create_base_file_attachment(
            caption=caption,
            user=user,
            has_file=has_file,
            orig_filename=orig_filename,
            with_local_site=with_local_site,
            local_site_name=local_site_name,
            local_site=local_site,
            **kwargs)

    def create_file_attachment_comment(self, review, file_attachment,
                                       diff_against_file_attachment=None,
                                       text='My comment', issue_opened=False,
                                       issue_status=None, extra_fields=None,
                                       reply_to=None, **kwargs):
        """Create a FileAttachmentComment for testing.

        The comment is tied to the given Review and FileAttachment. It's
        populated with default data that can be overridden by the caller.

        Args:
            review (reviewboard.reviews.models.review.Review):
                The review associated with the comment.

            file_attachment (reviewboard.attachments.models.FileAttachment):
                The file attachment associated with the comment.

            diff_against_file_attachment (reviewboard.attachments.models.
                                          FileAttachment, optional):
                The file attachment being diff against, for comments on
                attachment diffs.

            text (unicode):
                The text for the comment.

            issue_opened (bool, optional):
                Whether an issue is to be opened for the comment.

            issue_status (unicode, optional):
                The issue status to set, if an issue is opened. Defaults to
                being an open issue.

            extra_fields (dict, optional):
                Extra data to set on the comment.

            reply_to (reviewboard.reviews.models.file_attachment_comment.
                      FileAttachmentComment, optional):
                The comment this comment replies to.

            **kwargs (dict):
                Additional model attributes to set on the comment.

        Returns:
            reviewboard.reviews.models.file_attachment_comment.FileAttachmentComment:
            The resulting comment.
        """
        if issue_opened and not issue_status:
            issue_status = FileAttachmentComment.OPEN

        comment = FileAttachmentComment(
            file_attachment=file_attachment,
            diff_against_file_attachment=diff_against_file_attachment,
            text=text,
            issue_opened=issue_opened,
            issue_status=issue_status,
            reply_to=reply_to,
            **kwargs)

        if extra_fields:
            comment.extra_data = extra_fields

        comment.save()
        review.file_attachment_comments.add(comment)

        return comment

    def create_filediff(self, diffset, source_file='/test-file',
                        dest_file='/test-file', source_revision='123',
                        dest_detail='124', status=FileDiff.MODIFIED,
                        diff=DEFAULT_FILEDIFF_DATA, save=True):
        """Create a FileDiff for testing.

        The FileDiff is tied to the given DiffSet. It's populated with
        default data that can be overridden by the caller.

        Args:
            diffset (reviewboard.diffviewer.models.DiffSet):
                The parent diff set that will own this file.

            source_file (unicode, optional):
                The source filename.

            dest_file (unicode, optional):
                The destination filename, which will be the same as
                ``source_file`` unless the file was moved/renamed/copied.

            source_revision (unicode, optional):
                The source revision.

            dest_detail (unicode, optional):
                The destination revision or other detail as found in the
                parsed diff. This may be a timestamp or some other value.

            status (unicode, optional):
                The status of the file. This is the operation performed
                as indicated in the diff.

            diff (bytes, optional):
                The diff contents.

            save (bool, optional):
                Whether to automatically save the resulting object.

        Returns:
            reviewboard.diffviewer.models.FileDiff:
            The resulting FileDiff.
        """
        filediff = FileDiff(
            diffset=diffset,
            source_file=source_file,
            dest_file=dest_file,
            source_revision=source_revision,
            dest_detail=dest_detail,
            status=status,
            diff=diff)

        if save:
            filediff.save()

        return filediff

    def create_repository(self, with_local_site=False, name='Test Repo',
                          tool_name='Git', path=None, local_site=None,
                          extra_data=None, **kwargs):
        """Create a Repository for testing.

        The Repository may optionally be attached to a
        :py:class:`~reviewboard.site.models.LocalSite`. It's also populated
        with default data that can be overridden by the caller.

        Args:
            with_local_site (bool, optional):
                Whether to create the repository using a Local Site. This
                will choose one based on :py:attr:`local_site_name`.

                If ``local_site`` is provided, this argument is ignored.

            name (unicode, optional):
                The name of the repository.

            tool_name (unicode, optional):
                The name of the registered SCM Tool for the repository.

            path (unicode, optional):
                The path for the repository. If not provided, one will be
                computed.

            local_site (reviewboard.site.models.LocalSite, optional):
                The explicit Local Site to attach.

            extra_data (dict, optional):
                Explicit extra_data to attach to the repository.

            **kwargs (dict):
                Additional fields to set on the repository.

        Returns:
            reviewboard.scmtools.models.Repository:
            The new repository.
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
            elif tool_name == 'Perforce':
                path = 'localhost:1666'
            else:
                raise NotImplementedError

        repository = Repository(name=name,
                                local_site=local_site,
                                tool=Tool.objects.get(name=tool_name),
                                path=path,
                                **kwargs)

        if extra_data is not None:
            repository.extra_data = extra_data

        repository.save()

        return repository

    def create_review_request(self, with_local_site=False, local_site=None,
                              summary='Test Summary',
                              description='Test Description',
                              testing_done='Testing',
                              submitter='doc',
                              branch='my-branch',
                              local_id=1001,
                              bugs_closed='', status='P', public=False,
                              publish=False, commit_id=None, changenum=None,
                              time_added=None, last_updated=None,
                              repository=None, id=None,
                              create_repository=False,
                              target_people=None,
                              target_groups=None):
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
            branch=branch,
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

        if target_people:
            review_request.target_people = target_people

        if target_groups:
            review_request.target_groups = target_groups

        if publish:
            review_request.publish(review_request.submitter)

        if time_added and last_updated:
            ReviewRequest.objects.filter(pk=review_request.pk).update(
                time_added=time_added,
                last_updated=last_updated)
            review_request.time_added = time_added
            review_request.last_updated = last_updated
        elif time_added:
            ReviewRequest.objects.filter(pk=review_request.pk).update(
                time_added=time_added)
            review_request.time_added = time_added
        elif last_updated:
            ReviewRequest.objects.filter(pk=review_request.pk).update(
                last_updated=last_updated)
            review_request.last_updated = last_updated

        return review_request

    def create_visit(self, review_request, visibility, user='doc',
                     username=None, timestamp=None):
        """Create a ReviewRequestVisit for testing.

        The ReviewRequestVisit is tied to the given ReviewRequest and User.
        It's populated with default data that can be overridden by the caller.

        The provided user may either be a username or a User object.
        """
        if not isinstance(user, six.string_types):
            user = User.objects.get(username=user)

        return ReviewRequestVisit.objects.create(
            review_request=review_request,
            visibility=visibility,
            user=user)

    def create_review(self, review_request, user='dopey',
                      body_top='Test Body Top', body_bottom='Test Body Bottom',
                      ship_it=False, publish=False, timestamp=None, **kwargs):
        """Creates a Review for testing.

        The Review is tied to the given ReviewRequest. It's populated with
        default data that can be overridden by the caller.

        The provided user may either be a username or a User object.

        If publish is True, Review.publish() will be called.

        Args:
            review_request (reviewboard.reviews.models.review_request.
                            ReviewRequest):
                The review request the review is filed against.

            user (unicode or django.contrib.auth.models.User, optional):
                The username or User object owning the review.

            body_top (unicode, optional):
                The text for the ``body_top`` field.

            body_bottom (unicode, optional):
                The text for the ``body_bottom`` field.

            ship_it (bool, optional):
                The Ship It state for the review.

            publish (bool, optional):
                Whether to publish the review immediately after creation.

            timestamp (datetime.datetime, optional):
                The timestamp for the review.

            **kwargs (dict):
                Additional attributes to set in the review.

        Returns:
            reviewboard.reviews.models.review.Review:
            The resulting review.
        """
        if not isinstance(user, User):
            user = User.objects.get(username=user)

        review = Review.objects.create(
            review_request=review_request,
            user=user,
            body_top=body_top,
            body_bottom=body_bottom,
            ship_it=ship_it,
            **kwargs)

        if publish:
            review.publish()

        if timestamp:
            Review.objects.filter(pk=review.pk).update(timestamp=timestamp)
            review.timestamp = timestamp

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

    def create_reply(self, review, user='grumpy', body_top='Test Body Top',
                     timestamp=None, publish=False, **kwargs):
        """Create a review reply for testing.

        The reply is tied to the given Review. It's populated with default
        data that can be overridden by the caller.

        To reply to a ``body_top`` or ``body_bottom`` field, pass either
        ``body_top_reply_to=`` or ``body_bottom_reply_to=`` to this method.
        This will be passed to the review's constructor.

        Args:
            review (reviewboard.reviews.models.review.Review):
                The review being replied to.

            user (django.contrib.auth.models.User or unicode, optional):
                Either the user model or the username of the user who is
                replying to the review.

            body_top (unicode, optional):
                The body top text.

            timestamp (datetime.datetime, optional):
                The timestamp of the review.

            publish (bool, optional):
                Whether the review should be published. By default it's in
                draft form.

            **kwargs (dict):
                Additional arguments to pass to the
                :py:class:`~reviewboard.reviews.models.review.Review`
                constructor.

        Returns:
            reviewboard.reviews.models.review.Review:
            The resulting review.
        """
        if not isinstance(user, User):
            user = User.objects.get(username=user)

        reply = Review.objects.create(
            review_request=review.review_request,
            user=user,
            body_top=body_top,
            base_reply_to=review,
            **kwargs)

        if publish:
            reply.publish()

        if timestamp:
            Review.objects.filter(pk=reply.pk).update(timestamp=timestamp)
            reply.timestamp = timestamp

        return reply

    def create_screenshot(self, review_request, caption='My caption',
                          draft=False, active=True, **kwargs):
        """Create a Screenshot for testing.

        The screenshot is tied to the given
        :py:class:`~reviewboard.reviews.models.review_request.ReviewRequest`.
        It's populated with default data that can be overridden by the caller.

        Args:
            review_request (reviewboard.reviews.models.review_request.
                            ReviewRequest):
                The review request that ultimately owns the screenshot.

            caption (unicode, optional):
                The caption to use for the screenshot.

            draft (bool or
                   reviewboard.reviews.models.review_request_draft.
                   ReviewRequestDraft):
                A draft to associate the screenshot with. This can also be
                a boolean, for legacy reasons, which will attempt to look up
                or create a draft for the review request.

            active (bool):
                Whether this screenshot is considered active (not deleted).

            **kwargs (dict):
                Additional fields to set on the screenshot.

        Returns:
            reviewboard.reviews.models.screenshot.Screenshot:
            The resulting screenshot.
        """
        screenshot = Screenshot(caption=caption, **kwargs)
        filename = os.path.join(settings.STATIC_ROOT, 'rb', 'images',
                                'logo.png')

        with open(filename, 'r') as f:
            screenshot.image.save(filename, File(f), save=True)

        if draft:
            if isinstance(draft, ReviewRequestDraft):
                review_request_draft = draft
            else:
                review_request_draft = \
                    ReviewRequestDraft.create(review_request)

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
                                  issue_status=None, extra_fields=None,
                                  reply_to=None, **kwargs):
        """Create a ScreenshotComment for testing.

        The comment is tied to the given Review and Screenshot. It's
        It's populated with default data that can be overridden by the caller.

        Args:
            review (reviewboard.reviews.models.review.Review):
                The review associated with the comment.

            screenshot (reviewboard.reviews.models.screenshot.Screenshot):
                The screenshot associated with the comment.

            text (unicode):
                The text for the comment.

            x (int, optional):
                The X location for the comment on the screenshot.

            y (int, optional):
                The Y location for the comment on the screenshot.

            w (int, optional):
                The width for the comment on the screenshot.

            h (int, optional):
                The height for the comment on the screenshot.

            issue_opened (bool, optional):
                Whether an issue is to be opened for the comment.

            issue_status (unicode, optional):
                The issue status to set, if an issue is opened. Defaults to
                being an open issue.

            extra_fields (dict, optional):
                Extra data to set on the comment.

            reply_to (reviewboard.reviews.models.general_comment.
                      GeneralComment, optional):
                The comment this comment replies to.

            **kwargs (dict):
                Additional model attributes to set on the comment.

        Returns:
            reviewboard.reviews.models.screenshot_comment.ScreenshotComment:
            The resulting comment.
        """
        if issue_opened and not issue_status:
            issue_status = ScreenshotComment.OPEN

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

    def _create_base_file_attachment(self,
                                     caption='My Caption',
                                     orig_filename='filename.png',
                                     has_file=True,
                                     user=None,
                                     with_local_site=False,
                                     local_site_name=None,
                                     local_site=None,
                                     **kwargs):
        """Create a FileAttachment object with the given parameters.

        When creating a
        :py:class:`reviewboard.attachments.models.FileAttachment` that will be
        associated to a review request, a user and local_site should not be
        specified.

        Args:
            caption (unicode, optional):
                The caption for the file attachment.

            orig_filename (unicode, optional):
                The original name of the file to set in the model.

            has_file (bool, optional):
                ``True`` if an actual file object should be included in the
                model.

            user (django.contrib.auth.models.User, optonal):
                The user who owns the file attachment.

            with_local_site (bool, optional):
                ``True`` if the file attachment should be associated with a
                local site. If this is set, one of ``local_site_name`` or
                ``local_site`` should be provided as well.

            local_site_name (unicode, optional):
                The name of the local site to associate this attachment with.

            local_site (reviewboard.site.models.LocalSite, optional):
                The local site to associate this attachment with.

            kwargs (dict):
                Additional keyword arguments to pass into the FileAttachment
                constructor.

        Returns:
            reviewboard.attachments.models.FileAttachment:
            The new file attachment instance.
        """
        if with_local_site:
            local_site = self.get_local_site(name=local_site_name)

        file_attachment = FileAttachment(
            caption=caption,
            user=user,
            uuid='test-uuid',
            local_site=local_site,
            **kwargs)

        if has_file:
            filename = os.path.join(settings.STATIC_ROOT, 'rb', 'images',
                                    'logo.png')

            file_attachment.orig_filename = orig_filename
            file_attachment.mimetype = 'image/png'

            with open(filename, 'r') as f:
                file_attachment.file.save(filename, File(f), save=True)

        file_attachment.save()

        return file_attachment

    def create_general_comment(self, review, text='My comment',
                               issue_opened=False, issue_status=None,
                               extra_fields=None, reply_to=None, **kwargs):
        """Create a GeneralComment for testing.

        The comment is tied to the given Review. It is populated with
        default data that can be overridden by the caller.

        Args:
            review (reviewboard.reviews.models.review.Review):
                The review associated with the comment.

            text (unicode):
                The text for the comment.

            issue_opened (bool, optional):
                Whether an issue is to be opened for the comment.

            issue_status (unicode, optional):
                The issue status to set, if an issue is opened. Defaults to
                being an open issue.

            extra_fields (dict, optional):
                Extra data to set on the comment.

            reply_to (reviewboard.reviews.models.general_comment.
                      GeneralComment, optional):
                The comment this comment replies to.

            **kwargs (dict):
                Additional model attributes to set on the comment.

        Returns:
            reviewboard.reviews.models.general_comment.GeneralComment:
            The resulting comment.
        """
        if issue_opened and not issue_status:
            issue_status = GeneralComment.OPEN

        comment = GeneralComment(
            text=text,
            issue_opened=issue_opened,
            issue_status=issue_status,
            reply_to=reply_to,
            **kwargs)

        if extra_fields:
            comment.extra_data = extra_fields

        comment.save()
        review.general_comments.add(comment)

        return comment

    def create_status_update(self, review_request, user='dopey',
                             service_id='service', summary='Status Update',
                             state=StatusUpdate.PENDING,
                             review=None, change_description=None,
                             timestamp=None):
        """Create a status update for testing.

        It is populated with default data that can be overridden by the caller.

        Args:
            review_request (reviewboard.reviews.models.ReviewRequest):
                The review request to associate with the new status update.

            user (django.contrib.auth.models.User or unicode):
                Either the user model or the username of the user who should
                own the status update.

            service_id (unicode):
                The ID to fill in for the new model.

            summary (unicode):
                The summary to fill in for the new model.

            state (unicode):
                The state for the new model. This must be one of the valid
                choices for the state field.

            review (reviewboard.reviews.models.review.Review, optional):
                The review associated with this status update.

            change_description (reviewboard.changedescs.models.
                                ChangeDescription, optional):
                The change description for this status update.

            timestamp (datetime.datetime):
                The timestamp for the status update.

        Returns:
            reviewboard.reviews.models.StatusUpdate:
            The new status update.
        """
        if not isinstance(user, User):
            user = User.objects.get(username=user)

        status_update = StatusUpdate.objects.create(
            review_request=review_request,
            change_description=change_description,
            service_id=service_id,
            summary=summary,
            state=state,
            review=review,
            user=user)

        if timestamp:
            StatusUpdate.objects.filter(pk=status_update.pk).update(
                timestamp=timestamp)
            status_update.timestamp = timestamp

        return status_update

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
            events=events.split(','),
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

    def create_oauth_application(
        self, user, local_site=None, with_local_site=False,
        redirect_uris='http://example.com',
        authorization_grant_type=Application.GRANT_CLIENT_CREDENTIALS,
        client_type=Application.CLIENT_PUBLIC,
        **kwargs):
        """Create an OAuth application.

        Args:
            user (django.contrib.auth.models.User):
                The user whom is to own the application.

            local_site (reviewboard.site.models.LocalSite, optional):
                The LocalSite for the application to be associated with, if
                any.

            redirect_uris (unicode, optional):
                A whitespace-separated list of allowable redirect URIs.

            authorization_grant_type (unicode, optional):
                The grant type for the application.

            client_type (unicode, optional):
                The application client type.

            **kwargs (dict):
                Additional keyword arguments to pass to the
                :py:class:`~reviewboard.oauth.models.Application` initializer.

        Returns:
            reviewboard.oauth.models.Application:
            The created application.
        """
        if not local_site:
            if with_local_site:
                local_site = self.get_local_site(self.local_site_name)
            else:
                local_site = None

        return Application.objects.create(
            user=user,
            local_site=local_site,
            authorization_grant_type=authorization_grant_type,
            redirect_uris=redirect_uris,
            client_type=client_type,
            extra_data='{}',
            **kwargs)

    def create_oauth_token(self, application, user, scope='', expires=None,
                           **kwargs):
        """Create an OAuth2 access token for testing.

        Args:
            application (reviewboard.oauth.models.Application):
                The application the token should be associated with.

            user (django.contrib.auth.models.User):
                The user who should own the token.

            scope (unicode, optional):
                The scopes of the token. This argument defaults to the empty
                scope.

            expires (datetime.timedelta, optional):
                How far into the future the token expires. If not provided,
                this argument defaults to one hour.

        Returns:
            oauth2_provider.models.AccessToken:
            The created access token.
        """
        if expires is None:
            expires = timedelta(hours=1)

        return AccessToken.objects.create(
            application=application,
            token=generate_token(),
            expires=timezone.now() + expires,
            scope=scope,
            user=user,
        )

    @contextmanager
    def siteconfig_settings(self, settings, reload_settings=True):
        """Temporarily sets siteconfig settings for a test.

        Args:
            settings (dict):
                The new siteconfig settings to set.

            reload_settings (bool, optional):
                Whether to reload and recompute all settings, applying them
                to Django and other objects.

        Context:
            The current site configuration will contain the new settings for
            this test.
        """
        try:
            with super(TestCase, self).siteconfig_settings(settings):
                if reload_settings:
                    load_site_config()

                yield
        finally:
            if reload_settings:
                load_site_config()
