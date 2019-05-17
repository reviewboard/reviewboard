from __future__ import unicode_literals

import logging
import os
import re
import traceback
from zipfile import ZipFile

from django.conf import settings
from django.core.paginator import InvalidPage, Paginator
from django.core.urlresolvers import NoReverseMatch
from django.http import (HttpResponse,
                         HttpResponseBadRequest,
                         HttpResponseNotFound,
                         HttpResponseNotModified,
                         HttpResponseServerError,
                         Http404)
from django.shortcuts import get_object_or_404
from django.utils.safestring import mark_safe
from django.utils.six.moves import cStringIO as StringIO
from django.utils.translation import ugettext as _
from django.views.generic.base import TemplateView, View
from djblets.siteconfig.models import SiteConfiguration
from djblets.util.compat.django.template.loader import render_to_string
from djblets.util.http import encode_etag, etag_if_none_match, set_etag
from pygments import highlight
from pygments.formatters import HtmlFormatter
from pygments.lexers import get_lexer_by_name

from reviewboard.diffviewer.commit_utils import (diff_histories,
                                                 get_base_and_tip_commits)
from reviewboard.diffviewer.diffutils import (get_diff_files,
                                              get_enable_highlighting)
from reviewboard.diffviewer.errors import PatchError, UserVisibleError
from reviewboard.diffviewer.models import DiffCommit, DiffSet, FileDiff
from reviewboard.diffviewer.renderers import (get_diff_renderer,
                                              get_diff_renderer_class)
from reviewboard.scmtools.errors import FileNotFoundError
from reviewboard.site.urlresolvers import local_site_reverse


def get_collapse_diff(request):
    if request.GET.get('expand', False):
        return False
    elif request.GET.get('collapse', False):
        return True
    elif 'collapsediffs' in request.COOKIES:
        return (request.COOKIES['collapsediffs'] == "True")
    else:
        return True


