"""Managers for reviewboard.reviews.models."""

import logging

from django.contrib.auth.models import AnonymousUser, User
from django.core.exceptions import ObjectDoesNotExist
from django.db import connections, router, transaction, IntegrityError
from django.db.models import Manager, Q
from django.db.models.query import QuerySet
from djblets.db.managers import ConcurrencyManager

from reviewboard.deprecation import RemovedInReviewBoard60Warning
from reviewboard.diffviewer.models import DiffSetHistory
from reviewboard.scmtools.errors import ChangeNumberInUseError
from reviewboard.scmtools.models import Repository
from reviewboard.site.models import LocalSite


logger = logging.getLogger(__name__)


class CommentManager(ConcurrencyManager):
    """A manager for Comment models.

    This handles concurrency issues with Comment models.

    Version Added:
        5.0
    """

    def accessible(self, user, extra_query=None, local_site=None,
                   distinct=False):
        """Return a queryset for comments accessible by the given user.

        For superusers, all comments in all reviews will be returned.

        For regular users, only comments in reviews that they own or that
        are in the repositories, local sites, and review groups which the
        user has access to will be returned.

        For anonymous users, only comments that are in public repositories
        and whose review requests are not targeted by invite-only
        review groups will be returned.

        Args:
            user (django.contrib.auth.models.User):
                The User object that must have access to any
                returned comments.

            extra_query (django.db.models.Q, optional):
                Additional query parameters to add for filtering
                down the resulting queryset.

            local_site (reviewboard.site.models.LocalSite or
                        reviewboard.site.models.LocalSite.ALL, optional):
                A specific :term:`Local Site` that the comments must be
                associated with. It is assumed that the given user has access
                to the :term:`Local Site`. By default, this will only return
                comments not part of a site.

                This may be :py:attr:`LocalSite.ALL
                <reviewboard.site.models.LocalSite.ALL>`.

            distinct (bool, optional):
                Whether to return distinct results.

                Turning this on can decrease performance. It's off by default.

        Returns:
            django.db.models.query.QuerySet:
            The resulting queryset.
        """
        assert isinstance(user, (User, AnonymousUser))

        return self._query(user=user,
                           public=None,
                           extra_query=extra_query,
                           local_site=local_site,
                           status=None,
                           filter_private=True,
                           distinct=distinct)

    def from_user(self, user, *args, **kwargs):
        """Return the query for comments created by a user.

        Args:
            user (django.contrib.auth.models.User):
                The User object to query for.

            *args (tuple):
                Additional positional arguments to pass to the common
                :py:meth:`_query` function.

            **kwargs (dict):
                Additional keyword arguments to pass to the common
                :py:meth:`_query` function.

        Returns:
            django.db.models.query.QuerySet:
            A queryset for all the comments created by the given user.
        """
        assert isinstance(user, User)

        return self._query(extra_query=Q(review__user=user), *args, **kwargs)

    def _query(self, user=None, public=None, status='P', extra_query=None,
               local_site=None, filter_private=False, distinct=False):
        """Do a query for comments.

        Args:
            user (django.contrib.auth.models.User, optional):
                A user to query for.

            public (bool or None, optional):
                Whether to filter for comments from public (published) reviews.
                If set to `None`, comments from both published and unpublished
                reviews will be included.

            status (unicode, optional):
                The status of the review request that comments are associated
                with.

            extra_query (django.db.models.Q, optional):
                Additional query parameters to add.

            local_site (reviewboard.site.models.LocalSite or
                        reviewboard.site.models.LocalSite.ALL, optional):
                A local site to limit to, if appropriate. If a user is given,
                it is assumed that they have access to the :term:`Local Site`.
                By default, this will only return comments not part of a site.

                This may be :py:attr:`LocalSite.ALL
                <reviewboard.site.models.LocalSite.ALL>`.

            filter_private (bool, optional):
                Whether to filter out comments from review requests on private
                repositories or invite-only review groups that the user
                does not have access to. This will also filter out comments
                from unpublished reviews that are not owned by the user.

                This requires ``user`` to be provided.

            distinct (bool, optional):
                Whether to return distinct results.

                Turning this off can increase performance. It's on by default
                for backwards-compatibility.

        Returns:
            django.db.models.query.QuerySet:
            A queryset for the given conditions.
        """
        from reviewboard.reviews.models import Group

        q = Q()

        if local_site is not LocalSite.ALL:
            q &= Q(review__review_request__local_site=local_site)

        if status:
            q &= Q(review__review_request__status=status)

        if extra_query:
            q &= extra_query

        if filter_private and (not user or not user.is_superuser):
            repo_q = Q(review__review_request__repository=None)
            group_q = Q(review__review_request__target_groups=None)

            # TODO: should be consolidated with queries in ReviewRequestManager
            if user and user.is_authenticated:
                accessible_repo_ids = Repository.objects.accessible_ids(
                    user=user,
                    visible_only=False,
                    local_site=local_site)
                accessible_group_ids = Group.objects.accessible_ids(
                    user=user,
                    visible_only=False,
                    local_site=local_site)

                repo_q |= Q(('review__review_request__repository__in',
                             accessible_repo_ids))
                group_q |= Q(('review__review_request__target_groups__in',
                              accessible_group_ids))

                acl_check_q = (
                    repo_q &
                    (Q(review__review_request__target_people=user) |
                     group_q)
                )

                if public is None:
                    q &= (
                        Q(review__user=user) |
                        (Q(review__public=True) &
                         acl_check_q)
                    )
                elif public:
                    q &= Q(review__public=True) & acl_check_q
                else:
                    q &= Q(review__public=False) & Q(review__user=user)
            else:
                # Return an empty result when an unauthenticated user queries
                # for comments from unpublished reviews.
                if public is False:
                    return self.none()

                repo_q |= Q(review__review_request__repository__public=True)
                group_q |= \
                    Q(review__review_request__target_groups__invite_only=False)

                q &= repo_q & group_q & Q(review__public=True)
        else:
            if public is not None:
                q &= Q(review__public=public)

        queryset = self.filter(q)

        if distinct:
            queryset = queryset.distinct()

        return queryset


