import traceback

try:
    import pygments
    from pygments.lexers import get_lexer_for_filename
    # from pygments.lexers import guess_lexer_for_filename
    from pygments.formatters import HtmlFormatter
except ImportError:
    pass

from django import newforms as forms
from django.conf import settings
from django.http import HttpResponse, HttpResponseRedirect
from django.shortcuts import get_object_or_404, render_to_response
from django.template import RequestContext
from django.template.loader import render_to_string
from django.utils.html import escape
from djblets.util.misc import cache_memoize, get_object_or_none

from reviewboard.accounts.models import Profile
from reviewboard.diffviewer.forms import UploadDiffForm
from reviewboard.diffviewer.models import DiffSet, FileDiff, DiffSetHistory
from reviewboard.scmtools.models import Repository
import reviewboard.diffviewer.diffutils as diffutils
import reviewboard.scmtools as scmtools


class UserVisibleError(Exception):
    pass


def get_diff_files(diffset, filediff=None, interdiffset=None,
                   enable_syntax_highlighting=True):
    def get_original_file(file, revision):
        """Get a file either from the cache or the SCM.  SCM exceptions are
           passed back to the caller."""
        tool = diffset.repository.get_scmtool()

        if revision == scmtools.HEAD:
            return tool.get_file(file, revision)

        return cache_memoize("%s-%s" % (file, revision),
            lambda: tool.get_file(file, revision))

    def get_patched_file(buffer, filediff):
        return diffutils.patch(filediff.diff, buffer, filediff.dest_file)

    def get_chunks(filediff, interfilediff=None):
        def diff_line(linenum, oldline, newline, oldmarkup, newmarkup):
            if not oldline or not newline:
                return [linenum, oldmarkup or '', [], newmarkup or '', []]

            oldregion, newregion = \
                diffutils.get_line_changed_regions(oldline, newline)

            return [linenum, oldmarkup, oldregion, newmarkup, newregion]

        def new_chunk(lines, numlines, tag, collapsable=False):
            return {
                'lines': lines,
                'numlines': numlines,
                'change': tag,
                'collapsable': collapsable,
            }

        def add_ranged_chunks(lines, start, end, collapsable=False):
            numlines = end - start
            chunks.append(new_chunk(lines[start:end], end - start, 'equal',
                          collapsable))

        def apply_pygments(data, filename):
            # XXX Guessing is preferable but really slow, especially on XML
            #     files.
            #if filename.endswith(".xml"):
            lexer = get_lexer_for_filename(filename, stripnl=False)
            #else:
            #    lexer = guess_lexer_for_filename(filename, data, stripnl=False)

            try:
                # This is only available in 0.7 and higher
                lexer.add_filter('codetagify')
            except AttributeError:
                pass

            return pygments.highlight(data, lexer, HtmlFormatter()).splitlines()


        file = filediff.source_file
        revision = filediff.source_revision
        old = ""

        try:
            if revision != scmtools.PRE_CREATION:
                old = get_original_file(file, revision)

            new = get_patched_file(old, filediff)

            if interfilediff:
                old, new = new, get_patched_file(old, interfilediff)
        except Exception, e:
            raise UserVisibleError(str(e))

        a = (old or '').splitlines()
        b = (new or '').splitlines()
        a_num_lines = len(a)
        b_num_lines = len(b)

        markup_a = markup_b = None

        if enable_syntax_highlighting:
            try:
                # TODO: Try to figure out the right lexer for these files
                #       once instead of twice.
                markup_a = apply_pygments(old or '', filediff.source_file)
                markup_b = apply_pygments(new or '', filediff.dest_file)
            except ValueError:
                pass

        if not markup_a or not markup_b:
            markup_a = escape(old).splitlines()
            markup_b = escape(new).splitlines()

        chunks = []
        linenum = 1
        differ = diffutils.Differ(a, b, ignore_space=True,
                                  compat_version=diffset.diffcompat)

        for tag, i1, i2, j1, j2 in differ.get_opcodes():
            oldlines = markup_a[i1:i2]
            newlines = markup_b[j1:j2]
            numlines = max(len(oldlines), len(newlines))
            lines = map(diff_line,
                        range(linenum, linenum + numlines),
                        a[i1:i2], b[j1:j2], oldlines, newlines)
            linenum += numlines

            if tag == 'equal' and \
               numlines > settings.DIFF_CONTEXT_COLLAPSE_THRESHOLD:
                last_range_start = numlines - settings.DIFF_CONTEXT_NUM_LINES

                if len(chunks) == 0:
                    add_ranged_chunks(lines, 0, last_range_start, True)
                    add_ranged_chunks(lines, last_range_start, numlines)
                else:
                    add_ranged_chunks(lines, 0, settings.DIFF_CONTEXT_NUM_LINES)

                    if i2 == a_num_lines and j2 == b_num_lines:
                        add_ranged_chunks(lines,
                                          settings.DIFF_CONTEXT_NUM_LINES,
                                          numlines, True)
                    else:
                        add_ranged_chunks(lines,
                                          settings.DIFF_CONTEXT_NUM_LINES,
                                          last_range_start, True)
                        add_ranged_chunks(lines, last_range_start, numlines)
            else:
                chunks.append(new_chunk(lines, numlines, tag))

        return chunks

    def add_navigation_cues(files):
        """Add index, nextid and previd data to a list of files/chunks"""
        # FIXME: this modifies in-place right now, which is kind of ugly
        interesting = []
        indices = []
        for i, file in enumerate(files):
            file['index'] = i
            k = 1
            for j, chunk in enumerate(file['chunks']):
                if chunk['change'] != 'equal':
                    interesting.append(chunk)
                    indices.append((i, k))
                    k += 1

            file['num_changes'] = k - 1

        for chunk, previous, current, next in zip(interesting,
                                                  [None] + indices[:-1],
                                                  indices,
                                                  indices[1:] + [None]):
            chunk['index'] = current[1]
            if previous:
                chunk['previd'] = '%d.%d' % previous
            if next:
                chunk['nextid'] = '%d.%d' % next


    key_prefix = "diff-sidebyside"

    if enable_syntax_highlighting:
        key_prefix += "-hl"

    files = []

    if filediff:
        filediffs = [filediff]
    else:
        filediffs = diffset.files.all()

    for filediff in filediffs:
        if filediff.binary:
            chunks = []
        else:
            key = key_prefix
            interfilediff = None

            if interdiffset:
                # XXX This is slow. We should optimize this.
                for filediff2 in interdiffset.files.all():
                    if filediff2.source_file == filediff.source_file:
                        interfilediff = filediff2
                        break

                if interfilediff:
                    key += "interdiff-%s-%s" % (filediff.id, interfilediff.id)
            else:
                key += str(filediff.id)

            chunks = cache_memoize(key, lambda: get_chunks(filediff,
                                                           interfilediff))

        revision = filediff.source_revision

        if revision == scmtools.HEAD:
            revision = "HEAD"
        elif revision == scmtools.PRE_CREATION:
            revision = "Pre-creation"
        else:
            revision = "Revision %s" % revision

        files.append({
            'depot_filename': filediff.source_file,
            'revision': revision,
            'chunks': chunks,
            'filediff': filediff,
            'binary': filediff.binary,
        })

    add_navigation_cues(files)

    return files


