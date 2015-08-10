#
# djblets_images.py -- Image-related template tags
#
# Copyright (c) 2007-2009  Christian Hammond
# Copyright (c) 2007-2009  David Trowbridge
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

import logging
import os
import tempfile

from django import template
from django.core.files import File
from django.utils.six.moves import cStringIO as StringIO
try:
    from PIL import Image
except ImportError:
    import Image


register = template.Library()


def save_image_to_storage(image, storage, filename):
    """Save an image to storage."""
    (fd, tmp) = tempfile.mkstemp()
    file = os.fdopen(fd, 'w+b')
    image.save(file, 'png')
    file.close()

    file = File(open(tmp, 'rb'))
    storage.save(filename, file)
    file.close()

    os.unlink(tmp)


@register.simple_tag
def crop_image(file, x, y, width, height):
    """
    Crops an image at the specified coordinates and dimensions, returning the
    resulting URL of the cropped image.
    """
    filename = file.name
    storage = file.storage
    basename = filename

    if filename.find(".") != -1:
        basename = filename.rsplit('.', 1)[0]
    new_name = '%s_%d_%d_%d_%d.png' % (basename, x, y, width, height)

    if not storage.exists(new_name):
        try:
            file = storage.open(filename)
            data = StringIO(file.read())
            file.close()

            image = Image.open(data)
            image = image.crop((x, y, x + width, y + height))

            save_image_to_storage(image, storage, new_name)
        except (IOError, KeyError) as e:
            logging.error('Error cropping image file %s at %d, %d, %d, %d '
                          'and saving as %s: %s' %
                          (filename, x, y, width, height, new_name, e),
                          exc_info=1)
            return ""

    return storage.url(new_name)


# From http://www.djangosnippets.org/snippets/192
@register.filter
def thumbnail(file, size='400x100'):
    """
    Creates a thumbnail of an image with the specified size, returning
    the URL of the thumbnail.
    """
    x, y = [int(x) for x in size.split('x')]

    filename = file.name
    if filename.find(".") != -1:
        basename, format = filename.rsplit('.', 1)
        miniature = '%s_%s.%s' % (basename, size, format)
    else:
        basename = filename
        miniature = '%s_%s' % (basename, size)

    storage = file.storage

    if not storage.exists(miniature):
        try:
            file = storage.open(filename, 'rb')
            data = StringIO(file.read())
            file.close()

            image = Image.open(data)
            image.thumbnail([x, y], Image.ANTIALIAS)

            save_image_to_storage(image, storage, miniature)
        except (IOError, KeyError) as e:
            logging.error('Error thumbnailing image file %s and saving '
                          'as %s: %s' % (filename, miniature, e),
                          exc_info=1)
            return ""

    return storage.url(miniature)
