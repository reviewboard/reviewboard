#!/usr/bin/env python3
"""Builder for the code safety confusables dataset module.

This will pull down the latest lists of Unicode categories and confusables
from unicode.org and generate a mapping of confusables that we want to scan
for when displaying diffs. The result will be a new
:file:`reviewboard/codesafety/_unicode_confusables.py` file.

Version Added:
    5.0
"""

import os
import re
import sys
from urllib.request import urlopen


CATEGORIES_URL = 'ftp://ftp.unicode.org/Public/UNIDATA/Scripts.txt'
CONFUSABLES_URL = \
    'ftp://ftp.unicode.org/Public/security/latest/confusables.txt'


scripts_dir = os.path.abspath(os.path.dirname(__file__))
dest_filename = os.path.abspath(os.path.join(
    scripts_dir, '..', '..', 'reviewboard', 'codesafety', '_confusables.py'))


categories_data = {}


def _make_codepoints_key_path(codepoint):
    """Return a key path used for a Unicode codepoint.

    Args:
        codepoint (int):
            The Unicode codepoint to generate the key for.

    Returns:
        tuple:
        The key path.
    """
    return (
        codepoint & ~0xFFFF,
        codepoint & ~0xFFF,
        codepoint & ~0xFF,
        codepoint & ~0xF,
    )


def get_alias(codepoint):
    """Return the category alias for a codepoint.

    Args:
        codepoint (int):
            The codepoint.

    Returns:
        unicode:
        The category alias. If one is not found, this will be ``None``.
    """
    key = _make_codepoints_key_path(codepoint)

    try:
        codepoint_ranges = \
            categories_data['codepoints'][key[0]][key[1]][key[2]][key[3]]
    except KeyError:
        return None

    for codepoint_range in codepoint_ranges:
        if codepoint_range[0] <= codepoint <= codepoint_range[1]:
            return categories_data['aliases'][codepoint_range[2]]

    return None


def _load_data(url, line_re):
    """Download and iterate through a Unicode dataset.

    Args:
        url (str):
            The URL to download.

        line_re (re.RegexObject):
            The regex used to match lines.

    Yields:
        dict:
        Matched groups for each valid match of the regex.
    """
    data = urlopen(url).read()
    lines = data.decode('utf-8-sig').split('\n')

    for line in lines:
        if not line or line.startswith('#'):
            continue

        m = line_re.match(line)
        assert m, repr(line)

        yield m.groupdict()


def build_categories():
    """Download and build data on Unicode categories.

    This will download the Unicode categories dataset and parse it. It will
    populate :py:data:`categories_data` with lists of categories and aliases,
    and a tree of codepoint ranges.
    """
    # Note that we're acting like we're going to grab all categories from
    # the dataset, though in practice we're going to limit it to COMMON and
    # LATIN entries.
    #
    # This is because right now, we only need it for Unicode confusable maps,
    # but as we implement more Unicode checks, we will likely need to fetch
    # and store more information. Given the complexity of this, it's better to
    # have a more future-proof, "correct" implementation up-front.
    LINE_RE = re.compile(
        r'^(?P<codepoint_from>[0-9A-F]+)'
        r'(?:\.\.(?P<codepoint_through>[0-9A-F]+))?'
        r'\s*; (?P<alias>\w+) # (?P<category>[\w]+)',
        re.UNICODE)

    aliases = []
    alias_id_map = {}

    categories = []
    category_id_map = {}

    codepoint_ranges = {}

    for info in _load_data(CATEGORIES_URL, LINE_RE):
        alias = info['alias'].upper()

        if alias not in ('COMMON', 'LATIN'):
            continue

        if alias not in alias_id_map:
            alias_id_map[alias] = len(aliases)
            aliases.append(alias)

        category = info['category']

        if category not in category_id_map:
            category_id_map[category] = len(categories)
            categories.append(category)

        codepoint_from_s = info['codepoint_from']
        codepoint_through_s = info['codepoint_through'] or codepoint_from_s

        codepoint_from = int(codepoint_from_s, 16)
        codepoint_through = int(codepoint_through_s, 16)

        # Split into subtables. Key off from some prefix.
        prev_key = None
        cur_range = None

        # We need a quick way to look up Unicode codepoints, but it's too
        # expensive to maintain a mapping of every codepoint. So, instead
        # we have a 5-level tree.
        #
        # The first 4 levels are increasingly specific masks of starting
        # codepoint ranges, with the 5th level being the codepoints in that
        # range.
        #
        # Codepoint ranges are split up as needed to fit in the correct range.
        #
        # As an example, if we were storing category range 1F400..1F6D7
        # (RAT..ELEVATOR):
        #
        #     10000: {
        #         1F000: {
        #             1F400: {
        #                 1F400: [1F400..1F409],
        #                 ...
        #                 1F490: [1F490..1F499],
        #             },
        #             ..
        #             1F600: {
        #                 1F600: [1F600..1F609],
        #                 ...
        #                 1F6D0: [1F6D0..1F6D7],
        #             }
        #         }
        #     }
        #
        # In practice, the leafs often have more than one range, particularly
        # for the lower codepoint ranges.
        #
        # This is easy to build and fast for lookup.
        for codepoint in range(codepoint_from, codepoint_through + 1):
            key = _make_codepoints_key_path(codepoint)

            if key != prev_key:
                if cur_range:
                    codepoints = (
                        codepoint_ranges
                        .setdefault(prev_key[0], {})
                        .setdefault(prev_key[1], {})
                        .setdefault(prev_key[2], {})
                        .setdefault(prev_key[3], [])
                    )
                    codepoints.append(cur_range)

                cur_range = (
                    codepoint,
                    codepoint,
                    alias_id_map[alias],
                    category_id_map[category],
                )
            else:
                cur_range = (
                    cur_range[0],
                    codepoint,
                    cur_range[2],
                    cur_range[3],
                )

            prev_key = key

        if prev_key:
            codepoints = (
                codepoint_ranges
                .setdefault(prev_key[0], {})
                .setdefault(prev_key[1], {})
                .setdefault(prev_key[2], {})
                .setdefault(prev_key[3], [])
            )
            codepoints.append(cur_range)

    categories_data.update({
        'aliases': aliases,
        'categories': categories,
        'codepoints': codepoint_ranges,
    })


