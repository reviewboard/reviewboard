"""Condition support for Local Sites."""

from __future__ import unicode_literals


class LocalSiteModelChoiceMixin(object):
    """Mixin to restrict model choices to those on a Local Site.

    This will ensure that any queries are bound to a
    :py:class:`~reviewboard.site.models.LocalSite`, if provided to the
    condition field widget through
    :py:attr:`~djblets.forms.widgets.ConditionsWidget.choice_kwargs`.
    """

    #: The field on the model pointing to a LocalSite.
    local_site_attr = 'local_site'

    def get_queryset(self):
        """Return a queryset for the choice.

        The queryset will take into account a LocalSite, if one is provided
        for the conditions.

        Returns:
            django.db.models.query.QuerySet:
            The queryset for the choice.
        """
        queryset = super(LocalSiteModelChoiceMixin, self).get_queryset()
        local_site = self.extra_state.get('local_site')

        if local_site:
            queryset = queryset.filter(**{
                self.local_site_attr: local_site,
            })

        return queryset
