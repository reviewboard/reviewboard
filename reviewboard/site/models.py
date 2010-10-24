#
# models.py -- Models for the "reviewboard.site" app.
#
# Copyright (c) 2010  David Trowbridge
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
#

from django.contrib.auth.models import User
from django.db import models
from django.utils.translation import ugettext_lazy as _


class LocalSite(models.Model):
    """
    A division within a Review Board installation.

    This allows the creation of independent, isolated divisions within a given
    server. Users can be designated as members of a LocalSite, and optionally
    as admins (which allows them to manipulate the repositories, groups and
    users in the site).

    Pretty much every other model in this module can all be assigned to a single
    LocalSite, at which point only members will be able to see or manipulate
    these objects. Access control is performed at every level, and consistency
    is enforced through a liberal sprinkling of assertions and unit tests.
    """
    name = models.SlugField(_('name'), max_length=32, blank=False, unique=True)
    users = models.ManyToManyField(User, blank=True,
                                   related_name='localsite')
    admins = models.ManyToManyField(User, blank=True,
                                   related_name='localsite_admins')
    next_id = models.IntegerField(_('next review request ID'), default=1)
