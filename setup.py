#!/usr/bin/env python
#
# Setup script for Review Board.
#
# A big thanks to Django project for some of the fixes used in here for
# MacOS X and data files installation.

import os
import subprocess
import sys

try:
    from setuptools import setup, find_packages
except ImportError:
    from ez_setup import use_setuptools
    use_setuptools()
    from setuptools import setup, find_packages


from setuptools.command.egg_info import egg_info
from distutils.command.install_data import install_data
from distutils.command.install import INSTALL_SCHEMES
from distutils.core import Command

from reviewboard import (get_package_version,
                         VERSION,
                         django_version)


# Make sure this is a version of Python we are compatible with. This should
# prevent people on older versions from unintentionally trying to install
# the source tarball, and failing.
if sys.hexversion < 0x02050000:
    sys.stderr.write(
        'Review Board %s is incompatible with your version of Python.\n'
        'Please install Review Board 1.6.x or upgrade Python to at least '
        '2.6.x (preferably 2.7).\n' % get_package_version())
    sys.exit(1)
elif sys.hexversion < 0x02060500:
    sys.stderr.write(
        'Review Board %s is incompatible with your version of Python.\n'
        'Please install Review Board 1.7.x or upgrade Python to at least '
        '2.6.5 (preferably 2.7).\n' % get_package_version())
    sys.exit(1)


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
        # The install_data class uses ('install_data', 'install_dir') instead.
        self.set_undefined_options('install', ('install_lib', 'install_dir'))
        install_data.finalize_options(self)


class BuildEggInfo(egg_info):
    def run(self):
        if ('sdist' in sys.argv or
            'bdist_egg' in sys.argv or
            'install' in sys.argv):
            self.run_command('build_media')
            self.run_command('build_i18n')

        egg_info.run(self)


class BuildMedia(Command):
    user_options = []

    def initialize_options(self):
        pass

    def finalize_options(self):
        pass

    def run(self):
        retcode = subprocess.call([
            sys.executable, 'contrib/internal/build-media.py'])

        if retcode != 0:
            raise RuntimeError('Failed to build media files')


class BuildI18n(Command):
    description = 'Compile message catalogs to .mo'
    user_options = []

    def initialize_options(self):
        pass

    def finalize_options(self):
        pass

    def run(self):
        retcode = subprocess.call([
            sys.executable, 'contrib/internal/build-i18n.py'])

        if retcode != 0:
            raise RuntimeError('Failed to build i18n files')


cmdclasses = {
    'install_data': install_data,
    'egg_info': BuildEggInfo,
    'build_media': BuildMedia,
    'build_i18n': BuildI18n,
}


if sys.platform == "darwin":
    cmdclasses['install_data'] = osx_install_data


PACKAGE_NAME = 'ReviewBoard'

download_url = 'http://downloads.reviewboard.org/releases/%s/%s.%s/' % \
               (PACKAGE_NAME, VERSION[0], VERSION[1])


# Build the reviewboard package.
setup(name=PACKAGE_NAME,
      version=get_package_version(),
      license="MIT",
      description="Review Board, a web-based code review tool",
      url="https://www.reviewboard.org/",
      download_url=download_url,
      author="The Review Board Project",
      author_email="reviewboard@googlegroups.com",
      maintainer="Christian Hammond",
      maintainer_email="christian@beanbaginc.com",
      packages=find_packages(),
      entry_points={
          'console_scripts': [
              'rb-site = reviewboard.cmdline.rbsite:main',
              'rbssh = reviewboard.cmdline.rbssh:main',
          ],
          'reviewboard.hosting_services': [
              'assembla = reviewboard.hostingsvcs.assembla:Assembla',
              'beanstalk = reviewboard.hostingsvcs.beanstalk:Beanstalk',
              'bitbucket = reviewboard.hostingsvcs.bitbucket:Bitbucket',
              'bugzilla = reviewboard.hostingsvcs.bugzilla:Bugzilla',
              'codebasehq = reviewboard.hostingsvcs.codebasehq:CodebaseHQ',
              'fedorahosted = '
              'reviewboard.hostingsvcs.fedorahosted:FedoraHosted',
              'fogbugz = reviewboard.hostingsvcs.fogbugz:FogBugz',
              'github = reviewboard.hostingsvcs.github:GitHub',
              'gitlab = reviewboard.hostingsvcs.gitlab:GitLab',
              'gitorious = reviewboard.hostingsvcs.gitorious:Gitorious',
              'googlecode = reviewboard.hostingsvcs.googlecode:GoogleCode',
              'jira = reviewboard.hostingsvcs.jira:JIRA',
              'kiln = reviewboard.hostingsvcs.kiln:Kiln',
              'rbgateway = reviewboard.hostingsvcs.rbgateway:ReviewBoardGateway',
              'redmine = reviewboard.hostingsvcs.redmine:Redmine',
              'sourceforge = reviewboard.hostingsvcs.sourceforge:SourceForge',
              'trac = reviewboard.hostingsvcs.trac:Trac',
              'unfuddle = reviewboard.hostingsvcs.unfuddle:Unfuddle',
              'versionone = reviewboard.hostingsvcs.versionone:VersionOne',
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
              'digest = reviewboard.accounts.backends:HTTPDigestBackend',
          ],
      },
      cmdclass=cmdclasses,
      install_requires=[
          django_version,
          'django_evolution>=0.7.6,<=0.7.999',
          'django-haystack>=2.3.1',
          'django-multiselectfield',
          'Djblets>=0.9.3,<=0.9.999',
          'docutils',
          'markdown>=2.4.0,<2.4.999',
          'mimeparse>=0.1.3',
          'paramiko>=1.12',
          'pycrypto>=2.6',
          'Pygments>=2.1',
          'python-dateutil==1.5',
          'python-memcached',
          'pytz',
          'recaptcha-client',
          'Whoosh>=2.6',
      ],
      dependency_links=[
          'http://downloads.reviewboard.org/mirror/',
          'http://downloads.reviewboard.org/releases/Djblets/0.9/',
          'http://downloads.reviewboard.org/releases/django-evolution/0.7/',
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
      ])
