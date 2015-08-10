#
# loaders.py -- Loaders for extension data.
#
# Copyright (c) 2010-2011  Beanbag, Inc.
# Copyright (c) 2008-2010  Christian Hammond
#
# Permission is hereby granted, free of charge, to any person obtaining
# a copy of this software and associated documentation files (the
# "Software"), to deal in the Software without restriction, including
# without limitation the rights to use, copy, modify, merge, publish,
# distribute, sublicense, and/or sell copies of the Software, and to
# permit persons to whom the Software is furnished to do so, subject to
# the following conditions:
#
# The above copyright notice and this permission notice shall be included
# in all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
# EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
# MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT.
# IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY
# CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT,
# TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE
# SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

from __future__ import unicode_literals

from django.template import TemplateDoesNotExist
from pkg_resources import _manager as manager

from djblets.extensions.manager import get_extension_managers


def load_template_source(template_name, template_dirs=None):
    """Loads templates from enabled extensions."""
    if manager:
        resource = "templates/" + template_name

        for extmgr in get_extension_managers():
            for ext in extmgr.get_enabled_extensions():
                package = ext.info.app_name

                try:
                    return (manager.resource_string(package, resource),
                            'extension:%s:%s ' % (package, resource))
                except Exception:
                    pass

    raise TemplateDoesNotExist(template_name)

load_template_source.is_usable = manager is not None
