from __future__ import unicode_literals

import logging
import traceback

from django.conf import settings
from django.core.paginator import InvalidPage, Paginator
from django.http import (HttpResponse, HttpResponseNotModified,
                         HttpResponseServerError, Http404)
from django.shortcuts import get_object_or_404
from django.template import RequestContext
from django.template.loader import render_to_string
from django.utils.translation import ugettext as _
from django.views.generic.base import TemplateView, View
from djblets.siteconfig.models import SiteConfiguration
from djblets.util.http import encode_etag, etag_if_none_match, set_etag

from reviewboard.diffviewer.diffutils import (get_diff_files,
                                              get_enable_highlighting)
from reviewboard.diffviewer.errors import UserVisibleError
from reviewboard.diffviewer.models import DiffSet, FileDiff
from reviewboard.diffviewer.renderers import (get_diff_renderer,
                                              get_diff_renderer_class)
from reviewboard.scmtools.errors import FileNotFoundError


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

        * diffset
          - The DiffSet to render.

    The following may also be provided:

        * interdiffset
          - A DiffSet object representing the other end of an interdiff range.

    The following query parameters can be passed in on the URL:

        * ?expand=1
          - Expands all files within the diff viewer.

        * ?collapse=1
          - Collapses all files within the diff viewer, showing only
            modifications and a few lines of context.

        * ?file=<id>
          - Renders only the FileDiff represented by the provided ID.

        * ?page=<pagenum>
          - Renders diffs found on the given page number, if the diff viewer
            is paginated.
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
        files = get_diff_files(diffset=diffset,
                               interdiffset=interdiffset,
                               request=self.request)

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
                'page_numbers': paginator.page_range,
                'has_next': page.has_next(),
                'has_previous': page.has_previous(),
            },
        }

        if page.has_next():
            diff_context['pagination']['next_page'] = page.next_page_number()

        if page.has_previous():
            diff_context['pagination']['previous_page'] = \
                page.previous_page_number()

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

        * chunkindex
          - The index (0-based) of the chunk to render. If left out, the
            entire file will be rendered.

    Both ``filediff_id` and ``interfilediff_id`` need to be available in the
    URL (or otherwise passed to :py:meth:`get`). ``diffset_or_id`` and
    ``interdiffset_or_id`` are needed in :py:meth:`process_diff_info`, and
    so must be passed either in the URL or in a subclass's definition of
    that method.

    The caller may also pass ``?lines-of-context=`` as a query parameter to
    the URL to indicate how many lines of context should be provided around
    the chunk.
    """

    template_name = 'diffviewer/diff_file_fragment.html'
    error_template_name = 'diffviewer/diff_fragment_error.html'

    def get(self, request, *args, **kwargs):
        """Handles GET requests for this view.

        This will create the renderer for the diff fragment, render it, and
        return it.

        If there's an error when rendering the diff fragment, an error page
        will be rendered and returned instead.
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
            raise
        except Exception as e:
            logging.exception('%s.get: Error when processing diffset info '
                              'for filediff ID=%s, interfilediff ID=%s, '
                              'chunkindex=%s: %s',
                              self.__class__.__name__,
                              kwargs.get('filediff_id'),
                              kwargs.get('interfilediff_id'),
                              kwargs.get('chunkindex'),
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
        except Exception as e:
            if not isinstance(e, FileNotFoundError):
                logging.exception('%s.get: Error when rendering diffset for '
                                  'filediff ID=%s, interfilediff ID=%s, '
                                  'chunkindex=%s: %s',
                                  self.__class__.__name__,
                                  kwargs.get('filediff_id'),
                                  kwargs.get('interfilediff_id'),
                                  kwargs.get('chunkindex'),
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

            filediff_id (int):
                The ID of the
                :py:class:`~reviewboard.diffviewer.models.FileDiff` being
                rendered.

            interfilediff_id (int):
                The ID of the
                :py:class:`~reviewboard.diffviewer.models.FileDiff` on the
                other side of the diff revision, if viewing an interdiff.

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

        return encode_etag(etag)

    def process_diffset_info(self, diffset_or_id, filediff_id,
                             interfilediff_id=None, interdiffset_or_id=None,
                             **kwargs):
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

        if interfilediff_id:
            interfilediff = get_object_or_404(FileDiff, pk=interfilediff_id,
                                              diffset=interdiffset)
        else:
            interfilediff = None

        # Store this so we don't end up causing an SQL query later when looking
        # this up.
        filediff.diffset = diffset

        diff_file = self._get_requested_diff_file(diffset, filediff,
                                                  interdiffset, interfilediff)

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

        return {
            'chunk_index': chunk_index,
            'collapse_all': collapse_all,
            'highlighting': highlighting,
            'lines_of_context': lines_of_context,
        }

    def _get_requested_diff_file(self, diffset, filediff, interdiffset,
                                 interfilediff):
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
                               request=self.request)

        if files:
            file = files[0]

            if 'index' in self.request.GET:
                try:
                    file['index'] = int(self.request.GET.get('index'))
                except ValueError:
                    pass

            return file

        return None


def exception_traceback_string(request, e, template_name, extra_context={}):
    context = {'error': e}
    context.update(extra_context)
    if e.__class__ is not UserVisibleError:
        context['trace'] = traceback.format_exc()

    if request:
        request_context = RequestContext(request, context)
    else:
        request_context = context

    return render_to_string(template_name, request_context)


def exception_traceback(request, e, template_name, extra_context={}):
    return HttpResponseServerError(
        exception_traceback_string(request, e, template_name, extra_context))
