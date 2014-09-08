from __future__ import unicode_literals

from django.core.urlresolvers import NoReverseMatch, reverse


def local_site_reverse(viewname, request=None, local_site_name=None,
                       local_site=None, args=None, kwargs=None,
                       *func_args, **func_kwargs):
    """Reverses a URL name, returning a working URL.

    This works much like Django's reverse(), but handles returning a
    localsite version of a URL when invoked with a request within a localsite.
    """
    assert not (local_site_name and local_site)

    if request or local_site_name or local_site:
        if local_site:
            local_site_name = local_site.name
        elif request and not local_site_name:
            local_site_name = getattr(request, '_local_site_name', None)

        if local_site_name:
            if args:
                new_args = [local_site_name] + args
                new_kwargs = kwargs
            else:
                new_args = args
                new_kwargs = {
                    'local_site_name': local_site_name,
                }

                if kwargs:
                    new_kwargs.update(kwargs)

            try:
                return reverse(viewname, args=new_args, kwargs=new_kwargs,
                               *func_args, **func_kwargs)
            except NoReverseMatch:
                # We'll try it again without those arguments.
                pass

    return reverse(viewname, args=args, kwargs=kwargs,
                   *func_args, **func_kwargs)
