"""Command line tool for helping develop extensions.

This tool, :command:`rbext`, currently provides the ability to easily run
extension-provided unit tests. In the future, it'll also help with other
development tasks, and with updating the Package Store with the latest versions
of an extension.
"""

from __future__ import annotations

import argparse
import logging
import os
import re
import sys
from importlib import import_module
from textwrap import dedent
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Sequence
    from typing import NoReturn


logger = logging.getLogger(__name__)


os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'reviewboard.settings')

rbext_dir = os.path.abspath(os.path.dirname(__file__))
sys.path.insert(0, os.path.join(rbext_dir, 'conf', 'rbext'))

from django.utils.encoding import force_str
from importlib_metadata import Prepared

from reviewboard import (
    __version__ as reviewboard_version,
    get_manual_url,
)
from reviewboard.cmdline.utils.argparsing import (HelpFormatter,
                                                  RBProgVersionAction)
from reviewboard.cmdline.utils.console import init_console


# NOTE: We want to include Django-based modules as late as possible, in order
#       to allow extension-provided settings to apply.


MANUAL_URL = get_manual_url()
EXTENSION_MANUAL_URL = f'{MANUAL_URL}extending/'

console = None


class BaseCommand:
    """Base class for a command."""

    #: The name of a command.
    #:
    #: This is what the user will type on the command line after ``rbext``.
    name = None

    #: The summary of the command.
    #:
    #: This will be shown in the help output.
    help_summary = 'Run unit tests for an extension.'

    #: A description of the command, when displaying the command's own help.
    description_text = None

    def add_options(
        self,
        parser: argparse.ArgumentParser,
    ) -> None:
        """Add any command-specific options to the parser.

        Args:
            parser (argparse.ArgumentParser):
                The argument parser.
        """
        pass

    def run(
        self,
        options: argparse.Namespace,
    ) -> int:
        """Run the command.

        This will perform common setup work and then hand things off to
        :py:meth:`main`.

        Args:
            options (argparse.Namespace):
                Options set from the arguments.

        Returns:
            int:
            The return code for the process.
        """
        if options.settings_file:
            sys.path.insert(
                0,
                os.path.abspath(os.path.dirname(options.settings_file)))

        return self.main(options)

    def main(
        self,
        options: argparse.Namespace,
    ) -> int:
        """Perform the main operations for the command.

        Args:
            options (argparse.Namespace):
                Options set from the arguments.

        Returns:
            int:
            The command's exit code.
        """
        raise NotImplementedError

    def error(
        self,
        msg: str,
    ) -> NoReturn:
        """Display a fatal error to the user and exit.

        Args:
            msg (str):
                The message to display.

        Raises:
            django.core.management.CommandError:
            The resulting error.
        """
        from django.core.management import CommandError

        raise CommandError(msg)


