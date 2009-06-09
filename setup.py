#!/usr/bin/env python
#
# Setup script for Review Board.
#
# A big thanks to Django project for some of the fixes used in here for
# MacOS X and data files installation.

import os
import shutil
import sys

from ez_setup import use_setuptools
use_setuptools()

from setuptools import setup, find_packages
from setuptools.command.build_py import build_py
from distutils.command.install_data import install_data
from distutils.command.install import INSTALL_SCHEMES


# Make sure we're actually in the directory containing setup.py.
root_dir = os.path.dirname(__file__)

if root_dir != "":
    os.chdir(root_dir)


# Tell distutils to put the data_files in platform-specific installation
# locations. See here for an explanation:
# http://groups.google.com/group/comp.lang.python/browse_thread/thread/35ec7b2fed36eaec/2105ee4d9e8042cb
for scheme in INSTALL_SCHEMES.values():
    scheme['data'] = scheme['purelib']


class fixed_build_py(build_py):
    """
    A version of setuptools's build_py that works around a bug when the
    package dir is an empty string. While distutils documents that an empty
    string should be used when the package contents are in the same directory
    as setup.py, setuptools has a bug that breaks with this when installing
    package data from that directory.

    We temporarily set the package directory to "." so that _get_data_files
    can extract the path without breaking.
    """
    def __init__(self, *args, **kwargs):
        build_py.__init__(self, *args, **kwargs)
        self.workaround_pkgdir = False

    def get_package_dir(self, package):
        pkg_dir = build_py.get_package_dir(self, package)

        if self.workaround_pkgdir and pkg_dir == "":
            return "."

        return pkg_dir

    def _get_data_files(self):
        self.workaround_pkgdir = True
        results = build_py._get_data_files(self)
        self.workaround_pkgdir = False

        return results


class osx_install_data(install_data):
    # On MacOS, the platform-specific lib dir is
    # /System/Library/Framework/Python/.../
    # which is wrong. Python 2.5 supplied with MacOS 10.5 has an
    # Apple-specific fix for this in distutils.command.install_data#306. It
    # fixes install_lib but not install_data, which is why we roll our own
    # install_data class.

    def finalize_options(self):
        # By the time finalize_options is called, install.install_lib is
        # set to the fixed directory, so we set the installdir to install_lib.
        # The # install_data class uses ('install_data', 'install_dir') instead.
        self.set_undefined_options('install', ('install_lib', 'install_dir'))
        install_data.finalize_options(self)


if sys.platform == "darwin":
    cmdclasses = {'install_data': osx_install_data}
else:
    cmdclasses = {'install_data': install_data}


# We only want to do this if it's not an sdist build, which means there will
# be a PKG-INFO.
if not os.path.exists("PKG-INFO"):
    if os.path.exists("reviewboard"):
        shutil.rmtree("reviewboard")

    print "Copying tree to staging area..."
    shutil.copytree(".", "reviewboard", True)

    # Clean up things that shouldn't be in there...
    shutil.rmtree("reviewboard/ReviewBoard.egg-info", ignore_errors=True)
    shutil.rmtree("reviewboard/build", ignore_errors=True)
    shutil.rmtree("reviewboard/dist", ignore_errors=True)
    os.unlink("reviewboard/setup.py")
    os.unlink("reviewboard/ez_setup.py")

    if os.path.exists("reviewboard/settings_local.py"):
        os.unlink("reviewboard/settings_local.py")

    if os.path.exists("reviewboard/settings_local.pyc"):
        os.unlink("reviewboard/settings_local.pyc")

# Since we don't actually keep our directories in a reviewboard directory
# like we really should, we have to fake it. Prepend "reviewboard." here,
# set package_dir below, and make sure to exclude our svn:externals
# dependencies.
rb_dirs = []

for dirname in os.listdir("."):
    if os.path.isdir(dirname) and dirname != "reviewboard":
        rb_dirs.append(dirname)
        rb_dirs.append(dirname + ".*")

packages = [
    package_name
    for package_name in find_packages(
        exclude=["reviewboard.djblets",          "reviewboard.djblets.*",
                 "reviewboard.django_evolution", "reviewboard.django_evolution.*"] +
                rb_dirs)
]


# Import this now, since reviewboard is in the right place now.
from reviewboard import VERSION
IS_RELEASE = False


if IS_RELEASE:
    download_url = "http://downloads.review-board.org/releases/"
else:
    download_url = "http://downloads.review-board.org/nightlies/"


# Build the reviewboard package.
setup(name="ReviewBoard",
      version=VERSION,
      license="MIT",
      description="Review Board, a web-based code review tool",
      url="http://www.review-board.org/",
      download_url=download_url,
      author="The Review Board Project",
      author_email="reviewboard@googlegroups.com",
      maintainer="Christian Hammond",
      maintainer_email="chipx86@chipx86.com",
      packages=packages,
      entry_points = {
          'console_scripts': [
              'rb-site = reviewboard.cmdline.rbsite:main',
          ],
      },
      cmdclass=cmdclasses,
      install_requires=[
          'Django>=1.0.2',
          'django_evolution',
          'Djblets>=0.5rc2.dev_20090608',
          'Pygments>=0.10',
          'flup',
          'pytz'
      ],
      dependency_links = [
          "http://downloads.review-board.org/mirror/",
          download_url,
      ],
      include_package_data=True,
      zip_safe=False,
      classifiers=[
          "Development Status :: 4 - Beta",
          "Environment :: Web Environment",
          "Framework :: Django",
          "Intended Audience :: Developers",
          "License :: OSI Approved :: MIT License",
          "Natural Language :: English",
          "Operating System :: OS Independent",
          "Programming Language :: Python",
          "Topic :: Software Development",
          "Topic :: Software Development :: Quality Assurance",
      ]
)


if not os.path.exists("PKG-INFO"):
    shutil.rmtree("reviewboard")
