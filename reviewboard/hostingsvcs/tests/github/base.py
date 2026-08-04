"""Base class for GitHub tests.

Version Added:
    9.0:
    Split out from reviewboard.hostingsvcs.tests.test_github
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from reviewboard.hostingsvcs.github.service import GitHub
from reviewboard.hostingsvcs.testing import HostingServiceTestCase
from reviewboard.scmtools.crypto_utils import encrypt_password

if TYPE_CHECKING:
    from collections.abc import Mapping


class GitHubTestCase(HostingServiceTestCase[GitHub]):
    """Base class for GitHub test suites."""

    service_name = 'github'

    default_account_data: Mapping[str, str] = {
        'personal_token': encrypt_password('abc123'),
    }

    default_repository_extra_data: Mapping[str, str] = {
        'repository_plan': 'public',
        'github_public_repo_name': 'myrepo',
    }
