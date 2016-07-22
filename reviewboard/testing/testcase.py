from __future__ import unicode_literals

import copy
import os
import re
import sys
import warnings
from contextlib import contextmanager

from django.conf import settings
from django.contrib.auth.models import User
from django.core import serializers
from django.core.cache import cache
from django.core.files import File
from django.db import (DatabaseError, DEFAULT_DB_ALIAS, IntegrityError,
                       connections, router)
from django.db.models import get_apps
from djblets.testing.testcases import TestCase as DjbletsTestCase
from django.utils import six

from reviewboard import scmtools, initialize
from reviewboard.attachments.models import FileAttachment
from reviewboard.diffviewer.differ import DiffCompatVersion
from reviewboard.diffviewer.models import DiffSet, DiffSetHistory, FileDiff
from reviewboard.reviews.models import (Comment, FileAttachmentComment,
                                        Group, Review, ReviewRequest,
                                        ReviewRequestDraft, Screenshot,
                                        ScreenshotComment)
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

    _precompiled_fixtures = {}
    _fixture_dirs = []

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
                local_site = LocalSite.objects.get(name=self.local_site_name)
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
        """Creates a ReviewRequest for testing.

        The ReviewRequest may optionally be attached to a LocalSite. It's also
        populated with default data that can be overridden by the caller.

        If create_repository is True, a Repository will be created
        automatically. If set, a custom repository cannot be provided.

        The provided submitter may either be a username or a User object.

        If publish is True, ReviewRequest.publish() will be called.
        """
        if not local_site:
            if with_local_site:
                local_site = LocalSite.objects.get(name=self.local_site_name)
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
                            local_site=None, visible=True, invite_only=False):
        """Creates a review group for testing.

        The group may optionally be attached to a LocalSite. It's also
        populated with default data that can be overridden by the caller.
        """
        if not local_site and with_local_site:
            local_site = LocalSite.objects.get(name=self.local_site_name)

        return Group.objects.create(
            name=name,
            local_site=local_site,
            visible=visible,
            invite_only=invite_only)

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

    def _fixture_setup(self):
        """Set up fixtures for unit tests.

        Unlike Django's standard _fixture_setup function, this doesn't
        re-locate and re-deserialize the fixtures every time. Instead, it
        precompiles fixtures the first time they're found and reuses the
        objects for future tests.

        However, also unlike Django's, this does not accept compressed
        or non-JSON fixtures.
        """
        # Temporarily hide the fixtures, so that the parent class won't
        # do anything with them.
        self._hide_fixtures = True
        super(TestCase, self)._fixture_setup()
        self._hide_fixtures = False

        if getattr(self, 'multi_db', False):
            databases = connections
        else:
            databases = [DEFAULT_DB_ALIAS]

        for db in databases:
            if hasattr(self, 'fixtures'):
                self.load_fixtures(self.fixtures, db=db)

    def load_fixtures(self, fixtures, db=DEFAULT_DB_ALIAS):
        """Loads fixtures for the current test.

        This is called for every fixture in the testcase's ``fixtures``
        list. It can also be called by an individual test to add additional
        fixtures on top of that.
        """
        if not fixtures:
            return

        if db not in TestCase._precompiled_fixtures:
            TestCase._precompiled_fixtures[db] = {}

        for fixture in fixtures:
            if fixture not in TestCase._precompiled_fixtures[db]:
                self._precompile_fixture(fixture, db)

        self._load_fixtures(fixtures, db)

    def _precompile_fixture(self, fixture, db):
        """Precompiles a fixture.

        The fixture is loaded and deserialized, and the resulting objects
        are stored for future use.
        """
        assert db in TestCase._precompiled_fixtures
        assert fixture not in TestCase._precompiled_fixtures[db]

        fixture_path = None

        for fixture_dir in self._get_fixture_dirs():
            fixture_path = os.path.join(fixture_dir, fixture + '.json')

            if os.path.exists(fixture_path):
                break

        try:
            if not fixture_path:
                raise IOError('Fixture path not found')

            with open(fixture_path, 'r') as fp:
                TestCase._precompiled_fixtures[db][fixture] = [
                    obj
                    for obj in serializers.deserialize('json', fp, using=db)
                    if router.allow_syncdb(db, obj.object.__class__)
                ]
        except IOError as e:
            sys.stderr.write('Unable to load fixture %s: %s\n' % (fixture, e))

    def _get_fixture_dirs(self):
        """Returns the list of fixture directories.

        This is computed only once and cached.
        """
        if not TestCase._fixture_dirs:
            app_module_paths = []

            for app in get_apps():
                if hasattr(app, '__path__'):
                    # It's a 'models/' subpackage.
                    for path in app.__path__:
                        app_module_paths.append(path)
                else:
                    # It's a models.py module
                    app_module_paths.append(app.__file__)

            all_fixture_dirs = [
                os.path.join(os.path.dirname(path), 'fixtures')
                for path in app_module_paths
            ]

            TestCase._fixture_dirs = [
                fixture_dir
                for fixture_dir in all_fixture_dirs
                if os.path.exists(fixture_dir)
            ]

        return TestCase._fixture_dirs

    def _load_fixtures(self, fixtures, db):
        """Loads precompiled fixtures.

        Each precompiled fixture is loaded and then used to populate the
        database.
        """
        models = set()
        connection = connections[db]

        with connection.constraint_checks_disabled():
            for fixture in fixtures:
                assert db in TestCase._precompiled_fixtures
                assert fixture in TestCase._precompiled_fixtures[db]
                objects = TestCase._precompiled_fixtures[db][fixture]

                for obj in objects:
                    models.add(obj.object.__class__)

                    try:
                        obj = copy.copy(obj)
                        obj.save(using=db)
                    except (DatabaseError, IntegrityError) as e:
                        sys.stderr.write('Could not load %s.%s(pk=%s): %s\n'
                                         % (obj.object._meta.app_label,
                                            obj.object._meta.object_name,
                                            obj.object.pk,
                                            e))
                        raise

        # We disabled constraints above, so check now.
        connection.check_constraints(table_names=[
            model._meta.db_table
            for model in models
        ])

    def __getattribute__(self, name):
        if name == 'fixtures' and self.__dict__.get('_hide_fixtures'):
            raise AttributeError

        return super(TestCase, self).__getattribute__(name)
