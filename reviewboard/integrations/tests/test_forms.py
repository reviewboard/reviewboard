from __future__ import unicode_literals

from django import forms
from django.contrib.auth.models import User
from django.test import RequestFactory
from djblets.forms.fields import ConditionsField

from reviewboard.integrations.base import Integration, get_integration_manager
from reviewboard.integrations.forms import IntegrationConfigForm
from reviewboard.integrations.models import IntegrationConfig
from reviewboard.reviews.conditions import ReviewRequestConditionChoices
from reviewboard.reviews.models import Group
from reviewboard.site.models import LocalSite
from reviewboard.testing.testcase import TestCase


class MyIntegration(Integration):
    integration_id = 'my-integration'


class MyConfigForm(IntegrationConfigForm):
    my_conditions = ConditionsField(ReviewRequestConditionChoices)
    group = forms.ModelChoiceField(queryset=Group.objects.order_by('pk'))

    def serialize_group_field(self, group):
        return group.name


class IntegrationConfigFormTests(TestCase):
    """Unit tests for reviewboard.integrations.forms.IntegrationConfigForm."""

    def setUp(self):
        super(IntegrationConfigFormTests, self).setUp()

        self.local_site_1 = LocalSite.objects.create(name='site1')
        self.local_site_2 = LocalSite.objects.create(name='site2')

        self.manager = get_integration_manager()
        self.integration = \
            self.manager.register_integration_class(MyIntegration)

        self.request = RequestFactory().request()
        self.request.user = User.objects.create(username='test-user')

        self.local_site_1_group = self.create_review_group(
            name='local-site-1-group',
            local_site=self.local_site_1)

        self.local_site_2_group = self.create_review_group(
            name='local-site-2-group',
            local_site=self.local_site_2)

        self.global_site_group = self.create_review_group(
            name='global-site-group')

    def tearDown(self):
        super(IntegrationConfigFormTests, self).tearDown()

        self.manager.unregister_integration_class(MyIntegration)

    def test_without_localsite(self):
        """Testing IntegrationConfigForm without a LocalSite"""
        # Make sure the initial state and querysets are what we expect on init.
        form = MyConfigForm(integration=self.integration,
                            request=self.request)

        self.assertIsNone(form.limited_to_local_site)
        self.assertIn('local_site', form.fields)
        self.assertEqual(list(form.fields['group'].queryset),
                         [self.local_site_1_group,
                          self.local_site_2_group,
                          self.global_site_group])
        self.assertNotIn('local_site',
                         form.fields['my_conditions'].choice_kwargs)

        # Now test what happens when it's been fed data and validated.
        form = MyConfigForm(
            integration=self.integration,
            request=self.request,
            data={
                'name': 'Test',
                'my_conditions_last_id': '0',
                'my_conditions_mode': 'all',
                'my_conditions_choice[0]': 'review-groups',
                'my_conditions_operator[0]': 'contains-any',
                'my_conditions_value[0]': [self.global_site_group.pk],
                'group': self.global_site_group.pk,
            })

        self.assertIsNone(form.limited_to_local_site)
        self.assertIn('local_site', form.fields)
        self.assertEqual(list(form.fields['group'].queryset),
                         [self.local_site_1_group,
                          self.local_site_2_group,
                          self.global_site_group])
        self.assertNotIn('local_site',
                         form.fields['my_conditions'].choice_kwargs)

        self.assertTrue(form.is_valid())

        # Make sure any overridden querysets have been restored, so users can
        # still change entries.
        self.assertEqual(list(form.fields['group'].queryset),
                         [self.local_site_1_group,
                          self.local_site_2_group,
                          self.global_site_group])

        config = form.save()
        self.assertIsNone(config.local_site)
        self.assertEqual(config.settings['group'], 'global-site-group')

        condition_set = config.settings['my_conditions']
        self.assertEqual(list(condition_set.conditions[0].value),
                         [self.global_site_group])

    def _test_init_with_limit_to_local_site(self):
        """Testing IntegrationConfigForm initialization with
        limit_to_local_site
        """
        LocalSite.objects.create(name='local-site-1')
        local_site = LocalSite.objects.create(name='local-site-2')

        form = MyConfigForm(integration=self.integration,
                            request=self.request,
                            limit_to_local_site=local_site)

        self.assertNotIn('local_site', form.fields)
        self.assertEqual(form.limited_to_local_site, local_site)
        self.assertEqual(
            form.fields['my_conditions'].choice_kwargs,
            {
                'local_site': local_site,
            })

    def test_without_localsite_and_instance(self):
        """Testing IntegrationConfigForm without a LocalSite and editing
        instance
        """
        config = IntegrationConfig.objects.create(
            integration_id=self.integration.integration_id)

        form = MyConfigForm(
            integration=self.integration,
            request=self.request,
            instance=config,
            data={
                'name': 'Test',
                'my_conditions_last_id': '0',
                'my_conditions_mode': 'all',
                'my_conditions_choice[0]': 'review-groups',
                'my_conditions_operator[0]': 'contains-any',
                'my_conditions_value[0]': [self.global_site_group.pk],
                'group': self.global_site_group.pk,
            })

        self.assertTrue(form.is_valid())

        new_config = form.save()
        self.assertEqual(config.pk, new_config.pk)
        self.assertIsNone(new_config.local_site)

    def test_without_localsite_and_with_local_site_values(self):
        """Testing IntegrationConfigForm without a LocalSite and with field
        values on a LocalSite
        """
        form = MyConfigForm(
            integration=self.integration,
            request=self.request,
            data={
                'name': 'Test',
                'my_conditions_last_id': '0',
                'my_conditions_mode': 'all',
                'my_conditions_choice[0]': 'review-groups',
                'my_conditions_operator[0]': 'contains-any',
                'my_conditions_value[0]': [self.local_site_1_group.pk],
                'group': self.local_site_2_group.pk,
            })
        self.assertFalse(form.is_valid())
        self.assertEqual(
            form.errors,
            {
                'group': [
                    'Select a valid choice. That choice is not one of the '
                    'available choices.',
                ],
                'my_conditions': [
                    'There was an error with one of your conditions.'
                ],
            })
        self.assertEqual(
            form.fields['my_conditions'].widget.condition_errors,
            {
                0: 'Select a valid choice. 1 is not one of the available '
                   'choices.',
            })

    def test_with_limited_localsite(self):
        """Testing IntegrationConfigForm limited to a LocalSite"""
        form = MyConfigForm(integration=self.integration,
                            request=self.request,
                            limit_to_local_site=self.local_site_1)

        self.assertEqual(form.limited_to_local_site, self.local_site_1)
        self.assertNotIn('local_site', form.fields)
        self.assertEqual(list(form.fields['group'].queryset),
                         [self.local_site_1_group])
        self.assertEqual(
            form.fields['my_conditions'].choice_kwargs.get('local_site'),
            self.local_site_1)

    def test_with_limited_localsite_and_changing_site(self):
        """Testing IntegrationConfigForm limited to a LocalSite and changing
        LocalSite
        """
        form = MyConfigForm(
            integration=self.integration,
            request=self.request,
            data={
                'name': 'Test',
                'my_conditions_last_id': '0',
                'my_conditions_mode': 'all',
                'my_conditions_choice[0]': 'review-groups',
                'my_conditions_operator[0]': 'contains-any',
                'my_conditions_value[0]': [self.local_site_1_group.pk],
                'group': self.local_site_1_group.pk,
                'local_site': self.local_site_2.pk,
            },
            limit_to_local_site=self.local_site_1)

        self.assertEqual(form.limited_to_local_site, self.local_site_1)
        self.assertTrue(form.is_valid())
        self.assertEqual(form.cleaned_data['local_site'], self.local_site_1)
        self.assertEqual(list(form.fields['group'].queryset),
                         [self.local_site_1_group])
        self.assertEqual(
            form.fields['my_conditions'].choice_kwargs.get('local_site'),
            self.local_site_1)

        new_config = form.save()
        self.assertEqual(new_config.local_site, self.local_site_1)

    def test_with_limited_localsite_and_compatible_instance(self):
        """Testing IntegrationConfigForm limited to a LocalSite and editing
        compatible instance
        """
        config = IntegrationConfig.objects.create(
            integration_id=self.integration.integration_id,
            local_site=self.local_site_1)

        # This should just simply not raise an exception.
        MyConfigForm(integration=self.integration,
                     instance=config,
                     request=self.request,
                     limit_to_local_site=self.local_site_1)

    def test_with_limited_localsite_and_incompatible_instance(self):
        """Testing IntegrationConfigForm limited to a LocalSite and editing
        incompatible instance
        """
        config1 = IntegrationConfig.objects.create(
            integration_id=self.integration.integration_id)
        config2 = IntegrationConfig.objects.create(
            integration_id=self.integration.integration_id,
            local_site=self.local_site_2)

        error_message = (
            'The provided instance is not associated with a LocalSite '
            'compatible with this form. Please contact support.'
        )

        with self.assertRaisesMessage(ValueError, error_message):
            MyConfigForm(integration=self.integration,
                         request=self.request,
                         instance=config1,
                         limit_to_local_site=self.local_site_1)

        with self.assertRaisesMessage(ValueError, error_message):
            MyConfigForm(integration=self.integration,
                         request=self.request,
                         instance=config2,
                         limit_to_local_site=self.local_site_1)

    def test_with_limited_localsite_and_invalid_values(self):
        """Testing IntegrationConfigForm limited to a LocalSite with values
        not on the LocalSite
        """
        form = MyConfigForm(
            integration=self.integration,
            request=self.request,
            data={
                'name': 'Test',
                'my_conditions_last_id': '0',
                'my_conditions_mode': 'all',
                'my_conditions_choice[0]': 'review-groups',
                'my_conditions_operator[0]': 'contains-any',
                'my_conditions_value[0]': [self.local_site_2_group.pk],
                'group': self.global_site_group.pk,
            },
            limit_to_local_site=self.local_site_1)

        self.assertFalse(form.is_valid())
        self.assertEqual(
            form.errors,
            {
                'group': [
                    'Select a valid choice. That choice is not one of the '
                    'available choices.',
                ],
                'my_conditions': [
                    'There was an error with one of your conditions.'
                ],
            })
        self.assertEqual(
            form.fields['my_conditions'].widget.condition_errors,
            {
                0: 'Select a valid choice. 2 is not one of the available '
                   'choices.',
            })

    def test_with_localsite_in_data(self):
        """Testing IntegrationConfigForm with a LocalSite in form data"""
        # Make sure the initial state and querysets are what we expect on init.
        form = MyConfigForm(integration=self.integration,
                            request=self.request)

        self.assertIsNone(form.limited_to_local_site)
        self.assertIn('local_site', form.fields)
        self.assertEqual(list(form.fields['group'].queryset),
                         [self.local_site_1_group,
                          self.local_site_2_group,
                          self.global_site_group])
        self.assertNotIn('local_site',
                         form.fields['my_conditions'].choice_kwargs)

        # Now test what happens when it's been fed data and validated.
        form = MyConfigForm(
            integration=self.integration,
            request=self.request,
            data={
                'name': 'Test',
                'my_conditions_last_id': '0',
                'my_conditions_mode': 'all',
                'my_conditions_choice[0]': 'review-groups',
                'my_conditions_operator[0]': 'contains-any',
                'my_conditions_value[0]': [self.local_site_1_group.pk],
                'group': self.local_site_1_group.pk,
                'local_site': self.local_site_1.pk,
            })

        self.assertIsNone(form.limited_to_local_site)
        self.assertIn('local_site', form.fields)
        self.assertEqual(list(form.fields['group'].queryset),
                         [self.local_site_1_group,
                          self.local_site_2_group,
                          self.global_site_group])
        self.assertNotIn('local_site',
                         form.fields['my_conditions'].choice_kwargs)

        self.assertTrue(form.is_valid())

        # Make sure any overridden querysets have been restored, so users can
        # still change entries.
        self.assertEqual(list(form.fields['group'].queryset),
                         [self.local_site_1_group,
                          self.local_site_2_group,
                          self.global_site_group])
        self.assertNotIn('local_site',
                         form.fields['my_conditions'].choice_kwargs)

        new_config = form.save()
        self.assertEqual(new_config.local_site, self.local_site_1)
        self.assertEqual(new_config.settings['group'], 'local-site-1-group')

        condition_set = new_config.settings['my_conditions']
        self.assertEqual(list(condition_set.conditions[0].value),
                         [self.local_site_1_group])

    def test_with_localsite_in_data_and_instance(self):
        """Testing IntegrationConfigForm with a LocalSite in form data and
        editing instance
        """
        config = IntegrationConfig.objects.create(
            integration_id=self.integration.integration_id)

        form = MyConfigForm(
            integration=self.integration,
            request=self.request,
            data={
                'name': 'Test',
                'my_conditions_last_id': '0',
                'my_conditions_mode': 'all',
                'my_conditions_choice[0]': 'review-groups',
                'my_conditions_operator[0]': 'contains-any',
                'my_conditions_value[0]': [self.local_site_1_group.pk],
                'group': self.local_site_1_group.pk,
                'local_site': self.local_site_1.pk,
            },
            instance=config)
        self.assertTrue(form.is_valid())

        new_config = form.save()
        self.assertEqual(config.pk, new_config.pk)
        self.assertEqual(new_config.local_site, self.local_site_1)

    def test_with_localsite_in_data_and_invalid_values(self):
        """Testing IntegrationConfigForm with a LocalSite in form data and
        values not on the LocalSite
        """
        form = MyConfigForm(
            integration=self.integration,
            request=self.request,
            data={
                'name': 'Test',
                'my_conditions_last_id': '0',
                'my_conditions_mode': 'all',
                'my_conditions_choice[0]': 'review-groups',
                'my_conditions_operator[0]': 'contains-any',
                'my_conditions_value[0]': [self.local_site_2_group.pk],
                'group': self.global_site_group.pk,
                'local_site': self.local_site_1.pk,
            })
        self.assertFalse(form.is_valid())
        self.assertEqual(
            form.errors,
            {
                'group': [
                    'Select a valid choice. That choice is not one of the '
                    'available choices.',
                ],
                'my_conditions': [
                    'There was an error with one of your conditions.'
                ],
            })
        self.assertEqual(
            form.fields['my_conditions'].widget.condition_errors,
            {
                0: 'Select a valid choice. 2 is not one of the available '
                   'choices.',
            })
