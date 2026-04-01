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
    '%z': r'\x00]',
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

                # Strip the outer [ ] if present.
                if mapped.startswith('[') and mapped.endswith(']'):
                    out += mapped[1:-1]
                else:
                    out += mapped
                i += 2
            elif token == 'b':
                logger.error('Balanced paren operator "%%b" is not supported '
                             'in "%s"',
                             full_pattern)

                return None
            elif token in SPECIAL_CHARS:
                out += '\\' + token
                i += 2
            else:
                # % was unnecessarily used to escape a non-special character.
                # Just output the character.
                out += token
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
            else:
                # % was unnecessarily used to escape a non-special character.
                # Just output the character.
                out += pattern[i + 1]
                i += 2

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

        # 3) Character class.
        elif c == '[':
            end = pattern.find(']', i + 1)
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

        # 4) Unsupported non-greedy.
        elif c == '-' and i > 0 and pattern[i - 1] in '*+?':
            logger.error('Lua non-greedy "*-" not supported in "%s"',
                         pattern)
            return None

        # 5) Pass-through anchors and quantifiers.
        elif c in '^$.*+?':
            if c == '.':
                # This is a wildcard dot that matches any character.
                has_dot = True

            out += c
            i += 1

        # 6) Handle escapes not previously handled above.
        elif c == '\\':
            out += '\\\\'
            i += 1

        # 7) Escape other regex specials.
        elif c in r'{}[]|':
            out += '\\' + c
            i += 1

        # 8) Literal.
        else:
            out += c
            i += 1

    # If the pattern contains a '.', add DOTALL flag to match Lua behavior
    # where '.' matches any character including newlines.
    if has_dot:
        out = f'(?s){out}'

    return out
