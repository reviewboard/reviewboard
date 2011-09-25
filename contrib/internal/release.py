#!/usr/bin/env python
#
# Performs a release of Review Board. This can only be run by the core
# developers with release permissions.
#

import hashlib
import mimetools
import os
import shutil
import subprocess
import sys
import tempfile
import urllib2

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))
from reviewboard import __version__, __version_info__, is_release


PY_VERSIONS = ["2.4", "2.5", "2.6", "2.7"]

LATEST_PY_VERSION = PY_VERSIONS[-1]

PACKAGE_NAME = 'ReviewBoard'

RELEASES_URL = \
    'reviewboard.org:/var/www/downloads.reviewboard.org/' \
    'htdocs/releases/%s/%s.%s/' % (PACKAGE_NAME,
                                   __version_info__[0],
                                   __version_info__[1])
RBWEBSITE_API_URL = 'http://www.reviewboard.org/api/'
RELEASES_API_URL = '%sproducts/reviewboard/releases/' % RBWEBSITE_API_URL


built_files = []


def load_config():
    filename = os.path.join(os.path.expanduser('~'), '.rbwebsiterc')

    if not os.path.exists(filename):
        sys.stderr.write("A .rbwebsiterc file must exist in the form of:\n")
        sys.stderr.write("\n")
        sys.stderr.write("USERNAME = '<username>'\n")
        sys.stderr.write("PASSWORD = '<password>'\n")
        sys.exit(1)

    user_config = {}

    try:
        execfile(filename, user_config)
    except SyntaxError, e:
        sys.stderr.write('Syntax error in config file: %s\n'
                         'Line %i offset %i\n' % (filename, e.lineno, e.offset))
        sys.exit(1)

    auth_handler = urllib2.HTTPBasicAuthHandler()
    auth_handler.add_password(realm='Web API',
                              uri=RBWEBSITE_API_URL,
                              user=user_config['USERNAME'],
                              passwd=user_config['PASSWORD'])
    opener = urllib2.build_opener(auth_handler)
    urllib2.install_opener(opener)


def execute(cmdline):
    if isinstance(cmdline, list):
        print ">>> %s" % subprocess.list2cmdline(cmdline)
    else:
        print ">>> %s" % cmdline

    p = subprocess.Popen(cmdline,
                         shell=True,
                         stdout=subprocess.PIPE)

    s = ''

    for data in p.stdout.readlines():
        s += data
        sys.stdout.write(data)

    rc = p.wait()

    if rc != 0:
        print "!!! Error invoking command."
        sys.exit(1)

    return s


def run_setup(target, pyver=LATEST_PY_VERSION):
    execute("python%s ./setup.py release %s" % (pyver, target))


def clone_git_tree(git_dir):
    new_git_dir = tempfile.mkdtemp(prefix='reviewboard-release.')

    os.chdir(new_git_dir)
    execute('git clone %s .' % git_dir)

    return new_git_dir


def build_targets():
    for pyver in PY_VERSIONS:
        run_setup("bdist_egg", pyver)
        built_files.append("dist/%s-%s-py%s.egg" %
                           (PACKAGE_NAME, __version__, pyver))

    run_setup("sdist")
    built_files.append("dist/%s-%s.tar.gz" %
                       (PACKAGE_NAME, __version__))


def build_checksums():
    sha_filename = 'dist/%s-%s.sha256sum' % (PACKAGE_NAME, __version__)
    out_f = open(sha_filename, 'w')

    for filename in built_files:
        m = hashlib.sha256()

        in_f = open(filename, 'r')
        m.update(in_f.read())
        in_f.close()

        out_f.write('%s  %s\n' % (m.hexdigest(), os.path.basename(filename)))

    out_f.close()
    built_files.append(sha_filename)


def upload_files():
    execute("scp %s %s" % (" ".join(built_files), RELEASES_URL))


def tag_release():
    execute("git tag release-%s" % __version__)


def register_release():
    if __version_info__[4] == 'final':
        run_setup("register")

    scm_revision = execute(['git rev-parse', 'release-%s' % __version__])

    data = {
        'major_version': __version_info__[0],
        'minor_version': __version_info__[1],
        'micro_version': __version_info__[2],
        'patch_version': __version_info__[3],
        'release_type': __version_info__[4],
        'release_num': __version_info__[5],
        'scm_revision': scm_revision,
    }

    boundary = mimetools.choose_boundary()
    content = ''

    for key, value in data.iteritems():
        content += '--%s\r\n' % boundary
        content += 'Content-Disposition: form-data; name="%s"\r\n' % key
        content += '\r\n'
        content += str(value) + '\r\n'

    content += '--%s--\r\n' % boundary
    content += '\r\n'

    headers = {
        'Content-Type': 'multipart/form-data; boundary=%s' % boundary,
        'Content-Length': str(len(content)),
    }

    print 'Posting release to reviewboard.org'
    try:
        f = urllib2.urlopen(urllib2.Request(url=RELEASES_API_URL, data=content,
                                            headers=headers))
        f.read()
    except urllib2.HTTPError, e:
        print "Error uploading. Got HTTP code %d:" % e.code
        print e.read()
    except urllib2.URLError, e:
        try:
            print "Error uploading. Got URL error:" % e.code
            print e.read()
        except AttributeError:
            pass


def main():
    if not os.path.exists("setup.py"):
        sys.stderr.write("This must be run from the root of the "
                         "Review Board tree.\n")
        sys.exit(1)

    load_config()

    if not is_release():
        sys.stderr.write("This version is not listed as a release.\n")
        sys.exit(1)

    cur_dir = os.getcwd()
    git_dir = clone_git_tree(cur_dir)

    build_targets()
    build_checksums()
    upload_files()

    os.chdir(cur_dir)
    shutil.rmtree(git_dir)

    tag_release()
    register_release()


if __name__ == "__main__":
    main()
