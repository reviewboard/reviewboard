from __future__ import unicode_literals

from django.utils import six

from reviewboard.testing import TestCase
from reviewboard.webapi.base import WebAPIResource


class PolicyTestResource(WebAPIResource):
    policy_id = 'test'


class APIPolicyTests(TestCase):
    """Tests API policy through WebAPITokens."""
    def setUp(self):
        super(APIPolicyTests, self).setUp()

        self.resource = PolicyTestResource()

    def test_default_policy(self):
        """Testing API policy enforcement with default policy"""
        self.assert_policy(
            {},
            allowed_methods=['HEAD', 'GET', 'POST', 'PATCH', 'PUT', 'DELETE'])

    def test_global_allow_all(self):
        """Testing API policy enforcement with *.allow=*"""
        self.assert_policy(
            {
                '*': {
                    'allow': ['*'],
                }
            },
            allowed_methods=['HEAD', 'GET', 'POST', 'PATCH', 'PUT', 'DELETE'])

    def test_global_block_all(self):
        """Testing API policy enforcement with *.block=*"""
        self.assert_policy(
            {
                '*': {
                    'block': ['*'],
                }
            },
            blocked_methods=['HEAD', 'GET', 'POST', 'PATCH', 'PUT', 'DELETE'])

    def test_global_block_all_and_resource_allow_all(self):
        """Testing API policy enforcement with *.block=* and
        <resource>.*.allow=*
        """
        self.assert_policy(
            {
                '*': {
                    'block': ['*'],
                },
                'test': {
                    '*': {
                        'allow': ['*'],
                    },
                }
            },
            allowed_methods=['HEAD', 'GET', 'POST', 'PATCH', 'PUT', 'DELETE'])

    def test_global_allow_all_and_resource_block_all(self):
        """Testing API policy enforcement with *.allow=* and
        <resource>.*.block=*
        """
        self.assert_policy(
            {
                '*': {
                    'allow': ['*'],
                },
                'test': {
                    '*': {
                        'block': ['*'],
                    },
                }
            },
            blocked_methods=['HEAD', 'GET', 'POST', 'PATCH', 'PUT', 'DELETE'])

    def test_global_block_all_and_resource_all_allow_methods(self):
        """Testing API policy enforcement with *.block=* and
        <resource>.*.allow=[methods]
        """
        self.assert_policy(
            {
                '*': {
                    'block': ['*'],
                },
                'test': {
                    '*': {
                        'allow': ['GET', 'PUT'],
                    },
                }
            },
            allowed_methods=['GET', 'PUT'],
            blocked_methods=['HEAD', 'POST', 'PATCH', 'DELETE'])

    def test_global_allow_all_and_resource_all_block_specific(self):
        """Testing API policy enforcement with *.allow=* and
        <resource>.*.block=[methods]
        """
        self.assert_policy(
            {
                '*': {
                    'allow': ['*'],
                },
                'test': {
                    '*': {
                        'block': ['GET', 'PUT'],
                    },
                }
            },
            allowed_methods=['HEAD', 'POST', 'PATCH', 'DELETE'],
            blocked_methods=['GET', 'PUT'])

    def test_resource_block_all_and_allow_methods(self):
        """Testing API policy enforcement with <resource>.*.block=* and
        <resource>.*.allow=[methods] for specific methods
        """
        self.assert_policy(
            {
                'test': {
                    '*': {
                        'block': ['*'],
                        'allow': ['GET', 'PUT'],
                    }
                }
            },
            allowed_methods=['GET', 'PUT'],
            blocked_methods=['HEAD', 'POST', 'PATCH', 'DELETE'])

    def test_resource_allow_all_and_block_methods(self):
        """Testing API policy enforcement with <resource>.*.allow=* and
        <resource>.*.block=[methods] for specific methods
        """
        self.assert_policy(
            {
                'test': {
                    '*': {
                        'allow': ['*'],
                        'block': ['GET', 'PUT'],
                    },
                }
            },
            allowed_methods=['HEAD', 'POST', 'DELETE'],
            blocked_methods=['GET', 'PUT'])

    def test_id_allow_all(self):
        """Testing API policy enforcement with <resource>.<id>.allow=*"""
        self.assert_policy(
            {
                'test': {
                    '42': {
                        'allow': ['*'],
                    }
                }
            },
            resource_id=42,
            allowed_methods=['HEAD', 'GET', 'POST', 'PUT', 'DELETE'])

    def test_id_block_all(self):
        """Testing API policy enforcement with <resource>.<id>.block=*"""
        policy = {
            'test': {
                '42': {
                    'block': ['*'],
                }
            }
        }

        self.assert_policy(
            policy,
            resource_id=42,
            blocked_methods=['HEAD', 'GET', 'POST', 'PUT', 'DELETE'])

        self.assert_policy(
            policy,
            resource_id=100,
            allowed_methods=['HEAD', 'GET', 'POST', 'PUT', 'DELETE'])

    def test_resource_block_all_and_id_allow_all(self):
        """Testing API policy enforcement with <resource>.*.block=* and
        <resource>.<id>.allow=*
        """
        policy = {
            'test': {
                '*': {
                    'block': ['*'],
                },
                '42': {
                    'allow': ['*'],
                }
            }
        }

        self.assert_policy(
            policy,
            resource_id=42,
            allowed_methods=['HEAD', 'GET', 'POST', 'PUT', 'DELETE'])

        self.assert_policy(
            policy,
            resource_id=100,
            blocked_methods=['HEAD', 'GET', 'POST', 'PUT', 'DELETE'])

    def test_resource_allow_all_and_id_block_all(self):
        """Testing API policy enforcement with <resource>.<id>.allow=* and
        <resource>.<id>.block=*
        """
        policy = {
            'test': {
                '*': {
                    'allow': ['*'],
                },
                '42': {
                    'block': ['*'],
                }
            }
        }

        self.assert_policy(
            policy,
            resource_id=42,
            blocked_methods=['HEAD', 'GET', 'POST', 'PUT', 'DELETE'])

        self.assert_policy(
            policy,
            resource_id=100,
            allowed_methods=['HEAD', 'GET', 'POST', 'PUT', 'DELETE'])

    def test_global_block_all_and_id_allow_all(self):
        """Testing API policy enforcement with *.<id>.block=* and
        <resource>.<id>.allow=*
        """
        self.assert_policy(
            {
                '*': {
                    'block': ['*'],
                },
                'test': {
                    '42': {
                        'allow': ['*'],
                    }
                }
            },
            resource_id=42,
            allowed_methods=['HEAD', 'GET', 'POST', 'PUT', 'DELETE'])

    def test_global_allow_all_and_id_block_all(self):
        """Testing API policy enforcement with *.<id>.allow=* and
        <resource>.<id>.block=*"""
        policy = {
            '*': {
                'allow': ['*'],
            },
            'test': {
                '42': {
                    'block': ['*'],
                }
            }
        }

        self.assert_policy(
            policy,
            resource_id=42,
            blocked_methods=['HEAD', 'GET', 'POST', 'PUT', 'DELETE'])

        self.assert_policy(
            policy,
            resource_id=100,
            allowed_methods=['HEAD', 'GET', 'POST', 'PUT', 'DELETE'])

    def test_policy_methods_conflict(self):
        """Testing API policy enforcement with methods conflict"""
        self.assert_policy(
            {
                'test': {
                    '*': {
                        'allow': ['*'],
                        'block': ['*'],
                    },
                }
            },
            blocked_methods=['HEAD', 'GET', 'POST', 'PUT', 'DELETE'])

    def assert_policy(self, policy, allowed_methods=[], blocked_methods=[],
                      resource_id=None):
        if resource_id is not None:
            resource_id = six.text_type(resource_id)

        for method in allowed_methods:
            allowed = self.resource.is_resource_method_allowed(
                policy, method, resource_id)

            if not allowed:
                self.fail('Expected %s to be allowed, but was blocked'
                          % method)

        for method in blocked_methods:
            allowed = self.resource.is_resource_method_allowed(
                policy, method, resource_id)

            if allowed:
                self.fail('Expected %s to be blocked, but was allowed'
                          % method)
