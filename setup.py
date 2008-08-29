#!/usr/bin/env python
#
# Setup script for Review Board.
#
# A big thanks to Django project for some of the fixes used in here for
# MacOS X and data files installation.

import os
import sys

from ez_setup import use_setuptools
use_setuptools()

from setuptools import setup, find_packages
from distutils.command.install_data import install_data
from distutils.command.install import INSTALL_SCHEMES

from __init__ import VERSION # Ick.


# Make sure we're actually in the directory containing setup.py.
root_dir = os.path.dirname(__file__)

if root_dir != "":
    os.chdir(root_dir)


# Tell distutils to put the data_files in platform-specific installation
# locations. See here for an explanation:
# http://groups.google.com/group/comp.lang.python/browse_thread/thread/35ec7b2fed36eaec/2105ee4d9e8042cb
for scheme in INSTALL_SCHEMES.values():
    scheme['data'] = scheme['purelib']


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


# Since we don't actually keep our directories in a reviewboard directory
# like we really should, we have to fake it. Prepend "reviewboard." here,
# set package_dir below, and make sure to exclude our svn:externals
# dependencies.
packages = [
    "reviewboard." + package_name
    for package_name in find_packages(
        exclude=["djblets",          "djblets.*",
                 "django_evolution", "django_evolution.*"])
]


# Build the reviewboard package.
setup(name="ReviewBoard",
      version=VERSION,
      license="MIT",
      description="Review Board, a web-based code review tool",
      url="http://www.review-board.org/",
      author="The Review Board Project",
      author_email="reviewboard@googlegroups.com",
      maintainer="Christian Hammond",
      maintainer_email="chipx86@chipx86.com",
      packages=packages,
      package_dir={'reviewboard': ''},
      cmdclass=cmdclasses,
      install_requires=['Django>=1.0-beta-1', 'django_evolution', 'Djblets'],
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
