"""Unit tests for reviewboard.worker.main.

Version Added:
    9.0
"""

from __future__ import annotations

import contextlib
import io
import sys
from typing import TYPE_CHECKING

import kgb

from reviewboard import initialize
from reviewboard.broker.base.backends import (
    BaseBrokerBackend,
    BaseCeleryBrokerBackend,
)
from reviewboard.broker.registry import broker_registry
from reviewboard.testing.testcase import TestCase
from reviewboard.worker.main import (create_arg_parser,
                                     main as worker_main)
from reviewboard.worker.celery_worker import start_celery_worker

if TYPE_CHECKING:
    from typing import Sequence


class _NonCeleryBrokerBackend(BaseBrokerBackend):
    broker_id = 'non-celery-broker'


class WorkerMainArgumentTests(kgb.SpyAgency, TestCase):
    """Unit tests for reviewboard.worker.main argument handling.

    Version Added:
        9.0
    """

    def test_defaults(self) -> None:
        """Testing rbworker default values"""
        arg_parser = create_arg_parser()
        options = arg_parser.parse_args([
            '--site-dir=/site',
            '--broker=local',
        ])

        self.assertAttrsEqual(
            options,
            {
                'autoscale': None,
                'broker': 'local',
                'detach': False,
                'gid': None,
                'log_file': None,
                'log_level': 'INFO',
                'num_processes': None,
                'pid_file': None,
                'pool_cls': None,
                'site_dir': '/site',
                'uid': None,
                'umask': None,
            })

    def test_broker_with_value(self) -> None:
        """Testing rbworker --broker with a value"""
        arg_parser = create_arg_parser()
        options = arg_parser.parse_args([
            '--broker=my-broker',
            '--site-dir=/site',
        ])

        self.assertEqual(options.broker, 'my-broker')

    def test_broker_with_env(self) -> None:
        """Testing rbworker --broker defaults to $RB_WORKER_BROKER"""
        with self.override_env_vars({'RB_WORKER_BROKER': 'my-broker'}):
            arg_parser = create_arg_parser()
            options = arg_parser.parse_args([
                '--site-dir=/site',
            ])

            self.assertEqual(options.broker, 'my-broker')

    def test_broker_without_value(self) -> None:
        """Testing rbworker --broker without a value or
        $RB_WORKER_BROKER
        """
        with self.override_env_vars({'RB_WORKER_BROKER': None}):
            self._run_invalid_arg_test(
                [
                    '--site-dir=/site',
                ],
                expected_message=(
                    'the following arguments are required: -b/--broker'
                ),
            )

    def test_broker_with_invalid_id(self) -> None:
        """Testing rbworker --broker with an invalid ID"""
        self._run_invalid_arg_test(
            [
                '--broker=xxx',
                '--site-dir=/site',
            ],
            expected_message='Invalid broker ID provided for --broker: xxx',
        )

    def test_broker_with_non_celery_id(self) -> None:
        """Testing rbworker --broker with a non-Celery broker ID"""
        with self.add_registry_items(broker_registry,
                                     [_NonCeleryBrokerBackend]):
            self._run_invalid_arg_test(
                [
                    '--broker=non-celery-broker',
                    '--site-dir=/site',
                ],
                expected_message='is not a Celery-based broker',
            )

    def test_site_dir_with_value(self) -> None:
        """Testing rbworker --site-dir with a value"""
        arg_parser = create_arg_parser()
        options = arg_parser.parse_args([
            '--broker=local',
            '--site-dir=/env-site',
        ])

        self.assertEqual(options.site_dir, '/env-site')

    def test_site_dir_with_env(self) -> None:
        """Testing rbworker --site-dir defaults to $RB_WORKER_SITE_DIR"""
        with self.override_env_vars({'RB_WORKER_SITE_DIR': '/env-site'}):
            arg_parser = create_arg_parser()
            options = arg_parser.parse_args([
                '--broker=local',
            ])

            self.assertEqual(options.site_dir, '/env-site')

    def test_site_dir_without_value(self) -> None:
        """Testing rbworker --site-dir without a value"""
        with self.override_env_vars({'RB_WORKER_SITE_DIR': None}):
            self._run_invalid_arg_test(
                [
                    '--broker=local',
                ],
                expected_message=(
                    'the following arguments are required: --site-dir'
                ),
            )

    def test_hostname_with_value(self) -> None:
        """Testing rbworker --hostname with a value"""
        arg_parser = create_arg_parser()
        options = arg_parser.parse_args([
            '--broker=local',
            '--hostname=my-host',
            '--site-dir=/site',
        ])

        self.assertEqual(options.hostname, 'my-host')

    def test_hostname_with_env(self) -> None:
        """Testing rbworker --hostname defaults to $RB_WORKER_HOSTNAME"""
        with self.override_env_vars({'RB_WORKER_HOSTNAME': 'my-host'}):
            arg_parser = create_arg_parser()
            options = arg_parser.parse_args([
                '--broker=local',
                '--site-dir=/site',
            ])

            self.assertEqual(options.hostname, 'my-host')

    def test_log_level_with_value(self) -> None:
        """Testing rbworker --log-level with a value"""
        arg_parser = create_arg_parser()
        options = arg_parser.parse_args([
            '--broker=local',
            '--log-level=DEBUG',
            '--site-dir=/site',
        ])

        self.assertEqual(options.log_level, 'DEBUG')

    def test_log_level_with_env(self) -> None:
        """Testing rbworker --log-level defaults to $RB_WORKER_LOG_LEVEL"""
        with self.override_env_vars({'RB_WORKER_LOG_LEVEL': 'DEBUG'}):
            arg_parser = create_arg_parser()
            options = arg_parser.parse_args([
                '--site-dir=/site',
                '--broker=local',
            ])

            self.assertEqual(options.log_level, 'DEBUG')

    def test_log_level_with_invalid(self) -> None:
        """Testing rbworker --log-level with an invalid value"""
        self._run_invalid_arg_test(
            [
                '--site-dir=/site',
                '--broker=local',
                '--log-level=XXX',
            ],
            expected_message=(
                "argument -l/--log-level: invalid choice: 'XXX' (choose "
                "from 'DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL', "
                "'FATAL')"
            ),
        )

    def test_log_file_with_value(self) -> None:
        """Testing rbworker --log-file with a value"""
        arg_parser = create_arg_parser()
        options = arg_parser.parse_args([
            '--broker=local',
            '--log-file=/var/log/rb.log',
            '--site-dir=/site',
        ])

        self.assertEqual(options.log_file, '/var/log/rb.log')

    def test_log_file_with_env(self) -> None:
        """Testing rbworker --log-file defaults to $RB_WORKER_LOG_FILE"""
        with self.override_env_vars({'RB_WORKER_LOG_FILE': '/var/log/rb.log'}):
            arg_parser = create_arg_parser()
            options = arg_parser.parse_args([
                '--broker=local',
                '--site-dir=/site',
            ])

            self.assertEqual(options.log_file, '/var/log/rb.log')

    def test_pid_file_with_value(self) -> None:
        """Testing rbworker --pid-file with a value"""
        arg_parser = create_arg_parser()
        options = arg_parser.parse_args([
            '--broker=local',
            '--pid-file=/run/rb.pid',
            '--site-dir=/site',
        ])

        self.assertEqual(options.pid_file, '/run/rb.pid')

    def test_pid_file_with_env(self) -> None:
        """Testing rbworker --pid-file defaults to $RB_WORKER_PID_FILE"""
        with self.override_env_vars({'RB_WORKER_PID_FILE': '/run/rb.pid'}):
            arg_parser = create_arg_parser()
            options = arg_parser.parse_args([
                '--broker=local',
                '--site-dir=/site',
            ])

            self.assertEqual(options.pid_file, '/run/rb.pid')

    def test_uid_with_value(self) -> None:
        """Testing rbworker --uid with a value"""
        arg_parser = create_arg_parser()
        options = arg_parser.parse_args([
            '--broker=local',
            '--site-dir=/site',
            '--uid=1000',
        ])

        self.assertEqual(options.uid, 1000)

    def test_uid_with_env(self) -> None:
        """Testing rbworker --uid defaults to $RB_WORKER_UID"""
        with self.override_env_vars({'RB_WORKER_UID': '1000'}):
            arg_parser = create_arg_parser()
            options = arg_parser.parse_args([
                '--broker=local',
                '--site-dir=/site',
            ])

            self.assertEqual(options.uid, 1000)

    def test_uid_with_invalid(self) -> None:
        """Testing rbworker --uid with an invalid value"""
        self._run_invalid_arg_test(
            [
                '--broker=local',
                '--site-dir=/site',
                '--uid=xxx',
            ],
            expected_message=(
                "argument --uid: invalid int value: 'xxx'"
            ),
        )

    def test_gid_with_value(self) -> None:
        """Testing rbworker --gid with a value"""
        arg_parser = create_arg_parser()
        options = arg_parser.parse_args([
            '--broker=local',
            '--gid=1000',
            '--site-dir=/site',
        ])

        self.assertEqual(options.gid, 1000)

    def test_gid_with_env(self) -> None:
        """Testing rbworker --gid defaults to $RB_WORKER_GID"""
        with self.override_env_vars({'RB_WORKER_GID': '1000'}):
            arg_parser = create_arg_parser()
            options = arg_parser.parse_args([
                '--site-dir=/site',
                '--broker=local',
            ])

            self.assertEqual(options.gid, 1000)

    def test_gid_with_invalid(self) -> None:
        """Testing rbworker --gid with an invalid value"""
        self._run_invalid_arg_test(
            [
                '--site-dir=/site',
                '--broker=local',
                '--gid=not-a-gid',
            ],
            expected_message=(
                "argument --gid: invalid int value: 'not-a-gid'"
            ),
        )

    def test_umask_with_value(self) -> None:
        """Testing rbworker --umask with a value"""
        arg_parser = create_arg_parser()
        options = arg_parser.parse_args([
            '--broker=local',
            '--site-dir=/site',
            '--umask=0022',
        ])

        self.assertEqual(options.umask, '0022')

    def test_umask_with_env(self) -> None:
        """Testing rbworker --umask defaults to $RB_WORKER_UMASK"""
        with self.override_env_vars({'RB_WORKER_UMASK': '0022'}):
            arg_parser = create_arg_parser()
            options = arg_parser.parse_args([
                '--broker=local',
                '--site-dir=/site',
            ])

            self.assertEqual(options.umask, '0022')

    def test_num_processes_with_value(self) -> None:
        """Testing rbworker --num-processes with a value"""
        arg_parser = create_arg_parser()
        options = arg_parser.parse_args([
            '--broker=local',
            '--num-processes=4',
            '--site-dir=/site',
        ])

        self.assertEqual(options.num_processes, 4)

    def test_num_processes_with_env(self) -> None:
        """Testing rbworker --num-processes defaults to
        $RB_WORKER_NUM_PROCESSES
        """
        with self.override_env_vars({'RB_WORKER_NUM_PROCESSES': '4'}):
            arg_parser = create_arg_parser()
            options = arg_parser.parse_args([
                '--broker=local',
                '--site-dir=/site',
            ])

            self.assertEqual(options.num_processes, 4)

    def test_num_processes_with_invalid(self) -> None:
        """Testing rbworker --num-processes with an invalid value"""
        self._run_invalid_arg_test(
            [
                '--site-dir=/site',
                '--broker=local',
                '--num-processes=xxx',
            ],
            expected_message=(
                "argument --num-processes: invalid int value: 'xxx'"
            ),
        )

    def test_pool_with_value(self) -> None:
        """Testing rbworker --pool with a value"""
        arg_parser = create_arg_parser()
        options = arg_parser.parse_args([
            '--broker=local',
            '--pool=solo',
            '--site-dir=/site',
        ])

        self.assertEqual(options.pool_cls, 'solo')

    def test_pool_with_env(self) -> None:
        """Testing rbworker --pool defaults to $RB_WORKER_POOL"""
        with self.override_env_vars({'RB_WORKER_POOL': 'solo'}):
            arg_parser = create_arg_parser()
            options = arg_parser.parse_args([
                '--broker=local',
                '--site-dir=/site',
            ])

            self.assertEqual(options.pool_cls, 'solo')

    def test_pool_with_invalid(self) -> None:
        """Testing rbworker --pool with an invalid value"""
        self._run_invalid_arg_test(
            [
                '--site-dir=/site',
                '--broker=local',
                '--pool=xxx',
            ],
            expected_message=(
                "argument -P/--pool: invalid choice: 'xxx' (choose from "
                "'prefork', 'eventlet', 'gevent', 'solo', 'threads')"
            ),
        )

    def test_autoscale_with_value(self) -> None:
        """Testing rbworker --autoscale with a value"""
        arg_parser = create_arg_parser()
        options = arg_parser.parse_args([
            '--autoscale=10,3',
            '--broker=local',
            '--site-dir=/site',
        ])

        self.assertEqual(options.autoscale, '10,3')

    def test_autoscale_with_env(self) -> None:
        """Testing rbworker --autoscale defaults to $RB_WORKER_AUTOSCALE"""
        with self.override_env_vars({'RB_WORKER_AUTOSCALE': '10,3'}):
            arg_parser = create_arg_parser()
            options = arg_parser.parse_args([
                '--broker=local',
                '--site-dir=/site',
            ])

            self.assertEqual(options.autoscale, '10,3')

    def _run_invalid_arg_test(
        self,
        argv: Sequence[str],
        *,
        expected_message: str,
        expected_exit_code: int = 2,
    ) -> None:
        """Assert that calling a function raises SystemExit.

        Args:
            argv (list of str):
                The arguments to pass to the worker command.

            expected_exit_code (int, optional):
                The exit code expected from the process.

            expected_message (str, optional):
                A string that's expected to be found in standard error
                output.
        """
        with (contextlib.redirect_stderr(io.StringIO()) as stderr,
              self.assertRaises(SystemExit) as cm):
            worker_main(argv)

        if expected_message is not None:
            self.assertIn(expected_message, stderr.getvalue())

        self.assertEqual(cm.exception.code, expected_exit_code)


