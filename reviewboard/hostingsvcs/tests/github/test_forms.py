"""Unit tests for the GitHub repository forms.

Version Added:
    9.0
"""

from __future__ import annotations

from reviewboard.hostingsvcs.github.forms import (
    GitHubPrivateForm,
    GitHubPrivateOrgForm,
    GitHubPublicForm,
    GitHubPublicOrgForm,
)
from reviewboard.hostingsvcs.github.service import GitHub
from reviewboard.hostingsvcs.models import HostingServiceAccount
from reviewboard.hostingsvcs.tests.github.base import GitHubTestCase
from reviewboard.scmtools.models import Repository


class GitHubRepositoryFormTests(GitHubTestCase):
    """Unit tests for the GitHub repository plan forms."""

    def test_save_with_personal_plan(self) -> None:
        """Testing GitHubRepositoryForm.save writes canonical keys on a
        personal plan
        """
        for form_cls, repo_name_field in (
                (GitHubPublicForm, 'github_public_repo_name'),
                (GitHubPrivateForm, 'github_private_repo_name')):
            repository = self._create_repository()

            form = form_cls(
                data={repo_name_field: 'myrepo'},
                hosting_service_cls=GitHub)
            self.assertTrue(form.is_valid())

            form.save(repository)

            self.assertEqual(repository.extra_data['github_owner'],
                             'example')
            self.assertEqual(repository.extra_data['github_repo_name'],
                             'myrepo')

    def test_save_with_org_plan(self) -> None:
        """Testing GitHubRepositoryForm.save writes canonical keys on an
        organization plan
        """
        for form_cls, field_prefix in (
                (GitHubPublicOrgForm, 'github_public_org'),
                (GitHubPrivateOrgForm, 'github_private_org')):
            repository = self._create_repository()

            form = form_cls(
                data={
                    f'{field_prefix}_name': 'myorg',
                    f'{field_prefix}_repo_name': 'myrepo',
                },
                hosting_service_cls=GitHub)
            self.assertTrue(form.is_valid())

            form.save(repository)

            self.assertEqual(repository.extra_data['github_owner'], 'myorg')
            self.assertEqual(repository.extra_data['github_repo_name'],
                             'myrepo')

    def test_save_with_bug_tracker_prefix(self) -> None:
        """Testing GitHubRepositoryForm.save does not write canonical keys
        when configuring a legacy bug tracker
        """
        repository = self._create_repository()

        form = GitHubPublicForm(
            data={'bug_tracker-github_public_repo_name': 'bugsrepo'},
            hosting_service_cls=GitHub,
            prefix='bug_tracker')
        self.assertTrue(form.is_valid())

        form.save(repository)

        self.assertEqual(
            repository.extra_data['bug_tracker-github_public_repo_name'],
            'bugsrepo')
        self.assertNotIn('github_owner', repository.extra_data)
        self.assertNotIn('github_repo_name', repository.extra_data)

    def _create_repository(self) -> Repository:
        """Return a repository suitable for saving form data.

        Returns:
            reviewboard.scmtools.models.Repository:
            The new unsaved repository.
        """
        account = HostingServiceAccount(service_name='github',
                                        username='example')

        return Repository(hosting_account=account, extra_data={})
