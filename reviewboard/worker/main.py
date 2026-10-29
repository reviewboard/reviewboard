"""Main command line handler for the Review Board worker.

Version Added:
    9.0
"""

from __future__ import annotations

import argparse
import os
import socket
import sys
from typing import TYPE_CHECKING

# NOTE: Nothing in this function can import from anything within Django
#       or Review Board (outside of the top-level module), since the
#       environment is not yet set up.
from reviewboard import get_version_string, initialize

if TYPE_CHECKING:
    from collections.abc import Sequence


def create_arg_parser() -> argparse.ArgumentParser:
    """Create an argument parser for Review Board.

    Version Added:
        9.0

    Returns:
        argparse.ArgumentParser:
        The argument parser for Review Board.
    """
    # NOTE: Nothing in this function can import from anything within Django
    #       or Review Board, since the environment is not yet set up.

    rb_version = get_version_string()
    py_version = '%s.%s' % sys.version_info[:2]

    # Add the common options.
    arg_parser = argparse.ArgumentParser(
        description=(
            'Run the Review Board worker, connecting to a message broker.'
        ))
    arg_parser.add_argument(
        '-v',
        '--version',
        action='version',
        version=f'Review Board {rb_version} (Python {py_version})',
    )

    arg_parser.add_argument(
        '--site-dir',
        required=os.environ.get('RB_WORKER_SITE_DIR') is None,
        default=os.environ.get('RB_WORKER_SITE_DIR'),
        help=(
            'The path to the Review Board site directory. This is '
            'required, either as an argument or through the environment '
            'variable. [$RB_WORKER_SITE_DIR]'
        ))
    arg_parser.add_argument(
        '-b',
        '--broker',
        metavar='BROKER_ID',
        required=os.environ.get('RB_WORKER_BROKER') is None,
        default=os.environ.get('RB_WORKER_BROKER'),
        help=(
            'The ID of the message broker to use. This is required, '
            'either as an argument or through the environment variable. '
            '[$RB_WORKER_BROKER]'
        ),
    )
    arg_parser.add_argument(
        '-n',
        '--hostname',
        default=(
            os.environ.get('RB_WORKER_HOSTNAME') or
            f'reviewboard@{socket.gethostname()}'
        ),
        help=(
            'A custom hostname to set when communicating with the message '
            'queue. This can be a format string with: %%h (fully-qualified '
            'hostname: name.domain), %%n (name-only part of hostname), '
            '%%d (domain part of hostname). [$RB_WORKER_HOSTNAME]'
        ))

    # Logging option group.
    group = arg_parser.add_argument_group('Logging')
    group.add_argument(
        '-l',
        '--log-level',
        default=os.environ.get('RB_WORKER_LOG_LEVEL') or 'INFO',
        choices=(
            'DEBUG',
            'INFO',
            'WARNING',
            'ERROR',
            'CRITICAL',
            'FATAL',
        ),
        help='The minimum logging level [$RB_WORKER_LOG_LEVEL].',
    )
    group.add_argument(
        '-f',
        '--log-file',
        metavar='PATH',
        default=os.environ.get('RB_WORKER_LOG_FILE'),
        help=(
            'The path to the log file to write to. If not specified, all '
            'logging will be to stderr. [$RB_WORKER_LOG_FILE]'
        ))

    # Daemonization option group.
    group = arg_parser.add_argument_group('Daemonization')
    group.add_argument(
        '-D',
        '--detach',
        action='store_true',
        help=(
            'Detach the worker process, running in the background.'
        ),
    )
    group.add_argument(
        '--pid-file',
        metavar='PATH',
        default=os.environ.get('RB_WORKER_PID_FILE'),
        help=(
            'Path to a file to store the PID of the process. If this file '
            'exists and contains the PID of a running process, Review Bot '
            'will not start. [$RB_WORKER_PID_FILE]'
        ),
    )
    group.add_argument(
        '--uid',
        type=int,
        default=os.environ.get('RB_WORKER_UID'),
        help=(
            'The user ID or username to run as after detaching. '
            '[$RB_WORKER_UID]'
        ),
    )
    group.add_argument(
        '--gid',
        type=int,
        default=os.environ.get('RB_WORKER_GID'),
        help=(
            'The group ID or name to run as after detaching.'
            '[$RB_WORKER_GID]'
        ),
    )
    group.add_argument(
        '--umask',
        default=os.environ.get('RB_WORKER_UMASK'),
        help=(
            "The effective umask (in octal format) of the process to use "
            "after detaching. By default, the parent process's umask is "
            "used. [$RB_WORKER_UMASK]"
        ),
    )

    # Message/Process Handling option group.
    group = arg_parser.add_argument_group('Message/Process Handling')
    group.add_argument(
        '--num-processes',
        metavar='NUM_PROCESSES',
        type=int,
        default=os.environ.get('RB_WORKER_NUM_PROCESSES'),
        help=(
            'The number of child processes used to process the message '
            'queue. The default is the number of CPUs on your system. '
            '[$RB_WORKER_NUM_PROCESSES]'
        ),
    )
    group.add_argument(
        '-P',
        '--pool',
        dest='pool_cls',
        choices=(
            'prefork',
            'eventlet',
            'gevent',
            'solo',
            'threads',
        ),
        default=os.environ.get('RB_WORKER_POOL'),
        help=(
            'The pool implementation. prefork is the default, and is '
            'recommended. [$RB_WORKER_POOL]'
        ),
    )
    group.add_argument(
        '--autoscale',
        metavar='MIN,MAX',
        default=os.environ.get('RB_WORKER_AUTOSCALE'),
        help=(
            'Enable auto-scaling of workers. The value is in the form of '
            'max_concurrency,min_concurrency. For example, --autoscale=10,3 '
            'will keep 3 proceses, but grow to 10 if needed. '
            '[$RB_WORKER_AUTOSCALE]'
        ))

    return arg_parser


