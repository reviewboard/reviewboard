from __future__ import unicode_literals

from django.conf import settings


def media_serial(request):
    """
    Exposes a media serial number that can be appended to a media filename
    in order to make a URL that can be cached forever without fear of change.
    The next time the file is updated and the server is restarted, a new
    path will be accessed and cached.

    This returns the value of settings.MEDIA_SERIAL, which must either be
    set manually or ideally should be set to the value of
    djblets.cache.serials.generate_media_serial().
    """
    return {'MEDIA_SERIAL': getattr(settings, "MEDIA_SERIAL", "")}


def ajax_serial(request):
    """
    Exposes a serial number that can be appended to filenames involving
    dynamic loads of URLs in order to make a URL that can be cached forever
    without fear of change.

    This returns the value of settings.AJAX_SERIAL, which must either be
    set manually or ideally should be set to the value of
    djblets.cache.serials.generate_ajax_serial().
    """
    return {'AJAX_SERIAL': getattr(settings, "AJAX_SERIAL", "")}
