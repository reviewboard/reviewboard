"""Unit tests for reviewboard.accounts.forms.pages.APITokensForm.

Version Added:
    9.0
"""

from __future__ import annotations

from reviewboard.accounts.forms.pages import APITokensForm
from reviewboard.accounts.pages import AuthenticationPage
from reviewboard.accounts.views import MyAccountView
from reviewboard.extensions.hooks import WebAPITokenPoliciesHook
from reviewboard.extensions.tests.testcases import ExtensionHookTestCaseMixin
from reviewboard.testing import TestCase
from reviewboard.webapi.token_policies import BaseWebAPITokenPolicy


class _MyTokenPolicy(BaseWebAPITokenPolicy):
    token_policy_id = 'my-policy'
    name = 'My Policy'

    default_token_policy_doc = {
        'resources': {
            '*': {
                'allow': ['GET'],
                'block': ['*'],
            },
        },
    }


class APITokensFormTests(ExtensionHookTestCaseMixin, TestCase):
    """Unit tests for APITokensForm.

    Version Added:
        9.0
    """

    def test_get_js_view_data_policies(self) -> None:
        """Testing APITokensForm.get_js_view_data includes the built-in
        token policies
        """
        form = self._create_form()

        self.assertEqual(
            form.get_js_view_data()['policies'],
            [
                {
                    'id': 'read-write',
                    'name': 'Full access',
                    'policyDoc': {},
                },
                {
                    'id': 'read-only',
                    'name': 'Read-only',
                    'policyDoc': {
                        'resources': {
                            '*': {
                                'allow': ['GET', 'HEAD', 'OPTIONS'],
                                'block': ['*'],
                            },
                        },
                    },
                },
            ])

    def test_get_js_view_data_policies_with_extension(self) -> None:
        """Testing APITokensForm.get_js_view_data includes token policies
        registered by extensions
        """
        extension = self.extension
        assert extension is not None

        WebAPITokenPoliciesHook(extension, [_MyTokenPolicy])

        form = self._create_form()

        self.assertEqual(
            [
                policy['id']
                for policy in form.get_js_view_data()['policies']
            ],
            [
                'read-write',
                'read-only',
                'my-policy',
            ])

    def _create_form(self) -> APITokensForm:
        """Return a new API Tokens form for testing.

        Returns:
            reviewboard.accounts.forms.pages.APITokensForm:
            The new form.
        """
        user = self.create_user()
        request = self.create_http_request(user=user)

        view = MyAccountView()
        view.request = request

        page = AuthenticationPage(view, request, user)

        return APITokensForm(
            page=page,
            request=request,
            user=user,
        )
