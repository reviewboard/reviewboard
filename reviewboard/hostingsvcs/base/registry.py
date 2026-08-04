"""Registry for managing available hosting services.

Version Added:
    6.0:
    This replaces the registry code in the old
    :py:mod:`reviewboard.hostingsvcs.service` module.
"""

from __future__ import annotations

import inspect
import logging
import re
from importlib import import_module
from typing import TYPE_CHECKING

from django.urls import include, re_path
from django.utils.translation import gettext_lazy as _
from djblets.registries.errors import ItemLookupError
from djblets.registries.registry import (ALREADY_REGISTERED, LOAD_ENTRY_POINT,
                                         NOT_REGISTERED)

from reviewboard.hostingsvcs.urls import hosting_service_urls, repository_urls
from reviewboard.hostingsvcs.base.hosting_service import BaseHostingService
from reviewboard.registries.registry import EntryPointRegistry

if TYPE_CHECKING:
    from collections.abc import Iterator, Sequence
    from importlib.metadata import EntryPoint

    from django.urls import _AnyURL


logger = logging.getLogger(__name__)


class HostingServiceRegistry(EntryPointRegistry[type[BaseHostingService]]):
    """A registry for managing hosting services.

    Version Changed:
        6.0:
        * Moved from :py:mod:`reviewboard.hostingsvcs.service` to
          :py:mod:`reviewboard.hostingsvcs.base.registry`.
    """

    entry_point = 'reviewboard.hosting_services'
    lookup_attrs = ['hosting_service_id']

    errors = {
        ALREADY_REGISTERED: _(
            '"%(item)s" is already a registered hosting service.'
        ),
        LOAD_ENTRY_POINT: _(
            'Unable to load repository hosting service %(entry_point)s: '
            '%(error)s.'
        ),
        NOT_REGISTERED: _(
            '"%(attr_value)s" is not a registered hosting service.'
        ),
    }

    ######################
    # Instance variables #
    ######################

    #: A mapping of hosting service IDs to URLs for hosting services.
    #:
    #: Version Added:
    #:     9.0
    #:
    #: Type:
    #:     dict
    _hosting_service_url_patterns: dict[str, Sequence[_AnyURL]]

    #: A mapping of hosting service IDs to URLs for repositories.
    #:
    #: Type:
    #:     dict
    _repository_url_patterns: dict[str, Sequence[_AnyURL]]

    def __init__(self) -> None:
        """Initialize the registry."""
        super().__init__()

        self._hosting_service_url_patterns = {}
        self._repository_url_patterns = {}

    def get_defaults(self) -> Iterator[type[BaseHostingService]]:
        """Yield the built-in hosting services.

        This will make sure the standard hosting services are always present in
        the registry.

        Yields:
            type:
            The :py:class:`~reviewboard.hostingsvcs.base.hosting_service.
            BaseHostingService` subclasses.
        """
        for _module, _service_cls_name in (
                ('assembla', 'Assembla'),
                ('beanstalk', 'Beanstalk'),
                ('bitbucket', 'Bitbucket'),
                ('bugzilla', 'Bugzilla'),
                ('codebasehq', 'CodebaseHQ'),
                ('fedorahosted', 'FedoraHosted'),
                ('fogbugz', 'FogBugz'),
                ('forgejo', 'Forgejo'),
                ('gerrit', 'Gerrit'),
                ('github', 'GitHub'),
                ('gitlab', 'GitLab'),
                ('gitorious', 'Gitorious'),
                ('googlecode', 'GoogleCode'),
                ('jira', 'JIRA'),
                ('kiln', 'Kiln'),
                ('rbgateway', 'ReviewBoardGateway'),
                ('redmine', 'Redmine'),
                ('sourceforge', 'SourceForge'),
                ('splat', 'Splat'),
                ('trac', 'Trac'),
                ('unfuddle', 'Unfuddle'),
                ('versionone', 'VersionOne'),
            ):
            mod = import_module(f'reviewboard.hostingsvcs.{_module}')

            yield getattr(mod, _service_cls_name)

        yield from super().get_defaults()

    def get_hosting_service(
        self,
        hosting_service_id: str,
    ) -> type[BaseHostingService] | None:
        """Return a hosting service with the given ID.

        Args:
            hosting_service_id (str):
                The hosting service ID to return.

        Returns:
            type:
            The hosting service class, or ``None`` if not found.
        """
        try:
            return self.get('hosting_service_id', hosting_service_id)
        except ItemLookupError:
            return None

    def unregister(
        self,
        service: type[BaseHostingService],
    ) -> None:
        """Unregister a hosting service.

        This will also remove all registered URLs that the hosting service has
        defined.

        Args:
            service (type):
                The
                :py:class:`~reviewboard.hostingsvcs.base.hosting_service.
                BaseHostingService` subclass.
        """
        service_id = service.hosting_service_id

        super().unregister(service)

        if service_id:
            if patterns := self._hosting_service_url_patterns.pop(service_id,
                                                                  None):
                hosting_service_urls.remove_patterns(patterns)

            if patterns := self._repository_url_patterns.pop(service_id, None):
                repository_urls.remove_patterns(patterns)

    def unregister_by_id(
        self,
        hosting_service_id: str,
    ) -> None:
        """Unregister a hosting service by ID.

        This will also remove all registered URLs that the hosting service has
        defined.

        Args:
            hosting_service_id (str):
                The ID of the hosting service to unregister.
        """
        try:
            self.unregister_by_attr('hosting_service_id', hosting_service_id)
        except ItemLookupError:
            logger.error('Failed to unregister unknown hosting service "%s"',
                         hosting_service_id)

            raise

    def process_value_from_entry_point(
        self,
        entry_point: EntryPoint,
    ) -> type[BaseHostingService]:
        """Load the class from the entry point.

        The ``hosting_service_id`` attribute will be set on the class from the
        entry point's name.

        Args:
            entry_point (importlib.metadata.EntryPoint):
                The entry point.

        Returns:
            type:
            The :py:class:`HostingService` subclass.
        """
        cls = entry_point.load()
        assert inspect.isclass(cls)
        assert issubclass(cls, BaseHostingService)

        cls.hosting_service_id = entry_point.name
        return cls

    def register(
        self,
        service: type[BaseHostingService],
    ) -> None:
        """Register a hosting service.

        This also adds the URL patterns defined by the hosting service. If the
        hosting service has
        :py:attr:`HostingService.hosting_service_url_patterns` or
        :py:attr:`HostingService.repository_url_patterns` attributes that are
        non-``None``, they will be automatically added.

        Args:
            service (type):
                The :py:class:`HostingService` subclass.
        """
        super().register(service)

        hosting_service_url_patterns = service.hosting_service_url_patterns
        repository_url_patterns = service.repository_url_patterns

        if not (hosting_service_url_patterns or repository_url_patterns):
            return

        service_id = service.hosting_service_id
        assert service_id is not None
        escaped_id = re.escape(service_id)

        if hosting_service_url_patterns:
            patterns = [
                re_path(rf'^(?P<hosting_service_id>{escaped_id})/',
                        include(hosting_service_url_patterns)),
            ]

            self._hosting_service_url_patterns[service_id] = patterns
            hosting_service_urls.add_patterns(patterns)

        if repository_url_patterns:
            patterns = [
                re_path(rf'^(?P<hosting_service_id>{escaped_id})/',
                        include(repository_url_patterns)),
            ]

            self._repository_url_patterns[service_id] = patterns
            repository_urls.add_patterns(patterns)


#: The main registry of hosting services.
#:
#: Version Added:
#:     6.0
#:
#: Type:
#:     HostingServiceRegistry
hosting_service_registry = HostingServiceRegistry()
