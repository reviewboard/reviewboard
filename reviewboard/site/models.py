"""Models for Local Sites."""

from __future__ import annotations

from enum import Enum
from typing import ClassVar, Optional, TYPE_CHECKING, Union

from django.contrib.auth.models import User
from django.db import models
from django.utils.translation import gettext_lazy as _
from djblets.db.fields import JSONField
from housekeeping.functions import deprecate_non_keyword_only_args
from typing_extensions import Literal

from reviewboard.deprecation import RemovedInReviewBoard10_0Warning
from reviewboard.site.managers import LocalSiteManager

if TYPE_CHECKING:
    from typing import Final, TypeAlias

    from django.contrib.auth.models import AnonymousUser


class _LocalSiteConstants(Enum):
    """Constants for special LocalSite queries.

    Version Added:
        6.0:
        This replaces an older ALL-specific object, to aid in typing.
    """

    ALL = '<ALL>'


class LocalSite(models.Model):
    """A division within a Review Board installation.

    This allows the creation of independent, isolated divisions within a given
    server. Users can be designated as members of a LocalSite, and optionally
    as admins (which allows them to manipulate the repositories, groups and
    users in the site).

    Pretty much every other model in this module can all be assigned to a
    single LocalSite, at which point only members will be able to see or
    manipulate these objects. Access control is performed at every level, and
    consistency is enforced through a liberal sprinkling of assertions and unit
    tests.
    """

    #: A sentinel indicating all LocalSites.
    #:
    #: This is supported by some functions to perform a query against all
    #: LocalSites, as opposed to either a single LocalSite instance or the
    #: global site through ``None``.
    #:
    #: Check the documentation for a function's argument to determine whether
    #: this is supported.
    #:
    #: Note that the value is considered opaque. It can be compared directly
    #: using ``is``.
    #:
    #: Version Added:
    #:     5.0
    ALL: Final[Literal[_LocalSiteConstants.ALL]] = _LocalSiteConstants.ALL

    name = models.SlugField(
        _('name'),
        max_length=32,
        blank=False,
        unique=True,
    )

    public = models.BooleanField(
        default=False,
        db_index=True,
        help_text=_(
            'Allow people outside the team to access and post review '
            'requests and reviews.'
        ),
    )

    users: models.ManyToManyField[User, User] = models.ManyToManyField(
        User,
        blank=True,
        related_name='local_site',
    )

    admins: models.ManyToManyField[User, User] = models.ManyToManyField(
        User,
        blank=True,
        related_name='local_site_admins',
    )

    extra_data = JSONField(null=True)

    objects: ClassVar[LocalSiteManager] = LocalSiteManager()

    def is_accessible_by(
        self,
        user: AnonymousUser | User,
    ) -> bool:
        """Return whether or not the user has access to this LocalSite.

        This checks that the user is logged in, and that they're listed in the
        'users' field.

        Args:
            user (django.contrib.auth.models.AnonymousUser or
                  django.contrib.auth.models.User):
                The user to check.

        Returns:
            bool:
            ``True`` if the user has access. ``False`` if they do not.
        """
        return (self.public or
                (user.is_authenticated and
                 (user.is_staff or self.users.filter(pk=user.pk).exists())))

    @deprecate_non_keyword_only_args(RemovedInReviewBoard10_0Warning)
    def is_mutable_by(
        self,
        user: AnonymousUser | User,
        *,
        perm: str = 'site.change_localsite',
    ) -> bool:
        """Return whether or not a user can modify settings in a LocalSite.

        This checks that the user is either staff with the proper permissions,
        or that they're listed in the 'admins' field.

        By default, this is checking whether the LocalSite itself can be
        modified, but a different permission can be passed to check for
        another object.

        Version Changed:
            8.0:
            ``perm`` must now be provided as a keyword-only argument.
            Support for providing these as positional arguments is
            deprecated and will be removed in Review Board 10.

        Args:
            user (django.contrib.auth.models.AnonymousUser or
                  django.contrib.auth.models.User):
                The user to check.

            perm (str, optional):
                The explicit permission to check.

                Defaults to ``site.change_localsite``.

        Returns:
            bool:
            ``True`` if the user can modify the LocalSite settings.
            ``False`` if they cannot.
        """
        return user.has_perm(perm) or self.admins.filter(pk=user.pk).exists()

    def __str__(self) -> str:
        """Return the string form of the Local Site.

        This will return :py:attr:`name` directly.

        Returns:
            str:
            The Local Site name.
        """
        return self.name

    class Meta:
        db_table = 'site_localsite'
        verbose_name = _('Local Site')
        verbose_name_plural = _('Local Sites')


#: A filter value for matching a LocalSite, all LocalSites, or None.
#:
#: Version Added:
#:     5.0.7
AnyOrAllLocalSites: TypeAlias = Union[Optional[LocalSite],
                                      Literal[_LocalSiteConstants.ALL]]
