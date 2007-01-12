from django.core.cache import cache
from django.http import HttpResponse
from django.shortcuts import render_to_response
from django.template import RequestContext
from popen2 import Popen3
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

    for filediff in diffset.files.all():
        key = 'diff-sidebyside-%s' % filediff.id
        lines = cache.get(key)

        if lines == None:
            orig_buffer = cache.get(filediff.source_path)

            if orig_buffer == None:
                # It's not cached. Let's go get it.
                try:
                    orig_buffer = \
                        scmtools.get_tool().get_file(filediff.source_path)
                except Exception:
                    # TODO: Include the actual error.
                    return render_to_response(template_name, {
                        'error': "Unable to retrieve the source file %s" % \
                                 filediff.source_path
                    })

                cache.set(filediff.source_path, orig_buffer,
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

            f = open('/tmp/sidediff', 'w')
            f.write(sidebyside_diff)
            f.close()
            prev_change = ""

            for line in sidebyside_diff.split('\n'):
                change = ""

                if len(line) > DIFF_COL_WIDTH:
                    mark = line[DIFF_COL_WIDTH:DIFF_COL_WIDTH+3].strip()

                    if mark == "|":
                        change = "changed"
                    elif mark == "<":
                        change = "removed"
                    elif mark == ">":
                        change = "added"

                if prev_change != change:
                    new_chunk = True
                else:
                    new_chunk = False

                prev_change = change

                oldline = line[0:DIFF_COL_WIDTH]
                newline = line[DIFF_COL_WIDTH+3:]
                lines.append([new_chunk, change, oldline, newline])

            cache.set(key, lines, CACHE_EXPIRATION_TIME)


        files.append({'depot_filename': filediff.source_path,
                      'user_filename': filediff.filename,
                      'lines': lines})

    return render_to_response(template_name, {
        'files': files,
    })
