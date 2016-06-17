from __future__ import unicode_literals

from django.core.urlresolvers import NoReverseMatch, reverse


def local_site_reverse(viewname, request=None, local_site_name=None,
                       local_site=None, args=None, kwargs=None,
                       *func_args, **func_kwargs):
    """Reverse a URL name and return a working URL.

    This works much like Django's :py:func:`~django.core.urlresolvers.reverse`,
    but handles returning a LocalSite version of a URL when invoked with one of
    the following:

    * A ``request`` argument, representing an HTTP request to a URL within a
      LocalSite.
    * A ``local_site_name`` argument, indicating the name of the local site.
    * A ``local_site`` argument.

    Args:
        viewname (unicode):
            The name of the view to generate a URL for.

        request (django.http.HttpRequest, optional):
            The current HTTP request. The current local site can be extracted
            from this.

        local_site_name (unicode, optional):
            The name of the local site.

        local_site (reviewboard.site.models.LocalSite, optional):
            The local site.

        args (list, optional):
            Positional arguments to use for reversing in
            :py:func:`~django.core.urlresolvers.reverse`.

        kwargs (dict, optional):
            Keyword arguments to use for reversing in
             :py:func:`~django.core.urlresolvers.reverse`.

        func_args (tuple, optional):
            Additional positional arguments to pass to
            :py:func:`~django.core.urlresolvers.reverse`.

        func_kwargs (dict, optional):
            Additional keyword arguments to pass to
            :py:func:`~django.core.urlresolvers.reverse`.

    Returns:
        unicode:
        The reversed URL.

    Raises:
        django.core.urlresolvers.NoReverseMatch:
            Raised when there is no URL matching the view and arguments.
    """
    assert not (local_site_name and local_site)

    if request or local_site_name or local_site:
        if local_site:
            local_site_name = local_site.name
        elif request and not local_site_name:
            local_site_name = getattr(request, '_local_site_name', None)

        if local_site_name:
            if args:
                new_args = [local_site_name] + list(args)
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
