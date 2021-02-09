"""Console UI toolkit for command line tools."""

from __future__ import print_function, unicode_literals

import getpass
import shutil
import sys
import textwrap

from django.utils import six
from django.utils.encoding import force_str
from django.utils.six.moves import input


class ConsoleUI(object):
    """A UI toolkit that outputs to the console.

    This is considered internal API for Review Board. Its API may change
    without notice.

    Version Added:
        4.0
    """

    def __init__(self, allow_color=True):
        """Initialize the UI toolkit.

        Args:
            allow_color (bool, optional):
                Whether to allow color output in the UI.
        """
        super(ConsoleUI, self).__init__()

        # Make color styling available, if Django determines the terminal
        # supports it.
        from django.utils import termcolors
        from django.core.management.color import color_style, no_style

        if allow_color:
            self.style = color_style()
            self.header_style = termcolors.make_style(fg='yellow',
                                                      bg='black',
                                                      opts=('bold',))
            self.header_sep_style = termcolors.make_style(fg='yellow',
                                                          bg='black')
            self.prompt_style = termcolors.make_style(opts=('bold',))
        else:
            self.style = no_style()

            def plain_style(text):
                return text

            self.header_style = plain_style
            self.header_sep_style = plain_style
            self.prompt_style = plain_style

        # Get the terminal width in order to best fit wrapped content.
        term_width = 70

        if hasattr(shutil, 'get_terminal_size'):
            try:
                term_width = shutil.get_terminal_size()[0]
            except OSError:
                pass

        header_padding = 2
        text_padding = 4

        self.term_width = term_width
        self.header_sep = '\u2014' * term_width

        header_indent_str = ' ' * header_padding
        self.header_wrapper = textwrap.TextWrapper(
            initial_indent=header_indent_str,
            subsequent_indent=header_indent_str,
            width=term_width - header_padding)

        text_indent_str = ' ' * text_padding
        self.text_wrapper = textwrap.TextWrapper(
            initial_indent=text_indent_str,
            subsequent_indent=text_indent_str,
            break_long_words=False,
            width=term_width - text_padding)

        self.error_wrapper = textwrap.TextWrapper(
            initial_indent=self.style.ERROR('[!] '),
            subsequent_indent='    ',
            break_long_words=False,
            width=term_width - text_padding)

    def page(self, text, allow_back=True, is_visible_func=None,
             on_show_func=None):
        """Add a new "page" to display to the user.

        In the console UI, we only care if we need to display or ask questions
        for this page. Our representation of a page in this case is simply a
        boolean value. When it's ``False``, nothing associated with this page
        will be displayed to the user.

        Args:
            text (unicode):
                Text to display on the page.

            allow_back (bool, optional):
                Whether the user can go back a page, if allowed by the UI
                toolkit.

            is_visible_func (callable, optional):
                A function that returns whether the page is visible. If it
                returns ``False``, the page will be skipped. For example:

                .. code-block:: python

                def _is_visible():
                    return False

            on_show_func (callable, optional):
                A function to call when this page is shown. For example:

                .. code-block:: python

                   def _on_show():
                       pass

        Returns:
            object:
            An object representing the page. This is considered opaque to the
            caller.
        """
        visible = not is_visible_func or is_visible_func()

        if not visible:
            return False

        if on_show_func:
            on_show_func()

        fmt_str = '%%-%ds' % self.term_width

        print()
        print()
        print(self.header_sep_style(self.header_sep))
        print(self.header_style(fmt_str % self.header_wrapper.fill(text)))
        print(self.header_sep_style(self.header_sep))

        return True

    def prompt_input(self, page, prompt, default=None, password=False,
                     yes_no=False, optional=False, normalize_func=None,
                     save_obj=None, save_var=None):
        """Prompt the user for input.

        Args:
            page (object):
                The handle representing the page, as returned by
                :py:meth:`page`.

            prompt (unicode):
                The prompt to display.

            default (unicode, optional):
                A default value.

            password (bool, optional):
                Whether this is a password input.

            yes_no (bool, optional):
                Whether this is prompting for a Yes/No.

            optional (bool, optional):
                Whether the prompt is optional and can be skipped.

            normalize_func (callable, optional):
                A function to call to normalize the inputted text. For
                example:

                .. code-block:: python

                   def _my_normalize_func(text):
                       return text.strip()

            save_obj (object, optional):
                An object the inputted/normalized value will be set on. If
                provided, ``save_var`` must also be provided.

            save_var (object, optional):
                The attribute on ``save_obj`` to save the inputted/normalized
                value on.

        Returns:
            object:
            The resulting inputted/normalized value.
        """
        assert save_obj
        assert save_var

        if not page:
            return

        if yes_no:
            if default is True:
                prompt = '%s [Y/n]' % prompt
            elif default is False:
                prompt = '%s [y/N]' % prompt
                default = False
            else:
                prompt = '%s [y/n]' % prompt
        elif default:
            self.text(page, "The default is %s" % default)
            prompt = "%s [%s]" % (prompt, default)
        elif optional:
            prompt = '%s (optional)' % prompt

        print()

        prompt = self.prompt_style('%s: ' % prompt)
        value = None

        while not value:
            if password:
                temp_value = getpass.getpass(force_str(prompt))
                if save_var.startswith('reenter'):
                    if not self._confirm_reentry(save_obj, save_var,
                                                 temp_value):
                        self.error("Passwords must match.")
                        continue
                value = temp_value
            else:
                value = input(prompt)

            if not value:
                if default:
                    value = default
                elif optional:
                    break

            if yes_no:
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
                self.error("You must answer this question.")

        if normalize_func:
            value = normalize_func(value)

        if save_obj is not None and save_var is not None:
            setattr(save_obj, save_var, value)

        return value

    def prompt_choice(self, page, prompt, choices, save_obj=None,
                      save_var=None):
        """Prompt the user for a choice from a list.

        Args:
            page (object):
                The handle representing the page, as returned by
                :py:meth:`page`.

            prompt (unicode):
                The prompt to display.

            choices (list of unicode):
                The list of choices to present.

            save_obj (object, optional):
                An object the choice will be set on. If provided, ``save_var``
                must also be provided.

            save_var (object, optional):
                The attribute on ``save_obj`` to save the choice on.

        Returns:
            object:
            The resulting choice.
        """
        assert save_obj
        assert save_var

        if not page:
            return

        self.text(page, "You can type either the name or the number "
                        "from the list below.")

        prompt_style = self.prompt_style
        valid_choices = []
        i = 0

        for choice in choices:
            description = ''
            enabled = True

            if isinstance(choice, six.string_types):
                text = choice
            elif len(choice) == 2:
                text, enabled = choice
            else:
                text, description, enabled = choice

            if enabled:
                self.text(page,
                          '%s %s %s\n' % (prompt_style('(%d)' % (i + 1)),
                                          text, description),
                          leading_newline=(i == 0))
                valid_choices.append(text)
                i += 1

        print()

        prompt = self.prompt_style('%s: ' % prompt)
        choice = None

        while not choice:
            choice = input(prompt)

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

        if save_obj is not None and save_var is not None:
            setattr(save_obj, save_var, choice)

        return choice

    def wrap_text(self, text, indent=None):
        """Return a paragraph of text wrapped to the terminal width.

        Args:
            text (unicode):
                The text to wrap.

            indent (unicode, optional):
                A custom indentation string.

        Returns:
            unicode:
            The wrapped text.
        """
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

    def text(self, page, text, leading_newline=True, wrap=True):
        """Display a block of text to the user.

        Args:
            page (object):
                The handle representing the page, as returned by
                :py:meth:`page`.

            text (unicode):
                The text to display.
        """
        if not page:
            return

        if leading_newline:
            print()

        if wrap:
            print(self.wrap_text(text))
        else:
            print('    %s' % text)

    def disclaimer(self, page, text):
        """Display a block of disclaimer text to the user.

        This must be implemented by subclasses.

        Args:
            page (object):
                The handle representing the page, as returned by
                :py:meth:`page`.

            text (unicode):
                The text to display.
        """
        self.text(page, '%s: %s' % (self.style.WARNING('NOTE'), text))

    def error(self, text, force_wait=False, done_func=None):
        """Display an error message to the user.

        Args:
            text (unicode):
                The error text to show.

            force_wait (bool, optional):
                Whether the user is forced to acknowledge the error to
                continue.

            done_func (callable, optional):
                A function to call once the error has been shown/acknowledged.
                This takes no arguments.
        """
        print()

        for text_block in text.split('\n'):
            print(self.error_wrapper.fill(text_block))

        if force_wait:
            print()
            input('Press Enter to continue')

        if done_func:
            done_func()

    def urllink(self, page, url):
        """Display a URL to the user.

        Args:
            page (object):
                The handle representing the page, as returned by
                :py:meth:`page`.

            url (unicode):
                The URL to display.
        """
        self.text(page, url, wrap=False)

    def itemized_list(self, page, title, items):
        """Display an itemized list.

        Args:
            page (object):
                The handle representing the page, as returned by
                :py:meth:`page`.

            title (unicode):
                The title of the list.

            items (list of unicode):
                The list of items.
        """
        if title:
            self.text(page, "%s:" % title)

        for item in items:
            self.text(page, "    * %s" % item, False)

    def step(self, page, text, func, step_num=None, total_steps=None):
        """Add a step of a multi-step operation.

        This will indicate when it's starting and when it's complete.

        If both ``step_num`` and ``total_steps`` are provided, the step
        text will include a prefix showing what step it's on and how many
        there are total.

        Args:
            page (object):
                The page handle.

            text (unicode):
                The step text to display.

            func (callable):
                The function to call to execute the step.

            step_num (int, optional):
                The 1-based step number.

            total_steps (int, optional):
                The total number of steps.
        """
        if step_num is not None and total_steps is not None:
            text = '[%s/%s] %s' % (step_num, total_steps, text)

        sys.stdout.write('%s ... ' % text)
        func()
        print(self.style.SUCCESS('OK'))

    def _confirm_reentry(self, obj, reenter_var, value):
        """Return whether a re-entered piece of data matches.

        This is used to ensure that secrets and passwords are what the user
        intended to type.

        Args:
            obj (object):
                The object containing the value to confirm.

            reenter_var (unicode):
                The name of the attribute on ``obj`` containing the value.

            value (object):
                The value to match against.

        Returns:
            bool:
            ``True`` if the values match. ``False`` if they do not.
        """
        first_var = reenter_var.replace('reenter_', '')
        first_entry = getattr(obj, first_var)
        return first_entry == value