class TestCommand(BaseCommand):
    """A command that runs an extension's test suite."""

    name = 'test'
    help_summary = 'Run unit tests for an extension.'
    description_text = (
        'Runs the unit tests for your extension, looking for any tests.py '
        'or tests/*.py files.\n'
        '\n'
        'For simple extensions, you can just provide -m <modulename>.\n'
        '\n'
        'For more advanced extensions with many apps, you may need to '
        'define a custom settings_local.py file in your tree based on your '
        'Review Board development environment, RB_EXTRA_APPS to a list of '
        'Django app names required by the extension.\n'
        '\n'
        'This will wrap the "nose" test runner, which provides many '
        'additional options for running your tests. To see all available '
        'options, run:\n'
        '\n'
        '  nosetests --help\n'
        '\n'
        'To use any additional "nose" options, run this command with a '
        '"--" before the arguments and test names:\n'
        '\n'
        '  rbext test <options> -- <nose-options> <tests>'
    )

    def add_options(
        self,
        parser: argparse.ArgumentParser,
    ) -> None:
        """Add command line arguments for running tests.

        Args:
            parser (argparse.ArgumentParser):
                The argument parser.
        """
        parser.add_argument(
            '--pytest',
            action='store_true',
            default=False,
            dest='pytest',
            help='Use pytest runner instead of nose.')
        parser.add_argument(
            '--app',
            metavar='APP_LABEL',
            action='append',
            dest='app_names',
            help='A Django app label to add to the list of installed apps. '
                 'This is only required for tests that use apps not '
                 'enabled by extensions.')
        parser.add_argument(
            '-e',
            '--extension',
            metavar='EXTENSION_CLASS',
            dest='extension_class',
            help='The full module and class path to the extension to test.')
        parser.add_argument(
            '-m',
            '--module',
            action='append',
            metavar='MODULE_NAME',
            dest='module_names',
            help='The name(s) of the extension module(s) to test. For '
                 'example, if your tests are in "myextension.tests", you '
                 'might want to use "myextension". This may require '
                 'specifying multiple modules in the extension, and any '
                 'dependencies. You may want to use --extension instead.')
        parser.add_argument(
            '--pdb',
            action='append_const',
            dest='test_options',
            const='--pdb',
            help='Drop into a debugger on any failures or errors.')
        parser.add_argument(
            '--tree-root',
            metavar='PATH',
            default=os.getcwd(),
            help='The path to the root of the source tree.')
        parser.add_argument(
            '--with-coverage',
            action='append_const',
            dest='test_options',
            const='--with-coverage',
            help='Display a report on code covered or missed by tests.')
        parser.add_argument(
            '-x',
            '--stop',
            action='append_const',
            dest='test_options',
            const='-x',
            help='Stop running tests after the first failure.')
        parser.add_argument(
            'tests',
            metavar='TEST',
            nargs='*',
            help='Specific tests to run. This can be in the form of '
                 'mypackage.mymodule, mypackage.mymodule:TestsClass, or '
                 'mypackage.mymodule:TestsClass.test_method.')

    def main(
        self,
        options: argparse.Namespace,
    ) -> int:
        """Main function for running unit tests for the extension.

        Args:
            options (argparse.Namespace):
                Options set from the arguments.

        Returns:
            int:
            The command's exit code.
        """
        module_names = options.module_names or []

        os.environ['RB_TEST_MODULES'] = force_str(','.join(module_names))

        os.chdir(options.tree_root)
        os.environ['RB_RUNNING_TESTS'] = '1'

        from django import setup
        from django.apps import apps
        from django.conf import settings

        if not apps.ready:
            setup()

        installed_apps = list(settings.INSTALLED_APPS)

        # If an explicit extension is specified, then we'll want to grab its
        # list of apps.
        extension_class_name = options.extension_class

        assert console is not None

        if extension_class_name:
            module_name, class_name = extension_class_name.rsplit('.', 1)

            try:
                extension_class = getattr(import_module(module_name),
                                          class_name)
            except AttributeError:
                console.error(
                    f'The provided extension class "{class_name}" could not '
                    f'be found in {module_name}'
                )

                return 1
            except ImportError:
                console.error(
                    f'The provided extension class module "{module_name}" '
                    f'could not be found'
                )

                return 1

            installed_apps += (extension_class.apps or
                               [module_name.rsplit('.', 1)[0]])

        if options.app_names:
            installed_apps += options.app_names

        if installed_apps != list(settings.INSTALLED_APPS):
            settings.INSTALLED_APPS = installed_apps
            apps.set_installed_apps(installed_apps)

        from reviewboard.test import RBTestRunner

        use_pytest = options.pytest or os.path.exists('conftest.py')

        if not use_pytest:
            console.note(
                'Tests are running using the legacy nose test runner. Review '
                'Board 7 will switch to a pytest-based runner. To opt in to '
                'the new behavior, run with --pytest or create a conftest.py '
                'file.')

        test_runner = RBTestRunner(
            test_packages=module_names,
            cover_packages=module_names,
            verbosity=1,
            needs_collect_static=False,
            use_pytest=use_pytest)

        # Don't use +=, as we don't want to modify the list on the class.
        # We want to create a new one on the instance.
        test_runner.nose_options += (options.test_options or [])

        failures = test_runner.run_tests(options.tests)

        if failures:
            return 1
        else:
            return 0


