"""API interfaces for GitHub.

The data definitions here do not comprehensively include all fields, only
those that we need for our use.

Version Added:
    9.0
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class APIError(BaseModel):
    """API error for GitHub.

    Version Added:
        9.0
    """

    message: str


class AppManifestOwner(BaseModel):
    """The owner of a GitHub App created from a manifest.

    Version Added:
        9.0
    """

    login: str = ''
    type: str = ''


class AppManifestResponse(BaseModel):
    """API response for a GitHub App manifest conversion.

    This is returned when exchanging a temporary manifest code for the
    credentials of the newly-created app. The required fields hold the
    credentials we must store.

    Version Added:
        9.0
    """

    id: int
    slug: str
    client_id: str
    client_secret: str
    pem: str
    html_url: str = ''
    webhook_secret: str = ''
    owner: (AppManifestOwner | None) = None


class BaseCommit(BaseModel):
    """Data for the base commit in a comparison.

    Version Added:
        9.0
    """

    commit: CommitData


class Branch(BaseModel):
    """Data for a branch.

    Version Added:
        9.0
    """

    commit: GitObject
    name: str


class CommitData(BaseModel):
    """Data for a commit.

    Version Added:
        9.0
    """

    author: CommitUser
    committer: CommitUser
    message: str
    tree: GitObject


class CommitResponse(BaseModel):
    """API response for a Git commit.

    Version Added:
        9.0
    """

    commit: CommitData
    files: (list[FileEntry] | None) = Field(default=None)
    parents: list[GitObject]
    sha: str


class CommitUser(BaseModel):
    """Data for a user in a commit.

    Version Added:
        9.0
    """

    date: str
    name: str


class CompareCommitsResponse(BaseModel):
    """API response for comparing two commits.

    Version Added:
        9.0
    """

    base_commit: BaseCommit
    files: list[FileEntry]


class FileEntry(BaseModel):
    """An entry in the files list.

    Version Added:
        9.0
    """

    filename: str
    patch: str | None
    previous_filename: (str | None) = Field(default=None)
    status: Literal[
        'added',
        'removed',
        'modified',
        'renamed',
        'copied',
        'changed',
        'unchanged',
    ]
    sha: str


class GitObject(BaseModel):
    """Commit metadata.

    Version Added:
        9.0
    """

    sha: str


class InstallationAccount(BaseModel):
    """The user or organization a GitHub App is installed on.

    Version Added:
        9.0
    """

    avatar_url: str = ''

    #: The stable numeric ID of the account.
    #:
    #: Unlike the login, this does not change when a user or organization is
    #: renamed, so it is used to match an installation across reinstalls.
    id: int = 0

    login: str
    type: str = ''


class InstallationResponse(BaseModel):
    """API response for a GitHub App installation.

    Version Added:
        9.0
    """

    account: InstallationAccount
    repository_selection: str = ''


class Issue(BaseModel):
    """API response for issues.

    Version Added:
        9.0
    """

    body: str
    state: Literal['open', 'closed']
    title: str


class IssueResponse(BaseModel):
    """API response for issues.

    Version Added:
        9.0
    """

    value: Issue


class Repository(BaseModel):
    """API response for a repository.

    Version Added:
        9.0
    """

    clone_url: str
    default_branch: str
    mirror_url: str | None
    name: str
    owner: RepositoryOwner

    model_config = ConfigDict(extra='allow')


class RepositoryOwner(BaseModel):
    """A repository owner.

    Version Added:
        9.0
    """

    login: str


class TreeEntry(BaseModel):
    """An entry in a git tree.

    Version Added:
        9.0
    """

    path: str
    sha: str


class TreeResponse(BaseModel):
    """API response for a git tree.

    Version Added:
        9.0
    """

    tree: list[TreeEntry]
    truncated: bool
