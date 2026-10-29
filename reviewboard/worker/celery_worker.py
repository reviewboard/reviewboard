"""Celery worker process management.

Version Added:
    9.0
"""

from __future__ import annotations

import sys
import textwrap
from typing import TYPE_CHECKING

from celery import (
    __version__ as celery_version,
    concurrency as celery_concurrency,
    maybe_patch_concurrency,
)
from celery.bin.worker import detach as detach_process
from celery.platforms import maybe_drop_privileges
from celery.signals import celeryd_after_setup, celeryd_init
from kombu import Exchange, Queue

from reviewboard._version import get_version_string

if TYPE_CHECKING:
    from celery.app.utils import Settings as CelerySettings
    from celery.apps.worker import Worker

    from reviewboard.broker.base.backends import BaseCeleryBrokerBackend


@celeryd_init.connect
def setup_worker_logging(instance, conf, **kwargs):
    """Set up logging for Celery and Review Bot.

    This will configure the log formats we want Celery to use. This differs
    from Celery's defaults not just in the structure of the log entries, but
    also in the addition of the logger name (used to identify different
    tools).

    Args:
        instance (celery.app.base.Celery):
            The Celery instance.

        conf (celery.app.utils.Settings):
            The Celery configuration.

        **kwargs (dict, unused):
            Additional keyword arguments passed to the signal.
    """
    log_format = (
        '%(asctime)s - [%(levelname)s] %(name)s: %(message)s'
    )

    task_log_format = (
        '%(asctime)s - %(processName)s: %(task_name)s(%(task_id)s) - '
        '[%(levelname)s] %(name)s: %(message)s'
    )

    conf.update({
        'worker_log_format': log_format,
        'worker_task_log_format': task_log_format,
    })


@celeryd_after_setup.connect
def _on_after_celery_worker_setup(
    instance: Worker,
    conf: CelerySettings,
    **kwargs,
) -> None:
    """Set up Celery and output a welcome message.

    This will set up the queues used for the worker and then output
    inforamtion detailing the connection setup to aid in diagnostics.

    Args:
        instance (celery.apps.worker.Worker):
            The Celery instance.

        conf (celery.app.utils.Settings):
            The Celery configuration.

        **kwargs (dict, unused):
            Additional keyword arguments passed to the signal.
    """
    app = instance.app
    assert app is not None

    # Set up the common worker configuration.
    conf.accept_content = ['json']

    # Set up the default queues.
    #
    # TODO: Support extension-provided queues.
    queues = [
        Queue(
            queue_name,
            Exchange(queue_name, type='direct'),
            routing_key=queue_name,
        )
        for queue_name in (
            'celery',
            'reviewboard.local',
        )
    ]

    app.amqp.queues = queues

    # Write out some instructions to stdout.
    connection_uri = app.connection().as_uri()
    hostname = instance.hostname
    width = 75
    rb_version = get_version_string()

    s = [
        '',
        '=' * width,
        '',
        'Welcome!',
        '',
        f'This is the Review Board worker v{rb_version}, running on:',
        '',
        f'  Python v{sys.version}',
        f'  Celery v{celery_version}',
        '',
        textwrap.fill(
            f'Connecting to {connection_uri} as {hostname}.',
            width=width,
        ),
        '',
        'The following task queues will be managed:',
        '',
        *[
            f'  * {queue.name}'
            for queue in queues
        ],
        '',
        '=' * width,
        '',
    ]

    print('\n'.join(s))


def start_celery_worker(
    *,
    broker: BaseCeleryBrokerBackend,
    hostname: str,
    site_dir: str,
    log_level: (str | None) = None,
    log_file: (str | None) = None,
    detach: bool = False,
    pid_file: (str | None) = None,
    uid: (int | None) = None,
    gid: (int | None) = None,
    umask: (str | None) = None,
    num_processes: (int | None) = None,
    pool: (str | None) = None,
    autoscale: (str | None) = None,
) -> int:
    """Start the Celery-based Review Board worker.

    This will take in the requested arguments and start the worker, running
    either in the current process or in a detached process.

    This also takes care to patch the concurrency module, as per Celery's
    requirements, and to drop privileges if needed.

    Version Added:
        9.0

    Args:
        broker (reviewboard.broker.base.backends.BaseCeleryBrokerBackend):
            The broker backend instance used for communication.

        hostname (str):
            The local hostname the worker will identify as when talking to
            the broker.

        site_dir (str):
            The site directory owning the Review Board install.

        log_level (str):
            The minimum log level to pass to Celery.

        log_file (str):
            The path to a log file to write to.

        detach (bool):
            Whether to run the worker in a detached process.

        pid_file (str):
            The path to a PID file to write to when detaching.

        uid (int):
            The user ID to use when detaching.

        gid (int):
            The group ID to use when detaching.

        umask (str):
            The umask (in octal string format) to use for the process when
            detaching.

        num_processes (int):
            The number of concurrent processes to run.

        pool (str):
            The pool implementation.

        autoscale (str):
            The autoscale settings, in the form of
            ``max_concurrency,min_concurrency``.

    Returns:
        int:
        The worker's exit code.
    """
    # First thing to do is trigger a patch to the concurrency modules.
    # Normally, Celery will do this but ONLY if executing from the main
    # 'celery' command or through 'execute_from_commandline' (which we can't
    # use -- see below).
    maybe_patch_concurrency()

    # Check if we need to/can drop privileges, and do so.
    maybe_drop_privileges(uid=uid,
                          gid=gid)

    # Get the underlying Celery connection and prepare to launch the worker.
    broker_celery = broker.get_celery()

    if detach:
        # Some options are passed to detach() directly. Some are passed as
        # command line arguments. Some are both.
        detach_argv = [sys.argv[0]] + [
            f'--{name}={value}'
            for name, value in (
                ('autoscale', autoscale),
                ('broker', broker.broker_id),
                ('num-processes', num_processes),
                ('hostname', hostname),
                ('log-file', log_file),
                ('log-level', log_level),
                ('pid-file', pid_file),
                ('pool', pool),
                ('site-dir', site_dir),
            )
            if value is not None
        ]

        return detach_process(
            app=broker_celery,
            path=sys.executable,
            argv=detach_argv,
            logfile=log_file,
            pidfile=pid_file,
            uid=uid,
            gid=gid,
            umask=umask,
            executable=sys.executable,
            hostname=hostname,
        )
    else:
        pool_cls = (
            celery_concurrency.get_implementation(pool) or
            broker_celery.conf.CELERYD_POOL
        )

        worker = broker_celery.Worker(
            hostname=hostname,
            loglevel=log_level,
            logfile=log_file,
            detach=detach,
            pidfile=pid_file,
            uid=uid,
            gid=gid,
            umask=umask,
            concurrency=autoscale,
            pool_cls=pool_cls,
            autoscale=autoscale,
            quiet=True,
        )

        worker.start()

        return worker.exitcode
