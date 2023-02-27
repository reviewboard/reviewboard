"""Unit tests for reviewboard.reviews.manager.StatusUpdateManager.

Version Added:
    5.0.3
"""

from __future__ import annotations

from reviewboard.integrations.base import Integration, get_integration_manager
from reviewboard.integrations.models import IntegrationConfig
from reviewboard.reviews.models import StatusUpdate
from reviewboard.testing import TestCase


class MyIntegration(Integration):
    integration_id = 'my-integration'
    name = 'My Integration'


class StatusUpdateManagerTests(TestCase):
    """Unit tests for reviewboard.reviews.manager.StatusUpdateManager.

    Version Added:
        5.0.3
    """

    fixtures = ['test_users']

    def test_create_for_integration(self) -> None:
        """Testing StatusUpdateManager.create_for_integration"""
        self._run_create_for_integration_test()

    def test_create_for_integration_with_description(self) -> None:
        """Testing StatusUpdateManager.create_for_integration with description=
        """
        self._run_create_for_integration_test(
            description='my custom description...',
            expected_description='my custom description...')

    def test_create_for_integration_with_state(self) -> None:
        """Testing StatusUpdateManager.create_for_integration with state=
        """
        self._run_create_for_integration_test(
            state=StatusUpdate.DONE_FAILURE,
            expected_state=StatusUpdate.DONE_FAILURE)

    def test_create_for_integration_with_service_id(self) -> None:
        """Testing StatusUpdateManager.create_for_integration with service_id=
        """
        self._run_create_for_integration_test(
            service_id='xxx-my-service',
            expected_service_id='xxx-my-service')

    def test_create_for_integration_with_run_manually(self) -> None:
        """Testing StatusUpdateManager.create_for_integration with
        IntegrationConfig.run_manually
        """
        self._run_create_for_integration_test(
            config_run_manually=True,
            expected_state=StatusUpdate.NOT_YET_RUN,
            expected_description='waiting to run.')

    def test_create_for_integration_with_run_manually_and_description(
        self,
    ) -> None:
        """Testing StatusUpdateManager.create_for_integration with
        IntegrationConfig.run_manually and description=
        """
        self._run_create_for_integration_test(
            config_run_manually=True,
            description='my custom description...',
            expected_state=StatusUpdate.NOT_YET_RUN,
            expected_description='my custom description...')

    def test_create_for_integration_with_run_manually_and_state(self) -> None:
        """Testing StatusUpdateManager.create_for_integration with
        IntegrationConfig.run_manually and state=
        """
        self._run_create_for_integration_test(
            config_run_manually=True,
            state=StatusUpdate.DONE_FAILURE,
            expected_state=StatusUpdate.DONE_FAILURE,
            expected_description='waiting to run.')

    def test_create_for_integration_with_can_retry(self) -> None:
        """Testing StatusUpdateManager.create_for_integration with
        can_retry=True
        """
        self._run_create_for_integration_test(can_retry=True)

    def _run_create_for_integration_test(
        self,
        *,
        config_run_manually: bool = False,
        expected_state: str = StatusUpdate.PENDING,
        expected_service_id: str = 'my-integration',
        expected_summary: str = 'My Integration',
        expected_description: str = 'starting...',
        **kwargs,
    ) -> None:
        """Run a test for create_for_integration.

        Args:
            config_run_manually (bool, optional):
                Whether to set ``run_manually=True`` in the configuration.

            expected_state (str, optional):
                The expected Status Update state.

            expected_service_id (str, optional):
                The expected Status Update service ID.

            expected_summary (str, optional):
                The expected Status Update summary.

            expected_description (str, optional):
                The expected Status Update description.

            **kwargs (dict, optional):
                Keyword arguments to pass to
                :py:meth:`StatusUpdate.create_for_integration()
                <reviewboard.reviews.managers.StatusUpdate.
                create_for_integration>`.

        Raises:
            AssertionError:
                An expectation failed in the test.
        """
        config = IntegrationConfig.objects.create(
            integration_id=MyIntegration.integration_id,
            name='my-config')

        if config_run_manually:
            config.set('run_manually', True)

        bot_user = self.create_user(username='bot')
        review_request = self.create_review_request()

        integration_mgr = get_integration_manager()
        integration_mgr.register_integration_class(MyIntegration)

        try:
            integration = integration_mgr.get_integration(
                MyIntegration.integration_id)

            status_update = StatusUpdate.objects.create_for_integration(
                integration,
                config=config,
                user=bot_user,
                review_request=review_request,
                **kwargs)
        finally:
            integration_mgr.unregister_integration_class(MyIntegration)

        self.assertEqual(status_update.state, expected_state)
        self.assertEqual(status_update.service_id, expected_service_id)
        self.assertEqual(status_update.summary, expected_summary)
        self.assertEqual(status_update.description, expected_description)

        self.assertEqual(status_update.integration_config, config)
        self.assertEqual(status_update.user, bot_user)
        self.assertEqual(status_update.review_request, review_request)
        self.assertEqual(status_update.extra_data, {
            '__integration_config_id': config.pk,
            'can_retry': kwargs.get('can_retry', False),
        })
