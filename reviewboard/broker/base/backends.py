"""Base class for message broker backends.

Version Added:
    9.0
"""

from __future__ import annotations

import logging
import threading
from typing import Literal, TYPE_CHECKING, TypedDict, final

from celery import Celery
from celery.utils.nodenames import nodesplit
from djblets.log import log_timed
from djblets.siteconfig.models import SiteConfiguration

if TYPE_CHECKING:
    from collections.abc import Mapping, Sequence
    from typing import Any, ClassVar, NotRequired, TypeAlias

    from typelets.django.strings import StrOrPromise
    from typelets.funcs import KwargsDict
    from typelets.json import JSONDict, JSONDictImmutable

    from reviewboard.broker.base.forms import BaseBrokerSettingsForm


logger = logging.getLogger(__name__)


#: The status code from a worker scan result.
#:
#: Version Added:
#:     9.0
ScanWorkersResultStatus: TypeAlias = Literal['ok', 'error']


class BackendCeleryConfig(TypedDict):
    """Backend-managed configuration to set for Celery.

    Version Added:
        9.0
    """

    #: The Celery app configuration settings.
    app_config: Mapping[str, Any]

    #: Additional keyword arguments for the Celery instance.
    celery_kwargs: NotRequired[KwargsDict]


class ScannedWorker(TypedDict):
    """Information on a scanned worker connected to the broker.

    Version Added:
        9.0
    """

    #: The worker's reported hostname.
    hostname: str

    #: The full worker name.
    worker: str

    #: An error message set if the worker returns an unexpected response.
    #:
    #: This may include error data from the worker's response (if the
    #: ``error`` key is set in the response payload), or it may contain
    #: general guidance.
    error: NotRequired[str]


class ScanWorkersResult(TypedDict):
    """Results from scanning workers connected to the broker.

    Version Added:
        9.0
    """

    #: The status of the scan.
    status: ScanWorkersResultStatus

    #: The list of workers found during the scan.
    #:
    #: This is in the order in which workers responded to the scan. It will
    #: be empty if :py:attr:`status` is "error".
    workers: Sequence[ScannedWorker]

    #: An error message indicating why the scan failed.
    #:
    #: This is only set of :py:attr:`status` is "error".
    error: NotRequired[str]


