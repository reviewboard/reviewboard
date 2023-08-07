"""Registry for managing available hosting services.

Version Added:
    6.0:
    This replaces the registry code in the old
    :py:mod:`reviewboard.hostingsvcs.service` module.
"""

import re
from importlib import import_module

from django.urls import include, re_path
from django.utils.translation import gettext_lazy as _
from djblets.registries.registry import (ALREADY_REGISTERED, LOAD_ENTRY_POINT,
                                         NOT_REGISTERED)

import reviewboard.hostingsvcs.urls as hostingsvcs_urls
from reviewboard.registries.registry import EntryPointRegistry


class HostingServiceRegistry(EntryPointRegistry):
    """A registry for managing hosting services."""

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

    def __init__(self):
        super(HostingServiceRegistry, self).__init__()
        self._url_patterns = {}

    def get_defaults(self):
        """Yield the built-in hosting services.

        This will make sure the standard hosting services are always present in
        the registry.

        Yields:
            type:
            The :py:class:`~reviewboard.hostingsvcs.service.HostingService`
            subclasses.
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

        for value in super(HostingServiceRegistry, self).get_defaults():
            yield value

    def unregister(self, service):
        """Unregister a hosting service.

        This will remove all registered URLs that the hosting service has
        defined.

        Args:
            service (type):
                The
                :py:class:`~reviewboard.hostingsvcs.service.HostingService`
                subclass.
        """
        super(HostingServiceRegistry, self).unregister(service)

        if service.hosting_service_id in self._url_patterns:
            cls_urlpatterns = self._url_patterns[service.hosting_service_id]
            hostingsvcs_urls.dynamic_urls.remove_patterns(cls_urlpatterns)
            del self._url_patterns[service.hosting_service_id]

    def process_value_from_entry_point(self, entry_point):
        """Load the class from the entry point.

        The ``id`` attribute will be set on the class from the entry point's
        name.

        Args:
            entry_point (importlib.metadata.EntryPoint):
                The entry point.

        Returns:
            type:
            The :py:class:`HostingService` subclass.
        """
        cls = entry_point.load()
        cls.hosting_service_id = entry_point.name
        return cls

    def register(self, service):
        """Register a hosting service.

        This also adds the URL patterns defined by the hosting service. If the
        hosting service has a :py:attr:`HostingService.repository_url_patterns`
        attribute that is non-``None``, they will be automatically added.

        Args:
            service (type):
                The :py:class:`HostingService` subclass.
        """
        super(HostingServiceRegistry, self).register(service)

        if service.repository_url_patterns:
            cls_urlpatterns = [
                re_path(r'^(?P<hosting_service_id>%s)/'
                        % re.escape(service.hosting_service_id),
                        include(service.repository_url_patterns)),
            ]

            self._url_patterns[service.hosting_service_id] = cls_urlpatterns
            hostingsvcs_urls.dynamic_urls.add_patterns(cls_urlpatterns)


hosting_service_registry = HostingServiceRegistry()
