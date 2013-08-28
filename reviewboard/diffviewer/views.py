import logging
import traceback

from django.core.paginator import Paginator
from django.http import HttpResponseServerError, Http404
from django.shortcuts import get_object_or_404, render_to_response
from django.template import RequestContext
from django.template.loader import render_to_string
from django.utils.translation import ugettext as _
from djblets.siteconfig.models import SiteConfiguration

from reviewboard.diffviewer.diffutils import get_diff_files, \
                                             populate_diff_chunks, \
                                             get_enable_highlighting
from reviewboard.diffviewer.errors import UserVisibleError
from reviewboard.diffviewer.models import DiffSet, FileDiff
from reviewboard.diffviewer.renderers import get_diff_renderer, \
                                             get_diff_renderer_class


def get_collapse_diff(request):
    if request.GET.get('expand', False):
        return False
    elif request.GET.get('collapse', False):
        return True
    elif request.COOKIES.has_key('collapsediffs'):
        return (request.COOKIES['collapsediffs'] == "True")
    else:
        return True


def view_diff(request, diffset, interdiffset=None, extra_context={},
              template_name='diffviewer/view_diff.html'):
    highlighting = get_enable_highlighting(request.user)

    try:
        if interdiffset:
            logging.debug("Generating diff viewer page for interdiffset ids "
                          "%s-%s",
                          diffset.id, interdiffset.id, request=request)
        else:
            logging.debug("Generating diff viewer page for filediff id %s",
                          diffset.id, request=request)

        files = get_diff_files(diffset, None, interdiffset, request=request)

        # Break the list of files into pages
        siteconfig = SiteConfiguration.objects.get_current()

        paginator = Paginator(files,
                              siteconfig.get("diffviewer_paginate_by"),
                              siteconfig.get("diffviewer_paginate_orphans"))

        page_num = int(request.GET.get('page', 1))

        if request.GET.get('file', False):
            file_id = int(request.GET['file'])

            for i, f in enumerate(files):
                if f['filediff'].id == file_id:
                    page_num = i // paginator.per_page + 1
                    if page_num > paginator.num_pages:
                        page_num = paginator.num_pages
                    break

        page = paginator.page(page_num)

        collapse_diffs = get_collapse_diff(request)

        context = {
            'diffset': diffset,
            'interdiffset': interdiffset,
            'diffset_pair': (diffset, interdiffset),
            'files': page.object_list,
            'collapseall': collapse_diffs,

            # Add the pagination context
            'is_paginated': page.has_other_pages(),
            'page': page.number,
            'pages': paginator.num_pages,
            'page_numbers': paginator.page_range,
            'has_next': page.has_next(),
            'next_page': page.next_page_number(),
            'has_previous': page.has_previous(),
            'previous_page': page.previous_page_number(),
            'page_start_index': page.start_index(),
        }
        context.update(extra_context)

        renderer_class = get_diff_renderer_class()

        if renderer_class.preload_first_file and page.object_list:
            # Attempt to preload the first file before rendering any part of
            # the page. This helps to remove the perception that the diff
            # viewer takes longer to load now that we have progressive diffs.
            # Users were seeing the page itself load quickly, but didn't see
            # that first diff immediately and instead saw a spinner, making
            # them feel it was taking longer than it used to to load a page.
            # We just trick the user by providing that first file.
            first_file = page.object_list[0]
        else:
            first_file = None

        if first_file:
            filediff = first_file['filediff']

            if filediff.diffset == interdiffset:
                temp_files = get_diff_files(interdiffset, filediff, None,
                                            request=request)
            else:
                temp_files = get_diff_files(diffset, filediff, interdiffset,
                                            request=request)

            if temp_files:
                try:
                    populate_diff_chunks(temp_files, highlighting,
                                         request=request)
                except Exception, e:
                    file_temp = temp_files[0]
                    file_temp['index'] = first_file['index']
                    first_file['fragment'] = \
                        exception_traceback(request, e,
                                            'diffviewer/diff_fragment_error.html',
                                            extra_context={'file': file_temp})
                else:
                    file_temp = temp_files[0]
                    file_temp['index'] = first_file['index']

                    renderer = renderer_class(
                        file_temp,
                        highlighting=highlighting,
                        collapse_all=collapse_diffs,
                        extra_context=context)

                    first_file['fragment'] = renderer.render_to_string()

        response = render_to_response(template_name,
                                      RequestContext(request, context))
        response.set_cookie('collapsediffs', collapse_diffs)

        if interdiffset:
            logging.debug("Done generating diff viewer page for interdiffset "
                          "ids %s-%s",
                          diffset.id, interdiffset.id, request=request)
        else:
            logging.debug("Done generating diff viewer page for filediff "
                          "id %s",
                          diffset.id, request=request)

        return response
    except Exception, e:
        return exception_traceback(request, e, template_name)


def view_diff_fragment(
    request,
    diffset_or_id,
    filediff_id,
    base_url,
    interdiffset_or_id=None,
    chunkindex=None,
    template_name='diffviewer/diff_file_fragment.html',
    error_template_name='diffviewer/diff_fragment_error.html'):
    """View which renders a specific fragment from a diff."""

    def get_requested_diff_file(get_chunks=True):
        files = get_diff_files(diffset, filediff, interdiffset,
                               request=request)

        if get_chunks:
            populate_diff_chunks(files, highlighting, request=request)

        if files:
            assert len(files) == 1
            file = files[0]

            if 'index' in request.GET:
                file['index'] = request.GET.get('index')

            return file

        return None

    # Depending on whether we're invoked from a URL or from a wrapper
    # with precomputed diffsets, we may be working with either IDs or
    # actual objects. If they're objects, just use them as-is. Otherwise,
    # if they're IDs, we want to grab them both (if both are provided)
    # in one go, to save on an SQL query.
    diffset_ids = []
    diffset = None
    interdiffset = None

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

    # Store this so we don't end up causing an SQL query later when looking
    # this up.
    filediff.diffset = diffset

    highlighting = get_enable_highlighting(request.user)

    try:
        lines_of_context = request.GET.get('lines-of-context', '')
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
        # the entire chunk without any lines collapsed. In the case of showing
        # a range of lines, we're going to get all chunks and then only show
        # the range. This is so that we won't have separate cached entries for
        # each range.
        collapseall = False
    else:
        collapseall = get_collapse_diff(request)

    try:
        diff_file = get_requested_diff_file()

        if diff_file:
            renderer = get_diff_renderer(
                diff_file,
                chunk_index=chunkindex,
                highlighting=highlighting,
                collapse_all=collapseall,
                lines_of_context=lines_of_context,
                extra_context={
                    'base_url': base_url,
                },
                template_name=template_name)

            return renderer.render_to_response()

        raise UserVisibleError(
            _(u"Internal error. Unable to locate file record for filediff %s") % \
            filediff.id)
    except Exception, e:
        return exception_traceback(
            request, e, error_template_name,
            extra_context={'file': get_requested_diff_file(False)})


def exception_traceback_string(request, e, template_name, extra_context={}):
    context = { 'error': e }
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
