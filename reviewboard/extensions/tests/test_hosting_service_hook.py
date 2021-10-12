"""Unit tests for reviewboard.extensions.hooks.HostingServiceHook."""

from reviewboard.extensions.hooks import HostingServiceHook
from reviewboard.extensions.tests.testcases import BaseExtensionHookTestCase
from reviewboard.hostingsvcs.service import (get_hosting_service,
                                             HostingService)
from reviewboard.scmtools.errors import FileNotFoundError


class TestService(HostingService):
    hosting_service_id = 'test-service'
    name = 'Test Service'

    def get_file(self, repository, path, revision, *args, **kwargs):
        """Return the specified file from the repository.

        If the given file path is ``/invalid-path``, the file will be assumed
        to not exist and
        :py:exc:`reviewboard.scmtools.errors.FileNotFoundError` will be raised.

        Args:
            repository (reviewboard.scmtools.models.Repository):
                The repository the file belongs to.

            path (unicode):
                The file path.

            revision (unicode):
                The file revision.

            *args (tuple):
                Additional positional arguments.

            **kwargs (dict):
                Additional keyword arguments.

        Returns:
            unicode: The file data.

        Raises:
            reviewboard.scmtools.errors.FileNotFoundError:
                Raised if the file does not exist.
        """
        if path == '/invalid-path':
            raise FileNotFoundError(path, revision)

        return super(TestService, self).get_file(repository, path, revision,
                                                 *args, **kwargs)

    def get_file_exists(self, repository, path, revision, *args, **kwargs):
        """Return the specified file from the repository.

        If the given file path is ``/invalid-path``, the file will
        be assumed to not exist.

        Args:
            repository (reviewboard.scmtools.models.Repository):
                The repository the file belongs to.

            path (unicode):
                The file path.

            revision (unicode):
                The file revision.

            *args (tuple):
                Additional positional arguments.

            **kwargs (dict):
                Additional keyword arguments.

        Returns:
            bool: Whether or not the file exists.
        """
        if path == '/invalid-path':
            return False

        return super(TestService, self).get_file_exists(
            repository, path, revision, *args, **kwargs)


class HostingServiceHookTests(BaseExtensionHookTestCase):
    """Testing HostingServiceHook."""

    def test_register(self):
        """Testing HostingServiceHook initializing"""
        HostingServiceHook(self.extension, TestService)

        self.assertEqual(get_hosting_service('test-service'),
                         TestService)

    def test_register_without_hosting_service_id(self):
        """Testing HostingServiceHook initializing without hosting_service_id
        """
        class TestServiceWithoutID(TestService):
            hosting_service_id = None

        message = 'TestServiceWithoutID.hosting_service_id must be set.'

        with self.assertRaisesMessage(ValueError, message):
            HostingServiceHook(self.extension, TestServiceWithoutID)

    def test_unregister(self):
        """Testing HostingServiceHook uninitializing"""
        hook = HostingServiceHook(self.extension, TestService)
        hook.disable_hook()

        self.assertIsNone(get_hosting_service('test-service'))