class CreateCommand(BaseCommand):
    """A command for creating a new extension package."""

    name = 'create'
    help_summary = 'Create a new extension source tree.'
    description_text = (
        f'This takes care of creating a boilerplate extension and source '
        f'tree, giving you a starting point for developing a new extension.\n'
        f'\n'
        f'See the documentation for creating extensions:\n'
        f'\n'
        f'{EXTENSION_MANUAL_URL}'
    )

    def add_options(
        self,
        parser: argparse.ArgumentParser,
    ) -> None:
        """Add command line arguments for creating an extension.

        Args:
            parser (argparse.ArgumentParser):
                The argument parser.
        """
        parser.add_argument(
            '--name',
            required=True,
            help='The human-readable name for the extension. This is '
                 'required.')
        parser.add_argument(
            '--class-name',
            default=None,
            help='The class name for the extension (generally in CamelCase '
                 'form, without spaces). If not provided, this will be '
                 'based on the extension name.')
        parser.add_argument(
            '--package-name',
            default=None,
            help='The name of the package (using alphanumeric  ). '
                 'If not provided, this will be based on the extension '
                 'name.')
        parser.add_argument(
            '--package-version',
            default='1.0',
            help='The version for your extension and package.')
        parser.add_argument(
            '--summary',
            default=None,
            help='A one-line summary of the extension.')
        parser.add_argument(
            '--description',
            default=None,
            help='A short description of the extension.')
        parser.add_argument(
            '--author-name',
            default=None,
            help='The name of the author for the package and extension '
                 'metadata. This can be a company name.')
        parser.add_argument(
            '--author-email',
            default=None,
            help='The e-mail address of the author for the package and '
                 'extension metadata.')
        parser.add_argument(
            '--enable-configuration',
            action='store_true',
            default=False,
            help='Whether to enable a Configure button and view for the '
                 'extension.')
        parser.add_argument(
            '--enable-static-media',
            action='store_true',
            default=False,
            help='Whether to enable static media files for the package.')

    def main(
        self,
        options: argparse.Namespace,
    ) -> int:
        """Main function for creating an extension.

        Args:
            options (argparse.Namespace):
                Options set from the arguments.

        Returns:
            int:
            The command's exit code.
        """
        self._process_options(options)

        name = options.name
        package_name = options.package_name
        summary = options.summary
        description = options.description
        class_name = options.class_name
        configurable = options.enable_configuration
        enable_static_media = options.enable_static_media

        # Create the directory hierarchy.
        root_dir = package_name

        if os.path.exists(root_dir):
            self.error(
                f'There\'s already a directory named "{root_dir}". You must '
                f'remove it before you can create a new extension there.'
            )

        ext_dir = os.path.join(root_dir, package_name)
        static_dir = os.path.join(ext_dir, 'static')
        templates_dir = os.path.join(ext_dir, 'templates')

        for path in (root_dir, ext_dir):
            os.mkdir(path, 0o755)

        if enable_static_media:
            os.mkdir(static_dir, 0o755)

            for path in ('css', 'js', 'images'):
                os.mkdir(os.path.join(static_dir, path))

        # Create the packaging files.
        self._write_file(
            os.path.join(root_dir, 'README.md'),
            self._create_readme(name=name,
                                summary=summary,
                                description=description))

        self._write_file(
            os.path.join(root_dir, 'MANIFEST.in'),
            self._create_manifest(static_dir=static_dir,
                                  templates_dir=templates_dir))

        self._write_file(
            os.path.join(root_dir, 'pyproject.toml'),
            self._create_pyproject_toml(author=options.author_name,
                                        author_email=options.author_email,
                                        class_name=class_name,
                                        package_name=package_name,
                                        summary=summary,
                                        version=options.package_version))

        self._write_file(
            os.path.join(root_dir, 'conftest.py'),
            self._create_conftest_py())

        # Create the extension source files.
        self._write_file(os.path.join(ext_dir, '__init__.py'), '')

        self._write_file(
            os.path.join(ext_dir, 'extension.py'),
            self._create_extension_py(
                name=name,
                package_name=package_name,
                class_name=class_name,
                summary=summary,
                configurable=configurable,
                has_static_media=enable_static_media))

        if configurable:
            form_class_name = f'{class_name}Form'

            self._write_file(
                os.path.join(ext_dir, 'admin_urls.py'),
                self._create_admin_urls_py(
                    package_name=package_name,
                    class_name=class_name,
                    form_class_name=form_class_name))

            self._write_file(
                os.path.join(ext_dir, 'forms.py'),
                self._create_forms_py(form_class_name=form_class_name))

        # We're done!
        assert console is not None
        console.print(
            f'Generated a new extension in {os.path.abspath(root_dir)}')
        console.print()
        console.print('For information on writing your extension, see')
        console.print(EXTENSION_MANUAL_URL)

        return 0

    def _process_options(
        self,
        options: argparse.Namespace,
    ) -> None:
        """Process and normalize any provided options.

        This will attempt to provide suitable defaults for missing parameters,
        and to check that others are valid.

        Args:
            options (argparse.Namespace):
                Options set from the arguments.
        """
        name = options.name.strip()
        package_name = options.package_name
        class_name = options.class_name

        assert console is not None

        if not package_name:
            package_name = self._normalize_package_name(name)
            console.print(f'Using "{package_name}" as the package name.')
        else:
            package_name = package_name.strip()

            if not re.match(r'[A-Za-z][A-Za-z0-9._-]*', package_name):
                normalized = self._normalize_package_name(package_name)
                self.error(
                    f'"{package_name}" is not a valid package name. Try '
                    f'--package-name="{normalized}"'
                )

        if not class_name:
            class_name = self._normalize_class_name(name)
            console.print(f'Using "{class_name}" as the extension class name.')
        else:
            class_name = class_name.strip()

            if not re.match(r'[A-Za-z][A-Za-z0-9_]+Extension$', class_name):
                normalized = self._normalize_class_name(class_name)
                self.error(
                    f'"{class_name}" is not a valid class name. Try '
                    f'--class-name="{normalized}"'
                )

        options.name = name
        options.package_name = package_name
        options.class_name = class_name

    def _normalize_package_name(
        self,
        name: str,
    ) -> str:
        """Normalize a package name.

        This will ensure the package name is in a suitable format, replacing
        any invalid characters or dashes with ``_``, and converting it to
        lowercase.

        Args:
            name (str):
                The name of the package to normalize.

        Returns:
            str:
            The normalized name.
        """
        return Prepared.normalize(name)

    def _normalize_class_name(
        self,
        name: str,
    ) -> str:
        """Normalize a class name.

        This will ensure the class name is in a suitable format, converting it
        to CamelCase and adding an "Extension" at the end if needed.

        Args:
            name (str):
                The name of the class to normalize.

        Returns:
            str:
            The normalized class name.
        """
        class_name = ''.join(
            word.capitalize()
            for word in re.sub(r'[^A-Za-z0-9]+', ' ', name).split()
        )

        if not class_name.endswith('Extension'):
            class_name += 'Extension'

        return class_name

    def _write_file(
        self,
        filename: str,
        content: str,
        mode: (int | None) = None,
    ) -> None:
        """Write content to a file.

        This will create the file and write the provided content. The content
        will be stripped and dedented, with a trailing newline added, allowing
        the generation code to make use of multi-line strings.

        Args:
            filename (str):
                The path of the file to write.

            content (str):
                The content to write.

            mode (int):
                The optional permissions mode to set for the file.
        """
        with open(filename, 'w', encoding='utf-8') as fp:
            fp.write(dedent(content).strip())
            fp.write('\n')

        if mode is not None:
            os.chmod(filename, mode)

    def _create_readme(
        self,
        name: str,
        summary: str,
        description: str,
    ) -> str:
        """Create the content for a README.rst file.

        Args:
            name (str):
                The extension's name.

            summary (str):
                The extension's summary.

            description (str):
                A description of the extension.

        Returns:
            str:
            The resulting content for the file.
        """
        header_bar = '=' * len(name)
        content = '\n\n'.join(
            content
            for content in (summary, description)
            if content
        ) or 'Describe your extension.'

        return f"""
            {name}
            {header_bar}

            {content}
        """

    def _create_manifest(
        self,
        templates_dir: str,
        static_dir: str,
    ) -> str:
        """Create the content for a MANIFEST.in file.

        Args:
            templates_dir (str):
                The relative path to the templates directory.

            static_dir (str):
                The relative path to the static media directory.

        Returns:
            str:
            The resulting content for the file.
        """
        return f"""
            graft {templates_dir}
            graft {static_dir}

            include COPYING
            include INSTALL
            include README.md
            include *-requirements.txt

            global-exclude .*.sw[op] *.py[co] __pycache__ .DS_Store .noseids
        """

    def _create_pyproject_toml(
        self,
        *,
        author: str,
        author_email: str,
        class_name: str,
        package_name: str,
        summary: str,
        version: str,
    ) -> str:
        """Create the content for a pyproject.toml file.

        Version Changed:
            7.1:
            Added ``author``, ``author_email``, ``class_name``, ``summary``,
            and ``version`` arguments.

        Args:
            author (str):
                The name of the author of the extension.

                Version Added:
                    7.1

            author_email (str):
                The e-mail address of the author of the extension.

                Version Added:
                    7.1

            class_name (str):
                The name of the extension class.

                Version Added:
                    7.1

            package_name (str):
                The name of the package.

            summary (str):
                A summary of the package.

                Version Added:
                    7.1

            version (str):
                The version of the package.

                Version Added:
                    7.1

        Returns:
            str:
            The resulting content for the file.
        """
        if not author:
            author = '<REPLACE ME>'

        if not author_email:
            author_email = '<REPLACE ME>'

        if not summary:
            summary = '<REPLACE ME>'

        return f"""
            [build-system]
            requires = [
                # Update this for the target version of Review Board.
                'reviewboard~={reviewboard_version}',

                'reviewboard[extension-packaging]',
            ]
            build-backend = 'reviewboard.extensions.packaging.backend'


            [project]
            name = '{package_name}'
            version = '{version}'
            description = '{summary}'
            authors = [
                {{name = '{author}', email = '{author_email}'}}
            ]

            dependencies = [
                # Your package dependencies go here.
                # Don't include "ReviewBoard" in this list.
            ]

            classifiers = [
                # For a full list of package classifiers, see
                # https://pypi.python.org/pypi?%3Aaction=list_classifiers

                'Development Status :: 3 - Alpha',
                'Environment :: Web Framework',
                'Framework :: Review Board',
                'Operating System :: OS Independent',
                'Programming Language :: Python',
            ]


            [project.entry-points."reviewboard.extensions"]
            {package_name} = '{package_name}.extension:{class_name}'


            [tool.setuptools.packages.find]
            where = ['.']
            namespaces = false


            [tool.pytest.ini_options]
            DJANGO_SETTINGS_MODULE = "reviewboard.settings"
            django_debug_mode = false

            python_files = ["tests.py", "test_*.py"]
            python_classes = ["*Tests"]
            python_functions = ["test_*"]
            pythonpath = "."
            testpaths = ["{package_name}"]

            env = [
                "RB_RUNNING_TESTS=1",
                "RBSSH_STORAGE_BACKEND=reviewboard.ssh.storage.FileSSHStorage",
            ]

            addopts = ["--reuse-db"]

            required_plugins = [
                "pytest-django",
                "pytest-env",
            ]
        """

    def _create_conftest_py(self) -> str:
        """Return the content for a conftest.py file.

        Returns:
            str:
            The resulting content for the file.
        """
        return """
            pytest_plugins = ['reviewboard.testing.pytest_fixtures']
        """

    def _create_extension_py(
        self,
        name: str,
        package_name: str,
        class_name: str,
        summary: str,
        configurable: bool,
        has_static_media: bool,
    ) -> str:
        """Create the content for an extension.py file.

        Args:
            name (str):
                The name of the extension.

            package_name (str):
                The name of the package.

            class_name (str):
                The name of the extension class.

            summary (str):
                A summary of the extension.

            configurable (bool):
                Whether the package is set to be configurable.

            has_static_media (bool):
                Whether the package is set to have static media files.

        Returns:
            str:
            The resulting content for the file.
        """
        extension_docs_url = f'{EXTENSION_MANUAL_URL}extensions/'

        static_docs_url = f'{extension_docs_url}static-files/'
        static_media_content = f"""
                # You can create a list of CSS bundles to compile and ship
                # with your extension. These can include both *.css and
                # *.less (http://lesscss.org/) files. See
                # {static_docs_url}
                css_bundles = {{
                    # 'my-bundle-name': {{
                    #     'source_filenames': [
                    #         'css/style.less',
                    #     ],
                    #     'apply_to': ['my-view-url-name'],
                    # }},
                }}

                # JavaScript bundles are also supported. These support
                # standard .js (plain JavaScript), .es6.js (transpiled ES6+
                # JavaScript), and .ts (TypeScript) files.
                js_bundles = {{
                    # 'my-bundle-name': {{
                    #     'source_filenames': [
                    #         'js/script.es6.js',
                    #         'js/another-script.js',
                    #     ],
                    # }},
                }}
        """

        configure_docs_url = f'{extension_docs_url}configuration/'
        configuration_content = f"""
                # Default values for any configuration settings for your
                # extension.
                default_settings = {{
                    # 'my_field_1': 'my default value',
                    # 'my_field_2': False,
                }}

                # Set is_configurable and define an admin_urls.py to add
                # a standard configuration page for your extension.
                # See {configure_docs_url}
                is_configurable = True
        """

        metadata_name = repr(name)
        metadata_summary = repr(summary or 'REPLACE ME')
        hooks_docs_url = f'{extension_docs_url}#python-extension-hooks'
        extra_class_content = ''.join(
            extra_content
            for extra_content, should_add in (
                (configuration_content, configurable),
                (static_media_content, has_static_media))
            if should_add
        )

        return f'''
            """{name} for Review Board."""

            from django.utils.translation import gettext_lazy as _
            from reviewboard.extensions.base import Extension


            class {class_name}(Extension):
                """Internal description for your extension here."""

                metadata = {{
                    'Name': _({metadata_name}),
                    'Summary': _({metadata_summary}),
                }}
            {extra_class_content}
                def initialize(self) -> None:
                    """Initialize the extension."""
                    # Set up any hooks your extension needs here. See
                    # {hooks_docs_url}
        '''

    def _create_admin_urls_py(
        self,
        package_name: str,
        class_name: str,
        form_class_name: str,
    ) -> str:
        """Create the content for an admin_urls.py file.

        Args:
            package_name (str):
                The name of the package.

            class_name (str):
                The name of the extension class.

            form_class_name (str):
                The name of the extension settings form class.

        Returns:
            str:
            The resulting content for the file.
        """
        return f'''
            """Administration and configuration URLs for the extension."""

            from django.urls import path
            from reviewboard.extensions.views import configure_extension

            from {package_name}.extension import {class_name}
            from {package_name}.forms import {form_class_name}


            urlpatterns = [
                path(
                    '',
                    configure_extension,
                    {{
                        'ext_class': {class_name},
                        'form_class': {form_class_name},
                    }}),
            ]
        '''

    def _create_forms_py(
        self,
        form_class_name: str,
    ) -> str:
        """Create the content for a forms.py file.

        Args:
            form_class_name (str):
                The name of the extension settings form class.

        Returns:
            str:
            The resulting content for the file.
        """
        return f'''
            """Configuration forms for the extension."""

            from django import forms
            from djblets.extensions.forms import SettingsForm


            class {form_class_name}(SettingsForm):
                """Settings form for the extension."""

                # Add your fields here:
                # my_field_1 = forms.CharField()
                # my_field_2 = forms.BooleanField()
        '''