class BaseBrokerBackend:
    """Base class for a Review Board message broker backend.

    Message brokers are used for asynchronous task management. A task can be
    invoked on a broker, handled immediately or at a later point by any
    number of external workers, and then a response can later be processed by
    Review Board.

    Broker backends don't dictate how tasks are constructed, registered, or
    handled, either on the Review Board or worker side. They're simply
    responsible for connecting to the broker and putting named tasks in a
    queue.

    Messages placed in the queue use the Celery protocol v2 format, documented
    at https://docs.celeryq.dev/en/stable/internals/protocol.html.

    Byte strings, dates/times, decimals, and UUIDs are all serialized
    specially. Celery-based brokers and workers will handle these natively.
    Custom broker backends and workers will need to take care to support
    Kombu's serialization logic (see :py:mod:`kombu.utils.json`) and the
    protocol format.

    Subclasses are responsible for defining the configuration for the broker
    and handling all communication and task operations.

    Most subclasses will want to inherit from
    :py:class:`BaseCeleryBrokerBackend` instead.

    Version Added:
        9.0
    """

    #: The unique ID for the broker backend.
    #:
    #: This identifies this broker backend within Review Board, and not
    #: the underlying transport.
    #:
    #: This should be in :term:`slug` format.
    broker_id: str = ''

    #: The default timeout for connection checks on this broker backend.
    default_check_connection_timeout_secs: ClassVar[float] = 5.0

    #: The default timeout for worker scans on this broker backend.
    default_scan_timeout_secs: ClassVar[float] = 1.0

    #: The display name for the broker backend.
    #:
    #: This will be shown in the list of backends in the administration UI.
    name: StrOrPromise = ''

    #: The form class used for configuring this broker's settings.
    #:
    #: A form should always be supplied, and is required in order for the
    #: admin UI configuration form to check new broker settings by
    #: establishing a connection.
    settings_form: (type[BaseBrokerSettingsForm] | None) = None

    ######################
    # Instance variables #
    ######################

    #: The logger used for this broker.
    logger: logging.Logger

    @classmethod
    def get_broker_settings(cls) -> JSONDict:
        """Return mutable site configuration settings for the broker.

        If there's any issue validating the settings storage for the broker,
        an error will be logged and state will be reset.

        The result is guaranteed to be a valid broker settings dictionary
        present in siteconfig. If state had to be added or repaired, it will
        not be persisted to the database until the siteconfig is saved.

        Returns:
            dict:
            The stored broker settings.
        """
        siteconfig = SiteConfiguration.objects.get_current()
        broker_id = cls.broker_id
        was_corrupt = False

        brokers_settings = siteconfig.settings.setdefault('brokers', {})

        if not isinstance(brokers_settings, dict):
            # There was something other than a dict stored. Heal it and
            # prepare to log.
            brokers_settings = {}
            siteconfig.settings['brokers'] = brokers_settings
            was_corrupt = True

        broker_settings = brokers_settings.setdefault(broker_id, {})

        if not isinstance(broker_settings, dict):
            # There was something other than a dict stored. Heal it and
            # prepare to log.
            broker_settings = {}
            brokers_settings[broker_id] = broker_settings
            was_corrupt = True

        if was_corrupt:
            # Settings were corrupted and have been fixed. Log this.
            logger.error(
                'The configuration for broker %r was corrupt and had to be '
                'reset. You may need to reconfigure your broker in '
                'Admin UI -> Background Tasks.',
                broker_id,
            )

        return broker_settings

    def __init__(self) -> None:
        """Initialize the broker backend."""
        self.logger = logging.getLogger(f'{__name__}.{type(self).__name__}')

    def shutdown(self) -> None:
        """Shut down the message broker communication.

        Subclasses can override this to clean up state for the message broker
        and close any communication. They're responsible for opening
        communication again on demand when :py:meth:`broadcast` or
        :py:meth:`send_task` are used.

        By default, this does nothing.
        """
        pass

    def check_connection(
        self,
        broker_settings: JSONDictImmutable,
        *,
        timeout_secs: (float | None) = None,
    ) -> None:
        """Check that the broker can be reached using the provided settings.

        This is used to test new settings before they're saved. It won't
        affect any existing connection to the broker.

        By default, this does nothing. Subclasses can override this to
        connect to the broker and report any problems.

        Args:
            broker_settings (dict):
                The broker settings to check.

            timeout_secs (float, optional):
                The maximum amount of time to spend trying to connect, in
                seconds.

                If not provided, the backend's default timeout will be used.

        Raises:
            Exception:
                The broker couldn't be reached with these settings.

                This may be a backend-specific error. Callers should catch
                all exceptions.
        """
        pass

    def scan_workers(
        self,
        *,
        timeout_secs: (float | None) = None,
    ) -> ScanWorkersResult:
        """Perform a scan for all active workers connected to the broker.

        Args:
            timeout_secs (float, optional):
                The amount of time to wait for a result in seconds.

                If not provided, the backend's default timeout will be used.

        Returns:
            ScanWorkersResult:
            The result from the scan.
        """
        raise NotImplementedError

    def broadcast(
        self,
        command: str,
        command_args: KwargsDict,
    ) -> None:
        """Broadcast a message across the queue.

        This will be sent to all workers listening to this queue, allowing
        each to handle the request and individually respond if appropriate.

        Args:
            command (str):
                The command to dispatch.

            command_args (dict):
                Keyword arguments to send for the command.

        Raises:
            Exception:
                Something went wrong during broadcast.

                This may be a backend-specific error. Callers should catch
                all exceptions.
        """
        raise NotImplementedError

    def send_task(
        self,
        command: str,
        command_args: KwargsDict,
        *,
        queue: str,
    ) -> None:
        """Send a task to the queue for processing by a worker.

        This will be placed on the queue, and the first worker to process
        it will claim it.

        Tasks are comprised of a command identifier, any arguments for that
        command, and the name of the specific queue to send to. Workers
        can implement the task handling infrastructure however they see fit.

        .. warning::

           There is no guaranteed response time for tasks, and in fact a
           worker may never pick up the task if there are communication
           problems, broker problems, or downed workers.

        Args:
            command (str):
                The command to dispatch.

            command_args (dict):
                Keyword arguments to send for the command.

            queue (str):
                The name of the queue to send the task to.

        Raises:
            Exception:
                Something went wrong during sending the task.

                This may be a backend-specific error. Callers should catch
                all exceptions.
        """
        raise NotImplementedError


