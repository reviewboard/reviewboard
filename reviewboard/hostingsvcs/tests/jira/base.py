"""Base class for JIRA tests.

Version Added:
    9.0:
    Split up ``reviewboard.hostingsvcs.test_jira``.
"""

from __future__ import annotations

from types import SimpleNamespace
from typing import TYPE_CHECKING

import reviewboard.hostingsvcs.jira.service as jira_module
from reviewboard.hostingsvcs.testing import HostingServiceTestCase

if TYPE_CHECKING:
    from collections.abc import Mapping, Sequence
    from typing import Any

    from reviewboard.hostingsvcs.models import ConfiguredBugTracker


class FakeJIRAError(Exception):
    """A stand-in for jira.exceptions.JIRAError."""

    def __init__(
        self,
        text: str = '',
        status_code: (int | None) = None,
    ) -> None:
        """Initialize the error."""
        super().__init__(text)

        self.text = text
        self.status_code = status_code


class FakeRequestError(Exception):
    """A stand-in for requests.RequestException."""


class FakeJIRAIssue:
    """A stand-in for a JIRA issue."""

    def __init__(
        self,
        key: str,
        summary: str,
        status: str,
    ) -> None:
        """Initialize the issue."""
        self.key = key
        self.fields = SimpleNamespace(
            description='',
            summary=summary,
            status=status,
        )


class FakePickerResponse:
    """A stand-in for a response from JIRA's issue picker."""

    def __init__(
        self,
        keys: Sequence[str] = (),
    ) -> None:
        """Initialize the response.

        Args:
            keys (list of str, optional):
                The issue keys the picker matched.
        """
        self.keys = keys

    def raise_for_status(self) -> None:
        """Do nothing, since the request succeeded."""

    def json(self) -> dict[str, Any]:
        """Return the response payload."""
        return {
            'sections': [
                {
                    'id': 'cs',
                    'issues': [
                        {
                            'key': key,
                        }
                        for key in self.keys
                    ],
                },
            ],
        }


class FakeSession:
    """A stand-in for the HTTP session used by the JIRA client."""

    def get(
        self,
        url: str,
        params: Mapping[str, str],
    ) -> FakePickerResponse:
        """Return a response with no matches."""
        return FakePickerResponse()


class FakeJIRAClient:
    """A stand-in for jira.client.JIRA.

    The methods return empty results. Tests spy on them to provide
    results or errors.
    """

    def __init__(
        self,
        options: Mapping[str, Any],
        max_retries: int,
        timeout: float,
        basic_auth: (tuple[str, str] | None) = None,
    ) -> None:
        """Initialize the client."""
        self.options = options
        self.basic_auth = basic_auth
        self.timeout = timeout
        self._session = FakeSession()

    def myself(self) -> dict[str, Any]:
        """Return the authenticated user."""
        return {}

    def issue(
        self,
        id: str,
        fields: (str | None) = None,
    ) -> FakeJIRAIssue:
        """Return a single issue, or raise if it does not exist."""
        raise FakeJIRAError(
            text=f'Issue {id} does not exist',
            status_code=404,
        )

    def search_issues(
        self,
        jql: str,
        maxResults: int,  # noqa: N803
        validate_query: bool = True,
        fields: (str | None) = None,
    ) -> list[FakeJIRAIssue]:
        """Return search results."""
        return []


_UNSET = object()


def _restore_module_attr(
    attr: str,
    value: object,
) -> None:
    """Restore an attribute on the JIRA hosting service module.

    Args:
        attr (str):
            The name of the attribute.

        value (object):
            The original value, or ``_UNSET`` if the attribute did not exist.
    """
    if value is _UNSET:
        delattr(jira_module, attr)
    else:
        setattr(jira_module, attr, value)


class JIRATestCase(HostingServiceTestCase[jira_module.JIRA]):
    """Base class for JIRA unit tests.

    This handles mocking for the ``jira`` package.

    Version Added:
        9.0
    """

    service_name = 'jira'
    default_hosting_url = 'https://jira.example.com'

    def setUp(self) -> None:
        """Set up the test case."""
        super().setUp()

        # The jira package is optional, so these may not exist on the
        # module. They're put back the way they were after each test.
        fakes = {
            'has_jira': True,
            'JIRAClient': FakeJIRAClient,
            'JIRAError': FakeJIRAError,
            'RequestException': FakeRequestError,
        }

        for attr, value in fakes.items():
            self.addCleanup(
                _restore_module_attr,
                attr,
                getattr(jira_module, attr, _UNSET),
            )
            setattr(jira_module, attr, value)

    def get_jira_service(
        self,
        config: ConfiguredBugTracker,
    ) -> jira_module.JIRA:
        """Return the JIRA service for a bug tracker configuration.

        Args:
            config (reviewboard.hostingsvcs.models.ConfiguredBugTracker):
                The bug tracker configuration.

        Returns:
            reviewboard.hostingsvcs.jira.JIRA:
            The JIRA service.
        """
        service = config.service
        assert isinstance(service, jira_module.JIRA)

        return service
