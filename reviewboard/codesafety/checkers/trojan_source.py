"""Code safety checker for detecting "Trojan Source" attacks.

Version Added:
    5.0
"""

from __future__ import annotations

import logging
import unicodedata
from itertools import chain
from typing import (Dict, Iterable, Iterator, List, Optional, Sequence,
                    Set, Tuple)

from django.utils.html import format_html
from django.utils.safestring import SafeString, mark_safe
from django.utils.translation import gettext, gettext_lazy as _
from typing_extensions import TypeAlias

from reviewboard.codesafety.checkers.base import (BaseCodeSafetyChecker,
                                                  CodeSafetyCheckResults,
                                                  CodeSafetyContentItem)


logger = logging.getLogger(__name__)


_UnicodeRange: TypeAlias = Tuple[int, int]
_UnicodeRanges: TypeAlias = Tuple[_UnicodeRange, ...]


#: Zero-width Unicode characters.
#:
#: These characters can be used in some languages to make two different
#: identifiers appear to look the same.
#:
#: This regex covers the following characters:
#:
#: * ZWSP - Zero Width Space (U+200B)
#: * ZWNJ - Zero Width Non-Joiner (U+200C)
#:
#: Version Added:
#:     5.0
ZERO_WIDTH_UNICODE_CHAR_RANGES: _UnicodeRanges = (
    (0x200B, 0x200C),
)

#: Bi-directional Unicode characters.
#:
#: These can be used to alter the display of code, making a block of code
#: appear one way but actually execute another way.
#:
#: This regex covers the following characters:
#:
#: * LRE  - Left-to-Right Embedding (U+202A)
#: * RLE  - Right-to-Left Embedding (U+202B)
#: * LRO  - Left-to-Right Override (U+202D)
#: * RLO  - Right-to-Left Override (U+202E)
#: * LRI  - Left-to-Right Isolate (U+2066)
#: * RLI  - Right-to-Left Isolate (U+2067)
#: * FSI  - First Strong Isolate (U+2068)
#: * PDF  - Pop Directional Formatting (U+202C)
#: * PDI  - Pop Directional Isolate (U+2069)
#:
#: This is :cve:`2021-42574`.
#:
#: Version Added:
#:     5.0
BIDI_UNICODE_RANGES: _UnicodeRanges = (
    (0x202A, 0x202E),
    (0x2066, 0x2069),
)