def get_enable_highlighting(user):
    if user.is_authenticated():
        profile, profile_is_new = Profile.objects.get_or_create(user=user)
        user_syntax_highlighting = profile.syntax_highlighting
    else:
        user_syntax_highlighting = True

    return settings.DIFF_SYNTAX_HIGHLIGHTING and \
           user_syntax_highlighting and pygments


def render_diff_fragment(request, file, context,
                         template_name='diffviewer/diff_file_fragment.html'):
    context['file'] = file

    return render_to_string(template_name, RequestContext(request, context))


def build_diff_fragment(request, file, chunkindex, highlighting, collapseall,
                        context):
    key = 'diff-fragment-%s' % file['filediff'].id

    if chunkindex:
        chunkindex = int(chunkindex)
        if chunkindex < 0 or chunkindex >= len(file['chunks']):
            raise UserVisibleError("Invalid chunk index %s specified." % \
                                   chunkindex)

        file['chunks'] = [file['chunks'][chunkindex]]
        key += '-chunk-%s' % chunkindex

    if collapseall:
        key += '-collapsed'
    if highlighting:
        key += '-highlighting'

    return cache_memoize(key, lambda: render_diff_fragment(request, file,
                                                           context))


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
            'collapseall': collapseall,
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
        context = { 'error': e, }
        if e.__class__ is not UserVisibleError:
            context['trace'] = traceback.format_exc()

        return render_to_response(template_name,
                                  RequestContext(request, context))


def view_diff_fragment(request, diffset_id, filediff_id, interdiffset_id=None,
                       chunkindex=None,
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
                                                    highlighting, False,
                                                    context))
        raise UserVisibleError(
            "Internal error. Unable to locate file record for filediff %s" % \
            filediff.id)
    except Exception, e:
        context = { 'error': e, 'standalone': True, }
        if e.__class__ is not UserVisibleError:
            context['trace'] = traceback.format_exc()

        return render_to_response(template_name,
                                  RequestContext(request, context))


def upload(request, donepath, diffset_history_id=None,
           template_name='diffviewer/upload.html'):
    differror = None
    repository_id = request.REQUEST.get('repositoryid', None)

    if repository_id == None:
        return HttpResponse("A repository ID was not specified")

    try:
        repository = Repository.objects.get(pk=repository_id)
    except Repository.DoesNotExist:
        return HttpResponse("Repository ID %s was invalid" % repository_id)

    if request.method == 'POST':
        form_data = request.POST.copy()
        form_data.update(request.FILES)
        form = UploadDiffForm(form_data)

        if form.is_valid():
            if diffset_history_id != None:
                diffset_history = get_object_or_404(DiffSetHistory,
                                                    pk=diffset_history_id)
            else:
                diffset_history = None

            try:
                diffset = form.create(request.FILES['path'], diffset_history)
                return HttpResponseRedirect(donepath % diffset.id)
            except scmtools.FileNotFoundError, e:
                form.errors['path'] = forms.util.ErrorList([e])
            except scmtools.SCMError, e:
                form.errors['path'] = forms.util.ErrorList([e])
            except ValueError:
                # FIXME: it'd be nice to have some help as to exactly what broke
                # during parsing.
                form.errors['path'] = forms.util.ErrorList([
                    'This diff did not parse correctly'])
    else:
        form = UploadDiffForm(initial={'repositoryid': repository_id})

    return render_to_response(template_name, RequestContext(request, {
        'form': form,
        'diffs_use_absolute_paths':
            repository.get_scmtool().get_diffs_use_absolute_paths(),
    }))
