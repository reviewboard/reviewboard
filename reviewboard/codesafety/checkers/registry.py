"""Registry for code safety checkers.

Version Added:
    5.0
"""

from __future__ import annotations

from typing import Iterable, Optional

from reviewboard.codesafety.checkers.base import BaseCodeSafetyChecker
from reviewboard.codesafety.checkers.trojan_source import \
    TrojanSourceCodeSafetyChecker
from reviewboard.registries.registry import OrderedRegistry


class CodeSafetyCheckerRegistry(OrderedRegistry[BaseCodeSafetyChecker]):
    """Registry for managing code safety checkers.

    Version Added:
        5.0
    """

    lookup_attrs = ['checker_id']

    def get_checker(
        self,
        checker_id: str,
    ) -> Optional[BaseCodeSafetyChecker]:
        """Return a code checker with the specified ID.

        Args:
            checker_id (str):
                The ID of the code safety checker.

        Returns:
            The code checker instance, or ``None`` if not found.
        """
        return self.get('checker_id', checker_id)

    def get_defaults(self) -> Iterable[BaseCodeSafetyChecker]:
        """Return the default code safety checkers.

        Returns:
            list of reviewboard.codesafety.checkers.base.BaseCodeSafetyChecker:
            The list of default code safety checkers.
        """
        return [
            TrojanSourceCodeSafetyChecker(),
        ]
