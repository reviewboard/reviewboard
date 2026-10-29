"""Unit tests for reviewboard.worker.celery_worker.

Version Added:
    9.0
"""

from __future__ import annotations

import sys
from typing import TYPE_CHECKING

import kgb
from celery import (
    concurrency as celery_concurrency,
    maybe_patch_concurrency,
)
from celery.bin.worker import detach as detach_process
from celery.platforms import maybe_drop_privileges

from reviewboard.broker.base.backends import BaseCeleryBrokerBackend
from reviewboard.testing.testcase import TestCase
from reviewboard.worker.celery_worker import (
    _on_after_celery_worker_setup,
    setup_worker_logging,
    start_celery_worker,
)

if TYPE_CHECKING:
    from typelets.json import JSONDictImmutable

    from reviewboard.broker.base.backends import BackendCeleryConfig


class _MyBrokerBackend(BaseCeleryBrokerBackend):
    """A broker backend using Celery's in-memory transport for tests.

    Version Added:
        9.0
    """

    broker_id = 'test-broker'
    name = 'Test Broker'

    def get_celery_config(
        self,
        broker_settings: JSONDictImmutable,
    ) -> BackendCeleryConfig:
        return {
            'app_config': {
                'broker_url': 'memory://',
            },
        }


class CeleryWorkerTests(kgb.SpyAgency, TestCase):
    """Unit tests for reviewboard.worker.celery_worker.

    Version Added:
        9.0
    """

    def setUp(self) -> None:
        """Set up state for the test.

        This will spy on Celery methods that manipulate global state and
        disable them.
        """
        super().setUp()

        self.spy_on(maybe_patch_concurrency,
                    call_original=False)
        self.spy_on(maybe_drop_privileges,
                    call_original=False)

    def test_setup_worker_logging(self) -> None:
        """Testing setup_worker_logging"""
        conf = _MyBrokerBackend().get_celery().conf

        setup_worker_logging(
            instance=None,
            conf=conf,
        )

        self.assertEqual(
            conf.worker_log_format,
            '%(asctime)s - [%(levelname)s] %(name)s: %(message)s')
        self.assertEqual(
            conf.worker_task_log_format,
            '%(asctime)s - %(processName)s: %(task_name)s(%(task_id)s) - '
            '[%(levelname)s] %(name)s: %(message)s')

    def test_on_after_celery_worker_setup(self) -> None:
        """Testing _on_after_celery_worker_setup"""
        celery_app = _MyBrokerBackend().get_celery()
        worker = celery_app.Worker(hostname='worker@my-host')

        _on_after_celery_worker_setup(
            instance=worker,
            conf=celery_app.conf,
        )

        self.assertEqual(celery_app.conf.accept_content, ['json'])
        self.assertEqual(
            set(celery_app.amqp.queues.keys()),
            {
                'celery',
                'reviewboard.local',
            })

    def test_start_celery_worker_with_detach_true(self) -> None:
        """Testing start_celery_worker with detach=True"""
        self.spy_on(detach_process,
                    op=kgb.SpyOpReturn(0))

        broker = _MyBrokerBackend()
        celery_app = broker.get_celery()

        result = start_celery_worker(
            autoscale='10,3',
            broker=broker,
            detach=True,
            hostname='worker@my-host',
            log_file='/tmp/worker.log',
            log_level='INFO',
            num_processes=4,
            pid_file='/tmp/worker.pid',
            pool='prefork',
            site_dir='/site',
        )

        self.assertEqual(result, 0)

        self.assertSpyCalledWith(
            detach_process,
            sys.executable,
            [
                sys.argv[0],
                '--autoscale=10,3',
                '--broker=test-broker',
                '--num-processes=4',
                '--hostname=worker@my-host',
                '--log-file=/tmp/worker.log',
                '--log-level=INFO',
                '--pid-file=/tmp/worker.pid',
                '--pool=prefork',
                '--site-dir=/site',
            ],
            app=celery_app,
            hostname='worker@my-host',
            logfile='/tmp/worker.log',
            pidfile='/tmp/worker.pid',
        )

    def test_start_celery_worker_with_detach_false(self) -> None:
        """Testing start_celery_worker with detach=False"""
        broker = _MyBrokerBackend()
        celery_app = broker.get_celery()
        worker_cls = celery_app.Worker

        started_workers = []

        @self.spy_for(worker_cls.start,
                      owner=worker_cls)
        def _fake_start(worker) -> None:
            started_workers.append(worker)
            worker.exitcode = 0

        result = start_celery_worker(
            autoscale='10,3',
            broker=broker,
            detach=False,
            hostname='worker@my-host',
            log_file='/tmp/worker.log',
            log_level='INFO',
            pid_file='/tmp/worker.pid',
            pool='prefork',
            site_dir='/site',
        )

        self.assertEqual(result, 0)
        self.assertEqual(len(started_workers), 1)

        self.assertAttrsEqual(
            started_workers[0],
            {
                'autoscale': [10, 3],
                'hostname': 'worker@my-host',
                'logfile': '/tmp/worker.log',
                'pidfile': '/tmp/worker.pid',
                'pool_cls': celery_concurrency.get_implementation('prefork'),
                'quiet': True,
            })
