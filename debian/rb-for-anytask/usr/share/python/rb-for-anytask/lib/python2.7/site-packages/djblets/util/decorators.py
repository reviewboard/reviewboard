#
# decorators.py -- Miscellaneous, useful decorators.  This might end up moving
#                  to something with a different name.
#
# Copyright (c) 2007  David Trowbridge
# Copyright (c) 2007  Christian Hammond
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
from functools import update_wrapper
from inspect import getargspec
import warnings

from django import template
from django.conf import settings
from django.template import TemplateSyntaxError, Variable


# The decorator decorator.  This is copyright unknown, verbatim from
# http://wiki.python.org/moin/PythonDecoratorLibrary
def simple_decorator(decorator):
    """This decorator can be used to turn simple functions
       into well-behaved decorators, so long as the decorators
       are fairly simple. If a decorator expects a function and
       returns a function (no descriptors), and if it doesn't
       modify function attributes or docstring, then it is
       eligible to use this. Simply apply @simple_decorator to
       your decorator and it will automatically preserve the
       docstring and function attributes of functions to which
       it is applied."""
    def new_decorator(f):
        g = decorator(f)
        g.__name__ = f.__name__
        g.__doc__ = f.__doc__
        g.__dict__.update(f.__dict__)
        return g
    # Now a few lines needed to make simple_decorator itself
    # be a well-behaved decorator.
    new_decorator.__name__ = decorator.__name__
    new_decorator.__doc__ = decorator.__doc__
    new_decorator.__dict__.update(decorator.__dict__)
    return new_decorator


def augment_method_from(klass):
    """Augments a class's method with new decorators or documentation.

    This is useful when a class needs to add new decorators or new
    documentation to a parent class's method, without changing the behavior
    or burying the existing decorators.

    The methods using this decorator can provide code to run at the end of
    the parent function. Usually, though, it will just have an empty body
    of ``pass``.
    """
    def _dec(func):
        def _call(*args, **kwargs):
            try:
                f = augmented_func(*args, **kwargs)
            finally:
                func(*args, **kwargs)

            return f

        augmented_func = getattr(klass, func.__name__)

        _call.__name__ = func.__name__
        _call.__doc__ = func.__doc__ or augmented_func.__doc__
        _call.__dict__.update(augmented_func.__dict__)
        _call.__dict__.update(func.__dict__)

        real_func = _call.__dict__.get('_augmented_func', augmented_func)
        _call.__dict__['_augmented_func'] = real_func

        return _call

    return _dec


def basictag(takes_context=False):
    """
    A decorator similar to Django's @register.simple_tag that optionally
    takes a context parameter. This condenses many tag implementations down
    to a few lines of code.

    Example:
        @register.tag
        @basictag(takes_context=True)
        def printuser(context):
            return context['user']
    """
    class BasicTagNode(template.Node):
        def __init__(self, take_context, tag_name, tag_func, args):
            self.takes_context = takes_context
            self.tag_name = tag_name
            self.tag_func = tag_func
            self.args = args

        def render(self, context):
            args = [Variable(var).resolve(context) for var in self.args]

            if self.takes_context:
                return self.tag_func(context, *args)
            else:
                return self.tag_func(*args)

    def basictag_func(tag_func):
        def _setup_tag(parser, token):
            bits = token.split_contents()
            tag_name = bits[0]
            del(bits[0])

            params, xx, xxx, defaults = getargspec(tag_func)
            max_args = len(params)

            if takes_context:
                if params[0] == 'context':
                    max_args -= 1  # Ignore context
                else:
                    raise TemplateSyntaxError(
                        "Any tag function decorated with takes_context=True "
                        "must have a first argument of 'context'")

            min_args = max_args - len(defaults or [])

            if not min_args <= len(bits) <= max_args:
                if min_args == max_args:
                    raise TemplateSyntaxError(
                        "%r tag takes %d arguments." % (tag_name, min_args))
                else:
                    raise TemplateSyntaxError(
                        "%r tag takes %d to %d arguments, got %d." %
                        (tag_name, min_args, max_args, len(bits)))

            return BasicTagNode(takes_context, tag_name, tag_func, bits)

        _setup_tag.__name__ = tag_func.__name__
        _setup_tag.__doc__ = tag_func.__doc__
        _setup_tag.__dict__.update(tag_func.__dict__)
        return _setup_tag

    return basictag_func


def blocktag(*args, **kwargs):
    """Creates a block template tag with beginning/end tags.

    This does all the hard work of creating a template tag that can
    parse the arguments passed in and then parse all nodes between a
    beginning and end tag (such as myblock/endmyblock).

    By default, the end tag is prefixed with "end", but that can be
    changed by passing `end_prefix="end_"` or similar to @blocktag.

    blocktag will call the wrapped function with `context`  and `nodelist`
    parameters, as well as any parameters passed to the tag. It will
    also ensure that a proper error is raised if too many or too few
    parameters are passed.

    For example:

        @register.tag
        @blocktag
        def divify(context, nodelist, div_id=None):
            s = "<div"

            if div_id:
                s += " id='%s'" % div_id

            return s + ">" + nodelist.render(context) + "</div>"
    """
    class BlockTagNode(template.Node):
        def __init__(self, tag_name, tag_func, nodelist, args):
            self.tag_name = tag_name
            self.tag_func = tag_func
            self.nodelist = nodelist
            self.args = args

        def render(self, context):
            args = [Variable(var).resolve(context) for var in self.args]
            return self.tag_func(context, self.nodelist, *args)

    def _blocktag_func(tag_func):
        def _setup_tag(parser, token):
            bits = token.split_contents()
            tag_name = bits[0]
            del(bits[0])

            params, xx, xxx, defaults = getargspec(tag_func)
            max_args = len(params) - 2  # Ignore context and nodelist
            min_args = max_args - len(defaults or [])

            if not min_args <= len(bits) <= max_args:
                if min_args == max_args:
                    raise TemplateSyntaxError(
                        "%r tag takes %d arguments." % (tag_name, min_args))
                else:
                    raise TemplateSyntaxError(
                        "%r tag takes %d to %d arguments, got %d." %
                        (tag_name, min_args, max_args, len(bits)))

            nodelist = parser.parse((('%s%s' % (end_prefix, tag_name)),))
            parser.delete_first_token()
            return BlockTagNode(tag_name, tag_func, nodelist, bits)

        update_wrapper(_setup_tag, tag_func)

        return _setup_tag

    end_prefix = kwargs.get('end_prefix', 'end')

    if len(args) == 1 and callable(args[0]):
        # This is being called in the @blocktag form.
        return _blocktag_func(args[0])
    else:
        # This is being called in the @blocktag(...) form.
        return _blocktag_func


@simple_decorator
def root_url(url_func):
    """Decorates a function that returns a URL to add the SITE_ROOT."""
    def _add_root(*args, **kwargs):
        url = url_func(*args, **kwargs)

        if url[0] != '/':
            raise ValueError('Returned URL is not absolute')

        if hasattr(settings, 'SITE_ROOT'):
            return '%s%s' % (settings.SITE_ROOT, url[1:])
        else:
            return url

    warnings.warn('djblets.util.decorators.root_url is deprecated.',
                  DeprecationWarning)

    return _add_root
