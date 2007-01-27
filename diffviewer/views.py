from django.core.cache import cache
from django.http import HttpResponse, HttpResponseRedirect
from django.shortcuts import get_object_or_404, render_to_response
from django.template import RequestContext
from popen2 import Popen3
from reviewboard.diffviewer.forms import UploadDiffForm
from reviewboard.diffviewer.models import DiffSet, FileDiff
import os, sys, tempfile
import reviewboard.scmtools as scmtools

CACHE_EXPIRATION_TIME = 60 * 60 * 24 * 30 # 1 month
DIFF_COL_WIDTH=90
DIFF_OPTS = "--side-by-side --expand-tabs --width=%s" % (DIFF_COL_WIDTH * 2 + 3)

def view_diff(request, object_id, template_name='diffviewer/view_diff.html'):
    try:
        diffset = DiffSet.objects.get(pk=object_id)
    except DiffSet.DoesNotExist:
        raise Http404

    def cache_memoize(key, lookup_callable):
        if cache.has_key(key):
            return cache.get(key)
        data = lookup_callable()
        cache.set(file, buffer, CACHE_EXPIRATION_TIME)
        return data

    def get_original_file(file):
        """Get a file either from the cache or the SCM.  SCM exceptions are
           passed back to the caller."""
        return cache_memoize(file, lambda: scmtools.get_tool().get_file(file))

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
            raise Exception("The patch didn't apply cleanly: %s" % p.fromchild)

        f = open(newfile, "r")
        data = f.read()
        f.close()

        os.unlink(oldfile)
        os.unlink(newfile)

        return data


    ##### CRUFT BARRIER #####

    def diff2sidebyside(diff, file):
        """Helper to convert a normal diff to a side-by-side diff"""
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
            raise Exception("The patch didn't apply cleanly.")

        # FIXME: this chops everything to 90 characters.  Yes, p4 htmldiff does
        # this, but it also has a way to override it.  It'd be nice if this could
        # just generate wide diffs when appropriate.
        f = os.popen('diff %s %s %s' % (DIFF_OPTS, oldfile, newfile))
        sidebyside = f.read()
        f.close()

        os.unlink(oldfile)
        os.unlink(newfile)

        return sidebyside

    files = []
    file_index = 0

    for filediff in diffset.files.all():
        key = 'diff-sidebyside-%s' % filediff.id
        lines = cache.get(key)
        chunks = []

        if lines == None:
            try:
                orig_buffer = get_original_file(filediff.source_file)
                sidebyside_diff = diff2sidebyside(filediff.diff, orig_buffer)
            except Exception, e:
                return render_to_response(template_name,
                                          RequestContext(request, {
                    'error': '%s: %s' % (e, e.detail)
                }))

            lines = []
            next_chunk_index = 0

            prev_change = None

            change = ""
            chunk_info = None
            last_changed_index = 0
            i = 0

            for line in sidebyside_diff.split('\n'):
                chunk_changed = False

                oldline = line[0:DIFF_COL_WIDTH].rstrip()
                newline = line[DIFF_COL_WIDTH+3:].rstrip()

                if len(line) > DIFF_COL_WIDTH:
                    mark = line[DIFF_COL_WIDTH:DIFF_COL_WIDTH+3].strip()

                    if mark == "|":
                        change = "changed"
                    elif mark == "<":
                        change = "removed"
                    elif mark == ">":
                        change = "added"
                    else:
                        change = ""

                if prev_change != change:
                    if chunk_info != None:
                        chunks.append(chunk_info)

                    chunk_info = {
                        'oldtext': oldline,
                        'newtext': newline,
                        'change': change
                    }

                    if change != "":
                        last_changed_index = i
                        chunk_info['index'] = next_chunk_index
                        next_chunk_index += 1

                        if chunk_info['index'] == 0:
                            chunk_info['previd'] = file_index
                        else:
                            chunk_info['previd'] = "%s.%s" % \
                                (file_index, chunk_info['index'] - 1)

                        chunk_info['nextid'] = "%s.%s" % \
                            (file_index, chunk_info['index'] + 1)
                    else:
                        chunk_info['index'] = None

                    i += 1
                else:
                    chunk_info['oldtext'] += '\n' + oldline
                    chunk_info['newtext'] += '\n' + newline

                prev_change = change

            chunks.append(chunk_info)

            # Override the nextid of the last chunk to point to the next
            # file or section
            chunks[last_changed_index]['nextid'] = file_index + 1
            cache.set(key, chunks, CACHE_EXPIRATION_TIME)


        revision = \
            scmtools.get_tool().parse_diff_revision(filediff.source_detail)

        if revision == scmtools.HEAD:
            revision = "HEAD"
        else:
            revision = "r" + revision

        files.append({'depot_filename': filediff.source_file,
                      'user_filename': filediff.dest_file,
                      'revision': revision,
                      'index': file_index,
                      'chunks': chunks,
                      'num_chunks': next_chunk_index,
        })

        file_index += 1

    return render_to_response(template_name, RequestContext(request, {
        'files': files,
    }))


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
