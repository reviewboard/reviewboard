"""Argument parsing utilities for command line tools."""

from __future__ import unicode_literals

import argparse
import os
import sys

import reviewboard
from reviewboard.cmdline.utils.console import get_console


class HelpFormatter(argparse.RawDescriptionHelpFormatter):
    """Formats help text by preserving paragraphs."""

    indent_len = 2

    def _fill_text(self, text, width, indent):
        """Return wrapped description text.

        This will wrap each contained paragraph (separated by a newline)
        individually.

        Args:
            text (unicode):
                The text to wrap.

            width (int, unused):
                The terminal width.

            indent (unicode, unused):
                The string to prefix each line with, for indentation.

        Returns:
            unicode:
            The wrapped text.
        """
        console = get_console()
        indent_len_str = ' ' * self.indent_len

        return '\n'.join(
            console.wrap_text(paragraph, indent=indent or indent_len_str)
            for paragraph in text.split('\n')
        )


class RBProgVersionAction(argparse.Action):
    """Display the Review Board/command version.

    This is used instead of :py:mod:`argparse`'s default version handling
    in order to print text unindented and unwrapped.
    """

    def __init__(self, **kwargs):
        """Initialize the action.

        Args:
            **kwargs (dict):
                Keyword arguments for the action.
        """
        super(RBProgVersionAction, self).__init__(nargs=0, **kwargs)

    def __call__(self, parser, *args, **kwargs):
        """Call the action.

        This will display the version information directly to the terminal
        and then exit.

        Args:
            parser (argparse.ArgumentParser):
                The argument parser that called this action.

            *args (tuple, unused):
                Unused positional arguments.

            **kwargs (dict, unused):
                Unused keyword arguments.
        """
        parser.exit(message=('\n'.join([
            'Review Board/%s %s' % (parser.prog,
                                    reviewboard.get_version_string()),
            'Python %s' % sys.version.splitlines()[0],
            'Installed to %s' % os.path.dirname(reviewboard.__file__),
            '',
        ])))
