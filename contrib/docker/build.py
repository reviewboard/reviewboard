#!/usr/bin/env python
"""Builds a Docker image for the current version of Review Board."""

from __future__ import print_function, unicode_literals

import argparse
import os
import subprocess
import sys

docker_dir = os.path.dirname(__file__)
sys.path.insert(0, os.path.abspath(os.path.join(docker_dir, '..', '..')))
os.environ['DJANGO_SETTINGS_MODULE'] = 'reviewboard.settings'

from reviewboard import VERSION, get_package_version, is_release


IMAGE_NAME = 'beanbag/reviewboard'


if __name__ == '__main__':
    argparser = argparse.ArgumentParser(
        description='Build and optionally upload the Docker image.')
    argparser.add_argument(
        '--latest',
        dest='tag_latest',
        action='store_true',
        help='whether to tag with "latest" (should only be used if '
             'this is the very latest public version of Review Board.')
    argparser.add_argument(
        '--no-major',
        action='store_false',
        dest='tag_major',
        help='disable tagging the image with the "X.Y" major version tag')
    argparser.add_argument(
        '--upload',
        action='store_true',
        help='upload the image after build')

    options = argparser.parse_args()

    package_version = get_package_version()
    major_version = '%s.%s' % VERSION[:2]
    image_version = package_version

    # If this is a development release, check if a built package has been
    # placed in the packages/ directory.
    if not is_release():
        package_version = '%s.dev0' % package_version
        package_path = os.path.join(docker_dir, 'packages',
                                    'ReviewBoard-%s-py2.py3-none-any.whl'
                                    % package_version)

        if not os.path.exists(package_path):
            sys.stderr.write(
                'To build a Docker image for an in-development '
                'version of Review Board, you will\n'
                'need to build a development and place it at:\n'
                '\n'
                '%s\n'
                % package_path)
            sys.exit(1)

    tags = ['%s:%s' % (IMAGE_NAME, image_version)]

    if options.tag_major:
        tags.append('%s:%s' % (IMAGE_NAME, major_version))

    if options.tag_latest:
        tags.append(IMAGE_NAME)

    # Build the Docker command line to run.
    cmd = [
        'docker', 'build',
        '--build-arg', 'REVIEWBOARD_VERSION=%s' % package_version,
    ]

    for tag in tags:
        cmd += ['-t', tag]

    cmd.append('.')

    # Now build the image.
    p = subprocess.Popen(cmd,
                         stdin=sys.stdin,
                         stdout=sys.stdout,
                         stderr=sys.stderr,
                         cwd=docker_dir)

    if p.wait() != 0:
        sys.exit(1)

    if options.upload:
        for tag in tags:
            p = subprocess.Popen(['docker', 'push', tag],
                                 stdin=sys.stdin,
                                 stdout=sys.stdout,
                                 stderr=sys.stderr,
                                 cwd=docker_dir)

            if p.wait() != 0:
                sys.exit(1)
