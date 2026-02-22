"""Base support for code safety checkers.

Version Added:
    5.0
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Sequence, Set, TYPE_CHECKING

from django.template.loader import render_to_string
from django.utils.safestring import SafeString, mark_safe
from typing_extensions import NotRequired, TypedDict

from reviewboard.scmtools.models import Repository

if TYPE_CHECKING:
    # This is available only in django-stubs.
    from django.utils.functional import _StrOrPromise


class CodeSafetyContentItem(TypedDict):
    """An item of content in a file to check.

    Version Added:
        5.0.2
    """

    #: The path to the file in a diff to check.
    #:
    #: This can be used by checkers to perform checks on only certain kinds
    #: of files, or to change checking behavior based on the file type.
    #:
    #: This can just be a filename, rather than a full path, if that's all
    #: that's available.
    #:
    #: Type:
    #:     str
    path: str

    #: A list of one or more lines within the file to check.
    #:
    #: The checker cannot assume anything about the range of lines within the
    #: file.
    #:
    #: Type:
    #:     list of str
    lines: List[str]

    #: The repository the file is on, if any.
    #:
    #: Type:
    #:     rbtools.scmtools.models.Repository
    repository: NotRequired[Repository]


class CodeSafetyCheckResults(TypedDict):
    """The results of a code safety check.

    Version Added:
        5.0.2
    """

    #: A set of error IDs found by a code safety checker.
    #:
    #: The IDs are local to the code safety checker.
    #:
    #: Type:
    #:     list of str
    errors: NotRequired[Set[str]]

    #: A set of warning IDs found by a code safety checker.
    #:
    #: The IDs are local to the code safety checker.
    #:
    #: Type:
    #:     list of str
    warnings: NotRequired[Set[str]]


class BaseCodeSafetyChecker(object):
    """Base class for a code safety checker.

    Code safety checkers are used to analyze the content of lines of code in
    order to determine if there's anything suspicious or dangerous.

    They're designed to be very general-purpose, allowing the caller to check
    a group of lines (potentially from different files or revisions of files)
    at once, in order to get a list of any results (warnings or errors) that
    were found.

    They can also update the rendering of lines to highlight those results,
    and show a detailed message designed to be shown at the top of a file or
    in an API result.

    Version Added:
        5.0
    """

    #: The unique ID of the code safety checker, for registration purposes.
    #:
    #: Type:
    #:     str
    checker_id: Optional[str] = None

    #: The summary shown by the code safety checker for results.
    #:
    #: Type:
    #:    str
    summary: Optional[_StrOrPromise] = None

    #: The HTML template name for the alert at the top of a file.
    #:
    #: If provided, this will be used as the default template when rendering
    #: file alerts in :py:meth:`render_file_alert`.
    #:
    #: Type:
    #:     str
    file_alert_html_template_name: Optional[str] = None

    #: A mapping of warning IDs to human-readable labels.
    #:
    #: These will be used whenever the details on a warning needs to be shown
    #: to a user.
    #:
    #: Keys must be strings, and values should be lazily-localized strings.
    #:
    #: Type:
    #:     dict
    result_labels: Dict[str, _StrOrPromise] = {}

    def check_content(
        self,
        content_items: List[CodeSafetyContentItem],
        **kwargs,
    ) -> CodeSafetyCheckResults:
        """Check content for safety issues.

        One or more files may be checked at once, and one or more lines
        somewhere within those files. The checker should return any warnings
        or errors that are found within any of those provided lines.

        It's up to the caller to decide whether a full file's content,
        multiple file's contents, or specific ranges from multiple files are
        checked, and to handle the results appropriately.

        Subclasses can extend this with custom arguments. These should all
        be specified as keyword-only arguments. Review Board may set these
        based on stored configuration, depending on the code safety checker.

        Version Changed:
            5.0.2:
            Added explicit support for subclass-defined custom arguments.

        Args:
            content_items (list of dict):
                A list of dictionaries containing files and lines to check.

                See :py:class:`CodeSafetyContentItem` for the contents of
                each item.

            **kwargs (dict, unused):
                Additional keyword arguments, for future expansion.

        Returns:
            dict:
            Results from the checks. See :py:class:`CodeSafetyCheckResults`
            for details.
        """
        return {}

    def update_line_html(
        self,
        line_html: str,
        result_ids: Sequence[str] = [],
        **kwargs,
    ) -> SafeString:
        """Update the rendered diff HTML for a line.

        This can update the HTML for a line to highlight any content that
        triggered a warning, making the problem clear to reviewers or authors
        of changes.

        Callers should take care to ensure that the updates don't themselves
        cause any unsafe HTML to be generated.

        Subclasses can extend this with custom arguments. These should all
        be specified as keyword-only arguments. Review Board may set these
        based on stored configuration, depending on the code safety checker.

        Version Changed:
            5.0.2:
            Added explicit support for subclass-defined custom arguments.

        Args:
            line_html (str):
                The HTML of the line.

            result_ids (list of str):
                The list of result IDs that were found for the line.

            **kwargs (dict, unused):
                Additional keyword arguments, for future expansion.

        Returns:
            django.utils.safestring.SafeString:
            The updated HTML.
        """
        return mark_safe(line_html)

    def get_result_labels(
        self,
        result_ids: Sequence[str],
        **kwargs,
    ) -> List[str]:
        """Return a list of result labels for the given IDs for display.

        By default, this will generate a list based off
        :py:attr:`result_labels`. Subclasses can override this if they need
        to do something more specific.

        Args:
            result_ids (list of str):
                A list of one or more result IDs generated by this code
                safety checker.

            **kwargs (dict, unused):
                Additional keyword arguments, for future expansion.

        Returns:
            list of str:
            A list of result labels for the given IDs.
        """
        labels = self.result_labels

        # Note that we need to cast these to a string in case the text is
        # lazily-localized.
        return [
            str(labels.get(_result_id, _result_id))
            for _result_id in result_ids
        ]

    def render_file_alert_html(
        self,
        error_ids: Sequence[str],
        warning_ids: Sequence[str],
        **kwargs,
    ) -> Optional[SafeString]:
        """Render an alert for the top of a file.

        This is responsible for rendering an alert that explains the warnings
        and errors that were found. This would be shown at the top of a diff.

        By default, this will render :py:attr:`file_alert_html_template_name`,
        if specified, and provide context variables from
        :py:meth:`get_file_alert_context_data`.

        Subclasses can override this to provide additional information.

        Args:
            error_ids (list of str):
                A list of one or more error IDs generated by this code
                safety checker.

            warning_ids (list of str):
                A list of one or more warning IDs generated by this code
                safety checker.

            **kwargs (dict, unused):
                Additional keyword arguments, for future expansion.

        Returns:
            django.utils.safestring.SafeString:
            The alert HTML, or ``None`` if nothing will be displayed.
        """
        if not self.file_alert_html_template_name:
            return None

        context_data = self.get_file_alert_context_data(
            error_ids=error_ids or [],
            warning_ids=warning_ids or [],
            **kwargs)

        return render_to_string(self.file_alert_html_template_name,
                                context=context_data)

    def get_file_alert_context_data(
        self,
        error_ids: Sequence[str],
        warning_ids: Sequence[str],
        **kwargs,
    ) -> Dict[str, Any]:
        """Return context variables for the file alert template.

        By default, this returns:

        Keys:
            error_ids (list of str):
                The list of error IDs found by this code safety checker.

            error_labels (list of str):
                A list of human-readable warning labels for display.

            warning_ids (list of str):
                The list of warning IDs found by this code safety checker.

            warning_labels (list of str):
                A list of human-readable warning labels for display.

        Subclasses can override this to return additional data.

        Args:
            error_ids (list of str):
                A list of one or more error IDs generated by this code
                safety checker.

            warning_ids (list of str):
                A list of one or more warning IDs generated by this code
                safety checker.

            **kwargs (dict, unused):
                Additional keyword arguments, for future expansion.

        Returns:
            dict:
            A dictionary of context variables.
        """
        return {
            'error_ids': error_ids,
            'error_labels': self.get_result_labels(error_ids),
            'warning_ids': warning_ids,
            'warning_labels': self.get_result_labels(warning_ids),
        }
