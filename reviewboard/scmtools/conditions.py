"""Condition choices and operators for repositories and SCMTools."""

from django.utils.translation import gettext_lazy as _
from djblets.conditions.choices import (BaseConditionModelMultipleChoice,
                                        BaseConditionChoice,
                                        ConditionChoices)
from djblets.conditions.operators import (AnyOperator,
                                          BaseConditionOperator,
                                          ConditionOperators,
                                          IsNotOneOfOperator,
                                          IsOneOfOperator,
                                          UnsetOperator)
from djblets.conditions.values import ConditionValueMultipleChoiceField

from reviewboard.scmtools import scmtools_registry
from reviewboard.scmtools.models import Repository, Tool
from reviewboard.site.models import LocalSite


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


class RepositoriesChoice(RepositoryConditionChoiceMixin,
                         BaseConditionModelMultipleChoice):
    """A condition choice for matching repositories.

    This is used to match a :py:class:`~reviewboard.scmtools.models.Repository`
    against a list of repositories, against no repository (``None``), or
    against a repository public/private state.
    """

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

    def get_queryset(self):
        """Return the queryset used to look up repository choices.

        Returns:
            django.db.models.query.QuerySet:
            The queryset for repositories.
        """
        if self.extra_state.get('matching'):
            return (
                Repository.objects
                .filter(local_site=self.extra_state['local_site'])
            )
        else:
            request = self.extra_state.get('request')
            assert request is not None

            if 'local_site' in self.extra_state:
                local_site = self.extra_state['local_site']
            else:
                local_site = LocalSite.ALL

            return Repository.objects.accessible(
                user=request.user,
                local_site=local_site)

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
                           BaseConditionChoice):
    """A condition choice for matching repository types.

    This is used to match a :py:class:`~reviewboard.scmtools.models.Repository`
    of a certain type (based on the
    :py:class:`~reviewboard.scmtools.models.Tool`).
    """

    choice_id = 'repository_type'
    name = _('Repository type')

    operators = ConditionOperators([
        IsOneOfOperator,
        IsNotOneOfOperator,
    ])

    def default_value_field(self, **kwargs):
        """Return the default value field for this choice.

        This will call out to :py:meth:`get_queryset` before returning the
        field, allowing subclasses to simply set :py:attr:`queryset` or to
        perform more dynamic queries before constructing the form field.

        Args:
            **kwargs (dict):
                Extra keyword arguments for this function, for future
                expansion.

        Returns:
            djblets.conditions.values.ConditionValueMultipleModelField:
            The form field for the value.
        """
        repository_type_choices = [
            (scmtool.scmtool_id, scmtool.name)
            for scmtool in scmtools_registry
        ]
        return ConditionValueMultipleChoiceField(
            choices=repository_type_choices)

    def get_match_value(self, repository, **kwargs):
        """Return the value used for matching.

        This will return the SCMTool ID for the provided repository.

        Args:
            repository (reviewboard.scmtools.models.Repository):
                The provided repository.

            **kwargs (dict):
                Unused keyword arguments.

        Returns:
            str:
            The SCMTool ID for the repository's tool.
        """
        if repository:
            return repository.scmtool_id
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