class MainTests(kgb.SpyAgency, TestCase):
    """Unit tests for reviewboard.worker.main.main.

    Version Added:
        9.0
    """

    ######################
    # Instance variables #
    ######################

    #: The saved Python search path to restore after the test.
    _old_sys_path: list[str]

    def setUp(self) -> None:
        """Set up state for a test.

        This will store environmental state that will be manipulated during
        the test run and avoid redundant Review Board initialization.
        """
        super().setUp()

        self.spy_on(initialize, call_original=False)

        self._old_sys_path = list(sys.path)

    def tearDown(self) -> None:
        """Tear down state for a test.

        This will restore environmental state manipulated during the test
        run.
        """
        sys.path[:] = self._old_sys_path

        super().tearDown()

    def test_run_celery_worker(self) -> None:
        """Testing rbworker runs with a Celery-based broker"""
        self.spy_on(start_celery_worker,
                    op=kgb.SpyOpReturn(0))

        with self.assertRaises(SystemExit):
            worker_main([
                '--broker=local',
                '--hostname=my-host',
                '--site-dir=/site',
            ])

        self.assertSpyCalled(start_celery_worker)
        call = self.get_spy(start_celery_worker).last_call

        self.assertEqual(call.kwargs['hostname'], 'my-host')
        self.assertIsInstance(call.kwargs['broker'], BaseCeleryBrokerBackend)
        self.assertEqual(call.kwargs['broker'].broker_id, 'local')
