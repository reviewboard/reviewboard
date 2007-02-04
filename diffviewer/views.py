from difflib import SequenceMatcher
from django.conf import settings
from django.core.cache import cache
from django.http import HttpResponse, HttpResponseRedirect
from django.shortcuts import get_object_or_404, render_to_response
from django.template import RequestContext
from popen2 import Popen3
from reviewboard.diffviewer.forms import UploadDiffForm
from reviewboard.diffviewer.models import DiffSet, FileDiff
import os, sys, tempfile, traceback
import reviewboard.scmtools as scmtools

def view_diff(request, object_id, template_name='diffviewer/view_diff.html'):
    try:
        diffset = DiffSet.objects.get(pk=object_id)
    except DiffSet.DoesNotExist:
        raise Http404

    class UserVisibleError(Exception):
        pass

    def cache_memoize(key, lookup_callable):
        if cache.has_key(key):
            return cache.get(key)
        data = lookup_callable()
        cache.set(key, data, settings.CACHE_EXPIRATION_TIME)
        return data

    def get_original_file(file):
        """Get a file either from the cache or the SCM.  SCM exceptions are
           passed back to the caller."""
        try:
            return cache_memoize(file, lambda: scmtools.get_tool().get_file(file))
        except Exception, e:
            raise UserVisibleError(str(e))

    def patch(diff, file):
        """Apply a diff to a file.  Delegates out to `patch` because noone
           except Larry Wall knows how to patch."""
        (fd, oldfile) = tempfile.mkstemp()
        f = os.fdopen(fd, "w+b")
        f.write(file)
        f.close()

        newfile = '%s-new' % oldfile
        p = Popen3('patch -o %s %s' % (newfile, oldfile))
        p.tochild.write(diff)
        p.tochild.close()
        failure = p.wait()

        if failure:
            os.unlink(oldfile)
            os.unlink(newfile)
            raise UserVisibleError("The patch didn't apply cleanly: %s" %
                p.fromchild.read())

        f = open(newfile, "r")
        data = f.read()
        f.close()

        os.unlink(oldfile)
        os.unlink(newfile)

        return data

    def get_chunks(filediff):
        old = get_original_file(filediff.source_file)
        new = patch(filediff.diff, old)

        a = (old or '').splitlines(True)
        b = (new or '').splitlines(True)

        chunks = []
        for tag, i1, i2, j1, j2 in SequenceMatcher(None, a, b).get_opcodes():
            chunks.append({
                'oldtext': ''.join(a[i1:i2]),
                'newtext': ''.join(b[j1:j2]),
                'change': tag,
            })

        return chunks

    def add_navigation_cues(files):
        """Add index, nextid and previd data to a list of files/chunks"""
        # FIXME: this modifies in-place right now, which is kind of ugly
        interesting = []
        indices = []
        for i in range(len(files)):
            chunks = files[i]['chunks']
            for j in range(len(chunks)):
                chunk = chunks[j]
                if chunk['change'] != 'equal':
                    interesting.append(chunk)
                    indices.append('%d.%d' % (i, j))

        for chunk, previous, current, next in zip(interesting,
                                                  [None] + indices[:-1],
                                                  indices,
                                                  indices[1:] + [None]):
            chunk['index'] = current
            chunk['previd'] = previous
            chunk['nextid'] = next

    # Create a list of file objects.  We then postprocess this to reconcile
    # all of the chunk IDs.
    try:
        files = []
        for filediff in diffset.files.all():
            revision = \
                scmtools.get_tool().parse_diff_revision(filediff.source_detail)
            chunks = cache_memoize('diff-sidebyside-%s' % filediff.id,
                                   lambda: get_chunks(filediff))

            files.append({
                'depot_filename': filediff.source_file,
                'user_filename': filediff.dest_file,
                'revision': revision,
                'chunks': chunks,
            })

        add_navigation_cues(files)

        return render_to_response(template_name, RequestContext(request, {
            'files': files,
        }))

    except Exception, e:
        context = { 'error': e, }
        if e.__class__ is not UserVisibleError:
            context['trace'] = traceback.format_exc()

        return render_to_response(template_name,
                                  RequestContext(request, context))

def upload(request, donepath, diffset_history_id=None,
           template_name='diffviewer/upload.html'):
    differror = None

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
            except scmtools.FileNotFoundException, e:
                differror = str(e)
    else:
        form = UploadDiffForm()

    return render_to_response(template_name, RequestContext(request, {
        'differror': differror,
        'form': form,
        'diffs_use_absolute_paths':
            scmtools.get_tool().get_diffs_use_absolute_paths(),
    }))
