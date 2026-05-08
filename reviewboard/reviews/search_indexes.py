"""Search indexing for review requests."""

from __future__ import annotations

from typing import TYPE_CHECKING, cast

from django.contrib.auth.models import AnonymousUser, User
from django.db.models import Prefetch
from haystack import indexes

from reviewboard.diffviewer.models import DiffSet, FileDiff
from reviewboard.reviews.models import Group, ReviewRequest
from reviewboard.scmtools.models import Repository
from reviewboard.search.indexes import BaseSearchIndex
from reviewboard.site.models import LocalSite

if TYPE_CHECKING:
    from collections.abc import Sequence
    from reviewboard.accounts.models import User as RBUser

    from django.db.models import QuerySet


class ReviewRequestIndex(BaseSearchIndex[ReviewRequest],
                         indexes.Indexable):
    """A Haystack search index for Review Requests."""

    model = ReviewRequest
    local_site_attr = 'local_site_id'

    # We shouldn't use 'id' as a field name because it's by default reserved
    # for Haystack. Hiding it will cause duplicates when updating the index.
    review_request_id = indexes.IntegerField(model_attr='display_id')
    summary = indexes.CharField(model_attr='summary')
    description = indexes.CharField(model_attr='description')
    testing_done = indexes.CharField(model_attr='testing_done')
    commit_id = indexes.EdgeNgramField(model_attr='commit', null=True)
    bug = indexes.CharField(model_attr='bugs_closed')
    username = indexes.CharField(model_attr='submitter__username')
    author = indexes.CharField()
    last_updated = indexes.DateTimeField(model_attr='last_updated')
    url = indexes.CharField(model_attr='get_absolute_url')
    file = indexes.CharField()

    # These fields all contain information needed to perform queries about
    # whether a review request is accessible by a given user.
    private = indexes.BooleanField()
    private_repository_id = indexes.IntegerField()
    private_target_groups = indexes.MultiValueField()
    target_users = indexes.MultiValueField()

    def get_updated_field(self) -> str:
        """Return the name of the field indicating the last updated timestamp.

        Returns:
            str:
            The name of the field.
        """
        return 'last_updated'

    def index_queryset(
        self,
        using: (str | None) = None,
    ) -> QuerySet[ReviewRequest]:
        """Return a queryset for indexing review requests.

        This will only include review requests that are public.

        Args:
            using (str, unused):
                The name of the search index.

        Returns:
            django.db.models.QuerySet:
            The queryset to index.
        """
        has_local_sites = LocalSite.objects.has_local_sites()
        extra_prefetches: list[Prefetch] = []
        local_site_acl_fields: list[str] = []
        local_site_select_related: list[str | None] = []

        if has_local_sites:
            # If the server has Local Sites, prefetch them for all review
            # requests and select_related them for other relevant queries.
            #
            # If a Local Site is added for the first time while indexing,
            # this will result in N+1 query issues for every review request
            # or related object, which will be expensive. This would only
            # ever happen once, and should be an unlikely event.
            extra_prefetches.append(
                Prefetch(
                    'local_site',
                    queryset=(
                        LocalSite.objects
                        .only(
                            'name',
                        )
                    ),
                ),
            )

            local_site_acl_fields.append('local_site__public')
            local_site_select_related.append('local_site')
        else:
            local_site_select_related.append(None)

        return (
            self.get_model().objects
            .public(
                status=None,
                local_site=LocalSite.ALL,
                show_inactive=True,
                filter_private=False,
                distinct=False,
            )
            .only(
                # ReviewRequest fields.
                'bugs_closed',
                'changenum',
                'commit_id',
                'description',
                'last_updated',
                'local_id',
                'local_site_id',
                'public',
                'repository_id',
                'submitter_id',
                'summary',
                'testing_done',

                # DiffSetHistory fields.
                'diffset_history__id',
            )
            .select_related(
                'diffset_history',
            )
            .prefetch_related(
                Prefetch(
                    'repository',
                    queryset=(
                        Repository.objects
                        .only(
                            'local_site',
                            'public',

                            *local_site_acl_fields,
                        )
                        .select_related(*local_site_select_related)
                    )
                ),
                Prefetch(
                    'submitter',
                    queryset=(
                        User.objects
                        .select_related(
                            'profile',
                        )
                        .only(
                            # User fields.
                            'first_name',
                            'last_name',
                            'username',

                            # Profile fields.
                            'profile__extra_data',
                            'profile__is_private',
                        )
                    ),
                ),

                # Note that we're handling this nested relation very
                # carefully. A standard prefetch will fetch all columns for
                # each object in the relation specifier, while we really only
                # need the IDs necessary to chain the objects together.
                Prefetch(
                    'diffset_history__diffsets',
                    queryset=(
                        DiffSet.objects
                        .only(
                            'history_id',
                        )
                        .prefetch_related(
                            Prefetch(
                                'files',
                                queryset=(
                                    FileDiff.objects
                                    .only(
                                        'dest_file',
                                        'source_file',
                                    )
                                ),
                            ),
                        )
                    ),
                ),
                Prefetch(
                    'target_groups',
                    queryset=(
                        Group.objects
                        .only(
                            # Group fields.
                            'invite_only',
                            'local_site',

                            *local_site_acl_fields,
                        )
                        .select_related(*local_site_select_related)
                    ),
                ),
                Prefetch(
                    'target_people',
                    queryset=(
                        User.objects
                        .only('pk')
                    ),
                ),
                *extra_prefetches,
            )
        )

    def prepare_file(
        self,
        review_request: ReviewRequest,
    ) -> set[tuple[str, str]]:
        """Prepare the diff file information for the index.

        This will cover all filediffs across diffsets.

        Args:
            review_request (reviewboard.reviews.models.ReviewRequest):
                The review request being prepared.

        Returns:
            set:
            A set of tuples of:

            Tuple:
                0 (str):
                    The source file path.

                1 (str):
                    The destination file path.
        """
        return {
            (filediff.source_file, filediff.dest_file)
            for diffset in review_request.diffset_history.diffsets.all()
            for filediff in diffset.files.all()
        }

    def prepare_private(
        self,
        review_request: ReviewRequest,
    ) -> bool:
        """Prepare the private flag for the index.

        This will be set to true if the review request isn't generally
        accessible to users.

        Args:
            review_request (reviewboard.reviews.models.ReviewRequest):
                The review request being prepared.

        Returns:
            bool:
            ``True`` if the review request is private. ``False`` if public.
        """
        return not review_request.is_accessible_by(AnonymousUser(),
                                                   silent=True)

    def prepare_private_repository_id(
        self,
        review_request: ReviewRequest,
    ) -> int:
        """Prepare the private repository ID, if any, for the index.

        If there's no repository, or it's public, 0 will be returned instead.

        Args:
            review_request (reviewboard.reviews.models.ReviewRequest):
                The review request being prepared.

        Returns:
            int:
            The ID of the repository, or 0 if unset or public.
        """
        if review_request.repository and not review_request.repository.public:
            return review_request.repository_id
        else:
            return 0

    def prepare_private_target_groups(
        self,
        review_request: ReviewRequest,
    ) -> Sequence[int]:
        """Prepare the list of invite-only target groups for the index.

        If there aren't any invite-only groups associated, ``[0]`` will be
        returned. This allows queries to be performed that check that none
        of the groups are private, since we can't query against empty lists.

        Args:
            review_request (reviewboard.reviews.models.ReviewRequest):
                The review request being prepared.

        Returns:
            list of int:
            The list of invite-only group IDs, or ``[0]`` if there aren't
            any.
        """
        return [
            group.pk
            for group in review_request.target_groups.all()
            if group.invite_only
        ] or [0]

    def prepare_target_users(
        self,
        review_request: ReviewRequest,
    ) -> Sequence[int]:
        """Prepare the list of target users for the index.

        If there aren't any target users, ``[0]`` will be returned. This
        allows queries to be performed that check that there aren't any
        users in the list, since we can't query against empty lists.

        Args:
            review_request (reviewboard.reviews.models.ReviewRequest):
                The review request being prepared.

        Returns:
            list of int:
            The list of user IDs, or ``[0]`` if there aren't any.
        """
        return [
            user.pk
            for user in review_request.target_people.all()
        ] or [0]

    def prepare_author(
        self,
        review_request: ReviewRequest,
    ) -> str:
        """Prepare the author field.

        Args:
            review_request (reviewboard.reviews.models.review_request.
                            ReviewRequest):
                The review request being indexed.

        Returns:
            str:
            Either the author's full name (if their profile is public) or an
            empty string.
        """
        user = cast('RBUser', review_request.submitter)
        profile = user.get_profile(cached_only=True)

        if profile is None or profile.is_private:
            return ''

        return user.get_full_name()
