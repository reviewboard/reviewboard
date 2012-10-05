import logging
import traceback

from django.conf import settings
from django.core.paginator import Paginator
from django.http import HttpResponse, HttpResponseServerError, Http404
from django.shortcuts import get_object_or_404, render_to_response
from django.template import RequestContext
from django.template.loader import render_to_string
from django.utils.translation import ugettext as _
from djblets.siteconfig.models import SiteConfiguration
from djblets.util.misc import cache_memoize

from reviewboard.diffviewer.models import DiffSet, FileDiff
from reviewboard.diffviewer.diffutils import UserVisibleError, \
                                             compute_chunk_last_header, \
                                             get_diff_files, \
                                             populate_diff_chunks, \
                                             get_enable_highlighting


def build_diff_fragment(request, file, chunkindex, highlighting, collapseall,
                        lines_of_context, context,
                        template_name='diffviewer/diff_file_fragment.html'):
    cache = not lines_of_context
    key = ''

    if cache:
        filediff = file['filediff']
        key = "%s-%s-%s-" % (template_name, file['index'],
                             filediff.diffset.revision)

        if file['force_interdiff']:
            interfilediff = file['interfilediff']

            if interfilediff:
                key += 'interdiff-%s-%s' % (filediff.pk, interfilediff.pk)
            else:
                key += 'interdiff-%s-none' % filediff.pk
        else:
            key += str(filediff.pk)

    if chunkindex:
        chunkindex = int(chunkindex)
        num_chunks = len(file['chunks'])

        if chunkindex < 0 or chunkindex >= num_chunks:
            raise UserVisibleError(_(u"Invalid chunk index %s specified.") % \
                                   chunkindex)

        file['chunks'] = [file['chunks'][chunkindex]]

        if cache:
            key += '-chunk-%s' % chunkindex

        if lines_of_context:
            assert collapseall

            context['lines_of_context'] = lines_of_context

            chunk = file['chunks'][0]
            lines = chunk['lines']
            num_lines = len(lines)
            new_lines = []

            # If we only have one value, then assume it represents before
            # and after the collapsed header area.
            if len(lines_of_context) == 1:
                lines_of_context.append(lines_of_context[0])

            if lines_of_context[0] + lines_of_context[1] >= num_lines:
                # The lines of context we're expanding to would cover the
                # entire chunk, so just expand the entire thing.
                collapseall = False
            else:
                lines_of_context[0] = min(num_lines, lines_of_context[0])
                lines_of_context[1] = min(num_lines, lines_of_context[1])

                # The start of the collapsed header area.
                collapse_i = 0

                # Compute the start of the second chunk of code, after the
                # header.
                if chunkindex < num_chunks - 1:
                    chunk2_i = max(num_lines - lines_of_context[1], 0)
                else:
                    chunk2_i = num_lines

                if lines_of_context[0] and chunkindex > 0:
                    # The chunk of context preceding the header.
                    collapse_i = lines_of_context[0]
                    file['chunks'].insert(0, {
                        'change': chunk['change'],
                        'collapsable': False,
                        'index': chunkindex,
                        'lines': lines[:collapse_i],
                        'meta': chunk['meta'],
                        'numlines': collapse_i,
                    })

                # The header contents
                new_lines += lines[collapse_i:chunk2_i]

                if (chunkindex < num_chunks - 1 and
                    chunk2_i + lines_of_context[1] <= num_lines):
                    # The chunk of context after the header.
                    file['chunks'].append({
                        'change': chunk['change'],
                        'collapsable': False,
                        'index': chunkindex,
                        'lines': lines[chunk2_i:],
                        'meta': chunk['meta'],
                        'numlines': num_lines - chunk2_i,
                    })

                if new_lines:
                    numlines = len(new_lines)

                    chunk.update({
                        'lines': new_lines,
                        'numlines': numlines,
                        'collapsable': True,
                    })

                    # Fix the headers to accommodate the new range.
                    if chunkindex < num_chunks - 1:
                        for prefix, index in (('left', 1), ('right', 4)):
                            chunk['meta'][prefix + '_headers'] = [
                                header
                                for header in chunk['meta'][prefix + '_headers']
                                if header[0] <= new_lines[-1][index]
                            ]

                        chunk['meta']['headers'] = \
                            compute_chunk_last_header(new_lines, numlines,
                                                      chunk['meta'])
                else:
                    file['chunks'].remove(chunk)

    context.update({
        'collapseall': collapseall,
        'file': file,
        'lines_of_context': lines_of_context or (0, 0),
    })

    func = lambda: render_to_string(template_name,
                                    RequestContext(request, context))

    if cache:
        if collapseall:
            key += '-collapsed'

        if highlighting:
            key += '-highlighting'

        key += '-%s' % settings.AJAX_SERIAL

        return cache_memoize(key, func)
    else:
        return func()


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
                          diffset.id, interdiffset.id)
        else:
            logging.debug("Generating diff viewer page for filediff id %s",
                          diffset.id)

        files = get_diff_files(diffset, None, interdiffset)

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

        # Attempt to preload the first file before rendering any part of
        # the page. This helps to remove the perception that the diff viewer
        # takes longer to load now that we have progressive diffs. Users were
        # seeing the page itself load quickly, but didn't see that first
        # diff immediately and instead saw a spinner, making them feel it was
        # taking longer than it used to to load a page. We just trick the
        # user by providing that first file.
        if page.object_list:
            first_file = page.object_list[0]
        else:
            first_file = None

        if first_file:
            filediff = first_file['filediff']

            if filediff.diffset == interdiffset:
                temp_files = get_diff_files(interdiffset, filediff, None)
            else:
                temp_files = get_diff_files(diffset, filediff, interdiffset)

            if temp_files:
                try:
                    populate_diff_chunks(temp_files, highlighting)
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
                    first_file['fragment'] = \
                        build_diff_fragment(request, file_temp, None,
                                            highlighting, collapse_diffs, None,
                                            context,
                                            'diffviewer/diff_file_fragment.html')

        response = render_to_response(template_name,
                                      RequestContext(request, context))
        response.set_cookie('collapsediffs', collapse_diffs)

        if interdiffset:
            logging.debug("Done generating diff viewer page for interdiffset "
                          "ids %s-%s",
                          diffset.id, interdiffset.id)
        else:
            logging.debug("Done generating diff viewer page for filediff "
                          "id %s",
                          diffset.id)

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
        files = get_diff_files(diffset, filediff, interdiffset)

        if get_chunks:
            populate_diff_chunks(files, highlighting)

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

    if lines_of_context:
        collapseall = True
    elif chunkindex:
        # If we're currently expanding part of a chunk, we want to render
        # the entire chunk without any lines collapsed. In the case of showing
        # a range of lines, we're going to get all chunks and then only show
        # the range. This is so that we won't have separate cached entries for
        # each range.
        collapseall = False
    else:
        collapseall = get_collapse_diff(request)

    try:
        file = get_requested_diff_file()

        if file:
            context = {
                'standalone': chunkindex is not None,
                'base_url': base_url,
            }

            return HttpResponse(build_diff_fragment(request, file,
                                                    chunkindex,
                                                    highlighting, collapseall,
                                                    lines_of_context, context,
                                                    template_name))

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