class DefaultReviewerManager(Manager):
    """A manager for DefaultReviewer models."""

    def for_repository(self, repository, local_site):
        """Returns all DefaultReviewers that represent a repository.

        These include both DefaultReviewers that have no repositories
        (for backwards-compatibility) and DefaultReviewers that are
        associated with the given repository.
        """
        return self.filter(local_site=local_site).filter(
            Q(repository__isnull=True) | Q(repository=repository))

    def can_create(self, user, local_site=None):
        """Returns whether the user can create default reviewers."""
        return (user.is_superuser or
                (local_site and local_site.is_mutable_by(user)))


class ReviewGroupManager(Manager):
    """A manager for Group models."""

    def accessible(self, user, visible_only=True, local_site=None,
                   show_all_local_sites=None, distinct=True):
        """Return a queryset for review groups accessible by the given user.

        For superusers, all public and invite-only review groups will be
        returned.

        For regular users, only review groups that are public or that the
        user is on the access list for will be returned.

        For anonymous users, only public review groups will be returned.

        The returned list is further filtered down based on the
        ``visible_only`` and ``local_site`` parameters.

        Version Changed:
            5.0:
            Deprecated ``show_all_local_sites`` and added support for
            setting ``local_site`` to :py:class:`LocalSite.ALL
            <reviewboard.site.models.LocalSite.ALL>`.

        Version Changed:
            3.0.24:
            Added the ``distinct`` parameter.

        Args:
            user (django.contrib.auth.models.User):
                The user that must have access to any returned groups.

            visible_only (bool, optional):
                Whether only visible review groups should be returned.

            local_site (reviewboard.site.models.LocalSite or
                        reviewboard.site.models.LocalSite.ALL, optional):
                A specific :term:`Local Site` that the groups must be
                associated with. By default, this will only return groups
                not part of a site.

                This may be :py:attr:`LocalSite.ALL
                <reviewboard.site.models.LocalSite.ALL>`.

                Version Changed:
                    5.0:
                    Added support for :py:attr:`LocalSite.ALL
                    <reviewboard.site.models.LocalSite.ALL>`.

            show_all_local_sites (bool, optional):
                Whether review groups for all :term:`Local Sites` should be
                returned. This cannot be ``True`` if a ``local_site``
                instance was provided.

                Deprecated:
                    5.0:
                    Callers should instead set ``local_site`` to
                    :py:class:`LocalSite.ALL
                    <reviewboard.site.models.LocalSite.ALL>` instead of
                    setting this to ``True``.

            distinct (bool, optional):
                Whether to return distinct results.

                Turning this off can increase performance. It's on by default
                for backwards-compatibility.

        Returns:
            django.db.models.query.QuerySet:
            The resulting queryset.
        """
        if show_all_local_sites is not None:
            RemovedInReviewBoard60Warning.warn(
                'show_all_local_sites is deprecated. Please pass '
                'local_site=LocalSite.ALL instead. This will be required '
                'in Review Board 6.')

            if show_all_local_sites:
                assert local_site in (None, LocalSite.ALL)
                local_site = LocalSite.ALL
            else:
                assert local_site is not LocalSite.ALL

        q = Q()

        if user.is_superuser:
            if visible_only:
                q &= Q(visible=True)
        else:
            if local_site is LocalSite.ALL:
                perm_local_site = None
            else:
                perm_local_site = local_site

            if not user.has_perm('reviews.can_view_invite_only_groups',
                                 perm_local_site):
                q &= Q(invite_only=False)

            if visible_only:
                # We allow accessible() to return hidden groups if the user is
                # a member, so we must perform this check here.
                q &= Q(visible=True)

            if user.is_authenticated:
                q |= Q(users=user.pk)

        if local_site is not LocalSite.ALL:
            q &= Q(local_site=local_site)

        queryset = self.filter(q)

        if distinct:
            queryset = queryset.distinct()

        return queryset

    def accessible_ids(self, *args, **kwargs):
        """Return IDs of groups that are accessible by the given user.

        This wraps :py:meth:`accessible` and takes the same arguments
        (with the exception of ``distinct``, which is ignored).

        Version Changed:
            3.0.24:
            In prior versions, the order was not specified, but was
            generally numeric order. This should still be true, but
            officially, we no longer guarantee any order of results.

        Args:
            *args (tuple):
                Positional arguments to pass to :py:meth:`accessible`.

            **kwargs (dict):
                Keyword arguments to pass to :py:meth:`accessible`.

        Returns:
            list of int:
            The list of IDs.
        """
        kwargs['distinct'] = False

        return list(sorted(set(
            self.accessible(*args, **kwargs)
            .values_list('pk', flat=True)
        )))

    def can_create(self, user, local_site=None):
        """Returns whether the user can create groups."""
        return (user.is_superuser or
                (local_site and local_site.is_mutable_by(user)))


