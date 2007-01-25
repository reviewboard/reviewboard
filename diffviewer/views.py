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

    files = []
    file_index = 0
    chunks = []
    next_chunk_index = 0

    for filediff in diffset.files.all():
        key = 'diff-sidebyside-%s' % filediff.id
        lines = cache.get(key)
        chunks = []
        next_chunk_index = 0

        if lines == None:
            orig_buffer = cache.get(filediff.source_file)

            if orig_buffer == None:
                # It's not cached. Let's go get it.
                try:
                    orig_buffer = \
                        scmtools.get_tool().get_file(filediff.source_file)
                except Exception, e:
                    return render_to_response(template_name, {
                        'error': "%s: %s" % (e, e.detail)
                    })

                cache.set(filediff.source_file, orig_buffer,
                          CACHE_EXPIRATION_TIME)

            try:
                (fd, tempname) = tempfile.mkstemp()
                f = os.fdopen(fd, "w+b")
                f.write(orig_buffer)
                f.close()

                new_file = '%s-new' % tempname
                p = Popen3('patch -o %s %s' % (new_file, tempname))
                p.tochild.write(filediff.diff)
                p.tochild.close()
                ret = p.wait()

                if ret != 0:
                    os.unlink(tempname)
                    os.unlink(new_file)
                    return render_to_response(template_name, {
                        'error': "The patch didn't apply cleanly. Try " +
                                 "re-uploading the patch."
                    })

                f = os.popen('diff %s %s %s' % (DIFF_OPTS, tempname, new_file))
                sidebyside_diff = ''.join(f.readlines())
                f.close()

                os.unlink(tempname)
                os.unlink(new_file)

            except IOError, e:
                raise e # XXX

            lines = []
            next_chunk_index = 0

            f = open('/tmp/sidediff', 'w')
            f.write(sidebyside_diff)
            f.close()
            prev_change = None

            change = None
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


        files.append({'depot_filename': filediff.source_file,
                      'user_filename': filediff.dest_file,
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
    }))