def main(
    argv: Sequence[str] = sys.argv[1:],
) -> None:
    """Run the Review Board worker process.

    Version Added:
        9.0

    Args:
        argv (list):
            All command line arguments passed to Review Bot.
    """
    # First, parse the command line options/environment variables. These
    # do not depend on an established Review Board environment.
    arg_parser = create_arg_parser()
    options = arg_parser.parse_args(argv)

    # Now that we've parsed this, set up the Review Board environment.
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'reviewboard.settings')
    sys.path.insert(0, options.site_dir)

    # Initialize Review Board.
    #
    # TODO: Set up explicit logging.
    initialize(setup_logging=False)

    from reviewboard.broker.base.backends import BaseCeleryBrokerBackend
    from reviewboard.broker.registry import broker_registry
    from reviewboard.worker.celery_worker import start_celery_worker

    # Load the configured message broker backend.
    broker_cls = broker_registry.get_broker(options.broker)

    if broker_cls is None:
        arg_parser.error(
            f'Invalid broker ID provided for --broker: {options.broker}'
        )
    elif not issubclass(broker_cls, BaseCeleryBrokerBackend):
        # This really shouldn't happen unless someone builds a custom
        # broker. This is not supported at this time.
        arg_parser.error(
            'The broker ID provided for --broker is not a Celery-based '
            'broker. This is not supported by the Review Board worker.'
        )

    # Instantiate the broker backend.
    broker = broker_cls()

    # Start the worker.
    sys.exit(start_celery_worker(
        autoscale=options.autoscale,
        broker=broker,
        detach=options.detach,
        gid=options.gid,
        hostname=options.hostname,
        log_file=options.log_file,
        log_level=options.log_level,
        num_processes=options.num_processes,
        pid_file=options.pid_file,
        pool=options.pool_cls,
        site_dir=options.site_dir,
        uid=options.uid,
        umask=options.umask,
    ))


if __name__ == '__main__':
    main()