class ReviewRequestQuerySet(QuerySet):
    def with_counts(self, user):
        queryset = self

        if user and user.is_authenticated:
            select_dict = {}

            select_dict['new_review_count'] = """
                SELECT COUNT(*)
                  FROM reviews_review, accounts_reviewrequestvisit
                  WHERE reviews_review.public
                    AND reviews_review.review_request_id =
                        reviews_reviewrequest.id
                    AND accounts_reviewrequestvisit.review_request_id =
                        reviews_reviewrequest.id
                    AND accounts_reviewrequestvisit.user_id = %(user_id)s
                    AND reviews_review.timestamp >
                        accounts_reviewrequestvisit.timestamp
                    AND reviews_review.user_id != %(user_id)s
            """ % {
                'user_id': str(user.id)
            }

            queryset = self.extra(select=select_dict)

        return queryset


class ReviewRequestManager(ConcurrencyManager):
    """
    A manager for review requests. Provides specialized queries to retrieve
    review requests with specific targets or origins, and to create review
    requests based on certain data.
    """

    def get_queryset(self):
        """Return a QuerySet for ReviewRequest models.

        Returns:
            ReviewRequestQuerySet:
            The new QuerySet instance.
        """
        return ReviewRequestQuerySet(self.model)

    def create(self, user, repository, commit_id=None, local_site=None,
               create_from_commit_id=False, create_with_history=False):
        """Create a new review request.

        Args:
            user (django.contrib.auth.models.User):
                The user creating the review request. They will be tracked as
                the submitter.

            repository (reviewboard.scmtools.Models.Repository):
                The repository, if any, the review request is associated with.

                If ``None``, diffs cannot be added to the review request.

            commit_id (unicode, optional):
                An optional commit ID.

            local_site (reviewboard.site.models.LocalSite, optional):
                An optional LocalSite to associate the review request with.

            create_from_commit_id (bool, optional):
                Whether or not the given ``commit_id`` should be used to
                pre-populate the review request data. If ``True``, the given
                ``repository`` will be used to do so.

            create_with_history (bool, optional):
                Whether or not the created review request will support
                attaching multiple commits per diff revision.

                If ``False``, it will not be possible to use the
                :py:class:`~reviewboard.webapi.resources.diff.DiffResource` to
                upload diffs; the
                :py:class:`~reviewboard.webapi.resources.DiffCommitResource`
                must be used instead.

        Returns:
            reviewboard.reviews.models.review_request.ReviewRequest:
            The created review request.

        Raises:
            reviewboard.hostingsvcs.errors.HostingServiceError:
                The hosting service backing the repository encountered an
                error.

            reviewboard.scmtools.errors.ChangeNumberInUseError:
                The commit ID is already in use by another review request.

            reviewboard.scmtools.errors.SCMError:
                The repository tool encountered an error.

            ValueError:
                An invalid value was passed for an argument.
        """
        from reviewboard.reviews.models import ReviewRequestDraft

        if commit_id:
            # Try both the new commit_id and old changenum versions
            try:
                review_request = self.get(commit_id=commit_id,
                                          repository=repository)
                raise ChangeNumberInUseError(review_request)
            except ObjectDoesNotExist:
                pass

            try:
                draft = ReviewRequestDraft.objects.get(
                    commit_id=commit_id,
                    review_request__repository=repository)
                raise ChangeNumberInUseError(draft.review_request)
            except ObjectDoesNotExist:
                pass

            try:
                review_request = self.get(changenum=int(commit_id),
                                          repository=repository)
                raise ChangeNumberInUseError(review_request)
            except (ObjectDoesNotExist, TypeError, ValueError):
                pass

        if create_with_history:
            if repository is None:
                raise ValueError('create_with_history requires a repository.')
            elif create_from_commit_id:
                raise ValueError(
                    'create_from_commit_id and create_with_history cannot '
                    'both be set to True.')
            elif not repository.scmtool_class.supports_history:
                raise ValueError(
                    'This repository does not support review requests created '
                    'with history.')

        # Create the review request. We're not going to actually save this
        # until we're confident we have all the data we need.
        review_request = self.model(
            submitter=user,
            status='P',
            public=False,
            repository=repository,
            diffset_history=DiffSetHistory(),
            local_site=local_site)

        review_request.created_with_history = create_with_history

        if commit_id:
            review_request.commit = commit_id

        review_request.validate_unique()

        draft = None

        if commit_id and create_from_commit_id:
            try:
                draft = ReviewRequestDraft(review_request=review_request)
                draft.update_from_commit_id(commit_id)
            except Exception as e:
                logger.exception('Unable to update new review request from '
                                 'commit ID %s on repository ID=%s: %s',
                                 commit_id, repository.pk, e)
                raise

        # Now that we've guaranteed we have everything needed for this review
        # request, we can save all related objects and re-attach (since the
        # "None" IDs are cached).
        diffset_history = review_request.diffset_history
        diffset_history.save()
        review_request.diffset_history = diffset_history

        try:
            review_request.save()
        except IntegrityError as e:
            if 'changenum' in str(e):
                # We do have a race condition here where our check above may
                # have succeeded, but in the meantime another process ended up
                # creating the review request. This is more likely to happen
                # when the server is swamped and users start getting impatient.
                # In the case that we can't bail early, undo the objects we've
                # already created.
                if diffset_history:
                    diffset_history.delete()

                review_request = self.get(changenum=int(commit_id),
                                          repository=repository)
                raise ChangeNumberInUseError(review_request)
            else:
                raise

        if draft:
            draft.review_request = review_request
            draft.save()

            draft.add_default_reviewers()

        if local_site:
            # We want to atomically set the local_id to be a monotonically
            # increasing ID unique to the local_site. This isn't really
            # possible in django's DB layer, so we have to drop back to pure
            # SQL and then reload the model.
            from reviewboard.reviews.models import ReviewRequest

            with transaction.atomic():
                # TODO: Use the cursor as a context manager when we move over
                # to Django 1.7+.
                db = router.db_for_write(ReviewRequest)
                cursor = connections[db].cursor()
                cursor.execute(
                    'UPDATE %(table)s SET'
                    '  local_id = COALESCE('
                    '    (SELECT MAX(local_id) from'
                    '      (SELECT local_id FROM %(table)s'
                    '        WHERE local_site_id = %(local_site_id)s) as x'
                    '      ) + 1,'
                    '    1),'
                    '  local_site_id = %(local_site_id)s'
                    '    WHERE %(table)s.id = %(id)s' % {
                        'table': ReviewRequest._meta.db_table,
                        'local_site_id': local_site.pk,
                        'id': review_request.pk,
                    })
                cursor.close()

            review_request.local_id = (
                ReviewRequest.objects.filter(pk=review_request.pk)
                .values_list('local_id', flat=True)[0]
            )

        # Ensure that a draft exists, so that users will be prompted to publish
        # the new review request.
        ReviewRequestDraft.create(review_request)

        return review_request

    def get_to_group_query(self, group_name, local_site):
        """Return a Q() query object targeting a group.

        This is meant to be passed as an ``extra_query`` argument to
        :py:meth:`public`.

        Args:
            group_name (str):
                The name of the review group the review requests must be
                assigned to.

            local_site (reviewboard.site.models.LocalSite):
                The :term:`Local Site` that the review requests must be on,
                if any.

                This does not accept :py:attr:`LocalSite.ALL
                <reviewboard.site.models.LocalSite.ALL>`.

                Callers should first validate that the user has access to
                the Local Site, if provided.

        Returns:
            django.db.models.Q:
            The query object.
        """
        return Q(target_groups__name=group_name,
                 local_site=local_site)

    def get_to_user_groups_query(self, user_or_username):
        """Return a Q() query object targeting groups joined by a user.

        This is meant to be passed as an ``extra_query`` argument to
        :py:meth:`public`.

        Args:
            user_or_username (django.contrib.auth.models.User or str):
                The User instance or username that all review requests must
                be assigned to indirectly.

        Returns:
            django.db.models.Q:
            The query object.

        Raises:
            django.contrib.auth.models.User.DoesNotExist:
                A username was provided, and that user does not exist.
        """
        query_user = self._get_query_user(user_or_username)
        groups = list(query_user.review_groups.values_list('pk', flat=True))

        return Q(target_groups__in=groups)

    def get_to_user_directly_query(self, user_or_username):
        """Returns the query targeting a user directly.

        This will include review requests where the user has been listed
        as a reviewer, or the user has starred.

        This is meant to be passed as an ``extra_query`` argument to
        :py:meth:`public`.

        Args:
            user_or_username (django.contrib.auth.models.User or str):
                The User instance or username that all review requests must
                be assigned to directly.

        Returns:
            django.db.models.Q:
            The query object.

        Raises:
            django.contrib.auth.models.User.DoesNotExist:
                A username was provided, and that user does not exist.
        """
        query_user = self._get_query_user(user_or_username)

        q = Q(target_people=query_user)

        try:
            profile = query_user.get_profile()
            q |= Q(starred_by=profile)
        except ObjectDoesNotExist:
            pass

        return q

    def get_to_user_query(self, user_or_username):
        """Return a Q() query object targeting a user indirectly.

        This will include review requests where the user has been listed
        as a reviewer, or a group that the user belongs to has been listed,
        or the user has starred.

        This is meant to be passed as an ``extra_query`` argument to
        :py:meth:`public`.

        Args:
            user_or_username (django.contrib.auth.models.User or str):
                The User instance or username that all review requests must
                be assigned to (directly to indirectly).

        Returns:
            django.db.models.Q:
            The query object.

        Raises:
            django.contrib.auth.models.User.DoesNotExist:
                A username was provided, and that user does not exist.
        """
        query_user = self._get_query_user(user_or_username)
        groups = list(query_user.review_groups.values_list('pk', flat=True))

        q = Q(target_people=query_user) | Q(target_groups__in=groups)

        try:
            profile = query_user.get_profile()
            q |= Q(starred_by=profile)
        except ObjectDoesNotExist:
            pass

        return q

    def get_from_user_query(self, user_or_username):
        """Return a Q() query object for review requests owned by a user.

        This is meant to be passed as an ``extra_query`` argument to
        :py:meth:`public`.

        Args:
            user_or_username (django.contrib.auth.models.User or str):
                The User instance or username that all review requests must
                be owned by.

        Returns:
            django.db.models.Q:
            The query object.
        """
        if isinstance(user_or_username, User):
            return Q(submitter=user_or_username)
        else:
            return Q(submitter__username=user_or_username)

    def get_to_or_from_user_query(self, user_or_username):
        """Return a Q() query object for review requests involving a user.

        This is meant to be passed as an ``extra_query`` argument to
        :py:meth:`public`.

        Args:
            user_or_username (django.contrib.auth.models.User or unicode):
                The User instance or username that all review requests must
                either be owned by or assigned to (directly to indirectly).

        Returns:
            django.db.models.Q:
            The query object.

        Raises:
            django.contrib.auth.models.User.DoesNotExist:
                A username was provided, and that user does not exist.
        """
        return (self.get_to_user_query(user_or_username) |
                self.get_from_user_query(user_or_username))

    def public(self, filter_private=True, *args, **kwargs):
        """Query public review requests, filtered by given criteria.

        Args:
            filter_private (bool, optional):
                Whether to filter out any review requests on private
                repositories or invite-only review groups that the user
                does not have access to.

                By default, they are filtered out.

                This requires ``user`` to be provided.

            *args (tuple):
                Additional positional arguments to pass to the common
                :py:meth:`_query` function.

            **kwargs (dict):
                Additional keyword arguments to pass to the common
                :py:meth:`_query` function.

        Returns:
            django.db.models.query.QuerySet:
            The resulting queryset.
        """
        return self._query(filter_private=filter_private, *args, **kwargs)

    def to_group(self, group_name, local_site, *args, **kwargs):
        """Query review requests made to a review group.

        The result will be review requests assigned to a review group.

        By default, the results will not be filtered based on whether a user
        has access to the review requests (via private repository or
        invite-only review group ACLs). To filter based on access, pass
        ``filter_private=True``.

        Args:
            group_name (str):
                The name of the review group the review requests must be
                assigned to.

            local_site (reviewboard.site.models.LocalSite):
                The :term:`Local Site` that the review requests must be on,
                if any.

                This does not accept :py:attr:`LocalSite.ALL
                <reviewboard.site.models.LocalSite.ALL>`.

                Callers should first validate that the user has access to
                the Local Site, if provided.

            *args (tuple):
                Additional positional arguments to pass to the common
                :py:meth:`_query` function.

            **kwargs (dict):
                Additional keyword arguments to pass to the common
                :py:meth:`_query` function.

        Returns:
            django.db.models.query.QuerySet:
            The resulting queryset.
        """
        return self._query(
            extra_query=self.get_to_group_query(group_name, local_site),
            local_site=local_site,
            *args, **kwargs)

    def to_or_from_user(self, user_or_username, *args, **kwargs):
        """Query review requests a user is involved in.

        The result will be review requests from a user, assigned to the user,
        or assigned to a group the user is in.

        By default, the results will not be filtered based on whether a user
        has access to the review requests (via private repository or
        invite-only review group ACLs). To filter based on access, pass
        ``filter_private=True``.

        Args:
            user_or_username (django.contrib.auth.models.User or unicode):
                The User instance or username that all review requests must
                either be owned by or assigned to (directly to indirectly).

            *args (tuple):
                Additional positional arguments to pass to the common
                :py:meth:`_query` function.

            **kwargs (dict):
                Additional keyword arguments to pass to the common
                :py:meth:`_query` function.

        Returns:
            django.db.models.query.QuerySet:
            A queryset of all review requests the users is involved in as
            either a submitter or a reviewer (either directly assigned or
            indirectly as a member of a group).

        Raises:
            django.contrib.auth.models.User.DoesNotExist:
                A username was provided, and that user does not exist.
        """
        return self._query(
            extra_query=self.get_to_or_from_user_query(user_or_username),
            *args, **kwargs)

    def to_user_groups(self, username, *args, **kwargs):
        """Query review requests made to a user's review groups.

        The result will be review requests assigned to a group the user is in.

        By default, the results will not be filtered based on whether a user
        has access to the review requests (via private repository or
        invite-only review group ACLs). To filter based on access, pass
        ``filter_private=True``.

        Args:
            username (django.contrib.auth.models.User or str):
                The User instance or username.

        Returns:
            django.db.models.query.QuerySet:
            A queryset of all review requests the users is involved in as
            either a submitter or a reviewer (either directly assigned or
            indirectly as a member of a group).

        Raises:
            django.contrib.auth.models.User.DoesNotExist:
                A username was provided, and that user does not exist.
        """
        return self._query(
            extra_query=self.get_to_user_groups_query(username),
            *args, **kwargs)

    def to_user_directly(self, user_or_username, *args, **kwargs):
        """Query review requests assigned directly to a user.

        The result will be review requests assigned to the user.

        By default, the results will not be filtered based on whether a user
        has access to the review requests (via private repository or
        invite-only review group ACLs). To filter based on access, pass
        ``filter_private=True``.

        Args:
            user_or_username (django.contrib.auth.models.User or unicode):
                The user object or username to query for.

            *args (tuple):
                Additional positional arguments to pass to the common
                :py:meth:`_query` function.

            **kwargs (dict):
                Additional keyword arguments to pass to the common
                :py:meth:`_query` function.

        Returns:
            django.db.models.query.QuerySet:
            The resulting queryset.

        Raises:
            django.contrib.auth.models.User.DoesNotExist:
                A username was provided, and that user does not exist.
        """
        return self._query(
            extra_query=self.get_to_user_directly_query(user_or_username),
            *args, **kwargs)

    def to_user(self, user_or_username, *args, **kwargs):
        """Query review requests assigned directly or indirectly to a user.

        The result will be review requests assigned to the user or to a group
        the user is in.

        By default, the results will not be filtered based on whether a user
        has access to the review requests (via private repository or
        invite-only review group ACLs). To filter based on access, pass
        ``filter_private=True``.

        Args:
            user_or_username (django.contrib.auth.models.User or unicode):
                The user object or username to query for.

            *args (tuple):
                Additional positional arguments to pass to the common
                :py:meth:`_query` function.

            **kwargs (dict):
                Additional keyword arguments to pass to the common
                :py:meth:`_query` function.

        Returns:
            django.db.models.query.QuerySet:
            The resulting queryset.

        Raises:
            django.contrib.auth.models.User.DoesNotExist:
                A username was provided, and that user does not exist.
        """
        return self._query(
            extra_query=self.get_to_user_query(user_or_username),
            *args, **kwargs)

    def from_user(self, user_or_username, *args, **kwargs):
        """Query review requests from a user.

        The result will be review requests created or currently owned by a
        user.

        By default, the results will not be filtered based on whether a user
        has access to the review requests (via private repository or
        invite-only review group ACLs). To filter based on access, pass
        ``filter_private=True``.

        Args:
            user_or_username (django.contrib.auth.models.User or unicode):
                The user object or username to query for.

            *args (tuple):
                Additional positional arguments to pass to the common
                :py:meth:`_query` function.

            **kwargs (dict):
                Additional keyword arguments to pass to the common
                :py:meth:`_query` function.

        Returns:
            django.db.models.query.QuerySet:
            The resulting queryset.
        """
        return self._query(
            extra_query=self.get_from_user_query(user_or_username),
            *args, **kwargs)

    def _query(self, user=None, status='P', with_counts=False,
               extra_query=None, local_site=None, filter_private=False,
               show_inactive=False, show_all_unpublished=False,
               show_all_local_sites=None):
        """Return a queryset for review requests matching the given criteria.

        By default, the results will not be filtered based on whether a user
        has access to the review requests (via private repository or
        invite-only review group ACLs). To filter based on access, pass
        ``filter_private=True``.

        Version Changed:
            5.0:
            Deprecated ``show_all_local_sites`` and added support for
            setting ``local_site`` to :py:class:`LocalSite.ALL
            <reviewboard.site.models.LocalSite.ALL>`.

        Args:
            user (django.contrib.auth.models.User, optional):
                The user that must have access to any returned review
                requests, if limiting access by user.

            status (str, optional):
                A review request status to filter by.

            with_counts (bool, optional):
                Whether to include new review counts since the last
                visit.

                If set, this will make use of
                :py:meth:`ReviewRequestQuerySet.with_counts`.

            extra_query (django.db.models.Q, optional):
                Optional additional queries for the queryset.

            local_site (reviewboard.site.models.LocalSite or
                        reviewboard.site.models.LocalSite.ALL, optional):
                A specific :term:`Local Site` that the groups must be
                associated with. By default, this will only return groups
                not part of a site.

                This may be :py:attr:`LocalSite.ALL
                <reviewboard.site.models.LocalSite.ALL>`.

                Callers should first validate that the user has access to
                the Local Site, if provided.

                Version Changed:
                    5.0:
                    Added support for :py:attr:`LocalSite.ALL
                    <reviewboard.site.models.LocalSite.ALL>`.

            filter_private (bool, optional):
                Whether to filter out any review requests on private
                repositories or invite-only review groups that the user
                does not have access to.

                This requires ``user`` to be provided.

            show_inactive (bool, optional):
                Whether to filter out review requests for inactive users.

            show_all_unpublished (bool, optional):
                Whether to include review requests not yet published.

            show_all_local_sites (bool, optional):
                Whether review requests for all :term:`Local Sites` should be
                returned. This cannot be ``True`` if a ``local_site``
                instance was provided.

                Deprecated:
                    5.0:
                    Callers should instead set ``local_site`` to
                    :py:class:`LocalSite.ALL
                    <reviewboard.site.models.LocalSite.ALL>` instead of
                    setting this to ``True``.

        Returns:
            django.db.models.query.QuerySet:
            The resulting queryset.
        """
        from reviewboard.reviews.models import Group

        if show_all_local_sites is not None:
            RemovedInReviewBoard60Warning.warn(
                'show_all_local_sites is deprecated. Please pass '
                'local_site=LocalSite.ALL instead. This will be required '
                'in Review Board 6.')

            if show_all_local_sites:
                assert local_site in (None, LocalSite.ALL)
                local_site = LocalSite.ALL
            else:
                assert local_site is not LocalSite.ALL

        is_authenticated = (user is not None and user.is_authenticated)

        if show_all_unpublished:
            q = Q()
        else:
            q = Q(public=True)

            if is_authenticated:
                q |= Q(submitter=user)

        if not show_inactive:
            q &= Q(submitter__is_active=True)

        if status:
            q &= Q(status=status)

        if local_site is not LocalSite.ALL:
            q &= Q(local_site=local_site)

        if extra_query:
            q &= extra_query

        if filter_private and (not user or not user.is_superuser):
            # This must always be kept in sync with RBSearchForm.search.
            repo_q = Q(repository=None)
            group_q = Q(target_groups=None)

            if is_authenticated:
                accessible_repo_ids = Repository.objects.accessible_ids(
                    user=user,
                    visible_only=False,
                    local_site=local_site)
                accessible_group_ids = Group.objects.accessible_ids(
                    user=user,
                    visible_only=False,
                    local_site=local_site)

                repo_q |= Q(repository__in=accessible_repo_ids)
                group_q |= Q(target_groups__in=accessible_group_ids)

                q &= (
                    Q(submitter=user) |
                    (repo_q &
                     (Q(target_people=user) |
                      group_q))
                )
            else:
                repo_q |= Q(repository__public=True)
                group_q |= Q(target_groups__invite_only=False)

                q &= repo_q & group_q

        queryset = self.filter(q).distinct()

        if with_counts:
            queryset = queryset.with_counts(user)

        return queryset

    def _get_query_user(self, user_or_username):
        """Return a User object, given a possible User or username.

        If a User instance is provided, it will be directly returned.

        If a username is provided, it will be looked up and then returned.

        Args:
            user_or_username (django.contrib.auth.models.User or str):
                The User instance or username to look up.

        Returns:
            django.contrib.auth.models.User:
            The resulting User instance.

        Raises:
            django.contrib.auth.models.User.DoesNotExist:
                A username was provided, and that user does not exist.
        """
        if isinstance(user_or_username, User):
            return user_or_username
        else:
            return User.objects.get(username=user_or_username)

    def for_id(self, pk, local_site=None):
        """Returns the review request matching the given ID and LocalSite.

        If a LocalSite is provided, then the ID will be matched against the
        displayed ID for the LocalSite, rather than the in-database ID.
        """
        if local_site is None:
            return self.model.objects.get(pk=pk)
        else:
            return self.model.objects.get(Q(local_id=pk) &
                                          Q(local_site=local_site))


