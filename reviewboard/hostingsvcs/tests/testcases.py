from __future__ import unicode_literals

from kgb import SpyAgency

from reviewboard.hostingsvcs.models import HostingServiceAccount
from reviewboard.hostingsvcs.service import get_hosting_service
from reviewboard.testing import TestCase


class ServiceTests(SpyAgency, TestCase):
    service_name = None

    def __init__(self, *args, **kwargs):
        super(ServiceTests, self).__init__(*args, **kwargs)

        self.assertNotEqual(self.service_name, None)
        self.service_class = get_hosting_service(self.service_name)

    def setUp(self):
        super(ServiceTests, self).setUp()
        self.assertNotEqual(self.service_class, None)

    def _get_repository_info(self, field, plan=None):
        if plan:
            self.assertNotEqual(self.service_class.plans, None)
            result = None

            for plan_type, info in self.service_class.plans:
                if plan_type == plan:
                    result = info[field]
                    break

            self.assertNotEqual(result, None)
            return result
        else:
            self.assertEqual(self.service_class.plans, None)
            self.assertTrue(hasattr(self.service_class, field))

            return getattr(self.service_class, field)

    def _get_form(self, plan=None, fields={}):
        form = self._get_repository_info('form', plan)
        self.assertNotEqual(form, None)

        form = form(fields)
        self.assertTrue(form.is_valid())

        return form

    def _get_hosting_account(self, use_url=False, local_site=None):
        if use_url:
            hosting_url = 'https://example.com'
        else:
            hosting_url = None

        return HostingServiceAccount(service_name=self.service_name,
                                     username='myuser',
                                     hosting_url=hosting_url,
                                     local_site=local_site)

    def _get_service(self):
        return self._get_hosting_account().service

    def _get_repository_fields(self, tool_name, fields, plan=None,
                               with_url=False, hosting_account=None):
        form = self._get_form(plan, fields)

        if not hosting_account:
            hosting_account = self._get_hosting_account(with_url)

        service = hosting_account.service
        self.assertNotEqual(service, None)

        field_vars = form.clean().copy()
        field_vars.update(hosting_account.data)

        return service.get_repository_fields(username=hosting_account.username,
                                             hosting_url='https://example.com',
                                             plan=plan,
                                             tool_name=tool_name,
                                             field_vars=field_vars)
