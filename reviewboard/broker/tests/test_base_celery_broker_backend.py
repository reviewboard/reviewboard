"""Unit tests for reviewboard.broker.base.backends.BaseCeleryBrokerBackend.

Version Added:
    9.0
"""

from __future__ import annotations

import logging

import kgb
from kombu import Connection

from reviewboard.broker.backends.memory import MemoryBrokerBackend
from reviewboard.testing.testcase import TestCase


class BaseCeleryBrokerBackendTests(kgb.SpyAgency, TestCase):
    """Unit tests for BaseCeleryBrokerBackend.

    Version Added:
        9.0
    """

    def test_check_connection(self) -> None:
        """Testing BaseCeleryBrokerBackend.check_connection"""
        backend = MemoryBrokerBackend()

        self.spy_on(Connection.ensure_connection,
                    owner=Connection)

        backend.check_connection({})

        self.assertSpyCalledWith(Connection.ensure_connection,
                                 max_retries=0,
                                 timeout=5.0)

        # The backend's own Celery instance should not have been built.
        self.assertIsNone(backend._celery)

    def test_check_connection_with_broker_settings(self) -> None:
        """Testing BaseCeleryBrokerBackend.check_connection uses the
        provided broker settings
        """
        backend = MemoryBrokerBackend()

        self.spy_on(backend.get_celery_config)
        self.spy_on(backend.get_broker_settings)

        backend.check_connection({
            'key': 'value',
        })

        self.assertSpyCalledWith(
            backend.get_celery_config,
            {
                'key': 'value',
            })
        self.assertSpyNotCalled(backend.get_broker_settings)

    def test_check_connection_with_timeout(self) -> None:
        """Testing BaseCeleryBrokerBackend.check_connection with
        timeout_secs=
        """
        backend = MemoryBrokerBackend()

        self.spy_on(Connection.ensure_connection,
                    owner=Connection)

        backend.check_connection({},
                                 timeout_secs=2.0)

        self.assertSpyCalledWith(Connection.ensure_connection,
                                 max_retries=0,
                                 timeout=2.0)

    def test_check_connection_with_error(self) -> None:
        """Testing BaseCeleryBrokerBackend.check_connection with a
        connection error
        """
        backend = MemoryBrokerBackend()

        self.spy_on(Connection.ensure_connection,
                    owner=Connection,
                    op=kgb.SpyOpRaise(ConnectionError('Oh no')))

        with self.assertRaisesMessage(ConnectionError, 'Oh no'):
            backend.check_connection({})

    def test_shutdown(self) -> None:
        """Testing BaseCeleryBrokerBackend.shutdown"""
        backend = MemoryBrokerBackend()
        celery = backend.get_celery()

        self.spy_on(celery.close)

        backend.shutdown()

        self.assertSpyCalled(celery.close)
        self.assertIsNone(backend._celery)

    def test_shutdown_when_not_connected(self) -> None:
        """Testing BaseCeleryBrokerBackend.shutdown when not connected"""
        backend = MemoryBrokerBackend()
        self.spy_on(backend.get_celery)

        backend.shutdown()

        self.assertSpyNotCalled(backend.get_celery)
        self.assertIsNone(backend._celery)

    def test_scan_workers_with_no_workers(self) -> None:
        """Testing BaseCeleryBrokerBackend.scan_workers with no workers"""
        backend = MemoryBrokerBackend()

        self.spy_on(
            backend.get_celery().control.ping,
            op=kgb.SpyOpReturn([]))

        workers = backend.scan_workers()

        self.assertEqual(
            workers,
            {
                'status': 'ok',
                'workers': [],
            })

    def test_scan_workers(self) -> None:
        """Testing BaseCeleryBrokerBackend.scan_workers with workers"""
        backend = MemoryBrokerBackend()

        self.spy_on(
            backend.get_celery().control.ping,
            op=kgb.SpyOpReturn([
                {
                    'worker1@server1': {
                        'ok': 'pong',
                    },
                    'worker2': {
                        'ok': 'pong',
                    },
                },
                {
                    'worker1@server2': {
                        'ok': 'pong',
                    },
                },
                {},
            ]))

        workers = backend.scan_workers()

        self.assertEqual(
            workers,
            {
                'status': 'ok',
                'workers': [
                    {
                        'hostname': 'server1',
                        'worker': 'worker1@server1',
                    },
                    {
                        'hostname': 'worker2',
                        'worker': 'worker2',
                    },
                    {
                        'hostname': 'server2',
                        'worker': 'worker1@server2',
                    },
                ],
            })

    def test_scan_workers_with_worker_error(self) -> None:
        """Testing BaseCeleryBrokerBackend.scan_workers with a worker error"""
        backend = MemoryBrokerBackend()

        self.spy_on(
            backend.get_celery().control.ping,
            op=kgb.SpyOpReturn([
                {
                    'worker1@server1': {
                        'ok': 'pong',
                    },
                    'worker2@server1': {
                        'ok': 'pong',
                    },
                },
                {
                    'worker1@server2': {},
                },
                {},
            ]))

        workers = backend.scan_workers()

        self.assertEqual(
            workers,
            {
                'status': 'error',
                'workers': [
                    {
                        'hostname': 'server1',
                        'worker': 'worker1@server1',
                    },
                    {
                        'hostname': 'server1',
                        'worker': 'worker2@server1',
                    },
                    {
                        'error': (
                            "Unexpected result when querying worker status "
                            "for worker1@server2. Please check the worker's "
                            "logs for more information."
                        ),
                        'hostname': 'server2',
                        'worker': 'worker1@server2',
                    },
                ],
            })

    def test_scan_workers_with_worker_error_message(self) -> None:
        """Testing BaseCeleryBrokerBackend.scan_workers with a worker error
        containing an error message
        """
        backend = MemoryBrokerBackend()

        self.spy_on(
            backend.get_celery().control.ping,
            op=kgb.SpyOpReturn([
                {
                    'worker1@server1': {
                        'ok': 'pong',
                    },
                    'worker2@server1': {
                        'ok': 'pong',
                    },
                },
                {
                    'worker1@server2': {
                        'error': 'oh no',
                    },
                },
                {},
            ]))

        workers = backend.scan_workers()

        self.assertEqual(
            workers,
            {
                'status': 'error',
                'workers': [
                    {
                        'hostname': 'server1',
                        'worker': 'worker1@server1',
                    },
                    {
                        'hostname': 'server1',
                        'worker': 'worker2@server1',
                    },
                    {
                        'error': (
                            'Unexpected result when querying worker status '
                            'for worker1@server2: "oh no". Please check the '
                            'worker\'s logs for more information.'
                        ),
                        'hostname': 'server2',
                        'worker': 'worker1@server2',
                    },
                ],
            })

    def test_scan_workers_with_scan_error(self) -> None:
        """Testing BaseCeleryBrokerBackend.scan_workers with a scan error"""
        backend = MemoryBrokerBackend()

        self.spy_on(backend.get_celery().control.ping,
                    op=kgb.SpyOpRaise(Exception('oh no')))
        workers = backend.scan_workers()

        self.assertEqual(
            workers,
            {
                'error': 'Unable to perform a worker scan: oh no',
                'status': 'error',
                'workers': [],
            })

    def test_broadcast_when_connected(self) -> None:
        """Testing BaseCeleryBrokerBackend.broadcast when connected"""
        backend = MemoryBrokerBackend()
        backend.get_celery()

        self.spy_on(backend._build_celery)

        with self.assertLogs(logger=backend.logger,
                             level=logging.DEBUG) as logs:
            backend.broadcast('test', {})

        self.assertSpyNotCalled(backend._build_celery)

        output = logs.output
        self.assertEqual(len(output), 3)
        self.assertTrue(output[0].endswith(
            "Begin: Broadcasting message 'test' to workers"))
        self.assertTrue(output[1].endswith(
            "End: Broadcasting message 'test' to workers"))
        self.assertRegex(
            output[2],
            r".* Broadcasting message 'test' to workers took \d*\.\d* seconds")

    def test_broadcast_when_not_connected(self) -> None:
        """Testing BaseCeleryBrokerBackend.broadcast when not connected"""
        backend = MemoryBrokerBackend()

        self.spy_on(backend._build_celery)

        with self.assertLogs(logger=backend.logger,
                             level=logging.DEBUG) as logs:
            backend.broadcast('test', {})

        self.assertSpyCalled(backend._build_celery)

        output = logs.output
        self.assertEqual(len(output), 3)
        self.assertTrue(output[0].endswith(
            "Begin: Broadcasting message 'test' to workers"))
        self.assertTrue(output[1].endswith(
            "End: Broadcasting message 'test' to workers"))
        self.assertRegex(
            output[2],
            r".* Broadcasting message 'test' to workers took \d*\.\d* seconds")

    def test_send_task_when_connected(self) -> None:
        """Testing BaseCeleryBrokerBackend.send_task when connected"""
        backend = MemoryBrokerBackend()
        backend.get_celery()

        self.spy_on(backend._build_celery)

        with self.assertLogs(logger=backend.logger,
                             level=logging.DEBUG) as logs:
            backend.send_task('test', {},
                              queue='test')

        self.assertSpyNotCalled(backend._build_celery)

        output = logs.output
        self.assertEqual(len(output), 3)
        self.assertTrue(output[0].endswith(
            "Begin: Sending task 'test' to workers on queue 'test'"))
        self.assertTrue(output[1].endswith(
            "End: Sending task 'test' to workers on queue 'test'"))
        self.assertRegex(
            output[2],
            r".* Sending task 'test' to workers on queue 'test' took "
            r"\d*\.\d* seconds")

    def test_send_task_when_not_connected(self) -> None:
        """Testing BaseCeleryBrokerBackend.send_task when not connected"""
        backend = MemoryBrokerBackend()

        self.spy_on(backend._build_celery)

        with self.assertLogs(logger=backend.logger,
                             level=logging.DEBUG) as logs:
            backend.send_task('test', {},
                              queue='test')

        self.assertSpyCalled(backend._build_celery)

        output = logs.output
        self.assertEqual(len(output), 3)
        self.assertTrue(output[0].endswith(
            "Begin: Sending task 'test' to workers on queue 'test'"))
        self.assertTrue(output[1].endswith(
            "End: Sending task 'test' to workers on queue 'test'"))
        self.assertRegex(
            output[2],
            r".* Sending task 'test' to workers on queue 'test' took "
            r"\d*\.\d* seconds")

    def test_get_celery_when_connected(self) -> None:
        """Testing BaseCeleryBrokerBackend.get_celery when connected"""
        backend = MemoryBrokerBackend()
        backend.get_celery()

        self.spy_on(backend._build_celery)

        app = backend.get_celery()

        self.assertIsNotNone(app)
        self.assertIs(backend._celery, app)
        self.assertEqual(app.main, 'reviewboard')
        self.assertEqual(app.conf.broker_url, 'memory://')
        self.assertEqual(app.conf.task_serializer, 'json')
        self.assertSpyNotCalled(backend._build_celery)

    def test_get_celery_when_not_connected(self) -> None:
        """Testing BaseCeleryBrokerBackend.get_celery when not connected"""
        backend = MemoryBrokerBackend()

        self.spy_on(backend._build_celery)

        app = backend.get_celery()

        self.assertIsNotNone(app)
        self.assertIs(backend._celery, app)
        self.assertEqual(app.main, 'reviewboard')
        self.assertEqual(app.conf.broker_url, 'memory://')
        self.assertEqual(app.conf.task_serializer, 'json')
        self.assertSpyCalled(backend._build_celery)

    def test_get_celery_with_thread_claimed(self) -> None:
        """Testing BaseCeleryBrokerBackend.get_celery when another thread
        established the connection
        """
        backend = MemoryBrokerBackend()
        lock_count = 0

        # We'll be simulating an instance being set just after checking
        # backend._celery and just before acquiring the lock.
        class _FakeLock:
            def __enter__(_self, *args) -> _FakeLock:
                nonlocal lock_count

                lock_count += 1

                if lock_count == 1:
                    self.assertIsNone(backend._celery)
                    backend._celery = backend._build_celery()

                return _self

            def __exit__(self, *args) -> None:
                pass

        self.spy_on(backend._build_celery)
        backend._lock = _FakeLock()  # type: ignore

        app = backend.get_celery()

        self.assertEqual(lock_count, 1)
        self.assertSpyCallCount(backend._build_celery, 1)

        self.assertIsNotNone(app)
        self.assertIs(backend._celery, app)
        self.assertEqual(app.main, 'reviewboard')
        self.assertEqual(app.conf.broker_url, 'memory://')
        self.assertEqual(app.conf.task_serializer, 'json')
        self.assertSpyCalled(backend._build_celery)