def update_confusables():
    """Download and build data on Unicode confusables/homoglyphs.

    This will download the Unicode confusables dataset and parse it. It will
    extract confusables that can be confused with COMMON or LATIN characters
    (skipping lower codepoints, to avoid issues with, say, "1" and "l"
    appearing in the data), and return a mapping of confusable characters
    to the COMMON/LATIN characters they may be confused with.

    Returns:
        list:
        A list of confusables. Each entry is a tuple in the form of
        ``(confusable, confused_with)``.
    """
    LINE_RE = re.compile(
        r'^(?P<confusable_cp>[0-9A-F ]+) ;\t'
        r'(?P<confused_with_cp>[0-9A-F ]+) ;.*',
        re.UNICODE)

    confusables = []

    for info in _load_data(CONFUSABLES_URL, LINE_RE):
        # Parse and check the character that another may be confused with.
        confused_with_cp_strs = info['confused_with_cp'].split(' ')

        if len(confused_with_cp_strs) != 1:
            # We don't care about any confusables with multi-codepoint
            # characters.
            continue

        confused_with_cp = int(confused_with_cp_strs[0], 16)

        # Skip anything that's not confused with a standard ASCII character.
        # We're only concerned with confusing characters that may be in
        # common identifiers.
        if confused_with_cp >= 128:
            continue

        confused_with_alias = get_alias(confused_with_cp)

        # Skip anything that's not confused with a common or latin character.
        if confused_with_alias not in ('COMMON', 'LATIN'):
            continue

        # Parse and check confusable characters.
        confusable_cp_strs = info['confusable_cp'].split(' ')
        assert len(confusable_cp_strs) == 1, confusable_cp_strs

        confusable_cp = int(confusable_cp_strs[0], 16)

        # There are some confusables, like "1" and "l", that will be in
        # this file. Ignore anything that's ASCII. We only want the more
        # exotic characters.
        if confusable_cp < 128:
            continue

        confusables.append((
            confusable_cp,
            chr(confusable_cp),
            chr(confused_with_cp),
        ))

    confusables.sort()

    return confusables


def build_confusables_file():
    """Build the confusables file.

    This will generate :file:`reviewboard/codesafety/_unicode_confusables.py`.
    It will contain a dictionary mapping the confusables that we've decided
    to look for in source code.

    Raises:
        RuntimeError:
            This cannot be run on the current version of Python.
    """
    build_categories()
    confusables = update_confusables()

    filename = os.path.abspath(os.path.join(
        __file__, '..', '..', '..', 'reviewboard', 'codesafety',
        '_unicode_confusables.py'))

    with open(filename, 'w') as fp:
        fp.write('# coding: utf-8\n')
        fp.write('#\n')
        fp.write('# THIS FILE IS AUTOMATICALLY GENERATED!\n')
        fp.write('#\n')
        fp.write('# To update this file, run '
                 './contrib/internal/build-confusables.py\n')
        fp.write('\n')
        fp.write('COMMON_CONFUSABLES_MAP = {\n')

        for codepoint, confusable_char, confused_with_char in confusables:
            fp.write('    %r: %r,  # %X\n' %
                     (confusable_char, confused_with_char, codepoint))

        fp.write('}\n')

    print('Wrote Unicode confusables file: %s' % filename)


if __name__ == '__main__':
    try:
        build_confusables_file()
    except RuntimeError as e:
        sys.stderr.write('%s\n' % e)
        sys.exit(1)
