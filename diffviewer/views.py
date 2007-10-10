import traceback

try:
    import pygments
except ImportError:
    pygments = None

from django.conf import settings
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, render_to_response
from django.template import RequestContext
from django.template.loader import render_to_string
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
    key = template_name + '-%s' % file['filediff'].id

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
        }
        context.update(extra_context)

        # XXX We can probably make this even more awesome and completely skip
        #     the get_diff_files call, caching basically the entire context.
        for file in files:
            file['fragment'] = build_diff_fragment(request, file, None,
                                                   highlighting, collapseall,
                                                   context)

        context['files'] = files

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
