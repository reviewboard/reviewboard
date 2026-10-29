"""Local filesystem message broker backend.

Version Added:
    9.0
"""

from __future__ import annotations

import os
from typing import TYPE_CHECKING

from django import forms
from django.utils.translation import gettext, gettext_lazy as _

from reviewboard.admin.server import get_data_dir, get_hostname, is_nfs_path
from reviewboard.broker.base.backends import BaseCeleryBrokerBackend
from reviewboard.broker.base.forms import BaseBrokerSettingsForm

if TYPE_CHECKING:
    from typelets.json import JSONDictImmutable

    from reviewboard.broker.base.backends import BackendCeleryConfig


def _get_default_local_queue_dir() -> str:
    """Return the path to the default local queue directory.

    This directory would contain hostname-specific directories for
    local queues.

    Returns:
        str:
        The default local queue path.
    """
    return os.path.join(get_data_dir(), 'local-queue')


class LocalBrokerSettingsForm(BaseBrokerSettingsForm):
    """Settings form for the local filesystem broker.

    Version Added:
        9.0
    """

    queue_path = forms.CharField(
        label=_('Local queue path'),
        help_text=_(
            "The filesystem path used for local-only broker files. "
            "If empty, this defaults to a directory specific to this host "
            "in the site's data directory."
        ),
        required=False,
        widget=forms.TextInput(attrs={
            'size': '60',
        }),
    )

    def __init__(
        self,
        *args,
        **kwargs,
    ) -> None:
        """Initialize the form.

        Args:
            *args (tuple):
                Positional arguments passed to the form.

            **kwargs (dict):
                Keyword arguments passed to the form.
        """
        super().__init__(*args, **kwargs)

        self.fields['queue_path'].widget.attrs['placeholder'] = (
            gettext('auto: {path}')
            .format(path=os.path.join(
                _get_default_local_queue_dir(),
                '<hostname>',
            ))
        )

    class Meta:
        title = _('Local Broker Settings')

        fieldsets = (
            {
                'classes': ('wide',),
                'description': _(
                    "Review Board includes a local-only broker that can be "
                    "used on the local server. It's used to let the web "
                    "server run certain operations in the background."
                ),
                'fields': (
                    'queue_path',
                ),
            },
        )


class LocalBrokerBackend(BaseCeleryBrokerBackend):
    """A message broker backend using the local filesystem.

    This uses Kombu's ``filesystem://`` transport to store messages as files
    on the local filesystem. It's the default backend used for communication
    with worker processes, and will always be used for the built-in local
    companion worker.

    Note that this is not safe to use over NFS, and will loudly warn if it
    detects that it may be storing data on an NFS mount.

    Version Added:
        9.0
    """

    broker_id = 'local'
    name = _('Local (filesystem)')
    settings_form = LocalBrokerSettingsForm

    def check_connection(
        self,
        broker_settings: JSONDictImmutable,
        *,
        timeout_secs: (float | None) = None,
    ) -> None:
        """Check that the broker can be used with the provided settings.

        There's no server to connect to for the local broker. Instead, this
        checks that the queue path is an absolute path to a directory that
        Review Board can write to. If the directory doesn't exist yet, the
        closest existing parent directory must be writable, so that it can
        be created.

        If a queue path isn't configured, the default path is specific to
        each server's hostname. In that case, the shared
        :file:`local-queue` directory in the site data directory is checked.

        Nothing will be written to the filesystem from this check.

        Args:
            broker_settings (dict):
                The broker settings to check.

            timeout_secs (float, unused):
                The maximum amount of time to spend trying to connect.

        Raises:
            ValueError:
                The queue path can't be used.
        """
        queue_path = broker_settings.get('queue_path')

        if queue_path and isinstance(queue_path, str):
            # An explicit path was configured. Check that.
            if not os.path.isabs(queue_path):
                raise ValueError(
                    _('The queue path "{path}" must be an absolute path.')
                    .format(path=queue_path)
                )

            check_path = queue_path
        else:
            # No explicit path was chosen, so we'll go with the default.
            # For the connection check, we'll just look at the shared
            # local-queue directory, since the hostname-specific directory
            # under it may be for another server.
            check_path = _get_default_local_queue_dir()

        if os.path.exists(check_path):
            if not os.path.isdir(check_path):
                raise ValueError(
                    _('"{path}" is not a directory.')
                    .format(path=check_path)
                )
        else:
            # Find the closest parent directory that exists, since that's
            # where the queue directories will be created.
            check_path = os.path.dirname(check_path)

            while not os.path.exists(check_path):
                check_path = os.path.dirname(check_path)

        # Check if that path is writable.
        if not os.access(check_path, os.W_OK | os.X_OK):
            raise ValueError(
                _(
                    'Review Board does not have permission to write to '
                    '"{path}".'
                ).format(path=check_path)
            )

    def get_celery_config(
        self,
        broker_settings: JSONDictImmutable,
    ) -> BackendCeleryConfig:
        """Return configuration for the Celery app.

        This will ensure that the configured or default local queue
        directories exist and return them as options for Celery.

        If the queue path appears to be on NFS and Review Board is running
        on Linux, this will warn loudly in the logs.

        Args:
            broker_settings (dict):
                The stored settings for the broker.

        Returns:
            reviewboard.broker.base.backends.BackendCeleryConfig:
            The configuration settings for Celery.
        """
        # Use the configured queue path, falling back on a path in the
        # data directory. This may end up being an NFS mount on some
        # systems, so we'll have to check for that.
        queue_path = broker_settings.get('queue_path')

        if queue_path and not isinstance(queue_path, str):
            self.logger.error('queue_path broker setting is a %s, but should '
                              'be a string! Falling back to a default path.',
                              type(queue_path))
            queue_path = None

        if not queue_path:
            queue_path = os.path.join(_get_default_local_queue_dir(),
                                      get_hostname())

        assert isinstance(queue_path, str)

        if is_nfs_path(queue_path):
            # There may be issues using this on NFS. Warn loudly and
            # recommend an alternative approach.
            self.logger.warning(
                'The local broker queue path "%s" appears to be on an NFS '
                'mount. This may cause reliability issues, including '
                'message corruption or deadlocks. Please configure the '
                'queue path to a directory on the local filesystem, or '
                'switch to a dedicated broker service such as RabbitMQ.',
                queue_path,
            )

        # Create the directories if they don't already exist.
        control_path = os.path.join(queue_path, 'control')

        os.makedirs(queue_path, 0o700,
                    exist_ok=True)
        os.makedirs(control_path, 0o700,
                    exist_ok=True)

        self.logger.debug('Using local filesystem broker at %s', queue_path)

        return {
            'app_config': {
                'broker_transport_options': {
                    'control_folder': control_path,
                    'data_folder_in': queue_path,
                    'data_folder_out': queue_path,
                },
                'broker_url': 'filesystem://',
            },
        }
