"""Helpers for inspecting GitHub hosting service accounts.

GitHub App connections are spread across a few kinds of account:

* The hidden "app-record" account (role ``app``), which holds the app's
  credentials and is not used for repositories.
* "Installation" accounts (role ``installation``), one per user or organization
  the app is installed on.
* Personal Access Token accounts, which carry no ``github_app`` data.

These helpers centralize how those roles are detected, and define the models
for the ``github_app`` data stored on the accounts.

Version Added:
    9.0
"""

from __future__ import annotations

import logging
from typing import Annotated, Literal, TYPE_CHECKING, cast

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    TypeAdapter,
    ValidationError,
)
from typelets.symbols import UNSET

if TYPE_CHECKING:
    from typing import Final, TypeAlias

    from typing_extensions import TypeIs

    from reviewboard.hostingsvcs.models import HostingServiceAccount


logger = logging.getLogger(__name__)


class GitHubAppRecordData(BaseModel):
    """The ``github_app`` data stored on the hidden app-record account.

    This holds the credentials of the GitHub App, stored once and referenced
    by the installation accounts.

    The credential fields are required. Data missing any of them does not
    validate and is treated as absent. Fields GitHub may legitimately omit
    have defaults, and unknown fields are kept, so data written by a newer
    version survives a read/modify/write cycle here.

    Version Added:
        9.0
    """

    #: The GitHub App's numeric ID, used as the JWT issuer claim.
    app_id: int

    #: The URL-friendly name of the app on GitHub.
    app_slug: str

    #: The internal ID assigned to the app on GitHub.
    client_id: str

    #: The OAuth client secret.
    #:
    #: This is encrypted with :py:func:`~reviewboard.scmtools.crypto_utils.
    #: encrypt_password`.
    client_secret: str

    #: The URL to the app page on github.com.
    html_url: str = ''

    #: The app's PEM private key, Base64-encoded and then encrypted.
    #:
    #: Read this back with :py:func:`~reviewboard.hostingsvcs.github.app_auth.
    #: load_app_private_key`.
    private_key: str

    #: The username of the user or organization that the app is owned by.
    owner_login: str = ''

    #: The lowercased owner type.
    owner_type: Literal['user', 'organization', ''] = ''

    #: The account role.
    role: Literal['app'] = 'app'

    #: The webhook secret.
    #:
    #: This is encrypted with :py:func:`~reviewboard.scmtools.crypto_utils.
    #: encrypt_password`.
    webhook_secret: str

    model_config = ConfigDict(extra='allow')


class GitHubAppInstallationData(BaseModel):
    """The ``github_app`` data stored on an installation account.

    Each installation account represents the GitHub App installed on one user
    or organization. It references the app-record account for the app's
    credentials.

    The fields identifying the installation are required. Data missing any
    of them does not validate and is treated as absent. Fields GitHub may
    legitimately omit, and fields older accounts may lack, have defaults.
    Unknown fields are kept, so data written by a newer version survives a
    read/modify/write cycle here.

    Version Added:
        9.0
    """

    #: The primary key of the app-record account holding the credentials.
    app_account_id: int

    #: The installation's ID on GitHub.
    #:
    #: GitHub issues a new ID on each uninstall/reinstall.
    installation_id: int

    #: The URL to the owner's avatar image.
    owner_avatar_url: str = ''

    #: The stable numeric ID of the user or organization installed on.
    #:
    #: Unlike the login, this does not change on a rename.
    owner_id: int | None = None

    #: The username of the user or organization that the app is installed in.
    owner_login: str

    #: The lowercased owner type.
    owner_type: Literal['user', 'organization', ''] = ''

    #: Whether the app was installed on all or selected repositories.
    repository_selection: Literal['all', 'selected', ''] = ''

    #: The account role.
    role: Literal['installation'] = 'installation'

    model_config = ConfigDict(extra='allow')


#: The data stored under ``github_app`` on an account, keyed by role.
#:
#: Version Added:
#:     9.0
GitHubAppData: TypeAlias = Annotated[
    GitHubAppRecordData | GitHubAppInstallationData,
    Field(discriminator='role'),
]


