from __future__ import unicode_literals

from django.contrib.auth.context_processors import PermLookupDict, PermWrapper
from django.utils import six

from reviewboard.site.models import LocalSite


class AllPermsLookupDict(PermLookupDict):
    def __init__(self, user, app_label, perms_wrapper):
        super(AllPermsLookupDict, self).__init__(user, app_label)

        self.perms_wrapper = perms_wrapper

    def __repr__(self):
        return six.text_type(self.user.get_all_permissions(
            self.perms_wrapper.get_local_site()))

    def __getitem__(self, perm_name):
        return self.user.has_perm('%s.%s' % (self.app_label, perm_name),
                                  self.perms_wrapper.get_local_site())

    def __nonzero__(self):
        return super(AllPermsLookupDict, self).__nonzero__()

    def __bool__(self):
        return super(AllPermsLookupDict, self).__bool__()


class AllPermsWrapper(PermWrapper):
    def __init__(self, user, local_site_name):
        super(AllPermsWrapper, self).__init__(user)

        self.local_site_name = local_site_name
        self.local_site = None

    def __getitem__(self, app_label):
        return AllPermsLookupDict(self.user, app_label, self)

    def get_local_site(self):
        if self.local_site_name is None:
            return None

        if not self.local_site:
            self.local_site = LocalSite.objects.get(name=self.local_site_name)

        return self.local_site


def localsite(request):
    """Returns context variables useful to Local Sites.

    This provides the name of the Local Site (``local_site_name``), and
    a permissions variable used for accessing user permissions (``perm``).

    ``perm`` overrides the permissions provided by the Django auth framework.
    These permissions cover Local Sites along with the standard global
    permissions.
    """
    local_site_name = getattr(request, '_local_site_name', None)

    return {
        'local_site_name': local_site_name,
        'perms': AllPermsWrapper(request.user, local_site_name),
    }
