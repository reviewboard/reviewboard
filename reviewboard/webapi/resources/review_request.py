from __future__ import unicode_literals

import logging

import dateutil.parser
from django.contrib import auth
from django.contrib.auth.models import User
from django.core.exceptions import (PermissionDenied,
                                    ObjectDoesNotExist,
                                    ValidationError)
from django.db.models import Q
from django.utils import six
from django.utils.timezone import get_current_timezone, is_aware, make_aware
from djblets.util.decorators import augment_method_from
from djblets.webapi.decorators import (webapi_login_required,
                                       webapi_response_errors,
                                       webapi_request_fields)
from djblets.webapi.errors import (DOES_NOT_EXIST,
                                   INVALID_FORM_DATA,
                                   NOT_LOGGED_IN,
                                   PERMISSION_DENIED)
from pytz.exceptions import AmbiguousTimeError

from reviewboard.admin.server import build_server_url
from reviewboard.diffviewer.errors import (DiffTooBigError,
                                           DiffParserError,
                                           EmptyDiffError)
from reviewboard.reviews.errors import (CloseError,
                                        PermissionError,
                                        PublishError,
                                        ReopenError)
from reviewboard.reviews.fields import get_review_request_field
from reviewboard.reviews.models import ReviewRequest
from reviewboard.scmtools.errors import (AuthenticationError,
                                         ChangeNumberInUseError,
                                         EmptyChangeSetError,
                                         InvalidChangeNumberError,
                                         SCMError,
                                         RepositoryNotFoundError)
from reviewboard.site.urlresolvers import local_site_reverse
from reviewboard.ssh.errors import SSHError
from reviewboard.scmtools.models import Repository
from reviewboard.webapi.base import WebAPIResource
from reviewboard.webapi.decorators import webapi_check_local_site
from reviewboard.webapi.encoder import status_to_string, string_to_status
from reviewboard.webapi.errors import (CHANGE_NUMBER_IN_USE,
                                       CLOSE_ERROR,
                                       COMMIT_ID_ALREADY_EXISTS,
                                       DIFF_EMPTY,
                                       DIFF_TOO_BIG,
                                       DIFF_PARSE_ERROR,
                                       EMPTY_CHANGESET,
                                       INVALID_CHANGE_NUMBER,
                                       INVALID_REPOSITORY,
                                       INVALID_USER,
                                       MISSING_REPOSITORY,
                                       PUBLISH_ERROR,
                                       REOPEN_ERROR,
                                       REPO_AUTHENTICATION_ERROR,
                                       REPO_INFO_ERROR)
from reviewboard.webapi.mixins import MarkdownFieldsMixin
from reviewboard.webapi.resources import resources
from reviewboard.webapi.resources.repository import RepositoryResource
from reviewboard.webapi.resources.review_group import ReviewGroupResource
from reviewboard.webapi.resources.review_request_draft import \
    ReviewRequestDraftResource
from reviewboard.webapi.resources.user import UserResource