#: Type adapter for decoding stored app data.
#:
#: Version Added:
#:     9.0
_github_app_data_adapter: TypeAdapter[GitHubAppData] = \
    TypeAdapter(GitHubAppData)


#: Attribute used to cache the parsed github_app data on an account.
#:
#: Version Added:
#:     9.0
_CACHE_ATTR: Final[str] = '_github_app_data_cache'


def get_github_app_data(
    account: HostingServiceAccount,
) -> GitHubAppData | None:
    """Return the GitHub App data stored on an account.

    Version Added:
        9.0

    Args:
        account (reviewboard.hostingsvcs.models.HostingServiceAccount):
            The account to read.

    Returns:
        GitHubAppRecordData or GitHubAppInstallationData:
        The parsed ``github_app`` data, or ``None`` if the account has none
        or the stored data does not validate.
    """
    cached = getattr(account, _CACHE_ATTR, UNSET)

    if cached is not UNSET:
        return cast(GitHubAppData | None, cached)

    parsed: (GitHubAppData | None) = None

    if data := account.data.get('github_app'):
        try:
            parsed = _github_app_data_adapter.validate_python(data)
        except ValidationError as e:
            logger.warning(
                'Invalid github_app data on hosting service account %s: %s',
                account.pk, e)

    setattr(account, _CACHE_ATTR, parsed)

    return parsed


def set_github_app_data(
    account: HostingServiceAccount,
    app_data: GitHubAppData,
) -> None:
    """Store GitHub App data on an account.

    Version Added:
        9.0

    Args:
        account (reviewboard.hostingsvcs.models.HostingServiceAccount):
            The account to store the data on.

        app_data (GitHubAppRecordData or GitHubAppInstallationData):
            The data to store.
    """
    account.data['github_app'] = app_data.model_dump()
    setattr(account, _CACHE_ATTR, app_data)


def get_github_app_role(
    account: HostingServiceAccount,
) -> Literal['app', 'installation'] | None:
    """Return the GitHub App role for an account.

    Version Added:
        9.0

    Args:
        account (reviewboard.hostingsvcs.models.HostingServiceAccount):
            The account to check.

    Returns:
        str:
        The role for the hosting service account (either "app" or
        "installation").
    """
    if app_data := get_github_app_data(account):
        return app_data.role
    else:
        return None


def is_app_record_data(
    app_data: GitHubAppData | None,
) -> TypeIs[GitHubAppRecordData]:
    """Return whether a github_app data instance is for an app record.

    Version Added:
        9.0

    Args:
        app_data (GitHubAppData):
            The app data stored in the hosting account.

    Returns:
        bool:
        ``True`` if the app data is for an app record. ``False`` if the app
        data did not exist or is for an installation.
    """
    return isinstance(app_data, GitHubAppRecordData)


def is_app_record_account(
    account: HostingServiceAccount,
) -> bool:
    """Return whether an account is the hidden GitHub App record.

    Version Added:
        9.0

    Args:
        account (reviewboard.hostingsvcs.models.HostingServiceAccount):
            The account to check.

    Returns:
        bool:
        ``True`` if the account holds the app's credentials. ``False``,
        otherwise.
    """
    return is_app_record_data(get_github_app_data(account))


def is_installation_data(
    app_data: GitHubAppData | None,
) -> TypeIs[GitHubAppInstallationData]:
    """Return whether a github_app data instance is for an installation.

    Args:
        app_data (GitHubAppData):
            The app data stored in the hosting account.

    Returns:
        bool:
        ``True`` if the app data is for an installation. ``False`` if the app
        data did not exist or is for an app record.
    """
    return isinstance(app_data, GitHubAppInstallationData)


def is_installation_account(
    account: HostingServiceAccount,
) -> bool:
    """Return whether an account is a GitHub App installation.

    Version Added:
        9.0

    Args:
        account (reviewboard.hostingsvcs.models.HostingServiceAccount):
            The account to check.

    Returns:
        bool:
        ``True`` if the account represents an app installation.
    """
    return is_installation_data(get_github_app_data(account))