class DiffViewerView(TemplateView):
    """Renders the main diff viewer.

    This renders the diff viewer for a given DiffSet (or an interdiff
    between two DiffSets). It handles loading information on the diffs,
    generating the side-by-side view, and pagination.

    The view expects the following parameters to be provided:

    ``diffset``
        The DiffSet to render.

    The following may also be provided:

    ``interdiffset``
        A DiffSet object representing the other end of an interdiff range.

    The following query parameters can be passed in on the URL:

    ``?expand=1``
        Expands all files within the diff viewer.

    ``?collapse=1``
        Collapses all files within the diff viewer, showing only
        modifications and a few lines of context.

    ``?file=<id>``
        Renders only the FileDiff represented by the provided ID.

    ``?filenames=<pattern>[,<pattern>,...]``
        Renders files matching the given filenames or
        :py:mod:`patterns <fnmatch>`. Patterns are case-sensitive.

    ``?page=<pagenum>``
        Renders diffs found on the given page number, if the diff viewer
        is paginated.

    ``?base-commit-id=<id>``
        The ID of the base commit to use to generate the diff for diffs created
        with multiple commits.

        Only changes from after the specified commit will be included in the
        diff.

    ``?tip-commit-id=<id>``
        The ID of the tip commit to use to generate the diff for diffs created
        created with history.

        No changes from beyond this commit will be included in the diff.
    """

    template_name = 'diffviewer/view_diff.html'
    fragment_error_template_name = 'diffviewer/diff_fragment_error.html'

    def get(self, request, diffset, interdiffset=None, *args, **kwargs):
        """Handles GET requests for this view.

        This will render the full diff viewer based on the provided
        parameters.

        The full rendering time will be logged.

        If there's any exception thrown during rendering, an error page
        with a traceback will be returned instead.
        """
        self.collapse_diffs = get_collapse_diff(request)

        if interdiffset:
            logging.debug('Generating diff viewer page for interdiffset '
                          'ids %s-%s',
                          diffset.id, interdiffset.id, request=request)
        else:
            logging.debug('Generating diff viewer page for filediff id %s',
                          diffset.id, request=request)

        try:
            response = super(DiffViewerView, self).get(
                request, diffset=diffset, interdiffset=interdiffset,
                *args, **kwargs)

            if interdiffset:
                logging.debug('Done generating diff viewer page for '
                              'interdiffset ids %s-%s',
                              diffset.id, interdiffset.id, request=request)
            else:
                logging.debug('Done generating diff viewer page for filediff '
                              'id %s',
                              diffset.id, request=request)

            return response
        except Exception as e:
            if interdiffset:
                interdiffset_id = interdiffset.pk
            else:
                interdiffset_id = None

            logging.exception('%s.get: Error rendering diff for diffset '
                              'ID=%s, interdiffset ID=%s: %s',
                              self.__class__.__name__,
                              diffset.pk,
                              interdiffset_id,
                              e,
                              request=request)

            return exception_traceback(request, e, self.template_name)

    def render_to_response(self, *args, **kwargs):
        """Renders the page to an HttpResponse.

        This renders the diff viewer page, based on the context data
        generated, and sets cookies before returning an HttpResponse to
        the client.
        """
        response = super(DiffViewerView, self).render_to_response(*args,
                                                                  **kwargs)
        response.set_cookie('collapsediffs', self.collapse_diffs)

        return response

    def get_context_data(self, diffset, interdiffset, extra_context={},
                         **kwargs):
        """Calculates and returns data used for rendering the diff viewer.

        This handles all the hard work of generating the data backing the
        side-by-side diff, handling pagination, and more. The data is
        collected into a context dictionary and returned for rendering.
        """
        try:
            filename_patterns = \
                re.split(',+\s*', self.request.GET['filenames'].strip())
        except KeyError:
            filename_patterns = []

        base_commit_id = None
        base_commit = None

        tip_commit_id = None
        tip_commit = None

        commits_by_diffset_id = {}

        if diffset.commit_count > 0:
            diffset_pks = [diffset.pk]

            if interdiffset:
                diffset_pks.append(interdiffset.pk)

            commits = DiffCommit.objects.filter(diffset_id__in=diffset_pks)

            for commit in commits:
                commits_by_diffset_id.setdefault(commit.diffset_id, []).append(
                    commit)

            # Base and tip commit selection is not supported in interdiffs.
            if not interdiffset:
                raw_base_commit_id = self.request.GET.get('base-commit-id')
                raw_tip_commit_id = self.request.GET.get('tip-commit-id')

                if raw_base_commit_id is not None:
                    try:
                        base_commit_id = int(raw_base_commit_id)
                    except ValueError:
                        pass

                if raw_tip_commit_id is not None:
                    try:
                        tip_commit_id = int(raw_tip_commit_id)
                    except ValueError:
                        pass

                base_commit, tip_commit = get_base_and_tip_commits(
                    base_commit_id,
                    tip_commit_id,
                    commits=commits_by_diffset_id[diffset.pk])

        files = get_diff_files(diffset=diffset,
                               interdiffset=interdiffset,
                               request=self.request,
                               filename_patterns=filename_patterns,
                               base_commit=base_commit,
                               tip_commit=tip_commit)

        # Break the list of files into pages
        siteconfig = SiteConfiguration.objects.get_current()

        paginator = Paginator(files,
                              siteconfig.get('diffviewer_paginate_by'),
                              siteconfig.get('diffviewer_paginate_orphans'))

        page_num = int(self.request.GET.get('page', 1))

        if self.request.GET.get('file', False):
            file_id = int(self.request.GET['file'])

            for i, f in enumerate(files):
                if f['filediff'].pk == file_id:
                    page_num = i // paginator.per_page + 1

                    if page_num > paginator.num_pages:
                        page_num = paginator.num_pages

                    break

        try:
            page = paginator.page(page_num)
        except InvalidPage:
            page = paginator.page(paginator.num_pages)

        diff_context = {
            'commits': None,
            'commit_history_diff': None,
            'filename_patterns': list(filename_patterns),
            'revision': {
                'revision': diffset.revision,
                'is_interdiff': interdiffset is not None,
                'interdiff_revision': (interdiffset.revision
                                       if interdiffset else None),
            },
            'pagination': {
                'is_paginated': page.has_other_pages(),
                'current_page': page.number,
                'pages': paginator.num_pages,
                'page_numbers': list(paginator.page_range),
                'has_next': page.has_next(),
                'has_previous': page.has_previous(),
            },
        }

        if page.has_next():
            diff_context['pagination']['next_page'] = page.next_page_number()

        if page.has_previous():
            diff_context['pagination']['previous_page'] = \
                page.previous_page_number()

        if diffset.commit_count > 0:
            if interdiffset:
                diff_context['commit_history_diff'] = [
                    entry.serialize()
                    for entry in diff_histories(
                        commits_by_diffset_id[diffset.pk],
                        commits_by_diffset_id[interdiffset.pk])
                ]

            all_commits = [
                commit
                for pk in commits_by_diffset_id
                for commit in commits_by_diffset_id[pk]
            ]

            diff_context['commits'] = [
                commit.serialize()
                for commit in sorted(all_commits,
                                     key=lambda commit: commit.pk)
            ]

            revision_context = diff_context['revision']

            revision_context.update({
                'base_commit_id': base_commit_id,
                'tip_commit_id': tip_commit_id,
            })

        context = dict({
            'diff_context': diff_context,
            'diffset': diffset,
            'interdiffset': interdiffset,
            'diffset_pair': (diffset, interdiffset),
            'files': page.object_list,
            'collapseall': self.collapse_diffs,
        }, **extra_context)

        return context


