"""Condition choices and operators for repositories and SCMTools."""

from __future__ import unicode_literals

from django.utils.translation import ugettext_lazy as _
from djblets.conditions.choices import (BaseConditionModelMultipleChoice,
                                        ConditionChoices)
from djblets.conditions.operators import (AnyOperator,
                                          BaseConditionOperator,
                                          ConditionOperators,
                                          IsNotOneOfOperator,
                                          IsOneOfOperator,
                                          UnsetOperator)

from reviewboard.scmtools.models import Repository, Tool
from reviewboard.site.conditions import LocalSiteModelChoiceMixin


class RepositoryConditionChoiceMixin(object):
    """Mixin for condition choices that operate off repositories.

    This will set state needed to match against the choice.
    """

    value_kwarg = 'repository'


class IsRepositoryPrivateOperator(BaseConditionOperator):
    """An operator for matching private repositories."""

    operator_id = 'is-private'
    name = _('Is private')
    value_field = None

    def matches(self, match_value, **kwargs):
        """Return whether the repository is private.

        Args:
            match_value (reviewboard.scmtools.models.Repository):
                The repository to match.

            **kwargs (dict):
                Unused keyword arguments.

        Returns:
            bool:
            ``True`` if the repository is private. ``False`` if public.
        """
        return match_value is not None and not match_value.public


class IsRepositoryPublicOperator(BaseConditionOperator):
    """An operator for matching public repositories."""

    operator_id = 'is-public'
    name = _('Is public')
    value_field = None

    def matches(self, match_value, **kwargs):
        """Return whether the repository is public.

        Args:
            match_value (reviewboard.scmtools.models.Repository):
                The repository to match.

            **kwargs (dict):
                Unused keyword arguments.

        Returns:
            bool:
            ``True`` if the repository is public. ``False`` if private.
        """
        return match_value is not None and match_value.public


class RepositoriesChoice(LocalSiteModelChoiceMixin,
                         RepositoryConditionChoiceMixin,
                         BaseConditionModelMultipleChoice):
    """A condition choice for matching repositories.

    This is used to match a :py:class:`~reviewboard.scmtools.models.Repository`
    against a list of repositories, against no repository (``None``), or
    against a repository public/private state.
    """

    queryset = Repository.objects.all()
    choice_id = 'repository'
    name = _('Repository')

    operators = ConditionOperators([
        AnyOperator.with_overrides(name=_('Any repository')),
        UnsetOperator.with_overrides(name=_('No repository')),
        IsOneOfOperator,
        IsNotOneOfOperator,
        IsRepositoryPublicOperator,
        IsRepositoryPrivateOperator,
    ])

    def get_match_value(self, repository, **kwargs):
        """Return the value used for matching.

        This will return the provided repository directly.

        Args:
            repository (reviewboard.scmtools.models.Repository):
                The provided repository.

            **kwargs (dict):
                Unused keyword arguments.

        Returns:
            reviewboard.scmtools.models.Repository:
            The provided repository.
        """
        return repository


class RepositoryTypeChoice(RepositoryConditionChoiceMixin,
                           BaseConditionModelMultipleChoice):
    """A condition choice for matching repository types.

    This is used to match a :py:ref:`~reviewboard.scmtools.models.Repository`
    of a certain type (based on the
    :py:class:`~reviewboard.scmtools.models.Tool`).
    """

    queryset = Tool.objects.all()
    choice_id = 'repository_type'
    name = _('Repository type')

    operators = ConditionOperators([
        IsOneOfOperator,
        IsNotOneOfOperator,
    ])

    def get_match_value(self, repository, **kwargs):
        """Return the value used for matching.

        This will return the :py:class:`~reviewboard.scmtools.models.Tool`
        for the provided repository.

        Args:
            repository (reviewboard.scmtools.models.Repository):
                The provided repository.

            **kwargs (dict):
                Unused keyword arguments.

        Returns:
            reviewboard.scmtools.models.Tool:
            The repository's tool.
        """
        if repository:
            return repository.tool
        else:
            return None


class RepositoryConditionChoices(ConditionChoices):
    """A standard set of repository condition choices.

    This provides a handful of condition choices that are useful for
    repositories. They can be used in integrations or any other place
    where conditions are used.
    """

    choice_classes = [
        RepositoriesChoice,
        RepositoryTypeChoice,
    ]
