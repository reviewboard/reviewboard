"""Settings used to manage the processing and render of diffs.

Version Added:
    5.0.2
"""

from __future__ import annotations

import json
from dataclasses import dataclass, fields as dataclass_fields
from hashlib import sha256
from typing import Any, Dict, List, Optional, cast

from django.contrib.auth.models import User
from django.core.exceptions import ObjectDoesNotExist
from django.http import HttpRequest
from django.utils.functional import cached_property
from djblets.siteconfig.models import SiteConfiguration

from reviewboard.site.models import LocalSite


@dataclass
class DiffSettings:
    """Settings used to render a diff.

    These settings represent a combination of site configuration settings for
    the diff viewer and user-configured settings. They're used to control how
    the diff viewer displays diffs, covering syntax highlighting options,
    code safety checks, whitespace handling, and more.

    Version Added:
        5.0.2
    """

    #: A mapping of code safety checker IDs to configurations.
    #:
    #: Type:
    #:     dict
    code_safety_configs: Dict[str, Dict[str, Any]]

    #: The number of lines of context to show around modifications in a chunk.
    #:
    #: Type:
    #:     int
    context_num_lines: int

    #: A custom mapping of file extensions to Pygments lexers.
    #:
    #: Type:
    #:     dict
    custom_pygments_lexers: Dict[str, str]

    #: A list of file globs for which legacy whitespace rules should be used.
    #:
    #: Any file matching a pattern in this list will treat all whitespace as
    #: modifications to lines. Smart indentation handling and other features
    #: may behave differently.
    #:
    #: This is considered a legacy feature.
    #:
    #: Type:
    #:     list of str
    include_space_patterns: List[str]

    #: The number of files to include in each page of a diff.
    #:
    #: Type:
    #:     int
    paginate_by: int

    #: The maximum number of orphans to include on the last page of a diff.
    #:
    #: Orphans are extra files that would make up less than a full page. If
    #: there aren't more than this number of orphans, they'll be rolled up
    #: into the final page of the diff viewer.
    #:
    #: Type:
    #:     int
    paginate_orphans: int

    #: Whether to enable syntax highlighting.
    #:
    #: Type:
    #:     bool
    syntax_highlighting: bool

    #: The maximum number of lines in a file to allow syntax highlighting.
    #:
    #: If a file has lines beyond this threshold, syntax highlighting will
    #: be forcefully disabled.
    #:
    #: Type:
    #:     int
    syntax_highlighting_threshold: int

    @classmethod
    def create(
        cls,
        *,
        user: Optional[User] = None,
        local_site: Optional[LocalSite] = None,
        request: Optional[HttpRequest] = None,
        syntax_highlighting: Optional[bool] = None,
    ) -> DiffSettings:
        """Create diff settings based on the provided arguments.

        This will compute settings based on any HTTP request, Local Site, or
        user provided. The rest will be filled out from the site configuration.

        Syntax highlighting will be enabled if it's both enabled in the site
        configuration and in the user's profile.

        If ``request`` is provided, its associated user and Local Site will
        be used as defaults if ``user`` or ``local_site`` are not provided.

        Args:
            user (django.contrib.auth.models.User, optional):
                The user the settings should pertain to.

            local_site (reviewboard.site.models.LocalSite, optional):
                The Local Site that the settings should pertain to.

            request (django.http.HttpRequest, optional):
                The HTTP request from the client.

            syntax_highlighting (bool, optional):
                An explicit value for :py:attr:`syntax_highlighting`. If
                provided, the user and site settings will be ignored.

        Returns:
            DiffSettings:
            The settings for rendering the diff.
        """
        siteconfig = SiteConfiguration.objects.get_current()

        # If a request is passed, see if we need to extract information from
        # it to fill in missing attributes.
        if request is not None:
            if user is None and request.user.is_authenticated:
                # Satisfy the type checker.
                assert isinstance(request.user, User)

                user = request.user

            if local_site is None:
                local_site = getattr(request, 'local_site', None)

        # Figure out the default for syntax highlighting.
        if syntax_highlighting is None:
            syntax_highlighting = cast(
                bool,
                siteconfig.get('diffviewer_syntax_highlighting'))

            if syntax_highlighting and user and user.is_authenticated:
                # The server enables syntax highlighting. See if the user has
                # enabled or disabled it.
                try:
                    # Satisfy the type checker.
                    assert hasattr(user, 'get_profile')

                    syntax_highlighting = \
                        user.get_profile().syntax_highlighting
                except ObjectDoesNotExist:
                    pass

            assert syntax_highlighting is not None

        return cls(
            code_safety_configs=cast(
                Dict,
                siteconfig.get('code_safety_checkers')
            ),
            context_num_lines=cast(
                int,
                siteconfig.get('diffviewer_context_num_lines')),
            custom_pygments_lexers=cast(
                Dict[str, str],
                siteconfig.get('diffviewer_custom_pygments_lexers')),
            include_space_patterns=cast(
                List[str],
                siteconfig.get('diffviewer_include_space_patterns')),
            paginate_by=cast(
                int,
                siteconfig.get('diffviewer_paginate_by')),
            paginate_orphans=cast(
                int,
                siteconfig.get('diffviewer_paginate_orphans')),
            syntax_highlighting=syntax_highlighting,
            syntax_highlighting_threshold=cast(
                int,
                siteconfig.get('diffviewer_syntax_highlighting_threshold')))

    @cached_property
    def state_hash(self) -> str:
        """Return a hash of the current settings.

        This can be used as a component in cache keys and ETags to ensure
        that changes to diff settings trigger re-generations of diffs.

        This is calculated only once per instance. It won't take into account
        any setting changes since the first access.

        Type:
            str
        """
        return sha256(
            json.dumps(
                {
                    field.name: getattr(self, field.name)
                    for field in dataclass_fields(self)
                },
                sort_keys=True)
            .encode('utf-8')
        ).hexdigest()
