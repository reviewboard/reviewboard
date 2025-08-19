"""Base support for defining UI themes.

Version Added:
    7.0
"""

from __future__ import annotations

from enum import Enum
from typing import ClassVar, TYPE_CHECKING

if TYPE_CHECKING:
    from django.http import HttpRequest
    from typelets.django.strings import StrOrPromise


class InkColorScheme(Enum):
    """The Ink color scheme set by a theme.

    Version Added:
        7.0
    """

    #: A light color scheme.
    LIGHT = 'light'

    #: A dark color scheme.
    DARK = 'dark'

    #: A high-contrast color scheme.
    HIGH_CONTRAST = 'high-contrast'

    #: A color scheme adapting to current system settings.
    SYSTEM = 'system'


class BaseUITheme:
    """Base class for a UI theme.

    Version Added:
        7.0
    """

    #: The unique ID of the theme.
    #:
    #: This is used for registration and lookup purposes.
    #:
    #: These only need to be unique within other UI themes.
    #:
    #: Type:
    #:     str
    theme_id: ClassVar[str]

    #: The displayed name of the theme.
    #:
    #: This will be shown to the user when choosing themes. It should be
    #: localized.
    #:
    #: Type:
    #:     str
    name: ClassVar[StrOrPromise]

    #: The value for the ``data-ink-color-scheme=`` HTML attribute.
    #:
    #: This informs the CSS and JavaScript of the current color scheme.
    #:
    #: Type:
    #:     InkColorScheme
    ink_color_scheme: ClassVar[InkColorScheme]

    def get_html_attrs(
        self,
        *,
        request: HttpRequest,
    ) -> dict[str, str]:
        """Return HTML attributes to include on the root HTML element.

        By default, this sets ``data-theme`` to :py:attr:`theme_id` and
        ``data-ink-color-scheme`` to :py:attr:`ink_color_scheme``.

        Subclasses can override this to provide additional attributes.

        Args:
            request (django.http.HttpRequest):
                The HTTP request from the client.

        Returns:
            dict:
            The HTML attributes to include.
        """
        return {
            'data-ink-color-scheme': self.ink_color_scheme.value,
            'data-theme': self.theme_id,
        }
