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
from typing import Dict, Iterator, Optional, Sequence, TYPE_CHECKING, Type

from django.urls import include, re_path
from django.utils.translation import gettext_lazy as _
from djblets.registries.errors import ItemLookupError
from djblets.registries.registry import (ALREADY_REGISTERED, LOAD_ENTRY_POINT,
                                         NOT_REGISTERED)

from reviewboard.hostingsvcs.urls import dynamic_urls as hostingsvcs_urls
from reviewboard.hostingsvcs.base.hosting_service import BaseHostingService
from reviewboard.registries.registry import EntryPointRegistry

if TYPE_CHECKING:
    from django.urls import _AnyURL


logger = logging.getLogger(__name__)


class HostingServiceRegistry(EntryPointRegistry[Type[BaseHostingService]]):
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

    #: A mapping of hosting service IDs to URL patterns/resolvers.
    #:
    #: Type:
    #:     dict
    _url_patterns: Dict[str, Sequence[_AnyURL]]

    def __init__(self):
        """Initialize the registry."""
        super().__init__()

        self._url_patterns = {}

    def get_defaults(self) -> Iterator[Type[BaseHostingService]]:
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
            mod = import_module('reviewboard.hostingsvcs.%s' % _module)
            yield getattr(mod, _service_cls_name)

        yield from super().get_defaults()

    def get_hosting_service(
        self,
        hosting_service_id: str,
    ) -> Optional[Type[BaseHostingService]]:
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
        service: Type[BaseHostingService],
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
        hosting_service_id = service.hosting_service_id

        super().unregister(service)

        if hosting_service_id and hosting_service_id in self._url_patterns:
            cls_urlpatterns = self._url_patterns[hosting_service_id]
            hostingsvcs_urls.remove_patterns(cls_urlpatterns)
            del self._url_patterns[hosting_service_id]

    def unregister_by_id(
        self,
        hosting_service_id: str,
    ) -> None:
        """Unregister a hosting service by ID.

        This will also remove all registered URLs that the hosting service has
        defined.

        Args:
            service (type):
                The
                :py:class:`~reviewboard.hostingsvcs.base.hosting_service.
                BaseHostingService` subclass.
        """
        try:
            self.unregister_by_attr('hosting_service_id', hosting_service_id)
        except ItemLookupError:
            logger.error('Failed to unregister unknown hosting service "%s"',
                         hosting_service_id)

            raise

    def process_value_from_entry_point(
        self,
        entry_point,
    ) -> Type[BaseHostingService]:
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
        service: Type[BaseHostingService],
    ) -> None:
        """Register a hosting service.

        This also adds the URL patterns defined by the hosting service. If the
        hosting service has a :py:attr:`HostingService.repository_url_patterns`
        attribute that is non-``None``, they will be automatically added.

        Args:
            service (type):
                The :py:class:`HostingService` subclass.
        """
        super().register(service)

        if service.repository_url_patterns:
            assert service.hosting_service_id

            cls_urlpatterns = [
                re_path(r'^(?P<hosting_service_id>%s)/'
                        % re.escape(service.hosting_service_id),
                        include(service.repository_url_patterns)),
            ]

            self._url_patterns[service.hosting_service_id] = cls_urlpatterns
            hostingsvcs_urls.add_patterns(cls_urlpatterns)


#: The main registry of hosting services.
#:
#: Version Added:
#:     6.0
#:
#: Type:
#:     HostingServiceRegistry
hosting_service_registry = HostingServiceRegistry()
