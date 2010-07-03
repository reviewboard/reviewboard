#!/usr/bin/env python

import os
import pkg_resources
import platform
import sys
from random import choice


class SiteOptions(object):
    copy_media = platform.system() == "Windows"


def create_settings():
    if not os.path.exists("settings_local.py"):
        print "Creating a settings_local.py in the current directory."
        print "This can be modified with custom settings."

        src_path = os.path.join("contrib", "conf", "settings_local.py.tmpl")
        in_fp = open(src_path, "r")
        out_fp = open("settings_local.py", "w")

        for line in in_fp.xreadlines():
            if line.startswith("SECRET_KEY = "):
                secret_key = ''.join([
                    choice('abcdefghijklmnopqrstuvwxyz0123456789!@#$%^&*(-_=+)')
                    for i in range(50)
                ])

                out_fp.write('SECRET_KEY = "%s"\n' % secret_key)
            elif line.startswith("DATABASE_NAME = "):
                out_fp.write('DATABASE_NAME = "%s"\n' %
                             os.path.abspath("reviewboard.db"))
            else:
                out_fp.write(line)

        in_fp.close()
        out_fp.close()


def install_media(site):
    print "Rebuilding media paths..."

    media_path = os.path.join("htdocs", "media")
    uploaded_path = os.path.join(site.install_dir, media_path, "uploaded")
    site.mkdir(uploaded_path)
    site.mkdir(os.path.join(uploaded_path, "images"))

    if not pkg_resources.resource_exists("djblets", "media"):
        sys.stderr.write("Unable to find a valid Djblets installation.\n")
        sys.stderr.write("Make sure you've ran `python setup.py develop` "
                         "in the Djblets source tree.\n")
        sys.exit(1)

    print "Using Djblets media from %s" % \
        pkg_resources.resource_filename("djblets", "media")

    site.link_pkg_dir("djblets", "media", os.path.join(media_path, "djblets"))


def build_egg_info():
    os.system("%s setup.py egg_info" % sys.executable)


def main():
    if not os.path.exists(os.path.join("reviewboard", "manage.py")):
        sys.stderr.write("This must be run from the top-level Review Board "
                         "directory\n")
        sys.exit(1)


    # Insert the current directory first in the module path so we find the
    # correct reviewboard package.
    sys.path.insert(0, os.getcwd())
    from reviewboard.cmdline.rbsite import Site


    # Re-use the Site class, since it has some useful functions.
    site = Site("reviewboard", SiteOptions)

    create_settings()
    build_egg_info()

    install_media(site)

    print "Synchronizing database..."
    site.sync_database(allow_input=True)

    print
    print "Your Review Board tree is ready for development."
    print


if __name__ == "__main__":
    main()