class RBExt:
    """Command line tool for helping develop Review Board extensions.

    This tool provides subcommands useful for extension developers. It
    currently provides:

    * ``test``: Runs an extension's test suite.
    """

    COMMANDS = [
        CreateCommand(),
        TestCommand(),
    ]

    def run(
        self,
        argv: Sequence[str],
    ) -> int:
        """Run an rbext command with the provided arguments.

        During the duration of the run, :py:data:`sys.argv` will be set to
        the provided arguments.

        Args:
            argv (list of str):
                The command line arguments passed to the command. This should
                not include the executable name as the first element.

        Returns:
            int:
            The command's exit code.
        """
        global console

        console = init_console()

        command, options = self.parse_options(argv)

        # We call out to things like the test runner, which expect to operate
        # off of sys.argv. We want to simulate that now that we've parsed
        # options. We'll restore sys.argv after the command finishes.
        old_argv = sys.argv
        sys.argv = argv

        try:
            return command.run(options)
        except Exception as e:
            logger.exception('Unexpected exception when running command '
                             '"%s": %s',
                             command.name, e)
            return 1
        finally:
            sys.argv = old_argv

    def parse_options(
        self,
        argv: Sequence[str],
    ) -> tuple[BaseCommand, argparse.Namespace]:
        """Parse arguments for the command.

        Args:
            argv (list of str):
                The arguments provided on the command line.

        Returns:
            tuple:
            A 2-tuple of:

            Tuple:
                0 (BaseCommand):
                    The command to run.

                1 (argparse.Namespace):
                    The parsed arguments.
        """
        parser = argparse.ArgumentParser(
            prog='rbext',
            usage='%(prog)s <command>',
            formatter_class=HelpFormatter,
            description=(
                'rbext helps create initial source code trees for extensions '
                'and helps run extension test suites within a '
                'pre-established Review Board development environment.\n'
                '\n'
                'To get help on an individual command, run:\n'
                '\n'
                '  rbext <command> --help'
            ))
        parser.add_argument(
            '--version',
            action=RBProgVersionAction)

        subparsers = parser.add_subparsers(
            title='Commands',
            dest='command',
            description=(
                'To get additional help for these commands, run: '
                'rb-site <command> --help'
            ))

        commands = sorted(self.COMMANDS, key=lambda cmd: cmd.name)
        command_map = {}

        for command in commands:
            command_map[command.name] = command

            subparser = subparsers.add_parser(
                command.name,
                formatter_class=HelpFormatter,
                prog=f'{parser.prog} {command.name}',
                description=command.description_text,
                help=command.help_summary)

            subparser.add_argument(
                '-d',
                '--debug',
                action='store_true',
                dest='debug',
                default=False,
                help='Display debug output.')
            subparser.add_argument(
                '-s',
                '--settings-file',
                dest='settings_file',
                default=None,
                help='test_settings.py file to use for any custom settings.')

            command.add_options(subparser)

        # Prevent the '--' and anything after it from being parsed, so the
        # command can work with it.
        try:
            i = argv.index('--')
            argv = argv[:i]
        except ValueError:
            # The "--" isn't in the list anywhere.
            pass

        options = parser.parse_args(argv)

        if not options.command:
            parser.print_help()
            sys.exit(1)

        return command_map[options.command], options


def main() -> None:
    """Run rbext.

    This is used by the Python EntryPoint to run rbext. It will pass in any
    arguments found on the command line and exit with the correct error code.
    """
    sys.exit(RBExt().run(sys.argv[1:]))
