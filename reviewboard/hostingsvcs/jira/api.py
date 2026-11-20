"""API interfaces for JIRA.

These match the JIRA REST API (version 2), which JIRA Cloud and JIRA Data
Center both offer. The data definitions here only include the fields we use.

Version Added:
    9.0
"""

from __future__ import annotations

from pydantic import BaseModel


class APIError(BaseModel):
    """API error for JIRA.

    JIRA returns general errors in ``errorMessages``, and errors for
    specific fields or parameters in ``errors``.

    Version Added:
        9.0
    """

    errorMessages: list[str] = []  # noqa: N815
    errors: dict[str, str] = {}

    @property
    def message(self) -> str:
        """A readable message combining all the errors.

        Type:
            str
        """
        return ' '.join([*self.errorMessages, *self.errors.values()])


class IssueStatus(BaseModel):
    """The status of an issue.

    Version Added:
        9.0
    """

    name: str = ''


class IssueFields(BaseModel):
    """The fields of an issue.

    Only the fields that were asked for are returned by JIRA, so all of
    these are optional.

    Version Added:
        9.0
    """

    #: The plain-text description of the issue.
    description: (str | None) = None

    #: The status of the issue.
    status: (IssueStatus | None) = None

    #: The summary (title) of the issue.
    summary: (str | None) = None


class Issue(BaseModel):
    """An issue.

    Version Added:
        9.0
    """

    #: The issue's fields.
    fields: IssueFields

    #: The issue key, such as ``ENG-42``.
    key: str


class SearchResponse(BaseModel):
    """API response for a JQL search.

    JIRA Data Center's ``search`` endpoint and JIRA Cloud's ``search/jql``
    endpoint both return this.

    Version Added:
        9.0
    """

    issues: list[Issue] = []


class PickerIssue(BaseModel):
    """An issue matched by the issue picker.

    Version Added:
        9.0
    """

    key: str


class PickerSection(BaseModel):
    """A section of issue picker results.

    The picker returns a "history" section with recently viewed issues and
    a "current search" section with the actual matches.

    Version Added:
        9.0
    """

    issues: list[PickerIssue] = []


class PickerResponse(BaseModel):
    """API response for the issue picker.

    Version Added:
        9.0
    """

    sections: list[PickerSection] = []
