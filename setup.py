#!/usr/bin/env python
#
# Setup script for Review Board.
#
# A big thanks to Django project for some of the fixes used in here for
# MacOS X and data files installation.

import os
import subprocess
import sys

from ez_setup import use_setuptools
use_setuptools()

from setuptools import setup, find_packages
from setuptools.command.egg_info import egg_info
from distutils.command.install_data import install_data
from distutils.command.install import INSTALL_SCHEMES
from distutils.core import Command

from reviewboard import get_package_version, is_release, VERSION


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


class BuildEggInfo(egg_info):
    def run(self):
        if (sys.argv[0] in ('sdist', 'bdist_egg', 'install') and
            os.path.exists('settings_local.py')):
            self.run_command('build_media')

        egg_info.run(self)


class BuildMedia(Command):
    user_options = []

    def initialize_options(self):
        pass

    def finalize_options(self):
        pass

    def run(self):
        env = os.environ.copy()
        env['FORCE_BUILD_MEDIA'] = "1"
        retcode = subprocess.call(['./reviewboard/manage.py', 'collectstatic',
                                   '--noinput'],
                                  env=env)

        if retcode != 0:
            raise RuntimeError('Failed to build media files')


cmdclasses = {
    'install_data': install_data,
    'egg_info': BuildEggInfo,
    'build_media': BuildMedia,
}


if sys.platform == "darwin":
    cmdclasses['install_data'] = osx_install_data


PACKAGE_NAME = 'ReviewBoard'

if is_release():
    download_url = 'http://downloads.reviewboard.org/releases/%s/%s.%s/' % \
                   (PACKAGE_NAME, VERSION[0], VERSION[1])
else:
    download_url = 'http://downloads.reviewboard.org/nightlies/'


# Build the reviewboard package.
setup(name=PACKAGE_NAME,
      version=get_package_version(),
      license="MIT",
      description="Review Board, a web-based code review tool",
      url="http://www.reviewboard.org/",
      download_url=download_url,
      author="The Review Board Project",
      author_email="reviewboard@googlegroups.com",
      maintainer="Christian Hammond",
      maintainer_email="chipx86@chipx86.com",
      packages=find_packages(),
      entry_points = {
          'console_scripts': [
              'rb-site = reviewboard.cmdline.rbsite:main',
              'rbssh = reviewboard.cmdline.rbssh:main',
          ],
          'reviewboard.scmtools': [
              'bzr = reviewboard.scmtools.bzr:BZRTool',
              'clearcase = reviewboard.scmtools.clearcase:ClearCaseTool',
              'cvs = reviewboard.scmtools.cvs:CVSTool',
              'git = reviewboard.scmtools.git:GitTool',
              'hg = reviewboard.scmtools.hg:HgTool',
              'perforce = reviewboard.scmtools.perforce:PerforceTool',
              'plastic = reviewboard.scmtools.plastic:PlasticTool',
              'svn = reviewboard.scmtools.svn:SVNTool',
          ],
          'reviewboard.auth_backends': [
              'ad = reviewboard.accounts.backends:ActiveDirectoryBackend',
              'ldap = reviewboard.accounts.backends:LDAPBackend',
              'nis = reviewboard.accounts.backends:NISBackend',
              'x509 = reviewboard.accounts.backends:X509Backend',
          ],
      },
      cmdclass=cmdclasses,
      install_requires=[
          'Django>=1.4c2',
          'django_evolution>=0.6.5',
          'Djblets>=0.7alpha0.dev',
          'django-pipeline>=1.2b5',
          'Pygments>=1.4',
          'flup',
          'paramiko>=1.7.6',
          'python-dateutil==1.5',
          'python-memcached',
          'pytz',
          'recaptcha-client',
      ],
      dependency_links = [
          "http://downloads.reviewboard.org/mirror/",
          'http://www.djangoproject.com/download/1.4-rc-2/tarball/#egg=Django-1.4c2',
          download_url,
      ],
      include_package_data=True,
      zip_safe=False,
      classifiers=[
          "Development Status :: 5 - Production/Stable",
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
