"""Unit tests for reviewboard.broker.backends.local.

Version Added:
    9.0
"""

from __future__ import annotations

import base64
import glob
import json
import os
import shutil
import tempfile
from typing import TYPE_CHECKING

import kgb

from reviewboard.admin.server import get_data_dir, get_hostname
from reviewboard.broker.backends.local import LocalBrokerBackend
from reviewboard.testing.testcase import TestCase

if TYPE_CHECKING:
    from collections.abc import Sequence

    from typelets.json import JSONDict, JSONDictImmutable


class LocalBrokerBackendTests(kgb.SpyAgency, TestCase):
    """Unit tests for LocalBrokerBackend.

    Version Added:
        9.0
    """

    ######################
    # Instance variables #
    ######################

    #: Siteconfig settings that can be used for a test.
    broker_siteconfig_settings: JSONDict

    #: The temporary directory used for the local queue state.
    queue_dir: str

    def setUp(self) -> None:
        """Set up state for a test.

        This will set up a temporary directory for the message queue.
        """
        super().setUp()

        queue_dir = tempfile.mkdtemp()
        self.queue_dir = queue_dir

        self.broker_siteconfig_settings = {
            'brokers': {
                'local': {
                    'queue_path': queue_dir,
                },
            },
        }

    def tearDown(self) -> None:
        """Tear down state for a test.

        This will remove the temporary queue directory.
        """
        shutil.rmtree(self.queue_dir,
                      ignore_errors=True)

        delattr(self, 'broker_siteconfig_settings')
        delattr(self, 'queue_dir')

        super().tearDown()

    def test_check_connection_with_existing_dir(self) -> None:
        """Testing LocalBrokerBackend.check_connection with an existing
        writable directory
        """
        backend = LocalBrokerBackend()

        # This should not raise.
        backend.check_connection({
            'queue_path': self.queue_dir,
        })

    def test_check_connection_with_new_dir(self) -> None:
        """Testing LocalBrokerBackend.check_connection with a directory that
        doesn't exist yet under a writable parent
        """
        queue_dir = os.path.join(self.queue_dir, 'a', 'b')

        backend = LocalBrokerBackend()
        backend.check_connection({
            'queue_path': queue_dir,
        })

        self.assertFalse(os.path.exists(queue_dir))

    def test_check_connection_with_default_path(self) -> None:
        """Testing LocalBrokerBackend.check_connection with the default path"""
        self.spy_on(get_data_dir,
                    op=kgb.SpyOpReturn(self.queue_dir))
        self.spy_on(get_hostname)

        backend = LocalBrokerBackend()

        # This should not raise.
        backend.check_connection({})

        self.assertSpyNotCalled(get_hostname)

    def test_check_connection_with_default_path_unwritable(self) -> None:
        """Testing LocalBrokerBackend.check_connection with the default path
        and an unwritable data directory
        """
        data_dir = self.queue_dir
        backend = LocalBrokerBackend()
        message = (
            f'Review Board does not have permission to write to '
            f'"{data_dir}".'
        )

        self.spy_on(get_data_dir,
                    op=kgb.SpyOpReturn(data_dir))
        os.chmod(data_dir, 0o500)

        try:
            with self.assertRaisesMessage(ValueError, message):
                backend.check_connection({})
        finally:
            os.chmod(data_dir, 0o700)

    def test_check_connection_with_default_path_unwritable_local_queue(
        self,
    ) -> None:
        """Testing LocalBrokerBackend.check_connection with the default
        path and an unwritable local-queue directory
        """
        data_dir = self.queue_dir
        local_queue_dir = os.path.join(data_dir, 'local-queue')
        backend = LocalBrokerBackend()
        message = (
            f'Review Board does not have permission to write to '
            f'"{local_queue_dir}".'
        )

        self.spy_on(get_data_dir,
                    op=kgb.SpyOpReturn(data_dir))
        os.mkdir(local_queue_dir, 0o500)

        try:
            with self.assertRaisesMessage(ValueError, message):
                backend.check_connection({})
        finally:
            os.chmod(local_queue_dir, 0o700)

    def test_check_connection_with_relative_path(self) -> None:
        """Testing LocalBrokerBackend.check_connection with a relative path"""
        backend = LocalBrokerBackend()
        message = 'The queue path "queue" must be an absolute path.'

        with self.assertRaisesMessage(ValueError, message):
            backend.check_connection({
                'queue_path': 'queue',
            })

    def test_check_connection_with_file(self) -> None:
        """Testing LocalBrokerBackend.check_connection with a path to a file"""
        path = os.path.join(self.queue_dir, 'file')

        with open(path, 'w'):
            pass

        backend = LocalBrokerBackend()
        message = f'"{path}" is not a directory.'

        with self.assertRaisesMessage(ValueError, message):
            backend.check_connection({
                'queue_path': path,
            })

    def test_check_connection_with_unwritable_parent(self) -> None:
        """Testing LocalBrokerBackend.check_connection with a new directory
        under an unwritable parent
        """
        queue_dir = self.queue_dir
        backend = LocalBrokerBackend()
        message = (
            f'Review Board does not have permission to write to '
            f'"{queue_dir}".'
        )

        os.chmod(queue_dir, 0o500)

        try:
            with self.assertRaisesMessage(ValueError, message):
                backend.check_connection({
                    'queue_path': os.path.join(queue_dir, 'queue'),
                })
        finally:
            os.chmod(queue_dir, 0o700)

    def test_get_celery_config_with_default_path(self) -> None:
        """Testing LocalBrokerBackend.get_celery_config with default path
        """
        self.spy_on(get_hostname, op=kgb.SpyOpReturn('my-host.int'))

        backend = LocalBrokerBackend()
        celery_config = backend.get_celery_config({})

        queue_dir = os.path.join(get_data_dir(), 'local-queue', 'my-host.int')
        control_dir = os.path.join(queue_dir, 'control')

        self.assertEqual(
            celery_config,
            {
                'app_config': {
                    'broker_transport_options': {
                        'control_folder': control_dir,
                        'data_folder_in': queue_dir,
                        'data_folder_out': queue_dir,
                    },
                    'broker_url': 'filesystem://',
                },
            })

        self.assertTrue(os.path.exists(control_dir))
        self.assertTrue(os.path.exists(queue_dir))

    def test_get_celery_config_with_custom_path(self) -> None:
        """Testing LocalBrokerBackend.get_celery_config with custom path"""
        queue_dir = self.queue_dir
        control_dir = os.path.join(queue_dir, 'control')

        backend = LocalBrokerBackend()
        celery_config = backend.get_celery_config({
            'queue_path': queue_dir,
        })

        self.assertEqual(
            celery_config,
            {
                'app_config': {
                    'broker_transport_options': {
                        'control_folder': control_dir,
                        'data_folder_in': queue_dir,
                        'data_folder_out': queue_dir,
                    },
                    'broker_url': 'filesystem://',
                },
            })

        self.assertTrue(os.path.exists(control_dir))
        self.assertTrue(os.path.exists(queue_dir))

    def test_broadcast(self) -> None:
        """Testing LocalBrokerBackend.broadcast"""
        with self.siteconfig_settings(self.broker_siteconfig_settings):
            backend = LocalBrokerBackend()
            celery_app = backend.get_celery()

            mailbox = celery_app.control.mailbox
            fake_worker_queue = mailbox.get_queue('fake-worker@my-host')

            with celery_app.connection_for_write() as conn:
                fake_worker_queue(conn.default_channel).declare()

            queue_dir = self.queue_dir
            self.assertEqual(os.listdir(queue_dir), ['control'])
            self.assertEqual(os.listdir(os.path.join(queue_dir, 'control')),
                             ['celery.pidbox.exchange'])

            backend.broadcast(
                command='test-broadcast',
                command_args={
                    'key': 'value',
                },
            )

            messages = self._read_messages('fake-worker@my-host.celery.pidbox')
            self.assertEqual(len(messages), 1)

            message_body = messages[0]['body']
            assert isinstance(message_body, dict)

            self.assertEqual(message_body['method'], 'test-broadcast')
            self.assertEqual(message_body['arguments'], {
                'key': 'value',
            })

    def test_send_task(self) -> None:
        """Testing LocalBrokerBackend.send_task"""
        with self.siteconfig_settings(self.broker_siteconfig_settings):
            backend = LocalBrokerBackend()
            backend.send_task(
                command='test-task',
                command_args={
                    'key': 'value',
                },
                queue='my-queue',
            )

        queue_dir = self.queue_dir
        control_dir = os.path.join(queue_dir, 'control')

        # Check the control directory.
        self.assertEqual(os.listdir(control_dir), ['my-queue.exchange'])

        # Check the messages in the queue directory.
        messages = self._read_messages('my-queue')
        self.assertEqual(len(messages), 1)

        message_headers = messages[0]['headers']
        assert isinstance(message_headers, dict)

        self.assertEqual(message_headers['task'], 'test-task')
        self.assertEqual(message_headers['argsrepr'], '()')
        self.assertEqual(message_headers['kwargsrepr'], "{'key': 'value'}")

    def _read_messages(
        self,
        namespace: str,
    ) -> Sequence[JSONDictImmutable]:
        """Read messages from the queue directory.

        This will look for all messages that match the given namespace,
        parse them, normalize the body contents, and return the results.

        Args:
            namespace (str):
                The namespace for the messages.

        Returns:
            list of dict:
            The list of parsed and normalized message data.
        """
        queue_dir = self.queue_dir
        messages: list[JSONDictImmutable] = []

        message_files = glob.glob(os.path.join(queue_dir,
                                               f'*.{namespace}.msg'))

        for message_file in message_files:
            with open(message_file,
                      mode='r',
                      encoding='utf-8') as fp:
                message = json.load(fp)

                self.assertEqual(message['content-encoding'], 'utf-8')
                self.assertEqual(message['content-type'], 'application/json')

                if message['properties']['body_encoding'] == 'base64':
                    message['body'] = \
                        json.loads(base64.b64decode(message['body']))

                messages.append(message)

        return messages
