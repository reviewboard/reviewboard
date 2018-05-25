"""Custom search index fields."""

from __future__ import unicode_literals

from haystack import indexes


class BooleanField(indexes.BooleanField):
    """A custom BooleanField.

    This works around `an issue in django-haystack
    <https://github.com/django-haystack/django-haystack/issues/801>`_ that
    results in BooleanFields always returning ``True``.
    """

    value_map = {
        'true': True,
        'false': False,
    }

    def convert(self, value):
        """Convert value to a boolean value.

        Args:
            value (unicode):
                The value to convert

        Returns:
            bool:
            The boolean representation of ``value``.
        """
        if value is None:
            return None

        try:
            return self.value_map[value]
        except KeyError:
            return bool(value)
