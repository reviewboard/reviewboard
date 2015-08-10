from django.conf import settings

from djblets.util.decorators import simple_decorator


@simple_decorator
def add_root_url(url_func):
    """Decorates a function that returns a URL to add the SITE_ROOT."""
    def _add_root(*args, **kwargs):
        url = url_func(*args, **kwargs)

        if url[0] != '/':
            raise ValueError('Returned URL is not absolute')

        if hasattr(settings, 'SITE_ROOT'):
            return '%s%s' % (settings.SITE_ROOT, url[1:])
        else:
            return url

    return _add_root
