"""Utility for converting Lua patterns to Python regexes.

Version Added:
    9.0
"""

from __future__ import annotations

import logging


logger = logging.getLogger(__name__)


#: Translations for Lua character classes.
#:
#: Version Added:
#:     9.0
LUA_TO_PYTHON_CLASSES = {
    '%%': '%',
    '%A': '[^A-Za-z]',
    '%a': '[A-Za-z]',
    '%c': r'[\x00-\x1F\x7F]',
    '%C': r'[^\x00-\x1F\x7F]',
    '%d': r'\d',
    '%D': r'\D',
    '%L': '[^a-z]',
    '%l': '[a-z]',
    '%p': r'[!"#$%&\'()*+,\-./:;<=>?@[\\\]^_`{|}~]',
    '%P': r'[^!"#$%&\'()*+,\-./:;<=>?@[\\\]^_`{|}~]',
    '%s': r'\s',
    '%S': r'\S',
    '%U': '[^A-Z]',
    '%u': '[A-Z]',
    '%w': r'\w',
    '%W': r'\W',
    '%X': '[^A-Fa-f0-9]',
    '%x': '[A-Fa-f0-9]',
    '%Z': r'[^\x00]',
    '%z': r'\x00',
}


#: Special characters which need to be escaped.
#:
#: Version Added:
#:     9.0
SPECIAL_CHARS = '.^$*+?{}[]\\|()-'


def _translate_lua_char_class(
    contents: str,
    full_pattern: str,
) -> str | None:
    """Translate the inside of a Lua [...] class to Python

    This preserves only necessary escapes.

    Version Added:
        9.0

    Args:
        contents (str):
            The contents of the class.

        full_pattern (str):
            The full pattern being converted.

    Returns:
        str:
        The class to use in the Python regex.
    """
    out = ''
    i = 0

    while i < len(contents):
        if contents[i] == '%' and i + 1 < len(contents):
            token = contents[i:i + 2]

            if token in LUA_TO_PYTHON_CLASSES:
                mapped = LUA_TO_PYTHON_CLASSES[token]

                if mapped.startswith('[^'):
                    # A complement class cannot be merged into a positive
                    # class. Only allow it when it's the entire class.
                    if contents != token:
                        logger.error('Complement class "%s" cannot be '
                                     'combined with other items in a class '
                                     'in "%s"',
                                     token, full_pattern)

                        return None

                    out += mapped[1:-1]
                elif mapped.startswith('[') and mapped.endswith(']'):
                    # Strip the outer [ ].
                    out += mapped[1:-1]
                else:
                    out += mapped
                i += 2
            elif contents[i + 1] in SPECIAL_CHARS:
                out += '\\' + contents[i + 1]
                i += 2
            else:
                # % was unnecessarily used to escape a non-special character.
                # Just output the character.
                out += contents[i + 1]
                i += 2
        else:
            ch = contents[i]

            # Only escape \ and ] inside a class.
            if ch in r'\]':
                out += '\\' + ch
            else:
                out += ch

            i += 1

    return out


def lua_pattern_to_python(
    pattern: str,
) -> str | None:
    """Convert a Lua pattern to Python regex.

    Version Added:
        9.0

    Args:
        pattern (str):
            The pattern to convert.

    Returns:
        str:
        The converted regex.
    """
    i = 0
    out = ''
    has_dot = False

    # Whether the last emitted token is an item a quantifier can apply
    # to (a single character, escape, or class). Lua's "-" is only a
    # quantifier directly after such an item.
    last_was_item = False

    while i < len(pattern):
        c = pattern[i]

        # 1) Lua escapes (% prefix) and Python escapes (\ prefix).
        if c == '%' and i + 1 < len(pattern):
            token = pattern[i:i + 2]
            if token in LUA_TO_PYTHON_CLASSES:
                out += LUA_TO_PYTHON_CLASSES[token]
                i += 2
            elif pattern[i + 1] in SPECIAL_CHARS:
                out += '\\' + pattern[i + 1]
                i += 2
            elif pattern[i + 1] == 'b':
                logger.error('Balanced paren operator "%%b" is not supported '
                             'in "%s"',
                             pattern)

                return None
            elif pattern[i + 1] == 'f':
                logger.error('Frontier pattern "%%f" is not supported '
                             'in "%s"',
                             pattern)

                return None
            else:
                # % was unnecessarily used to escape a non-special character.
                # Just output the character.
                out += pattern[i + 1]
                i += 2

            last_was_item = True

        # 2) Handle backslash escapes (already escaped patterns).
        elif c == '\\' and i + 1 < len(pattern):
            next_char = pattern[i + 1]

            if next_char in SPECIAL_CHARS:
                # This is already a proper escape sequence, pass through.
                out += '\\' + next_char
                i += 2
            else:
                # Unknown escape, treat backslash as literal.
                out += '\\\\'
                i += 1

            last_was_item = True

        # 3) Character class.
        elif c == '[':
            # Find the closing ], following Lua's parsing rules: the
            # class holds at least one item (so a leading ], possibly
            # after ^, is part of the class), and %-escaped characters
            # are skipped.
            j = i + 1

            if j < len(pattern) and pattern[j] == '^':
                j += 1

            end = -1

            while j < len(pattern):
                if pattern[j] == '%':
                    j += 2
                else:
                    j += 1

                if j < len(pattern) and pattern[j] == ']':
                    end = j
                    break

            if end == -1:
                logger.error('Unterminated class in "%s"',
                             pattern)

                return None

            contents = pattern[i + 1:end]
            translated = _translate_lua_char_class(contents, pattern)

            if translated is None:
                return None

            out += f'[{translated}]'
            i = end + 1
            last_was_item = True

        # 4) Non-greedy quantifier (Lua "X-" is Python "X*?").
        elif c == '-' and last_was_item:
            out += '*?'
            i += 1
            last_was_item = False

        # 5) Pass-through anchors and quantifiers.
        elif c in '^$.*+?':
            if c == '.':
                # This is a wildcard dot that matches any character.
                has_dot = True

            out += c
            i += 1
            last_was_item = (c == '.')

        # 6) Handle escapes not previously handled above.
        elif c == '\\':
            out += '\\\\'
            i += 1
            last_was_item = True

        # 7) Escape other regex specials.
        elif c in r'{}[]|':
            out += '\\' + c
            i += 1
            last_was_item = True

        # 8) Literal.
        else:
            out += c
            i += 1

            # Lua's "(" and ")" delimit captures, which cannot be
            # quantified, and a lone "-" cannot be quantified either.
            last_was_item = c not in '()-'

    # If the pattern contains a '.', add DOTALL flag to match Lua behavior
    # where '.' matches any character including newlines.
    if has_dot:
        out = f'(?s){out}'

    return out