class DiffFragmentView(View):
    """Renders a fragment from a file in the diff viewer.

    Based on the diffset data and other arguments provided, this will render
    a fragment from a file in a diff. This may be the entire file, or some
    chunk within.

    The view expects the following parameters to be provided:

        * diffset_or_id
          - A DiffSet object or the ID for one.

        * filediff_id
          - The ID of a FileDiff within the DiffSet.

    The following may also be provided:

        * interdiffset_or_id
          - A DiffSet object or the ID for one representing the other end of
            an interdiff range.

        * interfilediff_id
          - A FileDiff ID for the other end of a revision range.

        * chunk_index
          - The index (0-based) of the chunk to render. If left out, the
            entire file will be rendered.

    Both ``filediff_id` and ``interfilediff_id`` need to be available in the
    URL (or otherwise passed to :py:meth:`get`). ``diffset_or_id`` and
    ``interdiffset_or_id`` are needed in :py:meth:`process_diff_info`, and
    so must be passed either in the URL or in a subclass's definition of
    that method.

    The following query parameters can be passed in on the URL:

    ``?lines-of-context=<count>``
        A number of lines of context to include above and below the chunk.

    ``?base-filediff-id<=id>``
        The primary key of the base FileDiff.

        This parameter is ignored if the review request was created without
        commit history support.

        This conflicts with the ``interfilediff_id``.
    """

    template_name = 'diffviewer/diff_file_fragment.html'
    error_template_name = 'diffviewer/diff_fragment_error.html'
    patch_error_template_name = 'diffviewer/diff_fragment_patch_error.html'

    def get(self, request, *args, **kwargs):
        """Handle GET requests for this view.

        This will create the renderer for the diff fragment, render it, and
        return it.

        If there's an error when rendering the diff fragment, an error page
        will be rendered and returned instead.

        Args:
            request (django.http.HttpRequest):
                The HTTP request.

            *args (tuple):
                Additional positional arguments for the view.

            **kwargs (dict):
                Additional keyword arguments for the view.

        Returns:
            django.http.HttpResponse:
            A response containing the rendered fragment.
        """
        filediff_id = kwargs.get('filediff_id')
        interfilediff_id = kwargs.get('interfilediff_id')
        chunk_index = kwargs.get('chunk_index')

        base_filediff_id = request.GET.get('base-filediff-id')

        try:
            renderer_settings = self._get_renderer_settings(**kwargs)
            etag = self.make_etag(renderer_settings, **kwargs)

            if etag_if_none_match(request, etag):
                return HttpResponseNotModified()

            diff_info_or_response = self.process_diffset_info(
                base_filediff_id=base_filediff_id,
                **kwargs)

            if isinstance(diff_info_or_response, HttpResponse):
                return diff_info_or_response
        except Http404:
            raise
        except Exception as e:
            logging.exception('%s.get: Error when processing diffset info '
                              'for filediff ID=%s, interfilediff ID=%s, '
                              'chunk_index=%s: %s',
                              self.__class__.__name__,
                              filediff_id,
                              interfilediff_id,
                              chunk_index,
                              e,
                              request=request)

            return exception_traceback(self.request, e,
                                       self.error_template_name)

        kwargs.update(diff_info_or_response)

        try:
            context = self.get_context_data(**kwargs)

            renderer = self.create_renderer(
                context=context,
                renderer_settings=renderer_settings,
                *args, **kwargs)
            response = renderer.render_to_response(request)
        except PatchError as e:
            logging.warning(
                '%s.get: PatchError when rendering diffset for filediff '
                'ID=%s, interfilediff ID=%s, chunk_index=%s: %s',
                self.__class__.__name__,
                filediff_id,
                interfilediff_id,
                chunk_index,
                e,
                request=request)

            try:
                url_kwargs = {
                    key: kwargs[key]
                    for key in ('chunk_index', 'interfilediff_id',
                                'review_request_id', 'filediff_id',
                                'revision', 'interdiff_revision')
                    if key in kwargs and kwargs[key] is not None
                }

                bundle_url = local_site_reverse('patch-error-bundle',
                                                kwargs=url_kwargs,
                                                request=request)
            except NoReverseMatch:
                # We'll sometimes see errors about this failing to resolve when
                # web crawlers start accessing fragment URLs without the proper
                # attributes. Ignore them.
                bundle_url = ''

            if e.rejects:
                lexer = get_lexer_by_name('diff')
                formatter = HtmlFormatter()
                rejects = highlight(e.rejects, lexer, formatter)
            else:
                rejects = None

            return HttpResponseServerError(render_to_string(
                template_name=self.patch_error_template_name,
                context={
                    'bundle_url': bundle_url,
                    'file': diff_info_or_response['diff_file'],
                    'filename': os.path.basename(e.filename),
                    'patch_output': e.error_output,
                    'rejects': mark_safe(rejects),
                },
                request=request))
        except FileNotFoundError as e:
            return HttpResponseServerError(render_to_string(
                template_name=self.error_template_name,
                context={
                    'error': e,
                    'file': diff_info_or_response['diff_file'],
                },
                request=request))
        except Exception as e:
            logging.exception('%s.get: Error when rendering diffset for '
                              'filediff ID=%s, interfilediff ID=%s, '
                              'chunkindex=%s: %s',
                              self.__class__.__name__,
                              filediff_id,
                              interfilediff_id,
                              chunk_index,
                              e,
                              request=request)

            return exception_traceback(
                self.request, e, self.error_template_name,
                extra_context={
                    'file': diff_info_or_response['diff_file'],
                })

        if response.status_code == 200:
            set_etag(response, etag)

        return response

    def make_etag(self, renderer_settings, filediff_id,
                  interfilediff_id=None, **kwargs):
        """Return an ETag identifying this render.

        Args:
            renderer_settings (dict):
                The settings determining how to render this diff.

                The following keys are required: ``collapse_all`` and
                ``highlighting``.

                The following key is optional: ``show_deleted``.

            filediff_id (int):
                The ID of the
                :py:class:`~reviewboard.diffviewer.models.filediff.FileDiff`
                being rendered.

            interfilediff_id (int):
                The ID of the
                :py:class:`~reviewboard.diffviewer.models.filediff.FileDiff` on
                the other side of the diff revision, if viewing an interdiff.

            **kwargs (dict):
                Additional keyword arguments passed to the function.

        Return:
            unicode:
            The encoded ETag identifying this render.
        """
        etag = '%s:%s:%s:%s:%s:%s' % (
            get_diff_renderer_class(),
            renderer_settings['collapse_all'],
            renderer_settings['highlighting'],
            filediff_id,
            interfilediff_id,
            settings.TEMPLATE_SERIAL)

        show_deleted = renderer_settings.get('show_deleted')

        if show_deleted:
            etag += ':%s' % show_deleted

        return encode_etag(etag)

    def process_diffset_info(self, diffset_or_id, filediff_id,
                             interfilediff_id=None, interdiffset_or_id=None,
                             base_filediff_id=None, **kwargs):
        """Process and return information on the desired diff.

        The diff IDs and other data passed to the view can be processed and
        converted into DiffSets. A dictionary with the DiffSet and FileDiff
        information will be returned.

        A subclass may instead return a HttpResponse to indicate an error
        with the DiffSets.
        """
        # Depending on whether we're invoked from a URL or from a wrapper
        # with precomputed diffsets, we may be working with either IDs or
        # actual objects. If they're objects, just use them as-is. Otherwise,
        # if they're IDs, we want to grab them both (if both are provided)
        # in one go, to save on an SQL query.
        diffset = None
        interdiffset = None

        diffset_ids = []

        if isinstance(diffset_or_id, DiffSet):
            diffset = diffset_or_id
        else:
            diffset_ids.append(diffset_or_id)

        if interdiffset_or_id:
            if isinstance(interdiffset_or_id, DiffSet):
                interdiffset = interdiffset_or_id
            else:
                diffset_ids.append(interdiffset_or_id)

        if diffset_ids:
            diffsets = DiffSet.objects.filter(pk__in=diffset_ids)

            if len(diffsets) != len(diffset_ids):
                raise Http404

            for temp_diffset in diffsets:
                if temp_diffset.pk == diffset_or_id:
                    diffset = temp_diffset
                elif temp_diffset.pk == interdiffset_or_id:
                    interdiffset = temp_diffset
                else:
                    assert False

        filediff = get_object_or_404(FileDiff, pk=filediff_id, diffset=diffset)

        base_filediff = None
        interfilediff = None

        if interfilediff_id and base_filediff_id:
            raise UserVisibleError(_(
                'Cannot generate an interdiff when base FileDiff ID is '
                'specified.'
            ))
        elif interfilediff_id:
            interfilediff = get_object_or_404(FileDiff, pk=interfilediff_id,
                                              diffset=interdiffset)
        elif base_filediff_id:
            base_filediff = get_object_or_404(FileDiff, pk=base_filediff_id,
                                              diffset=diffset)

            ancestors = filediff.get_ancestors(minimal=False)

            if base_filediff not in ancestors:
                raise UserVisibleError(_(
                    'The requested FileDiff (ID %s) is not a valid base '
                    'FileDiff for FileDiff %s.'
                    % (base_filediff_id, filediff_id)
                ))

        # Store this so we don't end up causing an SQL query later when looking
        # this up.
        filediff.diffset = diffset

        diff_file = self._get_requested_diff_file(
            diffset, filediff, interdiffset, interfilediff, base_filediff)

        if not diff_file:
            raise UserVisibleError(
                _('Internal error. Unable to locate file record for '
                  'filediff %s')
                % filediff.pk)

        return {
            'diffset': diffset,
            'interdiffset': interdiffset,
            'filediff': filediff,
            'diff_file': diff_file,
        }

    def create_renderer(self, context, renderer_settings, diff_file,
                        *args, **kwargs):
        """Creates the renderer for the diff.

        This calculates all the state and data needed for rendering, and
        constructs a DiffRenderer with that data. That renderer is then
        returned, ready for rendering.

        If there's an error in looking up the necessary information, this
        may raise a UserVisibleError (best case), or some other form of
        Exception.
        """
        return get_diff_renderer(
            diff_file,
            extra_context=context,
            template_name=self.template_name,
            **renderer_settings)

    def get_context_data(self, *args, **kwargs):
        """Returns context data used for rendering the view.

        This can be overridden by subclasses to provide additional data for the
        view.
        """
        return {}

    def _get_renderer_settings(self, chunk_index=None, **kwargs):
        """Calculate the render settings for the display of a diff.

        This will calculate settings based on user preferences and URL
        parameters. It does not calculate the state of any DiffSets or
        FileDiffs.
        """
        highlighting = get_enable_highlighting(self.request.user)

        try:
            lines_of_context = self.request.GET.get('lines-of-context', '')
            lines_of_context = [int(i) for i in lines_of_context.split(',', 1)]
        except (TypeError, ValueError):
            lines_of_context = None

        if chunk_index is not None:
            try:
                chunk_index = int(chunk_index)
            except (TypeError, ValueError):
                chunk_index = None

        if lines_of_context:
            collapse_all = True
        elif chunk_index is not None:
            # If we're currently expanding part of a chunk, we want to render
            # the entire chunk without any lines collapsed. In the case of
            # showing a range of lines, we're going to get all chunks and then
            # only show the range. This is so that we won't have separate
            # cached entries for each range.
            collapse_all = False
        else:
            collapse_all = get_collapse_diff(self.request)

        show_deleted = (self.request.GET.get('show-deleted') == '1')

        return {
            'chunk_index': chunk_index,
            'collapse_all': collapse_all,
            'highlighting': highlighting,
            'lines_of_context': lines_of_context,
            'show_deleted': show_deleted,
        }

    def _get_requested_diff_file(self, diffset, filediff, interdiffset,
                                 interfilediff, base_filediff):
        """Fetches information on the requested diff.

        This will look up information on the diff that's to be rendered
        and return it, if found. It may also augment it with additional
        data.

        The file will not contain chunk information. That must be specifically
        populated later.
        """
        files = get_diff_files(diffset=diffset,
                               interdiffset=interdiffset,
                               filediff=filediff,
                               interfilediff=interfilediff,
                               base_filediff=base_filediff,
                               request=self.request)

        if files:
            diff_file = files[0]

            try:
                diff_file['index'] = int(self.request.GET['index'])
            except (KeyError, ValueError):
                pass

            return diff_file

        return None


