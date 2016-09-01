from __future__ import unicode_literals

from django.test import RequestFactory
from djblets.forms.fields import ConditionsField

from reviewboard.integrations.base import Integration, get_integration_manager
from reviewboard.integrations.forms import IntegrationConfigForm
from reviewboard.reviews.conditions import ReviewRequestConditionChoices
from reviewboard.site.models import LocalSite
from reviewboard.testing.testcase import TestCase


class MyIntegration(Integration):
    pass


class MyConfigForm(IntegrationConfigForm):
    my_conditions = ConditionsField(ReviewRequestConditionChoices)


class IntegrationConfigFormTests(TestCase):
    """Unit tests for reviewboard.integrations.forms.IntegrationConfigForm."""

    def setUp(self):
        super(IntegrationConfigFormTests, self).setUp()

        self.integration = MyIntegration(get_integration_manager())
        self.request = RequestFactory().request()

    def test_init(self):
        """Testing IntegrationConfigForm initialization"""
        form = MyConfigForm(self.integration, self.request)

        local_site_1 = LocalSite.objects.create(name='local-site-1')
        local_site_2 = LocalSite.objects.create(name='local-site-2')

        local_site_ids = list(
            form.fields['local_site'].queryset
            .order_by('pk')
            .values_list('pk', flat=True)
        )

        self.assertIsNone(form.limit_to_local_site)
        self.assertEqual(local_site_ids, [local_site_1.pk, local_site_2.pk])
        self.assertEqual(form.fields['my_conditions'].choice_kwargs, {})

    def test_init_with_limit_to_local_site(self):
        """Testing IntegrationConfigForm initialization with
        limit_to_local_site
        """
        LocalSite.objects.create(name='local-site-1')
        local_site = LocalSite.objects.create(name='local-site-2')

        form = MyConfigForm(self.integration, self.request,
                            limit_to_local_site=local_site)

        local_site_ids = list(
            form.fields['local_site'].queryset
            .order_by('pk')
            .values_list('pk', flat=True)
        )

        self.assertEqual(form.limit_to_local_site, local_site)
        self.assertEqual(local_site_ids, [local_site.pk])
        self.assertEqual(
            form.fields['my_conditions'].choice_kwargs,
            {
                'local_site': local_site,
            })
