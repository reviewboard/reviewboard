#!/usr/bin/env python
#
# Setup script for Review Board.
#
# A big thanks to Django project for some of the fixes used in here for
# MacOS X and data files installation.

import json
import os
import subprocess
import sys
from distutils.command.install import INSTALL_SCHEMES
from distutils.command.install_data import install_data
from distutils.core import Command

try:
    from setuptools import setup, find_packages
except ImportError:
    from ez_setup import use_setuptools
    use_setuptools()
    from setuptools import setup, find_packages

from setuptools.command.develop import develop
from setuptools.command.egg_info import egg_info

from reviewboard import get_package_version, VERSION
from reviewboard.dependencies import (build_dependency_list,
                                      package_dependencies)


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
            'bdist_wheel' in sys.argv or
            'install' in sys.argv):
            self.run_command('build_media')
            self.run_command('build_i18n')

        egg_info.run(self)


class DevelopCommand(develop):
    """Installs Review Board in developer mode.

    This will install all standard and development dependencies (using Python
    wheels and node.js packages from npm) and add the source tree to the
    Python module search path. That includes updating the versions of pip
    and setuptools on the system.

    To speed up subsequent runs, callers can pass ``--no-npm`` to prevent
    installing node.js packages.
    """

    user_options = develop.user_options + [
        ('no-npm', None, "Don't install packages from npm"),
        ('use-npm-cache', None, "Use npm-cache to install packages"),
    ]

    boolean_options = develop.boolean_options + ['no-npm', 'use-npm-cache']

    def initialize_options(self):
        """Initialize options for the command."""
        develop.initialize_options(self)

        self.no_npm = None
        self.use_npm_cache = None

    def install_for_development(self):
        """Install the package for development.

        This takes care of the work of installing all dependencies.
        """
        if self.no_deps:
            # In this case, we don't want to install any of the dependencies
            # below. However, it's really unlikely that a user is going to
            # want to pass --no-deps.
            #
            # Instead, what this really does is give us a way to know we've
            # been called by `pip install -e .`. That will call us with
            # --no-deps, as it's going to actually handle all dependency
            # installation, rather than having easy_install do it.
            develop.install_for_development(self)
            return

        # Install the latest pip and setuptools. Note that the order here
        # matters, as otherwise a stale setuptools can be left behind,
        # causing installation errors.
        self._run_pip(['install', '-U', 'setuptools'])
        self._run_pip(['install', '-U', 'pip'])

        # Install the dependencies using pip instead of easy_install. This
        # will use wheels instead of eggs, which are ideal for our users.
        if sys.platform == 'darwin':
            # We're building on macOS, and some of our dependencies
            # (hi there, mercurial!) won't compile using gcc (their default
            # in some cases), so we want to force the proper compiler.
            os.putenv(b'CC', b'clang')

        self._run_pip(['install', '-e', '.'])
        self._run_pip(['install', '-r', 'dev-requirements.txt'])

        if not self.no_npm:
            if self.use_npm_cache:
                self.distribution.command_options['install_node_deps'] = {
                    'use_npm_cache': ('install_node_deps', 1),
                }

            self.run_command('install_node_deps')

    def _run_pip(self, args):
        """Run pip.

        Args:
            args (list):
                Arguments to pass to :command:`pip`.

        Raises:
            RuntimeError:
                The :command:`pip` command returned a non-zero exit code.
        """
        cmd = subprocess.list2cmdline([sys.executable, '-m', 'pip'] + args)
        ret = os.system(cmd)

        if ret != 0:
            raise RuntimeError('Failed to run `%s`' % cmd)


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


class InstallNodeDependenciesCommand(Command):
    """Install all node.js dependencies from npm.

    If ``--use-npm-cache`` is passed, this will use :command:`npm-cache`
    to install the packages, which is best for Continuous Integration setups.
    Otherwise, :command:`npm` is used.
    """

    description = \
        'Install the node packages required for building static media.'

    user_options = [
        ('use-npm-cache', None, "Use npm-cache to install packages"),
    ]

    boolean_options = ['use-npm-cache']

    def initialize_options(self):
        """Initialize options for the command."""
        self.use_npm_cache = None

    def finalize_options(self):
        """Finalize options for the command.

        This is required, but does not actually do anything.
        """
        pass

    def run(self):
        """Run the commands to install packages from npm.

        Raises:
            RuntimeError:
                There was an error finding or invoking the package manager.
        """
        if self.use_npm_cache:
            npm_command = 'npm-cache'
        else:
            npm_command = 'npm'

        try:
            subprocess.check_call([npm_command, '--version'])
        except subprocess.CalledProcessError:
            raise RuntimeError(
                'Unable to locate %s in the path, which is needed to '
                'install dependencies required to build this package.'
                % npm_command)

        # By this point, dependencies should be installed for us. We're also
        # using the same exact dependencies as Djblets, so no need to
        # duplicate that list.
        from djblets.dependencies import npm_dependencies

        with open('package.json', 'w') as fp:
            fp.write(json.dumps(
                {
                    'name': 'reviewboard',
                    'private': 'true',
                    'devDependencies': {},
                    'dependencies': npm_dependencies,
                },
                indent=2))

        print 'Installing node.js modules...'
        result = os.system('%s install' % npm_command)

        os.unlink('package.json')

        if result != 0:
            raise RuntimeError(
                'One or more node.js modules could not be installed.')


cmdclasses = {
    'develop': DevelopCommand,
    'egg_info': BuildEggInfo,
    'build_media': BuildMedia,
    'build_i18n': BuildI18n,
    'install_data': install_data,
    'install_node_deps': InstallNodeDependenciesCommand,
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
              'rbext = reviewboard.cmdline.rbext:main',
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
              'splat = reviewboard.hostingsvcs.splat:Splat',
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
      install_requires=build_dependency_list(package_dependencies),
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
