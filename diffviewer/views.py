import traceback

# This makes sure that the "pygments" identifier exists.  If the pygments
# library is not available, it will be None.  Otherwise, it will be the module
# object.
try:
    import pygments
except ImportError:
    pygments = None

from django.conf import settings
from django.core.paginator import Paginator
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, render_to_response
from django.template import RequestContext
from django.template.loader import render_to_string
from django.utils.safestring import mark_safe
from django.utils.translation import ugettext as _

from djblets.util.misc import cache_memoize, get_object_or_none

from reviewboard.accounts.models import Profile
from reviewboard.diffviewer.models import DiffSet, FileDiff
from reviewboard.diffviewer.diffutils import UserVisibleError, get_diff_files


def get_enable_highlighting(user):
    if user.is_authenticated():
        profile, profile_is_new = Profile.objects.get_or_create(user=user)
        user_syntax_highlighting = profile.syntax_highlighting
    else:
        user_syntax_highlighting = True

    return settings.DIFF_SYNTAX_HIGHLIGHTING and \
           user_syntax_highlighting and pygments


def build_diff_fragment(request, file, chunkindex, highlighting, collapseall,
                        context,
                        template_name='diffviewer/diff_file_fragment.html'):
    key = template_name + '-'

    if file['force_interdiff']:
        if file['interfilediff']:
            key += 'interdiff-%s-%s' % (file['filediff'].id,
                                        file['interfilediff'].id)
        else:
            key += 'interdiff-%s-none' % file['filediff'].id
    else:
        key += str(file['filediff'].id)

    if chunkindex:
        chunkindex = int(chunkindex)
        if chunkindex < 0 or chunkindex >= len(file['chunks']):
            raise UserVisibleError(_(u"Invalid chunk index %s specified.") % \
                                   chunkindex)

        file['chunks'] = [file['chunks'][chunkindex]]
        key += '-chunk-%s' % chunkindex

    if collapseall:
        key += '-collapsed'
        context['collapseall'] = True

    if highlighting:
        key += '-highlighting'

    context['file'] = file

    return cache_memoize(key,
        lambda: render_to_string(template_name,
                                 RequestContext(request, context)))


def view_diff(request, diffset_id, interdiffset_id=None, extra_context={},
              template_name='diffviewer/view_diff.html'):
    diffset = get_object_or_404(DiffSet, pk=diffset_id)
    interdiffset = get_object_or_none(DiffSet, pk=interdiffset_id)
    highlighting = get_enable_highlighting(request.user)

    try:
        files = get_diff_files(diffset, None, interdiffset, highlighting)

        # Break the list of files into pages
        paginator = Paginator(files, settings.DIFFVIEWER_PAGINATE_BY,
                                    orphans=settings.DIFFVIEWER_PAGINATE_ORPHANS)

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

        if request.GET.get('expand', False):
            collapseall = False
        elif request.GET.get('collapse', False):
            collapseall = True
        elif request.COOKIES.has_key('collapsediffs'):
            collapseall = (request.COOKIES['collapsediffs'] == "True")
        else:
            collapseall = True

        context = {
            'diffset': diffset,
            'interdiffset': interdiffset,
            'diffset_pair': (diffset, interdiffset),
        }
        context.update(extra_context)

        # XXX We can probably make this even more awesome and completely skip
        #     the get_diff_files call, caching basically the entire context.
        for file in page.object_list:
            file['fragment'] = mark_safe(build_diff_fragment(request,
                                                             file, None,
                                                             highlighting,
                                                             collapseall,
                                                             context))

        context['files'] = page.object_list

        # Add the pagination context
        context['is_paginated'] = page.has_other_pages()
        context['page'] = page.number
        context['pages'] = paginator.num_pages
        context['page_numbers'] = paginator.page_range
        context['has_next'] = page.has_next()
        context['next_page'] = page.next_page_number()
        context['has_previous'] = page.has_previous()
        context['previous_page'] = page.previous_page_number()

        response = render_to_response(template_name,
                                      RequestContext(request, context))
        response.set_cookie('collapsediffs', collapseall)
        return response

    except Exception, e:
        return exception_traceback(request, e, template_name)


def view_diff_fragment(request, diffset_id, filediff_id, interdiffset_id=None,
                       chunkindex=None, collapseall=False,
                       template_name='diffviewer/diff_file_fragment.html'):
    diffset = get_object_or_404(DiffSet, pk=diffset_id)
    filediff = get_object_or_404(FileDiff, pk=filediff_id, diffset=diffset)
    interdiffset = get_object_or_none(DiffSet, pk=interdiffset_id)
    highlighting = get_enable_highlighting(request.user)

    try:
        files = get_diff_files(diffset, filediff, interdiffset, highlighting)

        if files:
            assert len(files) == 1
            file = files[0]

            context = {
                'standalone': True,
            }

            return HttpResponse(build_diff_fragment(request, file,
                                                    chunkindex,
                                                    highlighting, collapseall,
                                                    context, template_name))
        raise UserVisibleError(
            _(u"Internal error. Unable to locate file record for filediff %s") % \
            filediff.id)
    except Exception, e:
        return exception_traceback(request, e, template_name,
                                   {'standalone': True})


def exception_traceback(request, e, template_name, extra_context={}):
    context = { 'error': e }
    context.update(extra_context)
    if e.__class__ is not UserVisibleError:
        context['trace'] = traceback.format_exc()

    return render_to_response(template_name,
                              RequestContext(request, context))
