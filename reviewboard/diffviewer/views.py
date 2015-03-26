from __future__ import unicode_literals

import logging
import traceback

from django.core.paginator import InvalidPage, Paginator
from django.http import HttpResponseServerError, Http404
from django.shortcuts import get_object_or_404
from django.template import RequestContext
from django.template.loader import render_to_string
from django.utils.translation import ugettext as _
from django.views.generic.base import TemplateView, View
from djblets.siteconfig.models import SiteConfiguration

from reviewboard.diffviewer.diffutils import (get_diff_files,
                                              populate_diff_chunks,
                                              get_enable_highlighting)
from reviewboard.diffviewer.errors import UserVisibleError
from reviewboard.diffviewer.models import DiffSet, FileDiff
from reviewboard.diffviewer.renderers import get_diff_renderer


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
        files = get_diff_files(diffset, None, interdiffset,
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

        * chunkindex
          - The index (0-based) of the chunk to render. If left out, the
            entire file will be rendered.

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
        context = self.get_context_data(**kwargs)

        try:
            renderer = self.create_renderer(context, *args, **kwargs)

            return renderer.render_to_response(request)
        except Http404:
            raise
        except Exception as e:
            return exception_traceback(
                self.request, e, self.error_template_name,
                extra_context={
                    'file': self._get_requested_diff_file(False),
                })

    def create_renderer(self, context, diffset_or_id, filediff_id,
                        interdiffset_or_id=None, chunkindex=None,
                        *args, **kwargs):
        """Creates the renderer for the diff.

        This calculates all the state and data needed for rendering, and
        constructs a DiffRenderer with that data. That renderer is then
        returned, ready for rendering.

        If there's an error in looking up the necessary information, this
        may raise a UserVisibleError (best case), or some other form of
        Exception.
        """
        # Depending on whether we're invoked from a URL or from a wrapper
        # with precomputed diffsets, we may be working with either IDs or
        # actual objects. If they're objects, just use them as-is. Otherwise,
        # if they're IDs, we want to grab them both (if both are provided)
        # in one go, to save on an SQL query.
        self.diffset = None
        self.interdiffset = None

        diffset_ids = []

        if isinstance(diffset_or_id, DiffSet):
            self.diffset = diffset_or_id
        else:
            diffset_ids.append(diffset_or_id)

        if interdiffset_or_id:
            if isinstance(interdiffset_or_id, DiffSet):
                self.interdiffset = interdiffset_or_id
            else:
                diffset_ids.append(interdiffset_or_id)

        if diffset_ids:
            diffsets = DiffSet.objects.filter(pk__in=diffset_ids)

            if len(diffsets) != len(diffset_ids):
                raise Http404

            for temp_diffset in diffsets:
                if temp_diffset.pk == diffset_or_id:
                    self.diffset = temp_diffset
                elif temp_diffset.pk == interdiffset_or_id:
                    self.interdiffset = temp_diffset
                else:
                    assert False

        self.highlighting = get_enable_highlighting(self.request.user)
        self.filediff = get_object_or_404(FileDiff, pk=filediff_id,
                                          diffset=self.diffset)

        # Store this so we don't end up causing an SQL query later when looking
        # this up.
        self.filediff.diffset = self.diffset

        try:
            lines_of_context = self.request.GET.get('lines-of-context', '')
            lines_of_context = [int(i) for i in lines_of_context.split(',', 1)]
        except (TypeError, ValueError):
            lines_of_context = None

        if chunkindex is not None:
            try:
                chunkindex = int(chunkindex)
            except (TypeError, ValueError):
                chunkindex = None

        if lines_of_context:
            collapseall = True
        elif chunkindex is not None:
            # If we're currently expanding part of a chunk, we want to render
            # the entire chunk without any lines collapsed. In the case of
            # showing a range of lines, we're going to get all chunks and then
            # only show the range. This is so that we won't have separate
            # cached entries for each range.
            collapseall = False
        else:
            collapseall = get_collapse_diff(self.request)

        self.diff_file = self._get_requested_diff_file()

        if not self.diff_file:
            raise UserVisibleError(
                _('Internal error. Unable to locate file record for '
                  'filediff %s')
                % self.filediff.pk)

        return get_diff_renderer(
            self.diff_file,
            chunk_index=chunkindex,
            highlighting=self.highlighting,
            collapse_all=collapseall,
            lines_of_context=lines_of_context,
            extra_context=context,
            template_name=self.template_name)

    def get_context_data(self, *args, **kwargs):
        """Returns context data used for rendering the view.

        This can be overridden by subclasses to provide additional data for the
        view.
        """
        return {}

    def _get_requested_diff_file(self, get_chunks=True):
        """Fetches information on the requested diff.

        This will look up information on the diff that's to be rendered
        and return it, if found. It may also augment it with additional
        data.

        If get_chunks is True, the diff file information will include chunks
        for rendering. Otherwise, it will just contain generic information
        from the database.
        """
        files = get_diff_files(self.diffset, self.filediff, self.interdiffset,
                               request=self.request)

        if get_chunks:
            populate_diff_chunks(files, self.highlighting,
                                 request=self.request)

        if files:
            assert len(files) == 1
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