class TrojanSourceCodeSafetyChecker(BaseCodeSafetyChecker):
    """Code safety checker for detecting "Trojan Source" attacks.

    Trojan Source attacks (:cve:`2021-42574`) enable a bad actor to write code
    that appears one way but behaves another way. This is done by taking
    advantage of Unicode bi-directional control characters or zero-width spaces
    to alter the way code is rendered, helping sneak malicious code past
    reviewers.

    This code safety checker looks for zero-width spaces and bi-directional
    control characters in lines. If found, warnings are flagged, characters
    are replaced with Unicode markers, and an alert is shown at the top of a
    diff, explaining the problem.

    See https://www.trojansource.codes/ for details on the attack.

    Version Added:
        5.0
    """

    checker_id = 'trojan_source'
    summary = _('Possible "Trojan Source" code')

    file_alert_html_template_name = 'codesafety/trojan_source_alert.html'

    result_labels = {
        'bidi': _('Bi-directional Unicode characters (CVE-2021-42574)'),
        'confusable': _('Confusable Unicode characters (CVE-2021-42694)'),
        'zws': _('Zero-width space characters (CVE-2021-42574)'),
    }

    _unsafe_unicode_check_map: Optional[Dict[_UnicodeRange, str]] = None

    _check_unicode_ranges = {
        'bidi': BIDI_UNICODE_RANGES,
        'zws': ZERO_WIDTH_UNICODE_CHAR_RANGES,
    }

    @classmethod
    def get_main_confusable_aliases(
        cls,
    ) -> Sequence[str]:
        """Return a list of main Unicode aliases that can be customized.

        Returns:
            list of str:
            The list of aliases.
        """
        from reviewboard.codesafety._unicode_confusables import \
            CONFUSABLES_ID_TO_ALIAS_MAP

        return sorted(CONFUSABLES_ID_TO_ALIAS_MAP)

    def check_content(
        self,
        content_items: List[CodeSafetyContentItem],
        *,
        check_confusables: bool = True,
        confusable_aliases_allowed: List[str] = [],
        **kwargs,
    ) -> CodeSafetyCheckResults:
        """Check content for possible Trojan Source code.

        This will scan the characters of each line, looking for any
        bi-directional or zero-width space Unicode characters. If found,
        appropriate warnings will be returned.

        Args:
            content_items (list of dict):
                A list of dictionaries containing files and lines to check.

            check_confusables (bool, optional):
                Whether to check the line for Unicode confusables.

            confusable_aliases_allowed (list of str, optional):
                A list of Unicode aliases to exclude from Unicode confusables
                checks.

            **kwargs (dict, unused):
                Additional keyword arguments, for future expansion.

        Returns:
            dict:
            Results from the checks, which may contain the following:

            Keys:
                warnings (list of str):
                    A list of Unicode warning IDs, local to this safety
                    checker.
        """
        num_possible_warnings = len(self.result_labels)
        warnings = set()

        lines = (
            _line
            for _item in content_items
            for _line in _item['lines']
        )

        # Iterate over all characters across the lines. Since we're only
        # looking for Unicode characters, and we'll probably encounter a lot
        # of simple ASCII characters, don't bother with anything under ASCII
        # 128.
        chars = (
            _char
            for _char in chain.from_iterable(lines)
            if ord(_char) >= 128
        )

        unsafe_chars_iter = self._iter_unsafe_chars(
            chars,
            check_confusables=check_confusables,
            confusable_aliases_allowed=confusable_aliases_allowed)

        for i, c, codepoint, check_name in unsafe_chars_iter:
            warnings.add(check_name)

            if len(warnings) == num_possible_warnings:
                # We don't need to check any more characters. We've
                # found at least one instance of everything we can
                # report.
                break

        return {
            'warnings': warnings,
        }

    def update_line_html(
        self,
        line_html: str,
        result_ids: Sequence[str],
        *,
        check_confusables: bool = True,
        confusable_aliases_allowed: List[str] = [],
        **kwargs,
    ) -> SafeString:
        """Update the rendered diff HTML for a line.

        This will highlight any Unicode characters that would have triggered
        warnings, displaying the Unicode character code instead of rendering
        the character itself.

        Args:
            line_html (str):
                The HTML of the line.

            result_ids (list of str, unused):
                The list of result IDs that were found for the line.

            check_confusables (bool, optional):
                Whether to check the line for Unicode confusables.

            confusable_aliases_allowed (list of str, optional):
                A list of Unicode aliases to exclude from Unicode confusables
                checks.

            **kwargs (dict, unused):
                Additional keyword arguments, for future expansion.

        Returns:
            django.utils.safestring.SafeString:
            The updated HTML.
        """
        result = []
        last_append_i = 0

        unsafe_chars_iter = self._iter_unsafe_chars(
            line_html,
            check_confusables=check_confusables,
            confusable_aliases_allowed=confusable_aliases_allowed)

        for i, c, codepoint, check_name in unsafe_chars_iter:
            result.append(line_html[last_append_i:i])

            # If it looks like a DUC and quacs like a DUC, then it's a
            # Displayed Unicode Character.
            #
            # We'll convert the character to a hex value and set the codepoint
            # and character entity on the tag so that the CSS can toggle its
            # display.
            try:
                char_name = unicodedata.name(c).title()
            except ValueError:
                char_name = gettext('Unknown')

            result.append(format_html(
                '<span class="rb-o-duc" data-codepoint="{codepoint}"'
                ' data-char="&#x{codepoint};" title="{title}"></span>',
                codepoint='%X' % codepoint,
                title=(
                    _('Unicode Character: %s')
                    % char_name
                )))
            last_append_i = i + 1

        result.append(line_html[last_append_i:])

        return mark_safe(''.join(result))

    def _iter_unsafe_chars(
        self,
        chars: Iterable[str],
        *,
        check_confusables: bool,
        confusable_aliases_allowed: List[str],
    ) -> Iterator[Tuple[int, str, int, str]]:
        """Iterate through a string, yielding unsafe characters.

        Args:
            chars (str):
                The characters to iterate through.

            check_confusables (bool, optional):
                Whether to check the line for Unicode confusables.

            confusable_aliases_allowed (list of str, optional):
                A list of Unicode aliases to exclude from Unicode confusables
                checks.

        Yields:
            tuple:
            Information on an unsafe character. This contains:

            Tuple:
                0 (int):
                    The 0-based index of the character in the provided string.

                1 (str):
                    The Unicode character.

                2 (int):
                    The Unicode codepoint.

                3 (str):
                    The result ID.
        """
        # We're importing this here, rather than at the module level, since
        # we want to avoid taking the hit until we need it the first time.
        from reviewboard.codesafety._unicode_confusables import (
            COMMON_CONFUSABLES_MAP,
            CONFUSABLES_ALIAS_TO_ID_MAP,
            ConfusablesMap,
        )

        confusables_map: ConfusablesMap = {}
        confusables_lang_ids_allowed: Set[int] = set()

        if check_confusables:
            confusables_map = COMMON_CONFUSABLES_MAP

            # Check if any specific languages have been opted into. These will
            # be excluded from any confusable checks.
            confusables_lang_ids_allowed = {
                CONFUSABLES_ALIAS_TO_ID_MAP[_alias]
                for _alias in confusable_aliases_allowed
                if _alias in CONFUSABLES_ALIAS_TO_ID_MAP
            }

        checks_map = self._get_unsafe_unicode_check_map()

        for i, c in enumerate(chars):
            codepoint = ord(c)

            if c in confusables_map:
                if (not confusables_lang_ids_allowed or
                    confusables_map[c][1] not in confusables_lang_ids_allowed):
                    yield i, c, codepoint, 'confusable'
            else:
                for check_range, check_name in checks_map.items():
                    if check_range[0] <= codepoint <= check_range[1]:
                        yield i, c, codepoint, check_name
                        break

    @classmethod
    def _get_unsafe_unicode_check_map(cls) -> Dict[_UnicodeRange, str]:
        """Return a range check map for matching unsafe Unicode characters.

        This is cached for all future instances.

        Returns:
            dict:
            The resulting range check map.
        """
        checks_map = cls._unsafe_unicode_check_map

        if checks_map is None:
            checks_map = {
                _range: _check_id
                for _check_id, _ranges in cls._check_unicode_ranges.items()
                for _range in _ranges
            }
            cls._unsafe_unicode_check_map = checks_map

        return checks_map
