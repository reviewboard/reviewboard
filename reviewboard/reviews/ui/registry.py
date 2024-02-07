"""Registry for Review UIs.

Version Added:
    7.0
"""

from __future__ import annotations

from importlib import import_module
from typing import Iterator, Type

from django.utils.translation import gettext_lazy as _
from djblets.registries.registry import (ALREADY_REGISTERED,
                                         NOT_REGISTERED)

from reviewboard.registries.registry import Registry
from reviewboard.reviews.ui.base import ReviewUI


class ReviewUIRegistry(Registry[Type[ReviewUI]]):
    """A registry for managing ReviewUIs.

    Version Added:
        7.0
    """

    errors = {
        ALREADY_REGISTERED: _(
            '"%(item)s" is already a registered Review UI.'
        ),
        NOT_REGISTERED: _(
            '"%(attr_value)s" is not a registered Review UI.'
        ),
    }

    def get_defaults(self) -> Iterator[type[ReviewUI]]:
        """Yield the built-in Review UIs.

        Yields:
            class:
            The built-in Review UI classes.
        """
        builtin_review_uis = (
            ('image', 'ImageReviewUI'),
            ('markdownui', 'MarkdownReviewUI'),
            ('text', 'TextBasedReviewUI'),
        )

        for _module, _cls_name in builtin_review_uis:
            mod = import_module(f'reviewboard.reviews.ui.{_module}')
            yield getattr(mod, _cls_name)
