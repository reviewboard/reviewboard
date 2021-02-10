"""Console functionality for command line tools."""

from __future__ import print_function, unicode_literals

import getpass
import shutil
import sys
import textwrap

from django.core.exceptions import ValidationError
from django.core.management.color import color_style, no_style
from django.utils import six, termcolors
from django.utils.six.moves import input


_console = None


class Console(object):
    """Utilities for displaying output to the console.

    This takes care of cleanly outputting various forms of content (text,
    notes, warnings, errors, itemized lists, and more) to the console.

    Callers should construct this by calling :py:func:`init_console`.

    Version Added:
        4.0
    """

    #: Standard text prompts.
    PROMPT_TYPE_TEXT = 'text'

    #: Password prompts.
    PROMPT_TYPE_PASSWORD = 'password'

    #: Yes/No prompts.
    PROMPT_TYPE_YES_NO = 'yes_no'

    def __init__(self, allow_color=False, stdout=sys.stdout,
                 stderr=sys.stderr, default_text_padding=0):
        """Initialize the console.

        Args:
            allow_color (bool, optional):
                Whether to use color in any console output. This applies to
                headers, notes, warnings, errors, and progress steps.

            stdout (io.IOBase):
                The stream to output standard text to.

            stderr (io.IOBase):
                The stream to output errors to.
        """
        self._allow_color = allow_color
        self.stdout = stdout
        self.stderr = stderr
        self.default_text_padding = default_text_padding

        # Get the terminal width in order to best fit wrapped content.
        term_width = 79

        if hasattr(shutil, 'get_terminal_size'):
            try:
                term_width = shutil.get_terminal_size()[0]
            except OSError:
                pass

        self.term_width = term_width
        self.header_sep = '\u2014' * self.term_width

        self._restyle_console()

    @property
    def allow_color(self):
        """Whether to use color for output.

        Type:
            bool
        """
        return self._allow_color

    @allow_color.setter
    def allow_color(self, allow_color):
        if self._allow_color is not allow_color:
            self._allow_color = allow_color
            self._restyle_console()

    def make_text_wrapper(self, prefix='', prefix_style=None, left_padding=0,
                          right_padding=None):
        """Return a new TextWrapper.

        The resulting :py:class:`textwrap.TextWrapper` will be tailored to the
        terminal width, and will make use of any provided prefix, style, and
        padding.

        Args:
            prefix (unicode, optional):
                A prefix for the first line in the wrapped content.

            prefix_style (callable, optional):
                The style function used to style the prefix.

            left_padding (int, optional):
                Padding to apply to the left of all lines.

            right_padding (int, optional):
                Padding to apply to the right of all lines. This defaults to
                the value of ``left_padding``.

        Returns:
            textwrap.TextWrapper:
            The resulting text wrapper.
        """
        left_indent_len = left_padding + len(prefix)

        if right_padding is None:
            right_padding = left_padding

        if prefix_style:
            prefix = prefix_style(prefix)

        return textwrap.TextWrapper(
            initial_indent='%s%s' % (' ' * left_padding, prefix),
            subsequent_indent=' ' * left_indent_len,
            break_long_words=False,
            width=self.term_width)

    def wrap_text(self, text, indent=None, wrapper=None):
        """Return a paragraph of text wrapped to the terminal width.

        Args:
            text (unicode):
                The text to wrap.

            indent (unicode, optional):
                A custom indentation string.

            wrapper (textwrap.TextWrapper, optional):
                A specific text wrapper to use. Defaults to the standard
                text wrapper for the console.

        Returns:
            unicode:
            The wrapped text.
        """
        if wrapper is None:
            wrapper = self.text_wrapper

        if indent is None:
            result = wrapper.fill(text)
        else:
            old_initial_indent = wrapper.initial_indent
            old_subsequent_indent = wrapper.subsequent_indent
            old_width = wrapper.width

            wrapper.initial_indent = indent
            wrapper.subsequent_indent = indent
            wrapper.width = self.term_width

            result = wrapper.fill(text)

            wrapper.initial_indent = old_initial_indent
            wrapper.subsequent_indent = old_subsequent_indent
            wrapper.width = old_width

        return result

    def print(self, text='', wrap=True, wrapper=None, style=None,
              trailing_newline=True):
        """Display a block of text to the user.

        Args:
            text (unicode):
                The text to display.

            wrap (bool, optional):
                Whether to wrap the text. Any newlines will result in new
                paragraphs.

            wrapper (textwrap.TextWrapper, optional):
                A specific text wrapper to use. Defaults to the standard
                text wrapper for the console.

            style (callable, optional):
                The style function used to style the text.

            trailing_newline (bool, optional):
                Whether to include a trailing newline at the end.
        """
        if style is None:
            style = self._plain_style

        if wrap:
            for i, paragraph in enumerate(text.strip().splitlines()):
                if i > 0:
                    self.stdout.write('\n\n')

                self.stdout.write(style(self.wrap_text(paragraph,
                                                       wrapper=wrapper)))
        else:
            for line in text.splitlines(True):
                self.stdout.write('%s%s' % (' ' * self.default_text_padding,
                                            style(line)))

        if trailing_newline:
            self.stdout.write('\n')

    def note(self, text, leading_newlines=True, trailing_newlines=True):
        """Display a block containing an important note.

        Args:
            text (unicode):
                The text to display.

            leading_newlines (bool, optional):
                Whether to show 2 newlines before the text.

            trailing_newlines (bool, optional):
                Whether to show 1 newline after the text.
        """
        if leading_newlines:
            self.print()

        self.print(text,
                   wrapper=self.note_wrapper)

        if trailing_newlines:
            self.print()

    def warning(self, text, leading_newlines=True, trailing_newlines=True):
        """Display a block containing a warning.

        Args:
            text (unicode):
                The text to display.

            leading_newlines (bool, optional):
                Whether to show 2 newlines before the text.

            trailing_newlines (bool, optional):
                Whether to show 1 newline after the text.
        """
        if leading_newlines:
            self.print()

        self.print(text,
                   wrapper=self.warning_wrapper)

        if trailing_newlines:
            self.print()

    def error(self, text, leading_newlines=True, trailing_newlines=True):
        """Display a block containing a warning.

        Args:
            text (unicode):
                The text to display.

            leading_newlines (bool, optional):
                Whether to show 2 newlines before the text.

            trailing_newlines (bool, optional):
                Whether to show 1 newline after the text.
        """
        if leading_newlines:
            self.print()

        self.print(text,
                   wrapper=self.error_wrapper)

        if trailing_newlines:
            self.print()

    def header(self, title, leading_newlines=True, trailing_newlines=True):
        """Display a header.

        Args:
            title (unicode):
                The header title.

            leading_newlines (bool, optional):
                Whether to show 2 newlines before the header.

            trailing_newlines (bool, optional):
                Whether to show 1 newline after the header.
        """
        if leading_newlines:
            self.print()
            self.print()

        self.print(self.header_sep,
                   style=self.header_sep_style,
                   wrapper=self.header_sep_wrapper)
        self.print(title,
                   style=self.header_sep_style,
                   wrapper=self.header_wrapper)
        self.print(self.header_sep,
                   style=self.header_sep_style,
                   wrapper=self.header_sep_wrapper)

        if trailing_newlines:
            self.print()

    def prompt_input(self, prompt, prompt_type=PROMPT_TYPE_TEXT,
                     default=None, optional=False, strip=True,
                     validate_func=None):
        """Prompt the user for input.

        Args:
            prompt (unicode):
                The text prompting for input.

            prompt_type (unicode, optional):
                The type of input to prompt for. This is one of:

                * :py:attr:`PROMPT_TYPE_TEXT`
                * :py:attr:`PROMPT_TYPE_PASSWORD`
                * :py:attr:`PROMPT_TYPE_YES_NO`

            default (bool or unicode, optional):
                The default value to show and use, if an explicit value isn't
                provided by the user.

                For yes/no prompts, this should be a boolean. For all else,
                a string.

            optional (bool, optional):
                Whether the prompt is optional and can be skipped by omitting
                a value.

            strip (bool, optional):
                Whether to strip the provided input.

            validate_func (callable, optional):
                An optional function for determining if input is valid. This
                takes the input as a parameter and raises a
                :py:class:`django.core.exceptions.ValidationError` if invalid.

                .. code-block:: python

                   def _is_valid(value):
                       if value != 'abc':
                           raise ValidationError('bad!')

        Returns:
            unicode:
            The resulting inputted value.
        """
        if prompt_type == self.PROMPT_TYPE_YES_NO:
            if default is True:
                prompt = '%s [Y/n]' % prompt
            elif default is False:
                prompt = '%s [y/N]' % prompt
                default = False
            else:
                prompt = '%s [y/n]' % prompt
        elif default:
            self.print()
            self.print('The default is "%s"' % default)
            prompt = '%s [%s]' % (prompt, default)
        elif optional:
            prompt = '%s (optional)' % prompt

        self.print()

        prompt = self.prompt_style('%s: ' % prompt)
        value = None

        while not value:
            self.print(prompt, trailing_newline=False)
            self.stdout.flush()

            if prompt_type == self.PROMPT_TYPE_PASSWORD:
                value = getpass.getpass(str(''),
                                        stream=self.stdout)
            else:
                value = input()

            if strip:
                value = value.strip()

            if not value:
                if default:
                    value = default
                elif optional:
                    break

            if validate_func is not None:
                try:
                    validate_func(value)
                except ValidationError as e:
                    for error in e.messages:
                        self.error(error)

                    value = None
                    continue

            if prompt_type == self.PROMPT_TYPE_YES_NO:
                if isinstance(value, bool):
                    # This came from the 'default' value.
                    norm_value = value
                else:
                    assert isinstance(value, six.string_types)
                    norm_value = value.lower()

                if norm_value not in (True, False, 'y', 'n', 'yes', 'no'):
                    self.error('Must specify one of Y/y/yes or N/n/no.')
                    value = None
                    continue
                else:
                    value = norm_value in (True, 'y', 'yes')
                    break
            elif not value:
                self.error('An answer is required.')

        return value

    def prompt_choice(self, prompt, choices):
        """Prompt the user for a choice from a list.

        Args:
            prompt (unicode):
                The text prompting for a choice.

            choices (list of dict):
                The list of choices to present. Each entry is a dictionary
                with the following keys:

                ``text`` (:py:class:`unicode`):
                    The text for the choice.

                ``description`` (:py:class:`unicode`, optional):
                    A description of the choice.

                ``enabled`` (:py:class:`bool`, optional):
                    Whether the option is enabled/visible.

        Returns:
            object:
            The resulting choice.
        """
        self.print()
        self.print('You can type either the name or the number from the '
                   'list below.')
        self.print()

        prompt_style = self.prompt_style
        valid_choices = []
        i = 0

        for choice in choices:
            if choice.get('enabled', True):
                text = choice['text']

                self.print(
                    '%s %s %s\n'
                    % (prompt_style('(%d)' % (i + 1)),
                       text,
                       choice.get('description', '')))
                valid_choices.append(text)
                i += 1

        self.print()

        prompt = self.prompt_style('%s: ' % prompt)
        choice = None

        while not choice:
            self.print(prompt, trailing_newline=False)
            choice = input()

            if choice not in valid_choices:
                try:
                    i = int(choice) - 1

                    if 0 <= i < len(valid_choices):
                        choice = valid_choices[i]
                        break
                except ValueError:
                    pass

                self.error("'%s' is not a valid option." % choice)
                choice = None

        return choice

    def itemized_list(self, items, title=''):
        """Display a list of items.

        Args:
            items (list of unicode):
                The list of items to show.

            title (unicode, optional):
                An optional title to show above the list.
        """
        self.print()

        if title:
            self.print('%s:' % title)
            self.print()

        wrapper = self.item_wrapper

        for item in items:
            self.print(item, wrapper=wrapper)

    def progress_step(self, text, func, step_num=None, total_steps=None):
        """Display one step of a multi-step operation.

        This will indicate when it's starting and when it's complete.

        If both ``step_num`` and ``total_steps`` are provided, the step
        text will include a prefix showing what step it's on and how many
        there are total.

        Args:
            text (unicode):
                The step text to display.

            func (callable):
                The function to call to execute the step.

            step_num (int, optional):
                The 1-based step number.

            total_steps (int, optional):
                The total number of steps.
        """
        assert callable(func)

        if step_num is not None and total_steps is not None:
            text = '[%s/%s] %s' % (step_num, total_steps, text)

        self.print('%s ... ' % text,
                   trailing_newline=False,
                   wrap=False)

        try:
            func()
            self.stdout.write(self.style.SUCCESS('OK'))
        except Exception as e:
            self.stdout.write('%s %s' % (self.style.ERROR('ERROR:'), e))

        self.stdout.write('\n')

    def _plain_style(self, text):
        """Return text as-is, without any styling.

        Args:
            text (unicode):
                The text to "style".

        Returns:
            unicode:
            The provided text.
        """
        return text

    def _restyle_console(self):
        """Restyle console output.

        This will create/re-create the output styles, based on the terminal
        size and whether color is allowed.
        """
        # Recompute the styles, based on whether color is allowed.
        if self.allow_color:
            self.style = color_style()

            self.header_style = termcolors.make_style(fg='yellow',
                                                      bg='black',
                                                      opts=('bold',))
            self.header_sep_style = termcolors.make_style(fg='yellow',
                                                          bg='black')
            self.prompt_style = termcolors.make_style(opts=('bold',))
        else:
            self.style = no_style()

            plain_style = self._plain_style
            self.header_style = plain_style
            self.header_sep_style = plain_style
            self.prompt_style = plain_style

        # Rebuild the text wrappers.
        text_padding = self.default_text_padding

        self.header_wrapper = self.make_text_wrapper(
            left_padding=1,
            right_padding=1)
        self.header_sep_wrapper = self.make_text_wrapper()
        self.text_wrapper = self.make_text_wrapper(
            left_padding=text_padding,
            right_padding=text_padding)
        self.note_wrapper = self.make_text_wrapper(
            prefix='Note: ',
            prefix_style=self.style.WARNING,
            left_padding=text_padding,
            right_padding=text_padding)
        self.warning_wrapper = self.make_text_wrapper(
            prefix='Warning: ',
            prefix_style=self.style.WARNING,
            left_padding=text_padding,
            right_padding=text_padding)
        self.error_wrapper = self.make_text_wrapper(
            prefix='[!] ',
            prefix_style=self.style.ERROR,
            left_padding=text_padding,
            right_padding=text_padding)
        self.item_wrapper = self.make_text_wrapper(
            prefix='* ',
            left_padding=text_padding,
            right_padding=text_padding)


def init_console(*args, **kwargs):
    """Initialize the console.

    This can only be called once.

    Args:
        **kwargs (dict):
            Keyword arguments to pass to :py:class:`Console`.

    Returns:
        Console:
        The resulting console instance.
    """
    global _console
    assert _console is None, 'init_console() was already called.'

    _console = Console(*args, **kwargs)

    return _console


def uninit_console():
    """Uninitialize the console."""
    global _console
    assert _console is not None, 'init_console() was never called.'

    _console = None


def get_console():
    """Return the console instance.

    Returns:
        Console:
        The initialized console, or ``None`` if not yet initialized.
    """
    return _console