class DownloadPatchErrorBundleView(DiffFragmentView):
    """A view to download the patch error bundle.

    This view allows users to download a bundle containing data to help debug
    issues when a patch fails to apply. The bundle will contain the diff, the
    original file (as returned by the SCMTool), and the rejects file, if
    applicable.
    """

    def get(self, request, *args, **kwargs):
        """Handle GET requests for this view.

        This will create the renderer for the diff fragment and render it in
        order to get the PatchError information. It then returns a response
        with a zip file containing all the debug data.

        If no PatchError occurred, this will return a 404.

        Args:
            request (django.http.HttpRequest):
                The HTTP request.

            *args (tuple):
                Additional positional arguments for the view.

            **kwargs (dict):
                Additional keyword arguments for the view.

        Returns:
            django.http.HttpResponse:
            A response containing the data bundle.
        """
        try:
            renderer_settings = self._get_renderer_settings(**kwargs)
            etag = self.make_etag(renderer_settings, **kwargs)

            if etag_if_none_match(request, etag):
                return HttpResponseNotModified()

            diff_info_or_response = self.process_diffset_info(**kwargs)

            if isinstance(diff_info_or_response, HttpResponse):
                return diff_info_or_response
        except Http404:
            return HttpResponseNotFound()
        except Exception as e:
            logging.exception(
                '%s.get: Error when processing diffset info for filediff '
                'ID=%s, interfilediff ID=%s, chunk_index=%s: %s',
                self.__class__.__name__,
                kwargs.get('filediff_id'),
                kwargs.get('interfilediff_id'),
                kwargs.get('chunk_index'),
                e,
                request=request)
            return HttpResponseServerError()

        kwargs.update(diff_info_or_response)

        try:
            context = self.get_context_data(**kwargs)

            renderer = self.create_renderer(
                context=context,
                renderer_settings=renderer_settings,
                *args, **kwargs)
            renderer.render_to_response(request)
        except PatchError as e:
            patch_error = e
        except Exception as e:
            logging.exception(
                '%s.get: Error when rendering diffset for filediff ID=%s, '
                'interfilediff ID=%s, chunk_index=%s: %s',
                self.__class__.__name__,
                kwargs.get('filediff_id'),
                kwargs.get('interfilediff_id'),
                kwargs.get('chunk_index'),
                e,
                request=request)
            return HttpResponseServerError()
        else:
            return HttpResponseNotFound()

        zip_data = StringIO()

        with ZipFile(zip_data, 'w') as zipfile:
            basename = os.path.basename(patch_error.filename)
            zipfile.writestr('%s.orig' % basename, patch_error.orig_file)
            zipfile.writestr('%s.diff' % basename, patch_error.diff)

            if patch_error.rejects:
                zipfile.writestr('%s.rej' % basename, patch_error.rejects)

            if patch_error.new_file:
                zipfile.writestr('%s.new' % basename, patch_error.new_file)

        rsp = HttpResponse(zip_data.getvalue(),
                           content_type='application/zip')
        rsp['Content-Disposition'] = \
            'attachment; filename=%s.zip' % basename

        return rsp


def exception_traceback_string(request, e, template_name, extra_context={}):
    context = {'error': e}
    context.update(extra_context)

    if not isinstance(e, UserVisibleError):
        context['trace'] = traceback.format_exc()

    return render_to_string(template_name=template_name,
                            context=context,
                            request=request)


def exception_traceback(request, e, template_name, extra_context={}):
    return HttpResponseServerError(
        exception_traceback_string(request, e, template_name, extra_context))
