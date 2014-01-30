====================
Diff Viewer Settings
====================

The Diff Viewer Settings page contains several customization options for the
diff viewer. These settings generally don't need to be changed unless you have
specified requirements for your server. It's split up into the following
sections:

* `General`_
* `Advanced`_


General
=======

* **Show syntax highlighting:**
    If enabled, syntax highlighting will be used in the Diff Viewer. This
    offers improved readability of diffs, but takes longer to render.

    This option can be overridden by users in their account settings.

    Note that syntax highlighting may be needed for some more advanced
    features, so disabling it can reduce the functionality of the diff
    viewer.

    This defaults to being enabled.

* **Syntax highlighting threshold:**
    This can be used to limit syntax highlighting for very large files. If
    this isn't blank or ``0``, then syntax highlighting will only be enabled
    for files with at most this many lines.

    This defaults to being blank.

* **Show trailing whitespace:**
    If enabled, excess whitespace on a line is shown as red blocks. This
    helps to visualize when a text editor has added unwanted whitespace to the
    end of a line.

    This defaults to being enabled.

* **Show all whitespace for:**
    This is a comma-separated list of file patterns for which all whitespace
    changes should be shown.

    Normally, whitespace-only changes are ignored in a diff, improving
    readability and allowing developers to concentrate on actual code changes.
    However, for some file formats, this isn't desired. These file patterns
    can be listed here.

    For example: ``*.py, *.txt``


Advanced
========

* **Max diff size:**
    The maximum size of an uploaded diff (in bytes).

    Any diffs larger than this will be rejected during upload. This can be
    used to lighten the load on the server.

    Specify 0 to allow diffs of any size.

    This defaults to 0.

* **Lines of Context:**
    The number of unchanged lines shown above and below changed lines.

    This defaults to 5.

* **Paginate by:**
    The number of files to display per page in the diff viewer.

    This defaults to 20.

* **Paginate orphans:**
    The number of extra files required before adding another page to the
    diff viewer. If, for example, a diff consisted of 25 files, and
    this was set to 10, then the files would be shortened into two pages.

    This defaults to 10.