class BaseCeleryBrokerBackend(BaseBrokerBackend):
    """Base class for a Celery-based Review Board message broker backend.

    Message brokers are used for asynchronous task management. A task can be
    invoked on a broker, handled immediately or at a later point by any
    number of external workers, and then a response can later be processed by
    Review Board.

    Celery is the primary method of communicating with a message broker.
    Subclasses can automatically leverage Celery for communication, providing
    only the configuration required for the transport.

    Version Added:
        9.0
    """

    ######################
    # Instance variables #
    ######################

    #: The managed Celery instance.
    _celery: Celery | None

    #: A lock for managing internal connection state.
    _lock: threading.Lock

    def __init__(self) -> None:
        """Initialize the broker."""
        super().__init__()

        self._celery = None
        self._lock = threading.Lock()

    def shutdown(self) -> None:
        """Shut down the message broker communication.

        The Celery instance will be immediately shut down and destroyed.
        Further communication will result in a new instance being created.
        """
        with self._lock:
            if (celery := self._celery) is not None:
                celery.close()
                self._celery = None

    def check_connection(
        self,
        broker_settings: JSONDictImmutable,
        *,
        timeout_secs: (float | None) = None,
    ) -> None:
        """Check that the broker can be reached using the provided settings.

        This will build a temporary Celery instance using the provided
        settings and make a single attempt to connect to the broker. The
        broker's existing Celery instance won't be touched.

        Args:
            broker_settings (dict):
                The broker settings to check.

            timeout_secs (float, optional):
                The maximum amount of time to spend trying to connect, in
                seconds.

                If not provided, the backend's default timeout will be used.

        Raises:
            Exception:
                The broker couldn't be reached with these settings.

                This may be a backend-specific error. Callers should catch
                all exceptions.
        """
        if timeout_secs is None:
            timeout_secs = self.default_check_connection_timeout_secs

        app = self._build_celery(broker_settings=broker_settings)
        conn = app.connection_for_write(connect_timeout=timeout_secs)

        try:
            conn.ensure_connection(
                max_retries=0,
                timeout=timeout_secs,
            )
        finally:
            conn.release()
            app.close()

    def scan_workers(
        self,
        *,
        timeout_secs: (float | None) = None,
    ) -> ScanWorkersResult:
        """Perform a scan for all active workers connected to the broker.

        Args:
            timeout_secs (float, optional):
                The amount of time to wait for a result in seconds.

                If not provided, a timeout of 10 seconds will be used.

        Returns:
            ScanWorkersResult:
            The result from the scan.
        """
        if timeout_secs is None:
            timeout_secs = self.default_scan_timeout_secs

        try:
            ping_result = self.get_celery().control.ping(timeout=timeout_secs)

            workers: list[ScannedWorker] = []
            status: ScanWorkersResultStatus = 'ok'

            for item in ping_result:
                for worker_host, data in item.items():
                    hostname = nodesplit(worker_host)[1]
                    worker_response = data.get('ok')

                    if worker_response == 'pong':
                        workers.append({
                            'hostname': hostname,
                            'worker': worker_host,
                        })
                    else:
                        response_error = data.get('error')

                        if response_error:
                            error_msg = (
                                f'Unexpected result when querying worker '
                                f'status for {worker_host}: '
                                f'"{response_error}". Please check the '
                                f'worker\'s logs for more information.'
                            )
                        else:
                            error_msg = (
                                f"Unexpected result when querying worker "
                                f"status for {worker_host}. Please check "
                                f"the worker's logs for more information."
                            )

                        status = 'error'
                        workers.append({
                            'error': error_msg,
                            'hostname': hostname,
                            'worker': worker_host,
                        })

            return {
                'status': status,
                'workers': workers,
            }
        except Exception as e:
            logger.exception('Unexpected error perrforming a worker scan: %s',
                             e)

            return {
                'error': f'Unable to perform a worker scan: {e}',
                'status': 'error',
                'workers': [],
            }

    def broadcast(
        self,
        command: str,
        command_args: KwargsDict,
    ) -> None:
        """Broadcast a message across the queue.

        This will be sent to all workers listening to this queue, allowing
        each to handle the request and individually respond if appropriate.

        Args:
            command (str):
                The command to dispatch.

            command_args (dict):
                Keyword arguments to send for the command.
        """
        with log_timed(f'Broadcasting message {command!r} to workers',
                       logger=self.logger):
            self.get_celery().control.broadcast(
                command,
                arguments=command_args,
                reply=False,
            )

    def send_task(
        self,
        command: str,
        command_args: KwargsDict,
        *,
        queue: str,
    ) -> None:
        """Send a task to the queue for processing by a worker.

        This will be placed on the queue, and the first worker to process
        it will claim it.

        Tasks are comprised of a command identifier, any arguments for that
        command, and the name of the specific queue to send to. Workers
        can implement the task handling infrastructure however they see fit.

        .. warning::

           There is no guaranteed response time for tasks, and in fact a
           worker may never pick up the task if there are communication
           problems, broker problems, or downed workers.

        Args:
            command (str):
                The command to dispatch.

            command_args (dict):
                Keyword arguments to send for the command.

            queue (str):
                The name of the queue to send the task to.
        """
        with log_timed(f'Sending task {command!r} to workers on queue '
                       f'{queue!r}',
                       logger=self.logger):
            self.get_celery().send_task(
                command,
                kwargs=command_args,
                queue=queue,
            )

    def get_celery_config(
        self,
        broker_settings: JSONDictImmutable,
    ) -> BackendCeleryConfig:
        """Return configuration for the Celery app.

        This returns the backend, configuration settings, and any other
        Celery keyword arguments needed to set up the connection.

        This must be implemented by subclasses.

        Args:
            broker_settings (dict):
                The stored settings for the broker.

        Returns:
            BackendCeleryConfig:
            The configuration for Celery.
        """
        raise NotImplementedError

    @final
    def get_celery(self) -> Celery:
        """Return a configured Celery instance.

        If a Celery instance doesn't already exist, a new one will be built
        and configured using settings provided by
        :py:meth:`get_celery_config`, which must be implemented by the
        subclass.

        Subclasses must not override this method.

        Returns:
            celery.Celery:
            The new Celery instance for this broker.
        """
        app = self._celery

        if app is None:
            # There's no Celery instance, so acquire a thread lock and try
            # to build one.
            with self._lock:
                # Now that we've acquired the lock, check if another thread
                # succeeded in building a Celery instance.
                app = self._celery

                if app is None:
                    # It has not, so build our own and set it.
                    app = self._build_celery()
                    self._celery = app

        return app

    @final
    def _build_celery(
        self,
        *,
        broker_settings: (JSONDictImmutable | None) = None,
    ) -> Celery:
        """Build a new configured Celery instance.

        The instance's configuration will be populated using
        :py:meth:`get_celery_config`.

        Subclasses must not override this method.

        Args:
            broker_settings (dict, optional):
                The broker settings to build the instance with.

                If not provided, the stored settings will be used.

        Returns:
            celery.Celery:
            The new Celery instance for this broker.
        """
        if broker_settings is None:
            broker_settings = self.get_broker_settings()

        celery_config = self.get_celery_config(broker_settings)

        # Create the instance locally using the above settings. Do NOT
        # set this as a global instance.
        app = Celery(
            'reviewboard',
            set_as_current=False,
            **celery_config.get('celery_kwargs', {})
        )
        app.config_from_object(celery_config['app_config'])
        app.conf.task_serializer = 'json'

        return app
