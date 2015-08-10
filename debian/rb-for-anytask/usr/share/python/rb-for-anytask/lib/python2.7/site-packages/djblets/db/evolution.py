#
# dbevolution.py -- Helpers for database evolutions
#
# Copyright (c) 2008-2009  Christian Hammond
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

from __future__ import unicode_literals

from django_evolution.mutations import BaseMutation


class FakeChangeFieldType(BaseMutation):
    """
    Changes the type of the field to a similar type.
    This is intended only when the new type is really a version of the
    old type, such as a subclass of that Field object. The two fields
    should be compatible or there could be migration issues.
    """
    def __init__(self, model_name, field_name, new_type):
        self.model_name = model_name
        self.field_name = field_name
        self.new_type = new_type

    def __repr__(self):
        return "FakeChangeFieldType('%s', '%s', '%s')" % \
            (self.model_name, self.field_name, self.new_type)

    def simulate(self, app_label, proj_sig):
        app_sig = proj_sig[app_label]
        model_sig = app_sig[self.model_name]
        field_dict = model_sig['fields']
        field_sig = field_dict[self.field_name]

        field_sig['field_type'] = self.new_type

    def mutate(self, app_label, proj_sig):
        # We can just call simulate, since it does the same thing.
        # We're not actually generating SQL, but rather tricking
        # Django Evolution.
        self.simulate(app_label, proj_sig)
        return ""
