from __future__ import unicode_literals

import inspect
import os
import re
import subprocess
import sys

import reviewboard
from reviewboard import VERSION


GIT_BRANCH_CONTAINS_RE = re.compile(r'^\s*([^\s]+)\s+([0-9a-f]+)\s.*')


_head_ref = None


def _run_git(cmd):
    """Run git with the given arguments, returning the output."""
    p = subprocess.Popen(['git'] + cmd, stdout=subprocess.PIPE)
    output, error = p.communicate()
    ret_code = p.poll()

    if ret_code:
        raise subprocess.CalledProcessError(ret_code, 'git')

    return output


def _get_branch_for_version():
    """Return the branch or tag for the current version of Review Board."""
    if VERSION[4] == 'final' or VERSION[5] > 0:
        branch = 'release-%s.%s' % (VERSION[0], VERSION[1])

        if reviewboard.is_release():
            if VERSION[2] > 0:
                branch += '.%s' % VERSION[2]

            if VERSION[4] != 'final':
                branch += VERSION[4]

                if VERSION[5] > 0:
                    branch += '%s' % VERSION[5]
        else:
            branch += '.x'

        return branch
    else:
        return 'master'


def git_get_nearest_tracking_branch(ref='HEAD', remote='origin'):
    """Return the nearest tracking branch for the given Git repository."""
    merge_base = _get_branch_for_version()

    try:
        _run_git(['fetch', 'origin', '%s:%s' % (merge_base, merge_base)])
    except Exception:
        # Ignore, as we may already have this. Hopefully it won't fail later.
        pass

    lines = _run_git(['branch', '-rv', '--contains', merge_base]).splitlines()

    remote_prefix = '%s/' % remote
    best_distance = None
    best_ref_name = None

    for line in lines:
        m = GIT_BRANCH_CONTAINS_RE.match(line.strip())

        if m:
            ref_name = m.group(1)
            sha = m.group(2)

            if (ref_name.startswith(remote_prefix) and
                not ref_name.endswith('/HEAD')):

                distance = len(_run_git(['log',
                                         '--pretty=format:%%H',
                                         '%s..%s' % (ref, sha)]).splitlines())

                if best_distance is None or distance < best_distance:
                    best_distance = distance
                    best_ref_name = ref_name

    if best_ref_name and best_ref_name.startswith(remote_prefix):
        # Strip away the "origin/".
        best_ref_name = best_ref_name[len(remote_prefix):]

    return best_ref_name


def get_git_doc_ref():
    """Return the revision used for linking to source code on GitHub."""
    global _head_ref

    if not _head_ref:
        try:
            branch = git_get_nearest_tracking_branch('.')
            _head_ref = _run_git(['rev-parse', branch]).strip()
        except subprocess.CalledProcessError:
            _head_ref = None

    return _head_ref


def github_linkcode_resolve(domain, info):
    """Return a link to the source on GitHub for the given autodoc info."""
    if (domain != 'py' or not info['module'] or
        not info['module'].startswith('reviewboard')):
        # These aren't the modules you're looking for.
        return None

    # Grab the module referenced in the docs.
    submod = sys.modules.get(info['module'])

    if submod is None:
        return None

    # Split that, trying to find the module at the very tail of the module
    # path.
    obj = submod

    for part in info['fullname'].split('.'):
        try:
            obj = getattr(obj, part)
        except:
            return None

    # Grab the name of the source file.
    try:
        filename = inspect.getsourcefile(obj)
    except:
        filename = None

    if not filename:
        return None

    filename = os.path.relpath(filename,
                               start=os.path.dirname(reviewboard.__file__))

    # Find the line number of the thing being documented.
    try:
        linenum = inspect.findsource(obj)[1]
    except:
        linenum = None

    # Build a reference for the line number in GitHub.
    if linenum:
        linespec = '#L%d' % (linenum + 1)
    else:
        linespec = ''

    # Get the branch/tag/commit to link to.
    ref = get_git_doc_ref()

    if not ref:
        ref = _get_branch_for_version()

    return ('https://github.com/reviewboard/reviewboard/blob/%s/reviewboard/'
            '%s%s'
            % (ref, filename, linespec))
