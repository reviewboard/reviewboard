"""API interfaces for Forgejo.

The names of the classes in this module reflect the names used in the Forgejo
swagger UI. The data definitions here do not comprehensively include all
fields, only those that we need for our use.

Version Added:
    7.1
"""

from __future__ import annotations

from typing import List, Optional

from pydantic import BaseModel


class APIError(BaseModel):
    """API error for Forgejo.

    Version Added:
        7.1
    """

    message: str
    url: str


class AccessToken(BaseModel):
    """API response for a Forgejo access token.

    Version Added:
        7.1
    """

    id: int
    name: str
    scopes: List[str]
    sha1: str
    token_last_eight: str


class GitBlobResponse(BaseModel):
    """API response for a Git blob.

    Version Added:
        7.1
    """

    content: str
    encoding: str
    sha: str
    size: int
    url: str


class CommitMeta(BaseModel):
    """Commit metadata.

    Version Added:
        7.1
    """

    created: str
    sha: str
    url: str


class CommitUser(BaseModel):
    """A user for a commit.

    Version Added:
        7.1
    """

    date: str
    email: str
    name: str


class Commit(BaseModel):
    """API response for a Git commit.

    Version Added:
        7.1
    """

    commit: RepoCommit
    created: str
    parents: List[CommitMeta]
    sha: str


class GitEntry(BaseModel):
    """An entry in a Git tree.

    Version Added:
        7.1
    """

    path: str
    sha: str
    size: int
    type: str


class GitObject(BaseModel):
    """API response for a Git object.

    Version Added:
        7.1
    """

    sha: str
    type: str
    url: str


class GitReference(BaseModel):
    """API data for a Git reference.

    Version Added:
        7.1
    """

    object: GitObject
    ref: str
    url: str


class GitTreeResponse(BaseModel):
    """API data for a Git tree.

    Version Added:
        7.1
    """

    page: int
    sha: str
    total_count: int
    tree: Optional[List[GitEntry]]
    truncated: bool


class Issue(BaseModel):
    """API data for an issue.

    Version Added:
        7.1
    """

    body: str
    id: int
    state: str
    title: str


class Repository(BaseModel):
    """API data for a repository.

    Version Added:
        7.1
    """

    clone_url: str
    default_branch: str
    description: str
    id: int
    name: str
    private: bool


class RepoCommit(BaseModel):
    """Data about a commit.

    Version Added:
        7.1
    """

    author: CommitUser
    committer: CommitUser
    message: str
    tree: CommitMeta
