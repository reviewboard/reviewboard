from __future__ import unicode_literals

import os
import re
import fnmatch

from pipeline.storage import default_storage

__all__ = ["glob", "iglob"]


def glob(pathname):
    """Return a list of paths matching a pathname pattern.

    The pattern may contain simple shell-style wildcards a la fnmatch.

    """
    return sorted(list(iglob(pathname)))


def iglob(pathname):
    """Return an iterator which yields the paths matching a pathname pattern.

    The pattern may contain simple shell-style wildcards a la fnmatch.

    """
    if not has_magic(pathname):
        try:
            if default_storage.exists(pathname):
                yield pathname
        except NotImplementedError:
            # Being optimistic
            yield pathname
        return
    dirname, basename = os.path.split(pathname)
    if not dirname:
        for name in glob1(dirname, basename):
            yield name
        return
    if has_magic(dirname):
        dirs = iglob(dirname)
    else:
        dirs = [dirname]
    if has_magic(basename):
        glob_in_dir = glob1
    else:
        glob_in_dir = glob0
    for dirname in dirs:
        for name in glob_in_dir(dirname, basename):
            yield os.path.join(dirname, name)

# These 2 helper functions non-recursively glob inside a literal directory.
# They return a list of basenames. `glob1` accepts a pattern while `glob0`
# takes a literal basename (so it only has to check for its existence).


def glob1(dirname, pattern):
    try:
        directories, files = default_storage.listdir(dirname)
        names = directories + files
    except Exception:
        # We are not sure that dirname is a real directory
        # and storage implementations are really exotic.
        return []
    if pattern[0] != '.':
        names = [x for x in names if x[0] != '.']
    return fnmatch.filter(names, pattern)


def glob0(dirname, basename):
    if default_storage.exists(os.path.join(dirname, basename)):
        return [basename]
    return []


magic_check = re.compile('[*?[]')


def has_magic(s):
    return magic_check.search(s) is not None
