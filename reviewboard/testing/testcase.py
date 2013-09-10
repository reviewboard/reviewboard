import os

from django.conf import settings
from django.contrib.auth.models import User
from django.core.cache import cache
from django.core.files import File
from djblets.testing.testcases import TestCase as DjbletsTestCase

from reviewboard import scmtools
from reviewboard.attachments.models import FileAttachment
from reviewboard.diffviewer.models import DiffSet, DiffSetHistory, FileDiff
from reviewboard.reviews.models import (Comment, Group, Review, ReviewRequest,
                                        Screenshot)
from reviewboard.scmtools.models import Repository, Tool
from reviewboard.site.models import LocalSite


class TestCase(DjbletsTestCase):
    """The base class for Review Board test cases.

    This class provides a number of convenient functions for creating
    common objects for testing, such as review requests and comments. They're
    populated with default data that can be overridden by the callers.

    This also overcomes an annoyance with default Django unit tests where
    the cache is not cleared across tests, leading to inconsistent results
    and useless testing.
    """
    local_site_name = 'local-site-1'

    def setUp(self):
        super(TestCase, self).setUp()

        # Clear the cache so that previous tests don't impact this one.
        cache.clear()

    def create_diffset(self, review_request=None, revision=1, repository=None,
                       name='diffset'):
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
            repository=repository)

        if review_request:
            review_request.diffset_history.diffsets.add(diffset)

        return diffset

    def create_diff_comment(self, review, filediff, interfilediff=None,
                            text='My comment', issue_opened=False,
                            first_line=1, num_lines=5, reply_to=None):
        """Creates a Comment for testing.

        The comment is tied to the given Review and FileDiff (and, optionally,
        an interfilediff). It's populated with default data that can be
        overridden by the caller.
        """
        if issue_opened:
            issue_status = Comment.OPEN
        else:
            issue_status = None

        return review.comments.create(
            filediff=filediff,
            interfilediff=interfilediff,
            first_line=first_line,
            num_lines=num_lines,
            text=text,
            issue_opened=issue_opened,
            issue_status=issue_status,
            reply_to=reply_to)

    def create_file_attachment(self, review_request,
                               orig_filename='filename.png',
                               caption='My Caption',
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

        review_request.file_attachments.add(file_attachment)

        return file_attachment

    def create_file_attachment_comment(self, review, file_attachment):
        """Creates a FileAttachmentComment for testing.

        The comment is tied to the given Review and FileAttachment. It's
        populated with default data that can be overridden by the caller.
        """
        return review.file_attachment_comments.create(
            file_attachment=file_attachment,
            text='My comment')

    def create_filediff(self, diffset, source_file='/test-file',
                        dest_file='/test-file', source_revision='123',
                        dest_detail='124', diff=''):
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
            status=FileDiff.MODIFIED,
            diff=diff)

    def create_repository(self, with_local_site=False, name='Test Repo',
                          tool_name='Git'):
        """Creates a Repository for testing.

        The Repository may optionally be attached to a LocalSite. It's also
        populated with default data that can be overridden by the caller.

        This accepts a tool_name of "Git", "Mercurial" or "Subversion".
        The correct bundled repository path will be used for the given
        tool_name.
        """
        if with_local_site:
            local_site = LocalSite.objects.get(name=self.local_site_name)
        else:
            local_site = None

        testdata_dir = os.path.join(os.path.dirname(scmtools.__file__),
                                    'testdata')

        if tool_name == 'Git':
            path = os.path.join(testdata_dir, 'git_repo')
        elif tool_name == 'Subversion':
            path = 'file://' + os.path.join(testdata_dir, 'svn_repo')
        elif tool_name == 'Mercurial':
            path = os.path.join(testdata_dir, 'hg_repo.bundle')
        else:
            raise NotImplementedError

        return Repository.objects.create(
            name=name,
            local_site=local_site,
            tool=Tool.objects.get(name=tool_name),
            path=path)

    def create_review_request(self, with_local_site=False, with_diffs=False,
                              summary='Test Summary',
                              description='Test Description',
                              testing_done='Testing',
                              submitter='doc', local_id=1001,
                              status='P', public=False, publish=False,
                              repository=None, id=None,
                              create_repository=False):
        """Creates a ReviewRequest for testing.

        The ReviewRequest may optionally be attached to a LocalSite. It's also
        populated with default data that can be overridden by the caller.

        If create_repository is True, a Repository will be created
        automatically. If set, a custom repository cannot be provided.

        The provided submitter may either be a username or a User object.

        If publish is True, ReviewRequest.publish() will be called.
        """
        if with_local_site:
            local_site = LocalSite.objects.get(name=self.local_site_name)
        else:
            local_site = None
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
            status=status,
            id=id)
        review_request.save()

        if publish:
            review_request.publish(review_request.submitter)

        return review_request

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
                            visible=True):
        """Creates a review group for testing.

        The group may optionally be attached to a LocalSite. It's also
        populated with default data that can be overridden by the caller.
        """
        if with_local_site:
            local_site = LocalSite.objects.get(name=self.local_site_name)
        else:
            local_site = None

        return Group.objects.create(
            name=name,
            local_site=local_site,
            visible=visible)

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

    def create_screenshot(self, review_request, caption='My caption'):
        """Creates a Screenshot for testing.

        The Screenshot is tied to the given ReviewRequest. It's populated
        with default data that can be overridden by the caller.
        """
        screenshot = Screenshot(caption=caption)
        filename = os.path.join(settings.STATIC_ROOT, 'rb', 'images',
                                'trophy.png')

        with open(filename, 'r') as f:
            screenshot.image.save(filename, File(f), save=True)

        review_request.screenshots.add(screenshot)

        return screenshot

    def create_screenshot_comment(self, review, screenshot, text='My comment',
                                  x=1, y=1, w=5, h=5):
        """Creates a ScreenshotComment for testing.

        The comment is tied to the given Review and Screenshot. It's
        It's populated with default data that can be overridden by the caller.
        """
        return review.screenshot_comments.create(
            screenshot=screenshot,
            text='My comment',
            x=x,
            y=y,
            w=w,
            h=h)
