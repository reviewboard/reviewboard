.. _integration-hook:

===============
IntegrationHook
===============

:py:class:`reviewboard.extensions.hooks.IntegrationHook` is used to register
new :ref:`integrations` in Review Board.

Integrations are similar to extensions, but are intended for connecting to
third-party services or tools. Each integration can have multiple
configurations, making them ideal for cases where different groups or teams
may have different requirements. For example, one group may want notifications
posted to their chat service while another may not.

Extensions can provide integrations by subclassing
:py:class:`reviewboard.integrations.Integration` and providing the necessary
functions and attributes. See :ref:`djblets:writing-integrations` to learn how
to write an integration.

Once you have an integration class, you can use this hook to register it as
part of your extension.


Example
=======

.. code-block:: python

    import json
    import logging
    from typing import TYPE_CHECKING
    from urllib.request import Request, urlopen

    from django import forms
    from djblets.forms.fields import ConditionsField
    from reviewboard.extensions.base import Extension
    from reviewboard.extensions.hooks import IntegrationHook, SignalHook
    from reviewboard.integrations.base import Integration
    from reviewboard.integrations.forms import IntegrationConfigForm
    from reviewboard.reviews.conditions import ReviewRequestConditionChoices

    if TYPE_CHECKING:
        from collections.abc import Mapping

        from django.contrib.auth.models import User
        from reviewboard.changedescs.models import ChangeDescription
        from reviewboard.reviews.models import ReviewRequest


    class SampleIntegrationConfigForm(IntegrationConfigForm):
        endpoint_url = forms.CharField(label='Endpoint URL', required=True)
        client_id = forms.CharField(label='Client ID', required=True)
        conditions = ConditionsField(ReviewRequestConditionChoices,
                                     label='Conditions')


    class SampleIntegration(Integration):
        name = 'Sample Integration'
        description = 'This is my special integration that does stuff.'

        default_settings = {
            'endpoint_url': 'https://example.com/endpoint/',
            'client_id': 'abc123',
        }

        config_form_cls = SampleIntegrationConfigForm

        @cached_property
        def icon_static_urls(self) -> Mapping[str, str]:
            extension = SampleExtension.instance

            return {
                '1x': extension.get_static_url('images/icon.png'),
                '2x': extension.get_static_url('images/icon@2x.png'),
            }

        def initialize(self) -> None:
            SignalHook(self, review_request_published,
                       self._on_review_request_published)

        def _on_review_request_published(
            self,
            user: User,
            review_request: ReviewRequest,
            changedesc: ChangeDescription,
            **kwargs,
        ) -> None:
            for config in self.get_configs(review_request.local_site):
                if not config.match_conditions(form_cls=self.config_form_cls,
                                               review_request=review_request):
                    continue

                try:
                    urlopen(Request(config['endpoint_url'], json.dumps({
                        'client_id': config['client_id'],
                        'review_request_id': review_request.display_id,
                    })
                except Exception as e:
                    logging.exception('Failed to send notification: %s', e)


    class SampleExtension(Extension):
        def initialize(self) -> None:
            IntegrationHook(self, SampleIntegration)
