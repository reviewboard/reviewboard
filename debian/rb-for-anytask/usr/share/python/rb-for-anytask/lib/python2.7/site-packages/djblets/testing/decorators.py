from __future__ import unicode_literals


def add_fixtures(fixtures, replace=False):
    """Adds or replaces the fixtures used for this test.

    This must be used along with :py:func:`djblets.testing.testcases.TestCase`.
    """
    def _dec(func):
        func._fixtures = fixtures
        func._replace_fixtures = replace
        return func

    return _dec
