"""Base class for JIRA tests.

Version Added:
    9.0:
    Split up ``reviewboard.hostingsvcs.test_jira``.
"""

from __future__ import annotations

from typing import TYPE_CHECKING
from urllib.parse import urlencode

from reviewboard.hostingsvcs.jira.service import JIRA
from reviewboard.hostingsvcs.testing import HostingServiceTestCase

if TYPE_CHECKING:
    from collections.abc import Sequence
    from typing import Any

    from reviewboard.hostingsvcs.models import ConfiguredBugTracker


class JIRATestCase(HostingServiceTestCase[JIRA]):
    """Base class for JIRA unit tests.

    Version Added:
        9.0
    """

    service_name = 'jira'
    default_hosting_url = 'https://jira.example.com'

    def get_jira_service(
        self,
        config: ConfiguredBugTracker,
    ) -> JIRA:
        """Return the JIRA service for a bug tracker configuration.

        Version Added:
            9.0

        Args:
            config (reviewboard.hostingsvcs.models.ConfiguredBugTracker):
                The bug tracker configuration.

        Returns:
            reviewboard.hostingsvcs.jira.service.JIRA:
            The JIRA service.
        """
        service = config.service
        assert isinstance(service, JIRA)

        return service

    def make_api_url(
        self,
        path: str,
        *,
        server_url: str = 'https://jira.example.com',
        **query: str,
    ) -> str:
        """Return the URL of a JIRA API request.

        Query parameters are sorted, the same way requests sort them.

        Version Added:
            9.0

        Args:
            path (str):
                The path of the API endpoint, relative to ``/rest/api/2/``.

            server_url (str, optional):
                The root URL of the JIRA server.

            **query (dict):
                The query parameters.

        Returns:
            str:
            The URL.
        """
        url = f'{server_url}/rest/api/2/{path}'

        if query:
            url = f'{url}?{urlencode(sorted(query.items()))}'

        return url

    def make_issue(
        self,
        key: str,
        summary: str,
        status: str,
        description: (str | None) = None,
    ) -> dict[str, Any]:
        """Return the API payload for an issue.

        Version Added:
            9.0

        Args:
            key (str):
                The issue key.

            summary (str):
                The issue summary.

            status (str):
                The name of the issue's status.

            description (str, optional):
                The issue description.

        Returns:
            dict:
            The issue payload.
        """
        fields: dict[str, Any] = {
            'status': {
                'name': status,
            },
            'summary': summary,
        }

        if description is not None:
            fields['description'] = description

        return {
            'fields': fields,
            'key': key,
        }

    def make_search_payload(
        self,
        issues: Sequence[dict[str, Any]],
    ) -> bytes:
        """Return the API payload for a JQL search.

        Version Added:
            9.0

        Args:
            issues (list of dict):
                The issue payloads, from :py:meth:`make_issue`.

        Returns:
            bytes:
            The search payload.
        """
        return self.dump_json({
            'issues': list(issues),
        })

    def make_picker_payload(
        self,
        keys: Sequence[str],
    ) -> bytes:
        """Return the API payload for the issue picker.

        Version Added:
            9.0

        Args:
            keys (list of str):
                The issue keys the picker matched.

        Returns:
            bytes:
            The picker payload.
        """
        return self.dump_json({
            'sections': [
                {
                    'id': 'cs',
                    'issues': [
                        {
                            'key': key,
                        }
                        for key in keys
                    ],
                },
            ],
        })
