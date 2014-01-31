from __future__ import unicode_literals

import re


# A list of regular expressions for headers in the source code that we can
# display in collapsed regions of diffs and diff fragments in reviews.
HEADER_REGEXES = {
    '.cs': [
        re.compile(
            r'^\s*((public|private|protected|static)\s+)+'
            r'([a-zA-Z_][a-zA-Z0-9_\.\[\]]*\s+)+?'     # return arguments
            r'[a-zA-Z_][a-zA-Z0-9_]*'                  # method name
            r'\s*\('                                   # signature start
        ),
        re.compile(
            r'^\s*('
            r'(public|static|private|protected|internal|abstract|partial)'
            r'\s+)*'
            r'(class|struct)\s+([A-Za-z0-9_])+'
        ),
    ],

    # This can match C/C++/Objective C header files
    '.c': [
        re.compile(r'^@(interface|implementation|class|protocol)'),
        re.compile(r'^[A-Za-z0-9$_]'),
    ],
    '.java': [
        re.compile(
            r'^\s*((public|private|protected|static)\s+)+'
            r'([a-zA-Z_][a-zA-Z0-9_\.\[\]]*\s+)+?'     # return arguments
            r'[a-zA-Z_][a-zA-Z0-9_]*'                  # method name
            r'\s*\('                                   # signature start
        ),
        re.compile(
            r'^\s*('
            r'(public|static|private|protected)'
            r'\s+)*'
            r'(class|struct)\s+([A-Za-z0-9_])+'
        ),
    ],
    '.js': [
        re.compile(r'^\s*function [A-Za-z0-9_]+\s*\('),
        re.compile(r'^\s*(var\s+)?[A-Za-z0-9_]+\s*[=:]\s*function\s*\('),
    ],
    '.m': [
        re.compile(r'^@(interface|implementation|class|protocol)'),
        re.compile(r'^[-+]\s+\([^\)]+\)\s+[A-Za-z0-9_]+[^;]*$'),
        re.compile(r'^[A-Za-z0-9$_]'),
    ],
    '.php': [
        re.compile(r'^\s*(public|private|protected)?\s*'
                   r'(class|function) [A-Za-z0-9_]+'),
    ],
    '.pl': [
        re.compile(r'^\s*sub [A-Za-z0-9_]+'),
    ],
    '.py': [
        re.compile(r'^\s*(def|class) [A-Za-z0-9_]+\s*\(?'),
    ],
    '.rb': [
        re.compile(r'^\s*(def|class) [A-Za-z0-9_]+\s*\(?'),
    ],
}

HEADER_REGEX_ALIASES = {
    # C/C++/Objective-C
    '.cc': '.c',
    '.cpp': '.c',
    '.cxx': '.c',
    '.c++': '.c',
    '.h': '.c',
    '.hh': '.c',
    '.hpp': '.c',
    '.hxx': '.c',
    '.h++': '.c',
    '.C': '.c',
    '.H': '.c',
    '.mm': '.m',

    # Perl
    '.pm': '.pl',

    # Python
    'SConstruct': '.py',
    'SConscript': '.py',
    '.pyw': '.py',
    '.sc': '.py',

    # Ruby
    'Rakefile': '.rb',
    '.rbw': '.rb',
    '.rake': '.rb',
    '.gemspec': '.rb',
    '.rbx': '.rb',
}