class ReviewManager(ConcurrencyManager):
    """A manager for Review models.

    This handles concurrency issues with Review models. In particular, it
    will try hard not to save two reviews at the same time, and if it does
    manage to do that (which may happen for pending reviews while a server
    is under heavy load), it will repair and consolidate the reviews on
    load. This prevents errors and lost data.
    """

    def accessible(self, user, extra_query=None, local_site=None,
                   public=None, distinct=False):
        """Return a queryset for reviews accessible by the given user.

        For superusers, all public (published) and unpublished reviews will
        be returned.

        For regular users, only reviews that are owned by the user or that
        are public in the repositories, local sites, and review groups which
        the user has access to will be returned.

        For anonymous users, only public reviews that are on public
        repositories and whose review requests are not targeted by invite-only
        review groups will be returned.

        Version Added:
            5.0

        Args:
            user (django.contrib.auth.models.User):
                The User object that must have access to any returned reviews.

            extra_query (django.db.models.Q, optional):
                Additional query parameters to add for filtering
                down the resulting queryset.

            local_site (reviewboard.site.models.LocalSite or
                        reviewboard.site.models.LocalSite.ALL, optional):
                A specific :term:`Local Site` that the reviews must be
                associated with. It is assumed that the given user has access
                to the :term:`Local Site`. By default, this will only return
                reviews not part of a site.

                This may be :py:attr:`LocalSite.ALL
                <reviewboard.site.models.LocalSite.ALL>`.

            public (bool or None, optional):
                Whether to filter for public (published) reviews. If set to
                ``None``, both published and unpublished reviews will be
                included.

            distinct (bool, optional):
                Whether to return distinct results.

                Turning this on can decrease performance. It's off by default.

        Returns:
            django.db.models.query.QuerySet:
            The resulting queryset.
        """
        assert isinstance(user, (User, AnonymousUser))

        return self._query(user=user,
                           public=public,
                           extra_query=extra_query,
                           local_site=local_site,
                           status=None,
                           filter_private=True,
                           distinct=distinct)

    def get_pending_review(self, review_request, user):
        """Return a user's pending review on a review request.

        This will handle fixing duplicate reviews if more than one pending
        review is found.

        Args:
            review_request (reviewboard.reviews.models.review_request.
                            ReviewRequest):
                The review request being reviewed.

            user (django.contrib.auth.models.User):
                The user making the review.

        Returns:
            reviewboard.reviews.models.review.Review:
            The pending review object.
        """
        if not user.is_authenticated:
            return None

        reviews = list(
            self.filter(user=user,
                        review_request=review_request,
                        public=False,
                        base_reply_to__isnull=True)
            .order_by('timestamp')
        )

        if len(reviews) == 0:
            return None
        elif len(reviews) == 1:
            return reviews[0]
        else:
            # We have duplicate reviews, which will break things. We need
            # to condense them.
            logging.warning('Duplicate pending reviews found for review '
                            'request ID %s, user %s. Fixing.',
                            review_request.id, user.username)

            return self.fix_duplicate_reviews(reviews)

    def get_pending_reply(self, review, user):
        """Return a user's pending reply to a given review.

        This will handle fixing duplicate reviews if more than one pending
        review reply is found.

        Args:
            review (reviewboard.reviews.models.review.Review):
                The review being replied to.

            user (django.contrib.auth.models.User):
                The user making the reply.

        Returns:
            reviewboard.reviews.models.review.Review:
            The pending review object.
        """
        if not user.is_authenticated:
            return None

        reviews = list(
            self.filter(user=user,
                        public=False,
                        base_reply_to=review)
            .order_by('timestamp')
        )

        if len(reviews) == 0:
            return None
        elif len(reviews) == 1:
            return reviews[0]
        else:
            # We have duplicate replies, which will break things. We need
            # to condense them.
            logging.warning('Duplicate pending replies found for review '
                            'ID %s, user %s. Fixing.',
                            review.id, user.username)

            return self.fix_duplicate_reviews(reviews)

    def fix_duplicate_reviews(self, reviews):
        """Fix duplicate reviews, condensing them into a single review.

        This will consolidate the data from all reviews into the first
        review in the list, and return the first review.

        Args:
            reviews (list of reviewboard.reviews.models.review.Review):
                The list of duplicate reviews.

        Returns:
            reviewboard.reviews.models.review.Review:
            The first review in the list containing the consolidated data.
        """
        master_review = reviews[0]

        for review in reviews[1:]:
            for attname in ["body_top", "body_bottom", "body_top_reply_to",
                            "body_bottom_reply_to"]:
                review_value = getattr(review, attname)

                if (review_value and not getattr(master_review, attname)):
                    setattr(master_review, attname, review_value)

            for attname in ["comments", "screenshot_comments",
                            "file_attachment_comments",
                            "general_comments"]:
                master_m2m = getattr(master_review, attname)
                review_m2m = getattr(review, attname)

                for obj in review_m2m.all():
                    master_m2m.add(obj)
                    review_m2m.remove(obj)

            master_review.save()
            review.delete()

        return master_review

    def from_user(self, user_or_username, *args, **kwargs):
        """Return the query for reviews created by a user.

        Args:
            user_or_username (django.contrib.auth.models.User or str):
                The User object or username.

            *args (tuple):
                Additional positional arguments to pass to the common
                :py:meth:`_query` function.

            **kwargs (dict):
                Additional keyword arguments to pass to the common
                :py:meth:`_query` function.

        Returns:
            django.db.models.query.QuerySet:
            A queryset for all the reviews created by the given user.
        """
        if isinstance(user_or_username, User):
            extra_query = Q(user=user_or_username)
        else:
            assert isinstance(user_or_username, str)
            extra_query = Q(user__username=user_or_username)

        return self._query(extra_query=extra_query, *args, **kwargs)

    def _query(self, user=None, public=None, status='P', extra_query=None,
               local_site=None, filter_private=False, base_reply_to=None,
               distinct=False):
        """Do a query for reviews.

        Version Changed:
            5.0:
            Added the ``distinct`` parameter.

        Args:
            user (django.contrib.auth.models.User, optional):
                A user to query for.

            public (bool or None, optional):
                Whether to filter for public (published) reviews. If set to
                ``None``, both published and unpublished reviews will be
                included.

            status (unicode, optional):
                The status of the review request that reviews are associated
                with.

            extra_query (django.db.models.Q, optional):
                Additional query parameters to add.

            local_site (reviewboard.site.models.LocalSite or
                        reviewboard.site.models.LocalSite.ALL, optional):
                A local site to limit to, if appropriate. If a user is given,
                it is assumed that they have access to the :term:`Local Site`.
                By default, this will only return reviews not part of a site.

                This may be :py:attr:`LocalSite.ALL
                <reviewboard.site.models.LocalSite.ALL>`.


                Callers should first validate that the user has access to
                the Local Site, if provided.

            filter_private (bool, optional):
                Whether to filter out reviews from review requests on private
                repositories or invite-only review groups that the user
                does not have access to. This will also filter out unpublished
                reviews that are not owned by the user.

                This requires ``user`` to be provided.

            base_reply_to (reviewboard.reviews.models.review.Review, optional):
                If provided, limit results to reviews that are part of the
                thread of replies to this review.

            distinct (bool, optional):
                Whether to return distinct results.

                Turning this on can decrease performance. It's off by default.

        Returns:
            django.db.models.query.QuerySet:
            A queryset for the given conditions.
        """
        from reviewboard.reviews.models import Group

        q = Q(base_reply_to=base_reply_to)

        if status:
            q &= Q(review_request__status=status)

        if local_site is not LocalSite.ALL:
            q &= Q(review_request__local_site=local_site)

        if extra_query:
            q &= extra_query

        if filter_private and (not user or not user.is_superuser):
            repo_q = Q(review_request__repository=None)
            group_q = Q(review_request__target_groups=None)

            # TODO: should be consolidated with queries in ReviewRequestManager
            if user and user.is_authenticated:
                accessible_repo_ids = Repository.objects.accessible_ids(
                    user=user,
                    visible_only=False,
                    local_site=local_site)
                accessible_group_ids = Group.objects.accessible_ids(
                    user=user,
                    visible_only=False,
                    local_site=local_site)

                repo_q |= \
                    Q(review_request__repository__in=accessible_repo_ids)
                group_q |= \
                    Q(review_request__target_groups__in=accessible_group_ids)

                acl_check_q = (
                    repo_q &
                    (Q(review_request__target_people=user) |
                     group_q)
                )

                if public is None:
                    q &= (
                        Q(user=user) |
                        (Q(public=True) &
                         acl_check_q)
                    )
                elif public:
                    q &= Q(public=True) & acl_check_q
                else:
                    q &= Q(public=False) & Q(user=user)
            else:
                # Return an empty result when an unauthenticated user queries
                # for unpublished reviews.
                if public is False:
                    return self.none()

                repo_q |= Q(review_request__repository__public=True)
                group_q |= Q(review_request__target_groups__invite_only=False)

                q &= repo_q & group_q & Q(public=True)
        else:
            if public is not None:
                q &= Q(public=public)

        queryset = self.filter(q)

        if distinct:
            queryset = queryset.distinct()

        return queryset