class ReviewRequestResource(MarkdownFieldsMixin, WebAPIResource):
    """Provides information on review requests.

    Review requests are one of the central concepts in Review Board. They
    represent code or files that are being placed up for review.

    A review request has a number of fields that can be filled out, indicating
    the summary, description of the change, testing that was done, affected
    bugs, and more. These must be filled out through the associated Review
    Request Draft resource.

    When a review request is published, it can be reviewed by users. It can
    then be updated, again through the Review Request Draft resource, or closed
    as submitted or discarded.
    """
    model = ReviewRequest
    name = 'review_request'

    fields = {
        'id': {
            'type': int,
            'description': 'The numeric ID of the review request.',
        },
        'approved': {
            'type': bool,
            'description': 'Whether the review request has been approved '
                           'by reviewers.\n'
                           '\n'
                           'On a default install, a review request is '
                           'approved if it has at least one Ship It! and '
                           'no open issues. Extensions may change these '
                           'requirements.',
            'added_in': '2.0',
        },
        'approval_failure': {
            'type': six.text_type,
            'description': 'The reason why the review request was not '
                           'approved. This will be ``null`` if approved.',
            'added_in': '2.0',
        },
        'blocks': {
            'type': ['reviewboard.webapi.resources.review_request.'
                     'ReviewRequestResource'],
            'description': 'The list of review requests that this '
                           'review request is blocking.',
            'added_in': '1.7.9',
        },
        'close_description': {
            'type': six.text_type,
            'description': 'The text describing the closing of the review '
                           'request.',
            'added_in': '2.0.12',
            'supports_text_types': True,
        },
        'close_description_text_type': {
            'type': MarkdownFieldsMixin.TEXT_TYPES,
            'description': 'The current or forced text type for the '
                           '``close_description`` field.',
            'added_in': '2.0.12',
        },
        'depends_on': {
            'type': ['reviewboard.webapi.resources.review_request.'
                     'ReviewRequestResource'],
            'description': 'The list of review requests that this '
                           'review request depends on.',
            'added_in': '1.7.9',
        },
        'extra_data': {
            'type': dict,
            'description': 'Extra data as part of the review request. '
                           'This can be set by the API or extensions.',
            'added_in': '2.0',
        },
        'issue_dropped_count': {
            'type': int,
            'description': 'The number of dropped issues on this '
                           'review request',
            'added_in': '2.0',
        },
        'issue_open_count': {
            'type': int,
            'description': 'The number of open issues on this review request',
            'added_in': '2.0',
        },
        'issue_resolved_count': {
            'type': int,
            'description': 'The number of resolved issues on this '
                           'review request',
            'added_in': '2.0',
        },
        'submitter': {
            'type': UserResource,
            'description': 'The user who submitted the review request.',
        },
        'time_added': {
            'type': six.text_type,
            'description': 'The date and time that the review request was '
                           'added (in ``YYYY-MM-DD HH:MM:SS`` format).',
        },
        'last_updated': {
            'type': six.text_type,
            'description': 'The date and time that the review request was '
                           'last updated (in ``YYYY-MM-DD HH:MM:SS`` format).',
        },
        'text_type': {
            'type': MarkdownFieldsMixin.TEXT_TYPES,
            'description': 'Formerly responsible for indicating the text '
                           'type for text fields. Replaced by '
                           '``close_description_text_type``, '
                           '``description_text_type``, and '
                           '``testing_done_text_type`` in 2.0.12.',
            'added_in': '2.0',
            'deprecated_in': '2.0.12',
        },
        'status': {
            'type': ('discarded', 'pending', 'submitted'),
            'description': 'The current status of the review request.',
        },
        'public': {
            'type': bool,
            'description': 'Whether or not the review request is currently '
                           'visible to other users.',
        },
        'changenum': {
            'type': int,
            'description': 'The change number that the review request '
                           'represents. These are server-side repository-'
                           'specific change numbers, and are not supported '
                           'by all types of repositories. It may be '
                           '``null``.\n'
                           '\n'
                           'This is deprecated in favor of the ``commit_id`` '
                           'field.',
            'deprecated_in': '2.0',
        },
        'commit_id': {
            'type': six.text_type,
            'description': 'The commit that the review request represents. '
                           'This obsoletes the ``changenum`` field.',
            'added_in': '2.0',
        },
        'repository': {
            'type': RepositoryResource,
            'description': "The repository that the review request's code "
                           "is stored on.",
        },
        'ship_it_count': {
            'type': int,
            'description': 'The number of Ship Its given to this '
                           'review request.',
            'added_in': '2.0',
        },
        'summary': {
            'type': six.text_type,
            'description': "The review request's brief summary.",
        },
        'description': {
            'type': six.text_type,
            'description': "The review request's description.",
            'supports_text_types': True,
        },
        'description_text_type': {
            'type': MarkdownFieldsMixin.TEXT_TYPES,
            'description': 'The current or forced text type for the '
                           '``description`` field.',
            'added_in': '2.0.12',
        },
        'testing_done': {
            'type': six.text_type,
            'description': 'The information on the testing that was done '
                           'for the change.',
            'supports_text_types': True,
        },
        'testing_done_text_type': {
            'type': MarkdownFieldsMixin.TEXT_TYPES,
            'description': 'The current or forced text type for the '
                           '``testing_done`` field.',
            'added_in': '2.0.12',
        },
        'bugs_closed': {
            'type': [six.text_type],
            'description': 'The list of bugs closed or referenced by this '
                           'change.',
        },
        'branch': {
            'type': six.text_type,
            'description': 'The branch that the code was changed on or that '
                           'the code will be committed to. This is a '
                           'free-form field that can store any text.',
        },
        'target_groups': {
            'type': [ReviewGroupResource],
            'description': 'The list of review groups who were requested '
                           'to review this change.',
        },
        'target_people': {
            'type': [UserResource],
            'description': 'The list of users who were requested to review '
                           'this change.',
        },
        'url': {
            'type': six.text_type,
            'description': "The URL to the review request's page on the site. "
                           "This is deprecated and will be removed in a "
                           "future version.",
            'added_in': '1.7.8',
            'deprecated_in': '2.0',
        },
        'absolute_url': {
            'type': six.text_type,
            'description': "The absolute URL to the review request's page on "
                           "the site.",
            'added_in': '2.0',
        },
    }
    uri_object_key = 'review_request_id'
    model_object_key = 'display_id'
    item_child_resources = [
        resources.change,
        resources.diff,
        resources.diff_context,
        resources.review_request_draft,
        resources.review_request_last_update,
        resources.review,
        resources.screenshot,
        resources.file_attachment,
    ]

    allowed_methods = ('GET', 'POST', 'PUT', 'DELETE')

    _close_type_map = {
        'submitted': ReviewRequest.SUBMITTED,
        'discarded': ReviewRequest.DISCARDED,
    }

    def get_related_links(self, obj=None, request=None, *args,
                          **kwargs):
        """Return related links for the resource.

        This will serialize the ``latest_diff`` link when called for the
        item resource with a resource that has associated diffs.

        Args:
            obj (reviewboard.reviews.models.review_request.ReviewRequest, optional):
                The review request.

            request (django.http.HttpRequest, optional):
                The current HTTP request.

            *args (tuple):
                Additional positional arguments.

            **kwargs (dict):
                Additional keyword arguments.

        Returns:
            dict:
            A dictionary of links related to the resource.
        """
        links = super(ReviewRequestResource, self).get_related_links(
            obj=obj, request=request, *args, **kwargs)

        if obj:
            # We already have the diffsets due to get_queryset(), so we aren't
            # performing another query here.
            diffsets = list(obj.diffset_history.diffsets.all())

            if diffsets:
                latest_diffset = diffsets[-1]
                links['latest_diff'] = {
                    'href': build_server_url(local_site_reverse(
                        'diff-resource',
                        request,
                        kwargs={
                            'review_request_id': obj.display_id,
                            'diff_revision': latest_diffset.revision,
                        })),
                    'method': 'GET',
                }

        return links

    def get_queryset(self, request, is_list=False, local_site_name=None,
                     *args, **kwargs):
        """Returns a queryset for ReviewRequest models.

        By default, this returns all published or formerly published
        review requests.

        If the queryset is being used for a list of review request
        resources, then it can be further filtered by one or more arguments
        in the URL. These are listed in @webapi_request_fields for get_list().

        Some arguments accept dates. The handling of dates is quite flexible,
        accepting a variety of date/time formats, but we recommend sticking
        with ISO8601 format.

        ISO8601 format defines a date as being in ``{yyyy}-{mm}-{dd}`` format,
        and a date/time as being in ``{yyyy}-{mm}-{dd}T{HH}:{MM}:{SS}``.
        A timezone can also be appended to this, using ``-{HH:MM}``.

        The following examples are valid dates and date/times:

            * ``2010-06-27``
            * ``2010-06-27T16:26:30``
            * ``2010-06-27T16:26:30-08:00``
        """
        local_site = self._get_local_site(local_site_name)

        if is_list:
            q = Q()

            if 'to-groups' in request.GET:
                for group_name in request.GET.get('to-groups').split(','):
                    q = q & self.model.objects.get_to_group_query(group_name,
                                                                  local_site)

            if 'to-users' in request.GET:
                for username in request.GET.get('to-users').split(','):
                    q = q & self.model.objects.get_to_user_query(username)

            if 'to-users-directly' in request.GET:
                to_users_directly = \
                    request.GET.get('to-users-directly').split(',')

                for username in to_users_directly:
                    q = q & self.model.objects.get_to_user_directly_query(
                        username)

            if 'to-users-groups' in request.GET:
                for username in request.GET.get('to-users-groups').split(','):
                    q = q & self.model.objects.get_to_user_groups_query(
                        username)

            if 'from-user' in request.GET:
                q = q & self.model.objects.get_from_user_query(
                    request.GET.get('from-user'))

            if 'repository' in request.GET:
                q = q & Q(repository=int(request.GET.get('repository')))

            commit_q = Q()
            if 'changenum' in request.GET:
                try:
                    commit_q = Q(changenum=int(request.GET.get('changenum')))
                except (TypeError, ValueError):
                    pass

            commit_id = request.GET.get('commit-id', None)
            if commit_id is not None:
                commit_q = commit_q | Q(commit_id=commit_id)

            if commit_q:
                q = q & commit_q

            if 'ship-it' in request.GET:
                ship_it = request.GET.get('ship-it')

                if ship_it in ('1', 'true', 'True'):
                    q = q & Q(shipit_count__gt=0)
                elif ship_it in ('0', 'false', 'False'):
                    q = q & Q(shipit_count=0)

            q = q & self.build_queries_for_int_field(
                request, 'shipit_count', 'ship-it-count')

            for issue_field in ('issue_open_count', 'issue_dropped_count',
                                'issue_resolved_count'):
                q = q & self.build_queries_for_int_field(
                    request, issue_field)

            if 'time-added-from' in kwargs:
                q = q & Q(time_added__gte=kwargs['time-added-from'])

            if 'time-added-to' in kwargs:
                q = q & Q(time_added__lt=kwargs['time-added-to'])

            if 'last-updated-from' in kwargs:
                q = q & Q(last_updated__gte=kwargs['last-updated-from'])

            if 'last-updated-to' in kwargs:
                q = q & Q(last_updated__lt=kwargs['last-updated-to'])

            status = string_to_status(request.GET.get('status', 'pending'))

            queryset = self.model.objects.public(
                user=request.user,
                status=status,
                local_site=local_site,
                extra_query=q,
                show_all_unpublished=(
                    'show-all-unpublished' in request.GET and
                    request.user.is_superuser
                ))

            # Only select/prefetch these for list resources, since we want to
            # reduce the number of queries. We don't want to do this when
            # retrieving individual items, as they'd end up stuck with
            # prefetched state, which could impact things when handling
            # PUT/DELETE operations.
            #
            # Here's a real-world example (which is interesting enough to
            # talk about): We had a bug before when the prefetching was done
            # for item resources where a publish on the draft resource would
            # fetch the review request from this resource (going through this
            # function and therefore prefetching), and then the publish
            # operation would associate the new diffset and then emit the
            # review_request_published signal. Handlers listening to this that
            # tried to fetch diffsets (Review Bot, in our case) would not see
            # the new diffset.
            #
            # By having this only in the list condition, we get the perforamnce
            # benefits we wanted without triggering that sort of bug.
            queryset = (
                queryset
                .select_related('diffset_history')
                .prefetch_related('changedescs',
                                  'diffset_history__diffsets')
            )
        else:
            queryset = self.model.objects.filter(local_site=local_site)

        return queryset

    def has_access_permissions(self, request, review_request, *args, **kwargs):
        return review_request.is_accessible_by(request.user)

    def has_modify_permissions(self, request, review_request, *args, **kwargs):
        return review_request.is_mutable_by(request.user)

    def has_delete_permissions(self, request, review_request, *args, **kwargs):
        return review_request.is_deletable_by(request.user)

    def get_extra_data_field_supports_markdown(self, review_request, key):
        field_cls = get_review_request_field(key)

        return field_cls and getattr(field_cls, 'enable_markdown', False)

    def get_is_close_description_rich_text(self, obj):
        if obj.status in (obj.SUBMITTED, obj.DISCARDED):
            if hasattr(obj, '_close_description'):
                # This was set when updating the description in a POST, so
                # use that instead of looking up from the database again.
                return obj._close_description_rich_text
            else:
                return obj.get_close_description()[1]
        else:
            return False

    def serialize_bugs_closed_field(self, obj, **kwargs):
        return obj.get_bug_list()

    def serialize_close_description_field(self, obj, **kwargs):
        if obj.status in (obj.SUBMITTED, obj.DISCARDED):
            if hasattr(obj, '_close_description'):
                # This was set when updating the description in a POST, so
                # use that instead of looking up from the database again.
                return obj._close_description
            else:
                return obj.get_close_description()[0]
        else:
            return None

    def serialize_close_description_text_type_field(self, obj, **kwargs):
        # This will be overridden by MarkdownFieldsMixin.
        return None

    def serialize_description_text_type_field(self, obj, **kwargs):
        # This will be overridden by MarkdownFieldsMixin.
        return None

    def serialize_ship_it_count_field(self, obj, **kwargs):
        return obj.shipit_count

    def serialize_status_field(self, obj, **kwargs):
        return status_to_string(obj.status)

    def serialize_testing_done_text_type_field(self, obj, **kwargs):
        # This will be overridden by MarkdownFieldsMixin.
        return None

    def serialize_id_field(self, obj, **kwargs):
        return obj.display_id

    def serialize_url_field(self, obj, **kwargs):
        return obj.get_absolute_url()

    def serialize_absolute_url_field(self, obj, request, **kwargs):
        return request.build_absolute_uri(obj.get_absolute_url())

    def serialize_commit_id_field(self, obj, **kwargs):
        return obj.commit

    @webapi_check_local_site
    @webapi_login_required
    @webapi_response_errors(NOT_LOGGED_IN, PERMISSION_DENIED, INVALID_USER,
                            INVALID_REPOSITORY, CHANGE_NUMBER_IN_USE,
                            INVALID_CHANGE_NUMBER, EMPTY_CHANGESET,
                            REPO_AUTHENTICATION_ERROR, REPO_INFO_ERROR,
                            MISSING_REPOSITORY, DIFF_EMPTY, DIFF_TOO_BIG,
                            DIFF_PARSE_ERROR)
    @webapi_request_fields(
        optional={
            'changenum': {
                'type': int,
                'description': 'The optional change number to look up for the '
                               'review request details. This only works with '
                               'repositories that support server-side '
                               'changesets.\n'
                               '\n'
                               'This is deprecated in favor of the '
                               '``commit_id`` field.',
                'deprecated_in': '2.0',
            },
            'commit_id': {
                'type': six.text_type,
                'description': 'The optional commit to create the review '
                               'request for. This should be used in place of '
                               'the ``changenum`` field.\n'
                               '\n'
                               'If ``create_from_commit_id=1`` is passed, '
                               'then the review request information and diff '
                               'will be based on this commit ID.',
                'added_in': '2.0',
            },
            'create_from_commit_id': {
                'type': bool,
                'description': 'If true, and if ``commit_id`` is provided, '
                               'the review request information and (when '
                               'supported) the idff will be based on the '
                               'commit ID.',
                'added_in': '2.0',
            },
            'force_text_type': {
                'type': MarkdownFieldsMixin.TEXT_TYPES,
                'description': 'The text type, if any, to force for returned '
                               'text fields. The contents will be converted '
                               'to the requested type in the payload, but '
                               'will not be saved as that type.',
                'added_in': '2.0.9',
            },
            'repository': {
                'type': six.text_type,
                'description': 'The path or ID of the repository that the '
                               'review request is for.',
            },
            'submit_as': {
                'type': six.text_type,
                'description': 'The optional user to submit the review '
                               'request as. This requires that the actual '
                               'logged in user is either a superuser or has '
                               'the ``reviews.can_submit_as_another_user`` '
                               'permission.',
            },
        },
        allow_unknown=True
    )
    def create(self, request, repository=None, submit_as=None, changenum=None,
               commit_id=None, local_site_name=None,
               create_from_commit_id=False, extra_fields={}, *args, **kwargs):
        """Creates a new review request.

        The new review request will start off as private and pending, and
        will normally be blank. However, if ``changenum`` or both
        ``commit_id`` and ``create_from_commit_id=1`` is passed and the given
        repository both supports server-side changesets and has changeset
        support in Review Board, some details (Summary, Description and
        Testing Done sections, for instance) may be automatically filled in
        from the server.

        Any new review request will have an associated draft (reachable
        through the ``draft`` link). All the details of the review request
        must be set through the draft. The new review request will be public
        when that first draft is published.

        A repository can be passed. This is required for diffs associated
        with a review request. A valid repository is in the form of a numeric
        repository ID, the name of a repository, or the path to a repository
        (matching exactly the registered repository's Path or Mirror Path
        fields in the adminstration interface).

        If a repository is not passed, this review request can only be
        used for attached files.

        Clients can create review requests on behalf of another user by setting
        the ``submit_as`` parameter to the username of the desired user. This
        requires that the client is currently logged in as a user that has the
        ``reviews.can_submit_as_another_user`` permission set. This capability
        is useful when writing automation scripts, such as post-commit hooks,
        that need to create review requests for another user.

        Extra data can be stored on the review request for later lookup by
        passing ``extra_data.key_name=value``. The ``key_name`` and ``value``
        can be any valid strings. Passing a blank ``value`` will remove the
        key.  The ``extra_data.`` prefix is required.
        """
        user = request.user
        local_site = self._get_local_site(local_site_name)

        changenum = changenum or None
        commit_id = commit_id or None

        if changenum is not None and commit_id is None:
            commit_id = six.text_type(changenum)

            # Preserve the old changenum behavior.
            create_from_commit_id = True

        if submit_as and user.username != submit_as:
            if not user.has_perm('reviews.can_submit_as_another_user',
                                 local_site):
                return self.get_no_access_error(request)

            user = self._find_user(submit_as, local_site, request)

            if not user:
                return INVALID_USER

        if repository is not None:
            try:
                try:
                    repository = Repository.objects.get(pk=int(repository),
                                                        local_site=local_site)
                except ValueError:
                    # The repository is not an ID.
                    repository = Repository.objects.get(
                        (Q(path=repository) |
                         Q(mirror_path=repository) |
                         Q(name=repository)) &
                        Q(local_site=local_site))
            except Repository.DoesNotExist:
                return INVALID_REPOSITORY, {
                    'repository': repository
                }
            except Repository.MultipleObjectsReturned:
                msg = ('Too many repositories matched "%s". '
                       'Try specifying the repository by name instead.'
                       % repository)

                return INVALID_REPOSITORY.with_message(msg), {
                    'repository': repository,
                }

            if not repository.is_accessible_by(request.user):
                return self.get_no_access_error(request)

        try:
            review_request = ReviewRequest.objects.create(
                user, repository, commit_id, local_site,
                create_from_commit_id=create_from_commit_id)

            if extra_fields:
                self.import_extra_data(review_request,
                                       review_request.extra_data,
                                       extra_fields)
                review_request.save(update_fields=['extra_data'])

            return 201, {
                self.item_result_key: review_request
            }
        except AuthenticationError:
            return REPO_AUTHENTICATION_ERROR
        except RepositoryNotFoundError:
            return MISSING_REPOSITORY
        except ChangeNumberInUseError as e:
            return CHANGE_NUMBER_IN_USE, {
                'review_request': e.review_request
            }
        except InvalidChangeNumberError:
            return INVALID_CHANGE_NUMBER
        except EmptyChangeSetError:
            return EMPTY_CHANGESET
        except DiffTooBigError:
            return DIFF_TOO_BIG
        except EmptyDiffError:
            return DIFF_EMPTY
        except DiffParserError as e:
            return DIFF_PARSE_ERROR, {
                'linenum': e.linenum,
                'message': six.text_type(e),
            }
        except SSHError as e:
            logging.error("Got unexpected SSHError when creating "
                          "repository: %s"
                          % e, exc_info=1, request=request)
            return REPO_INFO_ERROR
        except SCMError as e:
            logging.error("Got unexpected SCMError when creating "
                          "repository: %s"
                          % e, exc_info=1, request=request)
            return REPO_INFO_ERROR
        except ValidationError:
            return COMMIT_ID_ALREADY_EXISTS

    @webapi_check_local_site
    @webapi_login_required
    @webapi_response_errors(DOES_NOT_EXIST, NOT_LOGGED_IN, PERMISSION_DENIED)
    @webapi_request_fields(
        optional={
            'status': {
                'type': ('discarded', 'pending', 'submitted'),
                'description': 'The status of the review request. This can '
                               'be changed to close or reopen the review '
                               'request',
            },
            'changenum': {
                'type': int,
                'description': 'The optional change number to set or update.\n'
                               '\n'
                               'This can be used to re-associate with a new '
                               'change number, or to create/update a draft '
                               'with new information from the current '
                               'change number.\n'
                               '\n'
                               'This only works with repositories that '
                               'support server-side changesets.\n'
                               '\n'
                               'This is deprecated. Instead, set '
                               '``commit_id`` and ``update_from_commit_id=1`` '
                               ' on the draft.',
                'added_in': '1.5.4',
                'deprecated_in': '2.0',
            },
            'close_description': {
                'type': six.text_type,
                'description': 'The description of the update. Should only be '
                               'used if the review request have been '
                               'submitted or discarded.\n'
                               '\n'
                               'This replaces the old ``description`` field.',
                'added_in': '2.0.9',
                'supports_text_types': True,
            },
            'close_description_text_type': {
                'type': MarkdownFieldsMixin.SAVEABLE_TEXT_TYPES,
                'description': 'The text type for the close description '
                               'of the update field.',
                'added_in': '2.0',
                'deprecated_in': '2.0.12',
            },
            'description': {
                'type': six.text_type,
                'description': 'The description of the update. Should only be '
                               'used if the review request have been '
                               'submitted or discarded.\n'
                               '\n'
                               'This is deprecated. Instead, set '
                               '``close_description``.',
                'added_in': '1.6',
                'deprecated_in': '2.0.9',
                'supports_text_types': True,
            },
            'force_text_type': {
                'type': MarkdownFieldsMixin.TEXT_TYPES,
                'description': 'The text type, if any, to force for returned '
                               'text fields. The contents will be converted '
                               'to the requested type in the payload, but '
                               'will not be saved as that type.',
                'added_in': '2.0.9',
            },
            'text_type': {
                'type': MarkdownFieldsMixin.SAVEABLE_TEXT_TYPES,
                'description': 'The text type for the close description '
                               'of the update field.\n'
                               '\n'
                               'This is deprecated. Please use '
                               '``close_description_text_type`` instead.',
                'added_in': '2.0',
                'deprecated_in': '2.0.12',
            },
        },
        allow_unknown=True
    )
    def update(self, request, status=None, changenum=None,
               close_description=None, close_description_text_type=None,
               description=None, text_type=None,
               extra_fields={}, *args, **kwargs):
        """Updates the status of the review request.

        The only supported update to a review request's resource is to change
        the status, the associated server-side, change number, or to update
        information from the existing change number.

        The status can be set in order to close the review request as
        discarded or submitted, or to reopen as pending.

        For Perforce, a change number can either be changed to a new number, or
        the current change number can be passed. In either case, a new draft
        will be created or an existing one updated to include information from
        the server based on the change number. This behavior is deprecated,
        and instead, the commit_id field should be set on the draft.

        Changes to a review request's fields, such as the summary or the
        list of reviewers, is made on the Review Request Draft resource.
        This can be accessed through the ``draft`` link. Only when that
        draft is published will the changes end up back in this resource.

        Extra data can be stored on the review request for later lookup by
        passing ``extra_data.key_name=value``. The ``key_name`` and ``value``
        can be any valid strings. Passing a blank ``value`` will remove the
        key. The ``extra_data.`` prefix is required.
        """
        try:
            review_request = \
                resources.review_request.get_object(request, *args, **kwargs)
        except ObjectDoesNotExist:
            return DOES_NOT_EXIST

        is_mutating_field = (
            changenum is not None or
            extra_fields
        )

        if ((is_mutating_field and
             not self.has_modify_permissions(request, review_request)) or
            (status is not None and
             not review_request.is_status_mutable_by(request.user))):
            return self.get_no_access_error(request)

        if (status is not None and
            (review_request.status != string_to_status(status) or
             review_request.status != ReviewRequest.PENDING_REVIEW)):
            try:
                if status in self._close_type_map:
                    close_description = close_description or description
                    close_description_text_type = \
                        close_description_text_type or text_type

                    close_description_rich_text = (
                        close_description_text_type ==
                        self.TEXT_TYPE_MARKDOWN)

                    try:
                        review_request.close(
                            self._close_type_map[status],
                            request.user,
                            close_description,
                            rich_text=close_description_rich_text)
                    except CloseError as e:
                        return CLOSE_ERROR.with_message(six.text_type(e))

                    # Set this so that we'll return this new value when
                    # serializing the object.
                    review_request._close_description = close_description
                    review_request._close_description_rich_text = \
                        close_description_rich_text
                elif status == 'pending':
                    try:
                        review_request.reopen(request.user)
                    except ReopenError as e:
                        return REOPEN_ERROR.with_message(six.text_type(e))
                else:
                    raise AssertionError("Code path for invalid status '%s' "
                                         "should never be reached." % status)
            except PermissionError:
                return self.get_no_access_error(request)
            except PublishError as e:
                return PUBLISH_ERROR.with_message(six.text_type(e))

        # Preserve the old changenum behavior.
        changed_fields = []
        if changenum is not None:
            if review_request.repository is None:
                return INVALID_CHANGE_NUMBER

            if changenum != review_request.changenum:
                review_request.commit = six.text_type(changenum)
                changed_fields.append('changenum')
                changed_fields.append('commit_id')

            try:
                review_request.reopen(request.user)
            except ReopenError as e:
                return REOPEN_ERROR.with_message(six.text_type(e))

            try:
                draft = ReviewRequestDraftResource.prepare_draft(
                    request, review_request)
            except PermissionDenied:
                return PERMISSION_DENIED

            try:
                draft.update_from_commit_id(six.text_type(changenum))
            except InvalidChangeNumberError:
                return INVALID_CHANGE_NUMBER
            except EmptyChangeSetError:
                return EMPTY_CHANGESET

            draft.save()

        if extra_fields:
            self.import_extra_data(review_request, review_request.extra_data,
                                   extra_fields)
            changed_fields.append('extra_data')

        if changed_fields:
            review_request.save(update_fields=changed_fields)

        return 200, {
            self.item_result_key: review_request,
        }

    @webapi_check_local_site
    @augment_method_from(WebAPIResource)
    def delete(self, *args, **kwargs):
        """Deletes the review request permanently.

        This is a dangerous call to make, as it will delete the review
        request, associated screenshots, diffs, and reviews. There is no
        going back after this call is made.

        Only users who have been granted the ``reviews.delete_reviewrequest``
        permission (which includes administrators) can perform a delete on
        the review request.

        After a successful delete, this will return :http:`204`.
        """
        pass

    @webapi_check_local_site
    @webapi_request_fields(
        optional={
            'changenum': {
                'type': int,
                'description': 'The change number the review requests must '
                               'have set. This will only return one review '
                               'request per repository, and only works for '
                               'repository types that support server-side '
                               'changesets. This is deprecated in favor of '
                               'the ``commit_id`` field.',
            },
            'commit-id': {
                'type': six.text_type,
                'description': 'The commit that review requests must have '
                               'set. This will only return one review request '
                               'per repository.\n'
                               '\n'
                               'This obsoletes the ``changenum`` field.',
                'added_in': '2.0',
            },
            'time-added-to': {
                'type': six.text_type,
                'description': 'The date/time that all review requests must '
                               'be added before. This is compared against the '
                               'review request\'s ``time_added`` field. This '
                               'must be a valid :term:`date/time format`.',
            },
            'time-added-from': {
                'type': six.text_type,
                'description': 'The earliest date/time the review request '
                               'could be added. This is compared against the '
                               'review request\'s ``time_added`` field. This '
                               'must be a valid :term:`date/time format`.',
            },
            'last-updated-to': {
                'type': six.text_type,
                'description': 'The date/time that all review requests must '
                               'be last updated before. This is compared '
                               'against the review request\'s '
                               '``last_updated`` field. This must be a valid '
                               ':term:`date/time format`.',
            },
            'last-updated-from': {
                'type': six.text_type,
                'description': 'The earliest date/time the review request '
                               'could be last updated. This is compared '
                               'against the review request\'s '
                               '``last_updated`` field. This must be a valid '
                               ':term:`date/time format`.',
            },
            'from-user': {
                'type': six.text_type,
                'description': 'The username that the review requests must '
                               'be owned by.',
            },
            'repository': {
                'type': int,
                'description': 'The ID of the repository that the review '
                               'requests must be on.',
            },
            'show-all-unpublished': {
                'type': bool,
                'description': 'If set, and if the user is an admin, '
                               'unpublished review requests will also '
                               'be returned.',
                'aded_in': '2.0.8',
            },
            'issue-dropped-count': {
                'type': int,
                'description': 'The review request must have exactly the '
                               'provided number of dropped issues.',
                'added_in': '2.0',
            },
            'issue-dropped-count-lt': {
                'type': int,
                'description': 'The review request must have less than the '
                               'provided number of dropped issues.',
                'added_in': '2.0',
            },
            'issue-dropped-count-lte': {
                'type': int,
                'description': 'The review request must have at most the '
                               'provided number of dropped issues.',
                'added_in': '2.0',
            },
            'issue-dropped-count-gt': {
                'type': int,
                'description': 'The review request must have more than the '
                               'provided number of dropped issues.',
                'added_in': '2.0',
            },
            'issue-dropped-count-gte': {
                'type': int,
                'description': 'The review request must have at least the '
                               'provided number of dropped issues.',
                'added_in': '2.0',
            },
            'issue-open-count': {
                'type': int,
                'description': 'The review request must have exactly the '
                               'provided number of open issues.',
                'added_in': '2.0',
            },
            'issue-open-count-lt': {
                'type': int,
                'description': 'The review request must have less than the '
                               'provided number of open issues.',
                'added_in': '2.0',
            },
            'issue-open-count-lte': {
                'type': int,
                'description': 'The review request must have at most the '
                               'provided number of open issues.',
                'added_in': '2.0',
            },
            'issue-open-count-gt': {
                'type': int,
                'description': 'The review request must have more than the '
                               'provided number of open issues.',
                'added_in': '2.0',
            },
            'issue-open-count-gte': {
                'type': int,
                'description': 'The review request must have at least the '
                               'provided number of open issues.',
                'added_in': '2.0',
            },
            'issue-resolved-count': {
                'type': int,
                'description': 'The review request must have exactly the '
                               'provided number of resolved issues.',
                'added_in': '2.0',
            },
            'issue-resolved-count-lt': {
                'type': int,
                'description': 'The review request must have less than the '
                               'provided number of resolved issues.',
                'added_in': '2.0',
            },
            'issue-resolved-count-lte': {
                'type': int,
                'description': 'The review request must have at most the '
                               'provided number of resolved issues.',
                'added_in': '2.0',
            },
            'issue-resolved-count-gt': {
                'type': int,
                'description': 'The review request must have more than the '
                               'provided number of resolved issues.',
                'added_in': '2.0',
            },
            'issue-resolved-count-gte': {
                'type': int,
                'description': 'The review request must have at least the '
                               'provided number of resolved issues.',
                'added_in': '2.0',
            },
            'ship-it': {
                'type': bool,
                'description': 'The review request must have at least one '
                               'review with Ship It set, if this is 1. '
                               'Otherwise, if 0, it must not have any marked '
                               'Ship It.',
                'added_in': '1.6',
                'deprecated_in': '2.0',
            },
            'ship-it-count': {
                'type': int,
                'description': 'The review request must have exactly the '
                               'provided number of Ship Its.',
                'added_in': '2.0',
            },
            'ship-it-count-lt': {
                'type': int,
                'description': 'The review request must have less than the '
                               'provided number of Ship Its.',
                'added_in': '2.0',
            },
            'ship-it-count-lte': {
                'type': int,
                'description': 'The review request must have at most the '
                               'provided number of Ship Its.',
                'added_in': '2.0',
            },
            'ship-it-count-gt': {
                'type': int,
                'description': 'The review request must have more than the '
                               'provided number of Ship Its.',
                'added_in': '2.0',
            },
            'ship-it-count-gte': {
                'type': int,
                'description': 'The review request must have at least the '
                               'provided number of Ship Its.',
                'added_in': '2.0',
            },
            'status': {
                'type': ('all', 'discarded', 'pending', 'submitted'),
                'description': 'The status of the review requests.',
            },
            'to-groups': {
                'type': six.text_type,
                'description': 'A comma-separated list of review group names '
                               'that the review requests must have in the '
                               'reviewer list.',
            },
            'to-user-groups': {
                'type': six.text_type,
                'description': 'A comma-separated list of usernames who are '
                               'in groups that the review requests must have '
                               'in the reviewer list.',
            },
            'to-users': {
                'type': six.text_type,
                'description': 'A comma-separated list of usernames that the '
                               'review requests must either have in the '
                               'reviewer list specifically or by way of '
                               'a group.',
            },
            'to-users-directly': {
                'type': six.text_type,
                'description': 'A comma-separated list of usernames that the '
                               'review requests must have in the reviewer '
                               'list specifically.',
            }
        },
        allow_unknown=True
    )
    def get_list(self, request, *args, **kwargs):
        """Returns all review requests that the user has read access to.

        By default, this returns all published or formerly published
        review requests.

        The resulting list can be filtered down through the many
        request parameters.
        """
        invalid_fields = {}
        current_tz = get_current_timezone()

        for field in ('time-added-from', 'time-added-to', 'last-updated-from',
                      'last-updated-to'):
            if field in request.GET:
                try:
                    date = dateutil.parser.parse(request.GET[field])

                    if not is_aware(date):
                        date = make_aware(date, current_tz)

                    kwargs[field] = date
                except AmbiguousTimeError:
                    invalid_fields[field] = [
                        'The given timestamp string was ambiguous because of '
                        'daylight savings time changes. You may specify a UTC '
                        'offset instead.'
                    ]
                except ValueError:
                    invalid_fields[field] = [
                        'The given timestamp could not be parsed.'
                    ]

        if invalid_fields:
            return INVALID_FORM_DATA, {
                'fields': invalid_fields,
            }
        else:
            return super(ReviewRequestResource, self).get_list(
                request, *args, **kwargs)

    @augment_method_from(WebAPIResource)
    def get(self, *args, **kwargs):
        """Returns information on a particular review request.

        This contains full information on the latest published review request.

        If the review request is not public, then the client's logged in user
        must either be the owner of the review request or must have the
        ``reviews.can_edit_reviewrequest`` permission set. Otherwise, an
        error will be returned.
        """
        pass

    def get_object(self, request, local_site_name=None, *args, **kwargs):
        """Returns an object, given captured parameters from a URL.

        This is an override of the djblets WebAPIResource get_object, which
        knows about local_id and local_site_name.
        """
        if local_site_name:
            id_field = 'local_id'
        else:
            id_field = 'pk'

        return super(ReviewRequestResource, self).get_object(
            request, id_field=id_field, local_site_name=local_site_name,
            *args, **kwargs)

    def get_href(self, obj, request, *args, **kwargs):
        """Returns the URL for this object.

        This is an override of WebAPIResource.get_href which will use the
        local_id instead of the pk.
        """
        if obj.local_site_id:
            local_site_name = obj.local_site.name
        else:
            local_site_name = None

        href_kwargs = {
            self.uri_object_key: obj.display_id,
        }
        href_kwargs.update(self.get_href_parent_ids(obj))

        return request.build_absolute_uri(
            self.get_item_url(local_site_name=local_site_name, **href_kwargs))

    def _find_user(self, username, local_site, request):
        """Finds a User object matching ``username``.

        This will search all authentication backends, and may create the
        User object if the authentication backend knows that the user exists.
        """
        username = username.strip()

        if local_site:
            users = local_site.users
        else:
            users = User.objects

        try:
            user = users.get(username=username)
        except User.DoesNotExist:
            user = None

            if not local_site:
                for backend in auth.get_backends():
                    try:
                        return backend.get_or_create_user(username, request)
                    except Exception as e:
                        logging.error('Error when calling get_or_create_user '
                                      'for auth backend %r: %s',
                                      backend, e, exc_info=1)

        return user


review_request_resource = ReviewRequestResource()
